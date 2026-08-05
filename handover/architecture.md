# DataPulse — Architecture technique (handover)

> Complète [`project-overview.md`](project-overview.md) (contexte produit) avec le détail technique frontend / backend / stockage.

## 1. Vue d'ensemble

```
┌─────────────┐      HTTP/JSON       ┌──────────────────────┐      lit gold      ┌────────────────────┐
│  Frontend    │ ───────────────────▶ │  Backend FastAPI      │ ─────────────────▶ │  Stockage           │
│  React/Vite  │ ◀─────────────────── │  (routes → services)  │                    │  SQLite (2 bases)   │
└─────────────┘      /api/*          └──────────────────────┘ ◀───────────────── └────────────────────┘
                                                │  écrit                                    ▲
                                                ▼                                            │
                                        ┌──────────────┐      appelle (maths pures)   ┌──────┴───────┐
                                        │  etl/          │ ─────────────────────────▶ │  ml/            │
                                        │  orchestration │                            │  (mlops-api)    │
                                        └──────────────┘                            └────────────────┘
```

Trois responsabilités **jamais mélangées** :
- `storage/` = persistance pure, aucune logique métier
- `etl/` = orchestration + I/O, ne connaît pas les maths
- `ml/` = maths validées sur DataFrames, aucune I/O
- `api/` = expose le REST, lit **uniquement** le gold précalculé, ne fait jamais tourner le pipeline

En dev, Vite proxifie `/api` vers `localhost:8000` (pas de CORS à gérer manuellement en local ; CORS quand même configuré côté FastAPI pour `localhost`/`127.0.0.1`/IP locale sur le port 5173).

---

## 2. Frontend — `frontend/src/`

**Stack** : React 18 + Vite 5/6, Tailwind v4 (utilitaires) + CSS variables (tokens du design system), `react-router-dom`.

```
src/
├── pages/            # 1 fichier par page, brancher sur les hooks/api
│   ├── GlobalView.jsx    # Aperçu — route "/"
│   ├── SiteHealth.jsx     # route "/health"
│   ├── Forecast.jsx
│   ├── Anomalies.jsx
│   ├── Maintenance.jsx
│   └── Reminders.jsx      # pas une route nav — popover cloche, pas une page dédiée
├── components/       # composants réutilisables, sans logique métier propre
│   ├── HealthGauge.jsx      # gauge arc 270°
│   ├── StatusBadge.jsx      # icône + libellé, jamais couleur seule (a11y)
│   ├── EquipmentCard.jsx
│   ├── TrendChart.jsx        # courbe + bande de confiance, crosshair/tooltip
│   ├── AnomalyHistogram.jsx  # histogramme empilé par sévérité, jour/semaine/mois
│   ├── PMCalendar.jsx        # calendrier mensuel navigable
│   ├── KpiCard.jsx, DeltaTag.jsx, DueBadge.jsx, NotificationBell.jsx, Panel.jsx, Logo.jsx
├── layout/AppLayout.jsx   # sidebar + topbar (cloche rappels), tiroir mobile <768px
├── hooks/
│   ├── useApi.jsx    # wrapper fetch → { data, loading, error }, un hook par appel
│   └── useTheme.js   # bascule thème clair/sombre (tokens prêts dès Phase 2)
├── api/client.js     # client HTTP unique — un objet `api.*` par endpoint backend
├── design-system/     # tokens.css (palette, typo, espacements) extraits d'Identity v2
├── constants/, utils/
└── test/                 # setup Vitest + Testing Library
```

**Flux de données côté frontend** : une page appelle un hook `useApi` (ou directement `api.xxx()`) → `api/client.js` fait le `fetch` vers `/api/...` → le composant reçoit `{ data, loading, error }` et rend `Panel`/`Card`/`Chart` génériques. Aucune page ne parle au backend autrement que via `client.js` — c'est le seul endroit qui connaît les routes REST.

**Tests** : Vitest + Testing Library

**Responsive/a11y** : sidebar en tiroir sous 768px (hamburger + backdrop + Échap) ; `:focus-visible`, noms accessibles sur tous les interactifs, contrastes AA vérifiés.

---

## 3. Backend — `backend/app/`

**Stack** : FastAPI, Pydantic (schémas), SQLAlchemy 2.0 (`URL.create()`, jamais psycopg2 direct), pydantic-settings pour la config.

