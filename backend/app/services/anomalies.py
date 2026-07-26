"""Actions utilisateur sur les anomalies : acquittement / résolution.

Les épisodes d'anomalie proviennent du pipeline (mockés en attendant) et sont
en lecture seule. Ce module ne gère que la surcharge de statut décidée par
l'utilisateur, persistée dans la base applicative (voir `db/tables.AnomalyAction`).
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.tables import AnomalyAction
from app.models.anomalies import AnomalyStatus


def get_status_overrides(session: Session) -> dict[str, AnomalyStatus]:
    """Statuts décidés par l'utilisateur, indexés par id d'épisode."""
    rows = session.scalars(select(AnomalyAction)).all()
    return {r.episode_id: AnomalyStatus(r.status) for r in rows}


def set_status(session: Session, episode_id: str, status: AnomalyStatus) -> None:
    """Enregistre (ou remplace) l'action de l'utilisateur sur un épisode."""
    row = session.get(AnomalyAction, episode_id)
    if row is None:
        row = AnomalyAction(episode_id=episode_id)
        session.add(row)
    row.status = status.value
    row.updated_at = datetime.now(timezone.utc)
    session.commit()
