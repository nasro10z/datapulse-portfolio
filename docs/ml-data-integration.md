# DataPulse — Intégration ML & données sources

État **réalisé** de la Phase 8 (ce qui est construit) + **inventaire des données
brutes** fournies. Complète `docs/data-architecture.md`, qui décrit la *conception*
(couches bronze/silver/gold, séparation storage/etl/ml) ; ce document décrit
l'*implémentation* et les *entrées de données*.

---

## 1. Où on en est (Phase 8)

| Étape | Objet | Statut |
|---|---|---|
| A | Couche `storage/` (SQLite analytique, bronze/silver/gold) | ✅ fait |
| B | Package ML `mlops-api` vendorisé dans `app/ml/` | ✅ fait |
| C | `etl/ingest` : lecteurs bruts + fidélité + **écriture bronze** | ✅ fait (bronze : 137 970 temp/hum + 3 274 SCADA) |
| D | `etl/transform` : bronze → silver (préprocessing validé) | ✅ fait (silver `th_clean` : 107 047 lignes, 1 905 segments) |
| E | `etl/detect` : HMM → épisodes (par salle) → gold | ✅ fait (388 épisodes, HMM filtré sur seuil température) |
| G | source live anomalies → lecture gold | ✅ fait (`GET /api/anomalies` live = 388 épisodes ; health/forecast encore 501) |
| F, I | health/forecast → gold ; rebrancher Santé du site | ⏳ suivant |

Fidélité de l'ingestion vérifiée (voir §7) : environnemental **99.95 % / 99.76 %**,
SCADA **100 % exact** (reproduction bit-à-bit de `msc10_combined_ups.csv`).

Données brutes **reçues et en place** (§4) → C et D peuvent démarrer.

---

## 2. Étape A — couche storage (fait)

Base analytique **SQLite dédiée**, distincte de l'état applicatif et de la source.
Un **écrivain unique par fichier** (cf. `docs/data-architecture.md` §3).

- `app/storage/analytics_db.py` — moteur SQLite (WAL, `URL.create()`),
  `init_analytics_db()` (idempotent), câblé au lifespan FastAPI.
- `app/storage/schema/` — `Base` propre + 3 couches :
  - **bronze** : `raw_temp_humidity`, `raw_scada_log`, `ingest_watermark` ;
  - **silver** : `th_clean` (lectures nettoyées + segment) ;
  - **gold** : `anomaly_episode`, `health_score`, `forecast_point` (miroirs des
    modèles Pydantic → mapping ligne→modèle trivial).
- Fichier : `backend/data/datapulse_analytics.db` (gitignoré, recréé au démarrage).
- Tests : `backend/tests/test_storage.py` (4 tests : création des 7 tables,
  aller-retour bronze, reconstruction `AnomalyEpisode` depuis gold, silver+watermark).

## 3. Étape B — package ML vendorisé (fait)

Le pipeline validé (package `mlops-api`) est **copié dans le repo** sous `app/ml/` :

```
app/ml/
  environmental/     # HMM temp/humidité — EnvironmentalPredictor
  alarm_anomaly/     # IsolationForest alarmes SCADA — AnomalyPredictor
  models/            # artefacts .joblib + metadata.json + thresholds.json
  model_registry.py  # glue de LEUR API — NON utilisée (import obsolète), à retirer en G
  anomalies.py health.py README.md   # notre seam (contrat appelé par providers)
```

- Imports réécrits en `app.ml.*` ; `MODELS_DIR` pointe sur `app/ml/models`.
- Dépendances figées : `scikit-learn==1.9.0` (aligné sur les `.joblib`), `hmmlearn`,
  `openpyxl`, `joblib`.
