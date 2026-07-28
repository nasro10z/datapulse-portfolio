from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.app_db import get_session
from app.mocks.equipment import ALL_UNITS
from app.models.maintenance import CalendarEntry, ScheduleRequest
from app.services import maintenance as maintenance_service

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.get("/equipment", response_model=list[str])
def list_equipment() -> list[str]:
    """Parc réel du site — pour peupler le sélecteur d'équipement du formulaire."""
    return ALL_UNITS


@router.post("/schedule", response_model=CalendarEntry, status_code=201)
def schedule_pm(
    req: ScheduleRequest,
    session: Session = Depends(get_session),
) -> CalendarEntry:
    return maintenance_service.schedule(session, req)


@router.get("/calendar", response_model=list[CalendarEntry])
def get_calendar(session: Session = Depends(get_session)) -> list[CalendarEntry]:
    return maintenance_service.get_calendar(session)


@router.patch("/schedule/{pm_id}", response_model=CalendarEntry)
def update_pm(
    pm_id: str,
    req: ScheduleRequest,
    session: Session = Depends(get_session),
) -> CalendarEntry:
    entry = maintenance_service.update(session, pm_id, req)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Planning {pm_id} introuvable")
    return entry


@router.delete("/schedule/{pm_id}", status_code=204)
def delete_pm(pm_id: str, session: Session = Depends(get_session)) -> None:
    if not maintenance_service.delete(session, pm_id):
        raise HTTPException(status_code=404, detail=f"Planning {pm_id} introuvable")
