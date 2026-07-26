"""Actions utilisateur sur les rappels : snooze / acquittement.

Les rappels sont dérivés à la lecture (voir `mocks/reminders.py`) ; ce module
ne persiste que l'action de l'utilisateur, qui filtre ensuite la liste dérivée.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.tables import ReminderAction
from app.models.reminders import Reminder


def _get(session: Session, reminder_id: str) -> ReminderAction:
    row = session.get(ReminderAction, reminder_id)
    if row is None:
        row = ReminderAction(reminder_id=reminder_id)
        session.add(row)
    row.updated_at = datetime.now(timezone.utc)
    return row


def acknowledge(session: Session, reminder_id: str) -> None:
    row = _get(session, reminder_id)
    row.acknowledged = True
    session.commit()


def snooze(session: Session, reminder_id: str, hours: float) -> None:
    row = _get(session, reminder_id)
    row.snoozed_until = datetime.now(timezone.utc) + timedelta(hours=hours)
    session.commit()


def get_actions(session: Session) -> dict[str, ReminderAction]:
    return {r.reminder_id: r for r in session.scalars(select(ReminderAction)).all()}


def apply_actions(reminders: list[Reminder], actions: dict[str, ReminderAction]) -> list[Reminder]:
    """Retire les rappels acquittés et ceux encore sous snooze."""
    now = datetime.now(timezone.utc)
    out: list[Reminder] = []
    for r in reminders:
        a = actions.get(r.id)
        if a is None:
            out.append(r)
            continue
        if a.acknowledged:
            continue
        if a.snoozed_until is not None and _as_utc(a.snoozed_until) > now:
            continue
        out.append(r)
    return out


def _as_utc(dt: datetime) -> datetime:
    """SQLite ne conserve pas le fuseau : un datetime relu est naïf, on le
    réinterprète comme UTC (c'est ce qui a été écrit)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
