"""Source LIVE des anomalies — contrat d'intégration du pipeline ML validé.

⚠️ Non implémenté : ces fonctions définissent le *contrat* que le pipeline validé
(notebook Databricks) doit remplir une fois branché en Phase 8. Elles lèvent
`NotImplementedError` tant que le code réel n'est pas fourni. **Ne pas réécrire
la logique ML ici** (règle projet) : importer/adapter le pipeline existant, qui
consomme les données via `app/db/queries.py`.

Étapes attendues du pipeline (déjà validées, cf. CLAUDE.md) :
  1. Préprocessing : déduplication (242 timestamps), gaps >125s = discontinuité,
     segmentation par `cumsum()` (~1904 segments).
  2. Rolling stats multi-échelle (fenêtres 12/36/78 points).
  3. Détection d'épisodes par hystérésis sur seuils Tukey directionnels
     (mild_upper=27.85°C, extreme_upper=30.40°C ; exit_margin=0.5,
     min_exit_duration=5) → 27-36 épisodes cohérents.
  4. Mapping épisode → `AnomalyEpisode` (id stable, equipment, type, severity,
     direction, start, duration_min, peak_value, status calculé).

Le contrat est volontairement minimal : la source ne produit que les épisodes
bruts et la fenêtre d'observation ; surcharge de statut, filtrage et agrégations
sont partagés (`services/anomaly_aggregation.py`).
"""
from app.models.anomalies import AnomalyEpisode

_NOT_WIRED = (
    "Source live des anomalies non branchée : fournir le pipeline ML validé "
    "(voir app/ml/README.md) puis passer DATA_SOURCE=live."
)


def raw_episodes() -> list[AnomalyEpisode]:
    """Épisodes détectés par le pipeline sur la fenêtre courante (statut calculé,
    avant surcharge par l'action utilisateur)."""
    raise NotImplementedError(_NOT_WIRED)


def window_days() -> int:
    """Fenêtre d'observation réelle (jours) couverte par `raw_episodes`,
    pour le calcul du taux d'anomalies."""
    raise NotImplementedError(_NOT_WIRED)
