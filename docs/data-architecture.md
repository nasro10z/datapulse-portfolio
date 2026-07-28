# DataPulse — Architecture des données

Plan de stockage et d'intégration des données, historiques **et** temps réel.
Objectif de conception : **ne jamais mélanger la donnée (stockage) avec le
pipeline (ETL) ni avec les maths (ML)**, pour que chaque brique évolue seule.

Sert de source de vérité pour la Phase 8 (branchement du pipeline réel). Décisions
prises en session : stockage analytique **SQLite**, API qui **lit du gold
précalculé**, état applicatif **SQLite** (inchangé).

---

## 1. Principe directeur — trois responsabilités séparées

DataPulse sépare **trois** rôles, reliés par des contrats de schéma et jamais par
des accès croisés :

```
   SOURCE (PG, RO)          STOCKAGE ANALYTIQUE          API / SERVICES
  ┌───────────────┐        ┌────────────────────┐      ┌──────────────┐
  │ temp_humidity │        │  bronze (brut)     │      │  providers   │
  │ scada_logs    │──lit──▶│  silver (nettoyé)  │─lit─▶│  (live)      │
  │ ups_events    │        │  gold   (servi)    │      │  → Pydantic  │
  └───────────────┘        └────────────────────┘      └──────────────┘
          ▲                    ▲   écrit   │                    │
          │                    │           │                    │
       ┌──┴────────────────────┴───────────▼──┐        ┌────────▼───────┐
       │              ETL  (etl/)             │        │  ÉTAT APP      │
       │   orchestration + I/O (lit/écrit)   │        │  (SQLite)      │
       │   appelle ─▶  ml/  (maths pures)    │        │  actions user  │
       └──────────────────────────────────────┘        └────────────────┘
```

| Brique | Responsabilité | Ne fait **pas** |
|---|---|---|
| **`storage/`** | persistance pure : tables + repositories (DAO) | aucune logique métier, aucun pandas, aucun modèle |
| **`etl/`** | orchestration + I/O : lit bronze, appelle `ml/`, écrit silver/gold | ne connaît pas les maths ; ne dépend pas de l'API |
| **`ml/`** | les maths **validées** (préprocessing, hystérésis, forecast) sur DataFrames | aucune I/O, aucun accès DB |
| **`api/`** | expose le REST ; lit **uniquement** le gold via un repository | ne fait **jamais** tourner le pipeline |

**Garantie de maintenabilité** : changer la techno de stockage n'impacte que
`storage/` ; changer la logique ML n'impacte que `ml/` ; l'API ignore les deux.

---

## 2. Les trois couches (medallion)

Vocabulaire *medallion* (raffinage progressif du brut vers le prêt-à-servir).

| Couche | En clair | Contenu | Écrite par | Recalculable ? |
|---|---|---|---|---|
| **bronze** | le brut | copie append-only de la source + ingestion temps réel, telle quelle (doublons/trous inclus) | `etl/ingest` | non — c'est la vérité |
| **silver** | le nettoyé | sortie du préprocessing validé : dédup, gaps >125s classés, segments, rolling stats | `etl/transform` | oui (depuis bronze) |
| **gold** | le prêt-à-servir | résultat métier = ce que l'API renvoie : épisodes, scores, forecast, labels de validation | `etl/detect,score,forecast` | oui (depuis silver) |

Exemple d'un même point qui descend les couches :

| Couche | Donnée |
|---|---|
| bronze | `2026-07-01 10:00:00 · SALLE_SWITCH · 28.9°C · hum=NaN` (brut) |
| silver | même point dédupliqué · `segment_id=1450` · `rolling_mean_36=27.2` |
| gold | `EP-0031 · STULZ-03 · critical · start 10:00 · durée 42min · pic 30.8°C` |

**Point clé** : le schéma **gold = les modèles Pydantic déjà écrits**
(`AnomalyEpisode`, `HealthOverview`, `ForecastResponse`). L'API fait un `SELECT`
dans gold et renvoie le modèle, sans transformation.

---

## 3. Stockage physique — trois fichiers SQLite, un écrivain chacun

SQLite est adapté à l'échelle du projet (≈107k lignes historiques, ~720 points/jour
en temps réel, **un seul écrivain par fichier**). La séparation des fichiers est
ce qui empêche le mélange data ↔ ETL ↔ app.

| Fichier | Contenu | Écrit par | Lu par | Statut |
|---|---|---|---|---|
| **exports CSV** des tables (temp_humidity, scada_logs, ups_events) | données data center | fournis (PG `datacenter_ops` non joignable) | `etl/ingest` | fournis |
| `datapulse_analytics.db` | bronze + silver + gold | **l'ETL uniquement** | l'API (gold), l'ETL (bronze/silver) | **à créer** |
| `datapulse.db` | état app (PM, actions user) | **l'API uniquement** | l'API | existe |