```
app/
├── main.py              # FastAPI app, lifespan (init DB + seed démo), CORS, handler 501
├── config.py            # Settings : DATA_SOURCE (mock|live), chemins DB, CORS
├── providers.py          # aiguillage mock ↔ live — SEUL point que les routes appellent
├── api/                    # routes HTTP par domaine (health, anomalies, maintenance, reminders)
├── models/                # schémas Pydantic (contrats de réponse/requête)
├── services/               # logique métier réutilisable
│   ├── maintenance.py         # calcul date prochaine PM, CRUD planning
│   ├── anomalies.py             # overrides de statut (acquitter/résoudre)
│   ├── anomaly_aggregation.py   # agrégations partagées mock/live (stats, histogramme)
│   └── reminders.py
├── mocks/                # générateurs de données de démo (Phases 1–7), seed si DB vide
├── ml/                     # pipeline ML vendorisé (package mlops-api) — voir §3.2
├── etl/                     # orchestration bronze→silver→gold — voir §4.2
├── storage/               # accès à la base analytique — voir §4.1
└── db/                       # accès à l'état applicatif — voir §4.3
    ├── app_db.py               # engine + sessionmaker SQLite (état appli)
    ├── tables.py                # PMSchedule, AnomalyAction, ReminderAction
    ├── engine.py                 # connexion PostgreSQL source (URL.create(), non branchée)
    └── queries.py
```

### 3.1 Aiguillage mock ↔ live (`providers.py`)

Toutes les routes appellent `providers.py`, jamais `mocks/` ou `ml/` directement. Le choix de la source se fait par la variable d'environnement `DATA_SOURCE` :
- `DATA_SOURCE=mock` → générateurs seedés de `mocks/` (données cohérentes avec les seuils réels, mais synthétiques)
- `DATA_SOURCE=live` → lecture du gold via `ml/health.py` / `ml/anomalies.py`, qui s'appuient sur `storage/repositories/gold_repo.py`

Brancher le pipeline réel est donc un changement de **configuration**, pas une réécriture des routes. Si `DATA_SOURCE=live` et que le gold est vide (ETL pas encore lancé), l'API renvoie un `501` explicite (`NotImplementedError` → handler dédié dans `main.py`) plutôt qu'un 500 opaque.

La logique de surcharge de statut, de filtrage et d'agrégation (ex. histogramme, stats par sévérité) est **partagée** entre mock et live via `services/anomaly_aggregation.py` — elle ne dépend pas de la source des épisodes bruts.

### 3.2 `ml/` — pipeline ML vendorisé (package `mlops-api`)

```
ml/
├── environmental/     # HMM température/humidité — détection d'anomalies environnementales
├── alarm_anomaly/       # IsolationForest sur logs SCADA
├── health_score/         # scoring porté du notebook health_scores.ipynb (maths pures)
├── model_registry.py    # chargement des modèles + metadata.json (métriques livrées)
├── health.py, anomalies.py   # adaptateurs appelés par providers.py côté "live"
└── data/                    # artefacts / fixtures modèle
```

Code livré et déjà validé — **ne pas réécrire**, seulement l'exposer/intégrer proprement. Aucune I/O ici : entrée/sortie = DataFrames, appelé exclusivement par `etl/`.

---

## 4. Stockage — deux bases SQLite séparées, jamais mélangées

