from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.app_db import get_session
from app.models.maintenance import CalendarEntry, ScheduleRequest
from app.services import maintenance as maintenance_service

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.post("/schedule", response_model=CalendarEntry, status_code=201)
def schedule_pm(
    req: ScheduleRequest,
    session: Session = Depends(get_session),
) -> CalendarEntry:
    return maintenance_service.schedule(session, req)


@router.get("/calendar", response_model=list[CalendarEntry])
def get_calendar(session: Session = Depends(get_session)) -> list[CalendarEntry]:
    return maintenance_service.get_calendar(session)
