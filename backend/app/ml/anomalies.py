"""Source LIVE des anomalies — lit la couche **gold** précalculée par l'ETL.

Le pipeline (préprocessing → HMM → détection → épisodes) est exécuté hors ligne
par `app/etl` et matérialisé dans le gold (`anomaly_episode`). Cette source ne fait
donc que **lire** le gold : aucun calcul sur le chemin de requête. C'est le pendant
« live » de `mocks/anomalies.py`, choisi par `app/providers.py` selon `DATA_SOURCE`.

La surcharge de statut (actions utilisateur), le filtrage et les agrégations (stats,
histogramme) restent partagés avec le mock via `services/anomaly_aggregation.py`.
"""
from datetime import datetime, timezone

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


def reference_now() -> datetime:
    """Fin de la période **observée** — la borne haute des fenêtres glissantes.

    La source est un export historique figé : la dernière lecture capteur date de
    plusieurs semaines. Caler les fenêtres « 24 h / 7 j » sur l'horloge de la
    requête les placerait entièrement après la fin des données, et le KPI ne
    pourrait afficher que zéro — un « rien à signaler » impossible à distinguer
    d'un pipeline en panne. On borne donc sur la donnée elle-même.

    Volontairement la fin de la **couverture capteur**, pas la date du dernier
    épisode : une fenêtre calée sur le dernier épisode contiendrait toujours au
    moins une anomalie par construction, ce qui ne mesurerait plus rien.
    """
    with get_analytics_sessionmaker()() as session:
        last = silver_repo.last_ts(session)
    return last or datetime.now(timezone.utc)
