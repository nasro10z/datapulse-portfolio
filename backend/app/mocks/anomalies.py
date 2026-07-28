"""Source MOCK des anomalies — ~30 épisodes sur 60 jours, cohérents avec le
pipeline validé (27-36 épisodes après hystérésis, seuils Tukey directionnels).

Ce module ne fait que *produire les épisodes bruts*. La surcharge de statut, le
filtrage et les agrégations (stats, histogramme) sont partagés avec la source
live et vivent dans `services/anomaly_aggregation.py` ; le choix de la source
se fait dans `app/providers.py`.
"""
import random
from datetime import datetime, timedelta, timezone

from app.mocks.equipment import EXTREME_UPPER, MILD_UPPER, STULZ_UNITS, SOCOMEC_UNITS
from app.models.anomalies import (
    AnomalyDimension,
    AnomalyEpisode,
    AnomalyStatus,
    AnomalyType,
    Direction,
    Severity,
)

_EPISODE_COUNT = 30
WINDOW_DAYS = 60  # fenêtre d'observation simulée (pour le taux d'anomalies)


def _build_episodes() -> list[AnomalyEpisode]:
    rng = random.Random(1904)  # clin d'œil aux ~1904 segments du pipeline
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    episodes = []
    for i in range(_EPISODE_COUNT):
        severity = Severity.critical if rng.random() < 0.25 else Severity.alert
        direction = Direction.high if rng.random() < 0.8 else Direction.low
        if direction == Direction.high:
            peak = (rng.uniform(EXTREME_UPPER, EXTREME_UPPER + 2.5)
                    if severity == Severity.critical
                    else rng.uniform(MILD_UPPER, EXTREME_UPPER - 0.1))
        else:
            peak = rng.uniform(16.5, 19.5)
        # la salle switch est climatisée par les STULZ : ils dominent les épisodes
        equipment = rng.choice(STULZ_UNITS * 4 + SOCOMEC_UNITS)
        # démo : STULZ ~ détection environnementale (HMM temp/hum), SOCOMEC ~ alarme SCADA
        dimension = AnomalyDimension.environment if equipment.startswith("STULZ") else AnomalyDimension.scada
        start = now - timedelta(hours=rng.uniform(2, WINDOW_DAYS * 24))
        age_h = (now - start).total_seconds() / 3600
        status = (AnomalyStatus.resolved if age_h > 72
                  else AnomalyStatus.acknowledged if age_h > 24
                  else AnomalyStatus.open)
        episodes.append(AnomalyEpisode(
            id=f"EP-{i + 1:04d}",
            equipment=equipment,
            type=rng.choice(list(AnomalyType)),
            severity=severity,
            direction=direction,
            start=start.replace(microsecond=0),
            duration_min=round(rng.uniform(8, 160), 1),
            peak_value=round(peak, 2),
            status=status,
            dimension=dimension,
        ))
    episodes.sort(key=lambda e: e.start, reverse=True)
    return episodes


_EPISODES: list[AnomalyEpisode] = _build_episodes()


def raw_episodes() -> list[AnomalyEpisode]:
    """Épisodes bruts, statut simulé (avant surcharge par l'action utilisateur)."""
    return _EPISODES


def window_days() -> int:
    return WINDOW_DAYS


def reference_now() -> datetime:
    """Fin de la période observée. Les épisodes mockés sont générés autour de
    l'heure courante : la borne des fenêtres glissantes est donc bien `now`."""
    return datetime.now(timezone.utc)
