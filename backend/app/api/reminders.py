from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.app_db import get_session
from app.mocks import anomalies as mock_anomalies
from app.mocks import reminders as mock_reminders
from app.models.reminders import Reminder
from app.services import anomalies as anomalies_service
from app.services import maintenance as maintenance_service

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[Reminder])
def list_reminders(session: Session = Depends(get_session)) -> list[Reminder]:
    # calendrier et épisodes (statuts surchargés) sont lus ici et injectés :
    # `mocks/` reste sans dépendance à la base
    pm_entries = maintenance_service.get_calendar(session)
    episodes = mock_anomalies.get_episodes(anomalies_service.get_status_overrides(session))
    return mock_reminders.get_reminders(pm_entries, episodes)
