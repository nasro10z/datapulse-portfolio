"""Repository GOLD — lecture/écriture des épisodes servis à l'API.

Le gold miroite les modèles Pydantic : la conversion ligne ↔ `AnomalyEpisode` est
directe. C'est ce que `providers` (mode live) lira à l'étape G.
"""
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.anomalies import AnomalyEpisode
from app.storage.schema.gold import AnomalyEpisodeRow


def _naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def replace_episodes(session: Session, episodes: list[AnomalyEpisode]) -> int:
    """Remplace la table `anomaly_episode` par la liste fournie (backfill idempotent)."""
    session.execute(delete(AnomalyEpisodeRow))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for e in episodes:
        session.add(AnomalyEpisodeRow(
            id=e.id, equipment=e.equipment, type=e.type.value, severity=e.severity.value,
            direction=e.direction.value, start=_naive(e.start), duration_min=e.duration_min,
            peak_value=e.peak_value, status=e.status.value, dimension=e.dimension.value, computed_at=now,
        ))
    session.commit()
    return len(episodes)


def read_episodes(session: Session) -> list[AnomalyEpisode]:
    """Épisodes (statut calculé, avant surcharge par l'action utilisateur), plus récents d'abord."""
    rows = session.scalars(select(AnomalyEpisodeRow).order_by(AnomalyEpisodeRow.start.desc())).all()
    return [
        AnomalyEpisode(
            id=r.id, equipment=r.equipment, type=r.type, severity=r.severity,
            direction=r.direction, start=r.start, duration_min=r.duration_min,
            peak_value=r.peak_value, status=r.status, dimension=r.dimension,
        )
        for r in rows
    ]
