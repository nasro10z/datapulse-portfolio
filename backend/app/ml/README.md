# app/ml — pipeline ML (source « live »)

Ce package accueille le pipeline validé (preprocessing, segmentation, détection
par hystérésis / HMM / IsolationForest, forecasting). **Règle projet : `ml/`
(logique données/modèles) reste strictement séparé de `api/` (exposition REST).
Ne pas réécrire le code ML validé — l'importer/adapter ici.**

## Package `mlops-api` vendorisé (Étape B — fait)

Le pipeline validé est **copié dans le repo** sous :
- `environmental/` — HMM température/humidité (`EnvironmentalPredictor`) ;
- `alarm_anomaly/` — IsolationForest sur événements SCADA (`AnomalyPredictor`) ;
- `models/` — artefacts `.joblib` + `metadata.json` + `thresholds.json`.

Imports réécrits en `app.ml.*` ; `MODELS_DIR` pointe sur `app/ml/models`. Les deux
modèles chargent et prédisent. `model_registry.py` (glue de LEUR API FastAPI) est
copié pour référence mais **non utilisé** — DataPulse a son propre seam
(`app/providers.py`) ; il porte un import obsolète et sera retiré/adapté en G.

Les stubs `anomalies.py` / `health.py` ci-dessous restent le **contrat** appelé par
`providers` : ils seront implémentés (étapes E–G) pour dérouler ces prédicteurs sur
le bronze et produire le gold.

## Le seam mock ↔ live (Phase 8)

Toute l'application lit ses données métier via `app/providers.py`, qui aiguille
vers `mocks/` ou `ml/` selon une seule variable :

```
DATA_SOURCE=mock   # défaut — générateurs seedés (Phases 1–7)
DATA_SOURCE=live   # pipeline ML validé (package mlops-api) sur données CSV
```

Les routes n'importent jamais `mocks/` ni `ml/` directement. Brancher le pipeline
réel = implémenter les stubs ci-dessous, pas toucher aux routes.

## Contrat à implémenter

La source ne produit que le **brut** ; surcharge de statut, filtrage et
agrégations (stats, histogramme) sont partagés et vivent dans
`services/anomaly_aggregation.py` — ne pas les redéfinir ici.

- `ml/anomalies.py`
  - `raw_episodes() -> list[AnomalyEpisode]` — épisodes détectés sur la fenêtre
    courante (statut calculé, avant surcharge utilisateur).
  - `window_days() -> int` — fenêtre d'observation réelle (taux d'anomalies).
- `ml/health.py`
  - `get_overview() -> HealthOverview` — score global + sous-scores par famille.
  - `get_forecast(horizon) -> ForecastResponse` — historique + prévision + bande.

Les IDs d'épisode doivent être **stables** d'un appel à l'autre : les actions
utilisateur (acquitter/résoudre) sont persistées par id (`db/tables.AnomalyAction`).

## Données d'entrée

Source = **exports CSV** des tables (`temp_humidity`, `scada_logs`, `ups_events`) —
PostgreSQL `datacenter_ops` n'est **pas joignable directement** (plateforme isolée).
L'ingestion CSV → bronze vit dans `etl/ingest/` (voir `docs/data-architecture.md`).

## Étapes du pipeline (déjà validées — cf. CLAUDE.md)

1. Préprocessing : déduplication, gaps >125s = discontinuité, segmentation par
   `cumsum()`.
2. Rolling stats multi-échelle (fenêtres 12/36/78 points).
3. Détection par hystérésis, seuils Tukey directionnels (mild 26.75 / extreme
   28.65 °C ; exit_margin=0.5, min_exit_duration=5). Granularité **par salle**.

Le pipeline validé est livré sous forme du package **`mlops-api`** (2 modèles :
`environmental` HMM temp/humidité, `alarm_anomaly` IsolationForest SCADA) et
intégré **en librairie** — voir `docs/data-architecture.md` §8.

État du branchement live (`DATA_SOURCE=live`) :
- **anomalies + rappels** : branchés — `ml/anomalies.py` lit le gold (`gold_repo`),
  précalculé par `app/etl` (backfill → transform → detect). `GET /api/anomalies`
  sert les 388 épisodes réels.
- **health + forecast** : `ml/health.py` lève encore `NotImplementedError` → **501
  explicite** tant que le scoring composite + forecast (étape F) ne sont pas branchés.
