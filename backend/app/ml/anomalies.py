"""Source LIVE des anomalies — lit la couche **gold** précalculée par l'ETL.

Le pipeline (préprocessing → HMM → détection → épisodes) est exécuté hors ligne
par `app/etl` et matérialisé dans le gold (`anomaly_episode`). Cette source ne fait
donc que **lire** le gold : aucun calcul sur le chemin de requête. C'est le pendant
« live » de `mocks/anomalies.py`, choisi par `app/providers.py` selon `DATA_SOURCE`.

La surcharge de statut (actions utilisateur), le filtrage et les agrégations (stats,
histogramme) restent partagés avec le mock via `services/anomaly_aggregation.py`.
"""
from app.models.anomalies import AnomalyEpisode
from app.storage.analytics_db import get_analytics_sessionmaker
from app.storage.repositories import gold_repo, silver_repo


def raw_episodes() -> list[AnomalyEpisode]:
    """Épisodes détectés (statut calculé), lus depuis le gold."""
    with get_analytics_sessionmaker()() as session:
        return gold_repo.read_episodes(session)


def window_days() -> int:
    """Fenêtre d'observation réelle (jours) = étendue du silver, pour le taux d'anomalies."""
    with get_analytics_sessionmaker()() as session:
        return silver_repo.span_days(session)
