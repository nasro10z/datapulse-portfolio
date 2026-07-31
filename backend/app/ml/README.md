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

`anomalies.py` / `health.py` sont le **contrat** appelé par `providers` — tous deux
**implémentés** : ils lisent le gold précalculé par l'ETL (aucun modèle chargé sur
le chemin de requête).

## Package `health_score/` — score de santé du site (portage notebook)

Portage du notebook `health_scores.ipynb` de l'équipe data science, en **maths
pures** (DataFrame → DataFrame, aucune I/O) :

| Module | Rôle |
|---|---|
| `config.py` | poids v1.0, mots-clés d'alarme, dates/intervalles de PM, seuils de statut, bornes de plausibilité capteur |
| `features.py` | helpers (décroissance, saturation, durée continue, risque PM) + features horaires environnement / énergie / batterie |
| `scoring.py` | risques de base → calibration énergie → score global, domaine dominant, statut, priorité, action conseillée |
| `forecast_features.py` | fabrique de features dynamiques (~1 200 : retards, variations, vitesses, stats et pentes glissantes, accélération, dégradation continue, interactions) |
| `forecasting.py` | cible delta, entraînement XGBoost, sélection top-N sur validation, déroulé récursif amorti |

**Fidélité prouvée** : `tests/test_health_score.py::test_scoring_reproduces_notebook_output`
compare la sortie aux scores du notebook (`site_health_scores_v1_0.csv`) sur les
entrées livrées → égalité exacte. C'est ce test qui permet de faire évoluer ce
package sans reperdre la validation faite par l'équipe data science.

**Prévision — XGBoost sur le delta.** La cible apprise est la **variation** de
santé à +6 h, pas le niveau :

```
delta_prévu  = XGBoost(features)
santé_prévue = clip(santé_courante + delta_prévu, 0, 100)
```

C'est ce changement de cible qui débloque tout. `overall_site_health` se comporte
comme un AR(1) : prédire le niveau, c'est demander à des arbres d'extrapoler une
tendance, ce qu'ils ne savent pas faire — aucun modèle du notebook n'y battait la
persistance. Prédire le delta fait de la persistance un simple « delta = 0 », et il
ne reste au modèle qu'à apprendre l'écart.

Le modèle est d'abord entraîné sur les ~1 200 features dynamiques, puis
**réentraîné sur les N features les plus importantes** avec N ∈ {20, 50, 100, 200}
choisi sur la **validation**. Moins de features, moins de place pour surapprendre
sur ~2 100 heures.

Au-delà de +6 h : déroulé récursif à conditions inchangées, chaque delta au-delà du
premier pas **amorti** géométriquement (sinon la trajectoire se compose et sature à
100/100), bande élargie en √pas. Artefacts, features retenues et métriques
(persistance, modèle servi, variante pondérée sur les chutes) dans
`models/health_forecast/metadata.json`.

## Le seam mock ↔ live (Phase 8)

Toute l'application lit ses données métier via `app/providers.py`, qui aiguille
vers `mocks/` ou `ml/` selon une seule variable :

```
DATA_SOURCE=mock   # défaut — générateurs seedés (Phases 1–7)
DATA_SOURCE=live   # pipeline ML validé (package mlops-api) sur données CSV
```

Une **dérogation par domaine** permet de n'en basculer qu'une partie ; non
renseignée, le domaine suit `DATA_SOURCE` :

```
ANOMALIES_SOURCE=mock   # anomalies mockées…
HEALTH_SOURCE=live      # …santé sur le pipeline réel
```

Utile en démo : les épisodes réels s'arrêtent au 09/05/2026, donc les vues
d'anomalies bornées à une fenêtre récente (24 h / 7 j) n'ont rien à montrer, alors
que les scores de santé se lisent très bien sur la dernière heure connue.

Les routes n'importent jamais `mocks/` ni `ml/` directement. Brancher le pipeline
réel = implémenter les stubs ci-dessous, pas toucher aux routes.

## Le contrat (implémenté — lecture gold)

La source ne produit que le **brut** ; surcharge de statut, filtrage et
agrégations (stats, histogramme) sont partagés et vivent dans
`services/anomaly_aggregation.py` — ne pas les redéfinir ici.

- `ml/anomalies.py`
  - `raw_episodes() -> list[AnomalyEpisode]` — épisodes détectés sur la fenêtre
    courante (statut calculé, avant surcharge utilisateur).
  - `window_days() -> int` — fenêtre d'observation réelle (taux d'anomalies).
- `ml/health.py`
  - `get_overview()` — score global + sous-scores + scores par domaine.
  - `get_history(range_)` — série quotidienne (7 / 30 / 90 j).
  - `get_forecast(horizon)` — historique + prévision + bande + franchissements.
  - `get_predicted_faults(horizon)` — fenêtre de risque par domaine.
  - `get_subscore_forecast(horizon)` — séries par domaine.

Gold vide (ETL jamais lancé) → `NotImplementedError` avec la marche à suivre, donc
501 côté API : jamais de zéros qui passeraient pour des mesures.

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
