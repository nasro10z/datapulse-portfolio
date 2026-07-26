# app/ml — pipeline ML (source « live »)

Ce package accueille le pipeline validé (preprocessing, segmentation, détection
PELT/hystérésis, forecasting). **Règle projet : `ml/` (logique données/modèles)
reste strictement séparé de `api/` (exposition REST). Ne pas réécrire le code ML
validé — l'importer/adapter ici.**

## Le seam mock ↔ live (Phase 8)

Toute l'application lit ses données métier via `app/providers.py`, qui aiguille
vers `mocks/` ou `ml/` selon une seule variable :

```
DATA_SOURCE=mock   # défaut — générateurs seedés (Phases 1–7)
DATA_SOURCE=live   # pipeline ML validé sur PostgreSQL
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

`app/db/queries.py` lit les tables sources (`temp_humidity`, `scada_logs`,
`ups_events`) en DataFrames — ⚠️ noms de colonnes à confirmer contre le schéma
réel. Connexion via `db/engine.py` (`URL.create()`, jamais psycopg2 direct).

## Étapes du pipeline (déjà validées — cf. CLAUDE.md)

1. Préprocessing : déduplication (242 timestamps), gaps >125s = discontinuité,
   segmentation par `cumsum()` (~1904 segments).
2. Rolling stats multi-échelle (fenêtres 12/36/78 points).
3. Détection par hystérésis, seuils Tukey directionnels (mild 27.85 / extreme
   30.40 °C ; exit_margin=0.5, min_exit_duration=5) → 27-36 épisodes.
4. Validation finale contre `scenario_6_label` (point ouvert :
   `MIN_DURATION_FOR_JUMP=60` min sur l'approche PELT combinée).

Tant qu'un stub n'est pas implémenté, `DATA_SOURCE=live` renvoie **501 Not
Implemented** (message explicite) sur les endpoints concernés.
