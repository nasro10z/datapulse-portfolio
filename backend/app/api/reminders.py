from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import providers
from app.db.app_db import get_session
from app.mocks import reminders as mock_reminders
from app.models.reminders import Reminder, ReminderCount, SnoozeRequest
from app.services import anomalies as anomalies_service
from app.services import maintenance as maintenance_service
from app.services import reminders as reminders_service

router = APIRouter(prefix="/reminders", tags=["reminders"])


def _active_reminders(session: Session) -> list[Reminder]:
    # calendrier et épisodes (statuts surchargés) sont lus ici et injectés :
    # `mocks/` reste sans dépendance à la base
    pm_entries = maintenance_service.get_calendar(session)
    episodes = providers.anomaly_episodes(anomalies_service.get_status_overrides(session))
    derived = mock_reminders.get_reminders(pm_entries, episodes)
    # retire les rappels acquittés / encore sous snooze
    return reminders_service.apply_actions(derived, reminders_service.get_actions(session))


@router.get("", response_model=list[Reminder])
def list_reminders(session: Session = Depends(get_session)) -> list[Reminder]:
    return _active_reminders(session)


@router.get("/count", response_model=ReminderCount)
def count_reminders(session: Session = Depends(get_session)) -> ReminderCount:
    return ReminderCount(count=len(_active_reminders(session)))


@router.post("/{reminder_id}/acknowledge", status_code=204)
def acknowledge_reminder(reminder_id: str, session: Session = Depends(get_session)) -> None:
    reminders_service.acknowledge(session, reminder_id)


@router.post("/{reminder_id}/snooze", status_code=204)
def snooze_reminder(
    reminder_id: str,
    req: SnoozeRequest,
    session: Session = Depends(get_session),
) -> None:
    reminders_service.snooze(session, reminder_id, req.hours)