- **Vérifié** : les deux modèles chargent et prédisent depuis l'arborescence du repo
  (`environmental` sur un buffer de lectures ; `alarm_anomaly` sur des features
  d'événement). C'est un *smoke test* de tuyauterie, pas une validation de justesse.

Appel type (ce que fera `etl/detect` en E) :

```python
from app.ml.environmental.predict import EnvironmentalPredictor
from app.ml.alarm_anomaly.predict import AnomalyPredictor

env = EnvironmentalPredictor()
env.predict_one({"ts": "2026-03-24T05:54:03", "temperature": 24.3, "humidity": 38.6})
# -> {"is_anomaly": bool, "state": int, "score": float, "history_size": int}

AnomalyPredictor().predict_one({...features d'événement...})
# -> {"is_anomaly": bool, "score": float, "dominant_category": str}
```

Modèles (cf. `metadata.json`) : `environmental` HMM 6 états (F1 anomalie 0.83) ;
`alarm_anomaly` IsolationForest (300 arbres, contamination 3%, 720 events).
Seuils Tukey livrés : temp **mild 26.75 / extreme 28.65 °C** (`thresholds.json`).

---

## 4. Inventaire des données sources brutes

Emplacement : `backend/app/ml/data/raw/` (**gitignoré** — volumineux, fournis
manuellement). Ce sont les données **brutes** (≠ données nettoyées d'entraînement) :
l'ingestion (C) doit les normaliser avant de remplir le bronze.

| Fichier (dans data/raw/) | Rôle | Volume | Format / pièges | → bronze |
|---|---|---|---|---|
| `temp_humid_msc10.csv` | Température/humidité salle switch (modèle `environmental`) | **140 077** lignes | **latin-1** ; colonnes `ID `, `Date ` (JJ/MM/AAAA), `time` (HH:MM:SS), `Temperature`, `Humidité` (espaces/accents, **valeurs texte**) ; **pas de `ts`** (à reconstruire depuis `Date`+`time`) | `raw_temp_humidity` |
| `logs_msc10.xlsx` | Logs d'alarmes SCADA MSC-10 (récents, 2026) | **2 250** lignes | **en-tête réel en ligne 1** (ligne 0 = faux en-tête) ; colonnes `state`, `time` (**M/J/AAAA h:mm AM/PM**), `message` (`\MSC-10\ …`), `send Time` | `raw_scada_log` |
| `ups_socomec1_msc10_events.csv` | Événements onduleur SOCOMEC 1 | **1 024** lignes | **1re ligne parasite à sauter** ; latin-1 ; colonnes `Date` (JJ/MM/AAAA), `Time`, `Level` (Information…), `Description` (« … has been restored ») | `raw_scada_log` (via mapping UPS) |
| `alarmes_scada_2022.xlsx` | Alarmes SCADA **multi-sites** 2022 (historique) | **35 408** lignes (**2 664** = MSC 10) | **2 feuilles** (`Sheet` : 7 col dont Counter/NNMi/eMails ; `Sheet1` : `Unnamed:0`, state, time, message — version épurée) ; **multi-sites** → filtrer `message` contient « MSC 10 » | `raw_scada_log` (filtré MSC 10) |

`logs_msc10.xlsx` (2026) + le sous-ensemble MSC 10 de `alarmes_scada_2022.xlsx`
(2022) forment ensemble l'**historique d'alarmes SCADA de MSC-10**. Les autres sites
présents dans le fichier 2022 (six autres sites du même réseau) sont **hors
périmètre** et écartés à l'ingestion.

---

## 5. Écarts « brut ↔ entraînement » à traiter en ingestion/transform (C–D)

Ces différences sont la raison pour laquelle on ne peut pas déposer les fichiers et
lancer les loaders du package tels quels — l'ingestion doit les gérer :

1. **Encodage** : `temp_humid_msc10.csv` et `ups_*.csv` sont en **latin-1**, pas utf-8.
2. **`ts` à reconstruire** : temp/humidité et UPS n'ont pas de timestamp unique →
   `ts = Date + time` (`ts` était une feature créée dans les données nettoyées).
3. **En-têtes décalés** : `logs_msc10.xlsx` → `header=1` ; `alarmes_scada_2022.xlsx`
   → 1re colonne `Unnamed:0` sur la feuille épurée.
4. **Filtrage multi-sites** : `alarmes_scada_2022.xlsx` → ne garder que les lignes
   dont le `message` contient « MSC 10 » (2 664 / 35 408).
5. **Valeurs d'état** : l'entraînement ne comptait que `A` (actif) et `D` (résolu) ;
   le brut contient aussi **`Q`** et **`Acquittement - Système`** → ces lignes
   comptent dans `total_alarms` mais ni actives ni résolues. Décision à prendre en
   transform (les garder telles quelles vs mapper).
6. **Formats de date hétérogènes** : temp/hum & UPS en `JJ/MM/AAAA` ; SCADA en
   `M/J/AAAA h:mm:ss AM/PM` (US). Parsing distinct par source.
7. **Volume** : temp/hum brut 140k > 107k nettoyé (les doublons et lignes dégradées
   sont retirés en **silver**, pas en bronze qui reste une copie fidèle).

---

## 6. Lancer / tester

```bash
cd backend
.venv/Scripts/python -m pytest tests/     # 35 tests (4 storage + 2 fidélité)
```

Le backend reste en `DATA_SOURCE=mock` par défaut : aucune de ces étapes ne change
le comportement servi tant que l'ETL n'alimente pas le gold et que `providers` n'est
pas basculé en `live` (étape G).

---

## 7. Étape C — ingestion & fidélité (en cours)

Lecteurs des données brutes dans `app/etl/ingest/sources.py` (normalisation pure :
encodage, `ts`, en-têtes, filtrage MSC 10, mapping UPS). Ils **réutilisent** les
fonctions validées (`clean_and_dedupe`, `dedupe_and_index`) — jamais réimplémentées.

**Golden tests** (`tests/test_ingestion_fidelity.py`, skippés si données absentes) :

| Ingestion | Référence | Résultat |
|---|---|---|
| `load_temp_humidity` + `dedupe_and_index` | `temp_humid_last.csv` | temp **99.95 %**, hum **99.76 %** (seuil ≥ 99.5 %) |
| `load_scada_combined` | `msc10_combined_ups.csv` | **100 % exact** (2569/2569, catégories 100 %) |

Le résidu environnemental (~0.1–0.3 %) = millésime de l'export brut (timestamps en
plus, résolution des doublons), **pas** de divergence de logique.

**Découverte (notebook fourni) — les alarmes 2022 n'ont jamais servi au modèle.**
Le combiné d'entraînement (`msc10_combined_ups.csv`) est **entièrement 2026** (logs +
UPS). Dans le notebook, `ALARMES SCADA 2022.xlsx` (2 664 lignes MSC 10) était bien
concaténé, mais son format de date (`2/21/2022 2:02:53 PM`) a échoué au parsing →
**2 664 `log_time` en NaT**, supprimées par le `dropna` suivant. Notre ingestion
exclut 2022 explicitement → même résultat (2569 lignes, 100 %). À signaler comme
possible perte involontaire côté pipeline d'origine ; le modèle livré reste
entraîné sur 2026. Le lecteur `load_scada_alarms_2022` est conservé (backfill
historique élargi éventuel) mais **hors** du combiné modèle.

> ⚠️ Les 2 tests de fidélité lisent les gros fichiers bruts (~80 s). Ils sont
> skippés sans les données ; à isoler dans un marqueur « slow » si besoin d'un
> cycle rapide.
