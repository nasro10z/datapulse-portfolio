from fastapi import APIRouter

from app.mocks import maintenance as mock_maintenance
from app.models.maintenance import CalendarEntry, ScheduleRequest

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.post("/schedule", response_model=CalendarEntry, status_code=201)
def schedule_pm(req: ScheduleRequest) -> CalendarEntry:
    return mock_maintenance.schedule(req)


@router.get("/calendar", response_model=list[CalendarEntry])
def get_calendar() -> list[CalendarEntry]:
    return mock_maintenance.get_calendar()