> Migration future sans douleur : si le temps réel monte en charge, on remplace
> `datapulse_analytics.db` par une base PostgreSQL **sans toucher** à `etl/` ni à
> l'API — tout passe par les repositories (§5). Le WAL SQLite est activé pour la
> lecture concurrente pendant l'écriture ETL.

Configuration (`config.py` / `.env`) :

```
ANALYTICS_DB_PATH=backend/data/datapulse_analytics.db   # défaut
APP_DB_PATH=backend/data/datapulse.db                   # existant
DATA_SOURCE=mock                                         # existant (mock|live)
```

---

## 4. Batch et temps réel — un seul pipeline, deux déclencheurs

Pas deux mondes parallèles : **un** code de transformation, deux façons de le
déclencher (approche Kappa).

### Historique (backfill) — one-shot
```
lit source (fenêtre complète) → bronze → transform → detect/score/forecast → gold
```
Lancé une fois pour charger l'existant.

### Temps réel (incrémental) — sur intervalle
```
lit source WHERE ts > watermark → append bronze
  → recalcule les SEGMENTS TOUCHÉS (pas tout) → met à jour gold
```
- **Watermark** par table source, persisté dans `storage` (dernier `ts` ingéré).
- **Idempotence** : upsert par clé naturelle `(ts, sensor)` en bronze → réexécuter
  un cycle ne duplique rien.
- **Donnée en retard / désordonnée** : la segmentation se faisant par `cumsum`
  sur les gaps, un point tardif peut fusionner/scinder un segment → on **recompute
  le segment local**, pas toute l'histoire.

L'orchestration (ordre des étapes, watermark, idempotence) vit dans `etl/run.py`.
Déclenchement : au démarrage FastAPI (lifespan) + job périodique
(`asyncio`/`BackgroundTasks` pour la démo ; un vrai scheduler type cron/APScheduler
en production).

---

## 5. Le contrat storage ↔ ETL ↔ API : les repositories

Chaque couche est atteinte par un **repository** (DAO) : la seule surface publique
du stockage. C'est le contrat stable.

```
storage/repositories/
  bronze_repo.py   # append_temp_humidity(df), get_since(ts), get_watermark(table), set_watermark(...)
  silver_repo.py   # upsert_segments(df), upsert_rolling(df), get_segment(id), get_window(from,to)
  gold_repo.py     # replace_episodes(list), get_episodes(), upsert_health(...), get_overview(), ...
```

- `etl/` lit/écrit **uniquement** via ces repos → il ne connaît pas le SQL ni le
  fichier.
- `providers.py` (mode `live`) lit **uniquement** `gold_repo` → renvoie les modèles
  Pydantic. Les stubs `ml/anomalies.py` / `ml/health.py` deviennent de simples
  lectures gold (plus de `NotImplementedError`).
- La couche de service existante (`services/anomaly_aggregation.py` : stats,
  histogramme, filtres, surcharge de statut) reste **inchangée** — elle opère sur
  la liste d'épisodes quelle qu'en soit la source.

---

## 6. Structure repo cible

```
backend/app/
  storage/                    # NOUVEAU — persistance pure
    analytics_db.py           #   engine/session SQLite analytique (URL.create(), WAL)
    schema/
      bronze.py silver.py gold.py
    repositories/
      bronze_repo.py silver_repo.py gold_repo.py
    migrations/               #   alembic (évolution des schémas)
  etl/                        # NOUVEAU — orchestration + I/O
    ingest/
      backfill.py             #   source → bronze (historique, one-shot)
      incremental.py          #   source → bronze (temps réel, watermark)
    transform.py              #   bronze → silver   (appelle ml.preprocessing)
    detect.py                 #   silver → gold     (appelle ml.detection)
    forecast.py  score.py     #   silver → gold
    run.py                    #   orchestration : ordre, watermark, idempotence
  ml/                         #   maths pures (package mlops-api en librairie) — AUCUNE I/O
    preprocessing.py detection.py forecasting.py scoring.py
  db/
    engine.py                 #   base SOURCE PostgreSQL — non utilisée (PG non joignable)
    app_db.py                 #   base ÉTAT APP SQLite — INCHANGÉ
    # queries.py → obsolète (lecture PG) ; l'ingestion réelle lit des CSV dans etl/ingest
  providers.py                #   live → lit gold_repo (au lieu d'appeler le pipeline)
  api/ models/ services/      #   INCHANGÉS
```

> La source étant fournie en **CSV** (PG non joignable), `etl/ingest/` lit les
> fichiers CSV (les loaders du package `mlops-api`, `data_loading.py`, font déjà
> ce travail). `db/queries.py` (lecture PG) devient obsolète ; `db/` ne garde que
> la **connexion** à l'état app SQLite.