| Base | Fichier | Contenu | Qui écrit | Qui lit |
|---|---|---|---|---|
| **Analytique** (bronze/silver/gold) | `storage/analytics_db.py` (chemin configurable) | données du data center transformées | `etl/` uniquement | `ml/health.py`, `ml/anomalies.py` (jamais l'API directement) |
| **État applicatif** | `db/app_db.py` (`backend/data/datapulse.db` par défaut, `APP_DB_PATH`) | ce que l'utilisateur saisit dans l'outil (PM, acquittements, snooze) | `services/` via routes API | `services/` via routes API |

**Pourquoi séparées** : la donnée du data center (mesurée/dérivée par le pipeline) et l'état saisi par l'utilisateur n'ont pas le même cycle de vie ni la même source de vérité — l'un est recalculable depuis la source, l'autre non. PostgreSQL `datacenter_ops` reste en lecture seule dans tous les cas ; aucune écriture n'y retourne jamais.

### 4.1 Base analytique — `storage/` (medallion)

```
storage/
├── analytics_db.py         # engine SQLite dédié + init_analytics_db()
├── schema/
│   ├── bronze.py    # raw_temp_humidity, raw_scada_log
│   ├── silver.py    # th_clean, scada_clean
│   └── gold.py         # anomaly_episode, health_score_hourly, forecast_point
└── repositories/
    ├── bronze_repo.py   # écriture idempotente + watermark (backfill)
    ├── silver_repo.py
    └── gold_repo.py       # seul repo lu par ml/ côté API live
```


| Couche | Contenu | Écrite par | Recalculable |
|---|---|---|---|
| **bronze** | copie brute append-only de la source (doublons/trous inclus) | `etl/ingest` | non — c'est la vérité |
| **silver** | dédupliqué, gaps >125s classés, segments, rolling stats | `etl/transform` | oui, depuis bronze |
| **gold** | résultat métier servi par l'API (épisodes, scores, forecast) | `etl/detect,score,forecast` | oui, depuis silver |

Chiffres réels après backfill : `raw_temp_humidity`=137 970 lignes, `raw_scada_log`=3 274 ; silver `th_clean`=107 047 lignes / 1 905 segments ; gold=388 épisodes, 2 137 heures de health score, 164 points de forecast.

### 4.2 `etl/` — orchestration bronze→silver→gold

```
etl/
├── ingest/
│   ├── sources.py     # lecteurs bruts (CSV) — golden tests de fidélité vs source
│   └── backfill.py     # écriture bronze, idempotente (watermark)
├── transform.py        # bronze → silver (dedupe_and_index, add_segments, clean_and_dedupe)
├── detect.py            # silver → épisodes gold (HMM environnemental + filtre seuil réel)
├── score.py              # silver/gold → health_score_hourly (maths portées du notebook)
├── forecast.py          # → forecast_point (XGBoost sur delta 6h, top 20 features)
└── run.py                  # orchestrateur (lance les étapes dans l'ordre)
```

`etl/` est la **seule** couche qui a le droit d'appeler `ml/` **et** d'écrire dans `storage/`. Ni l'API ni les services ne le font.

### 4.3 État applicatif — `db/` (SQLite, `SQLAlchemy 2.0 DeclarativeBase`)

Trois tables (`db/tables.py`), toutes conçues sur le même principe : **l'objet dérivé du pipeline reste en lecture seule, seule l'action utilisateur est stockée, et vient surcharger la lecture** :

| Table | Clé | Rôle |
|---|---|---|
| `PMSchedule` | id auto | Planning de maintenance préventive saisi par l'utilisateur (équipement, dernière PM, période → `next_pm_date` recalculée à la lecture) |
| `AnomalyAction` | `episode_id` (ex. `EP-0001`) | Acquittement/résolution d'un épisode — surcharge le statut simulé/gold au moment de la lecture |
| `ReminderAction` | id du rappel (ex. `RM-AN-EP-0003`, `RM-PM-PM-0004`) | Snooze/acquittement — les rappels eux-mêmes sont **dérivés** (PM à venir, seuils, anomalies non acquittées), jamais stockés directement ; seule l'action filtre la liste dérivée |

Ce pattern « action persistée qui surcharge une donnée dérivée » est établi et réutilisé partout où l'utilisateur agit sur une donnée qui vient du pipeline — à reprendre pour toute future action similaire.

---

## 5. Bout en bout — exemple concret

**Lire l'aperçu santé d'un site (`GET /api/health/overview`)** :
1. Frontend : `GlobalView.jsx` appelle `api.healthOverview()` (`api/client.js`) via `useApi`.
2. Backend : route `api/health.py` appelle `providers.py`.
3. `providers.py` regarde `settings.data_source` :
   - `mock` → `mocks/health.py` génère un score cohérent avec les seuils réels
   - `live` → `ml/health.py` lit `storage/repositories/gold_repo.py` (table `health_score_hourly`/`health_score`)
4. Réponse validée par le schéma Pydantic `models/health.py`, renvoyée en JSON.
5. Frontend rend `HealthGauge` + `EquipmentCard` à partir de la réponse.

**Planifier une PM (`POST /api/maintenance/schedule`)** :
1. Frontend : formulaire `Maintenance.jsx` → `api.scheduleMaintenance(payload)`.
2. Backend : route `api/maintenance.py` → `services/maintenance.py` calcule `next_pm_date` et écrit dans **l'état applicatif** (`db/tables.py::PMSchedule`, via `db/app_db.py`) — jamais dans la base analytique ni dans PostgreSQL source.
3. `GET /api/maintenance/calendar` relit cette table pour peupler `PMCalendar.jsx`.

---

## 6. Documents liés

- [`project-overview.md`](project-overview.md) — contexte produit, avancement par phase