---

## 7. Ce que ça débloque

1. **`DATA_SOURCE=live` renvoie du vrai** : `providers` lit gold, plus de 501.
2. **Santé du site se rebranche** sur `/api/health/overview` sans effort — `gold`
   porte les scores, la page redevient réactive au pipeline (aujourd'hui elle lit
   des constantes de design ; cf. `siteHealthData.js`).

---

## 8. Le pipeline validé livré : package `mlops-api` (intégré en librairie)

La société data science a livré le pipeline validé sous forme d'un **package
Python autonome** (`mlops-api`), sorti du notebook Databricks. **Décision prise :
on l'intègre comme librairie** (`pip install -e`), pas comme microservice — un
seul service à déployer, appels en process, alignés sur `storage/etl/ml`. Sa
couche `api/` FastAPI et son Docker ne sont **pas** réutilisés (DataPulse a déjà
son API).

**Ce qu'il apporte :**

| Élément livré | Où il atterrit chez nous | Note |
|---|---|---|
| `src/environmental/` (HMM temp/humidité) + `src/alarm_anomaly/` (IsolationForest alarmes SCADA) | notre `ml/` (fonctions pures, réutilisées telles quelles) | ne pas réécrire |
| `models/*/*.joblib` + `metadata.json` + `thresholds.json` | artefacts chargés au démarrage | env : F1=0.83 ; alarm : 720 events |
| `preprocessing.py` (segments 125 s, rolling 12/36/78, Tukey, hystérésis) | `ml/` | = pipeline CLAUDE.md confirmé |
| `datapulse.db` (`temp_humid_last`, 107 060 lignes) + CSV | seed du **bronze** temp/humidité | données historiques présentes |

**Modèles = prédicteurs point-par-point, pas producteurs d'épisodes.**
`EnvironmentalPredictor.predict_one({ts,temp,hum})` et
`AnomalyPredictor.predict_one(features_event)` renvoient un `is_anomaly`/`score`
par lecture/événement. Le passage **points anormaux → `AnomalyEpisode` (gold)**
est le rôle de `etl/detect.py` (déroulé sur l'historique + regroupement). Le
buffer en RAM de `EnvironmentalPredictor` est remplacé par la lecture du bronze.

**Décisions arrêtées & réconciliation :**
- **Granularité : par salle** (décidé). Les épisodes `environmental` sont attribués
  à la salle (capteur SALLE_SWITCH), pas aux STULZ-01..10. `alarm_anomaly` reste au
  niveau *événement SCADA* avec catégorie (UPS/CLIM/ENERGY) — **nouvelle capacité**,
  absente des mocks actuels.
- **Seuils : 26.75 / 28.65** (décidé — valeurs livrées `thresholds.json`, split
  train). Constante `mocks/equipment.py` + docs déjà alignées.
- **Données SCADA brutes** (`logs_msc10.csv`, `ALARMES SCADA 2022.xlsx`,
  `ups_clean.csv`) : **fournies** → `alarm_anomaly` réentraînable + backfill possible.

---

## 9. Feuille de route d'implémentation (non-cassante, mock reste défaut)

| Étape | Livrable | Dépend de | Statut |
|---|---|---|---|
| A | `storage/` : `analytics_db.py` + schémas bronze/silver/gold + repositories (testable à vide) | — | prêt à démarrer |
| B | `ml/` : intégrer le package `mlops-api` en librairie (fonctions + artefacts) | package livré | **débloqué** (livré) |
| C | `etl/ingest` : seed bronze depuis `datapulse.db`/CSV (temp/hum) ; `db/queries.py` → `etl/ingest` pour la source PG | données temp/hum **présentes** ; SCADA brut + PG à obtenir | partiel |
| D | `etl/transform` (bronze→silver) en réutilisant `preprocessing.py` du package | A, B, C | — |
| E | `etl/detect` : dérouler les prédicteurs → **regrouper en `AnomalyEpisode`** → gold | B, D | mapping à écrire |
| F | `etl/score,forecast` : `gold.health_scores` + `gold.forecast_points` | D, E | scoring composite à définir |
| G | `providers` live → `gold_repo` ; retrait des stubs `NotImplementedError` | A, E, F | — |
| H | `etl/incremental` + watermark + job périodique (temps réel) | D–F | différé |
| I | Rebranchement Santé du site sur l'API | G | — |

**Bloquant restant** (le pipeline **et** les données sont fournis) :
- **Flux temps réel** : pas de source live (PG non joignable) → l'incrémental (H)
  attend qu'un flux ou des exports CSV réguliers soient mis en place. L'historique
  (backfill sur CSV) fonctionne dès maintenant.

Les étapes **A → G + I** peuvent démarrer : package livré, données temp/humidité
(107k lignes) + CSV SCADA fournis.
