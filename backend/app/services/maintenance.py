"""Plannings de maintenance préventive : calcul de la prochaine PM + persistance.

Le calendrier de PM est saisi par l'utilisateur : ce ne sont pas des données
mockées et le pipeline ML ne les remplacera pas en Phase 8. Ce module vit donc
dans `services/` et non dans `mocks/` (seul le jeu de démonstration initial
reste dans `mocks/maintenance.py`).
"""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.tables import PMSchedule
from app.models.maintenance import CalendarEntry, PeriodUnit, ScheduleRequest


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    # borne au dernier jour du mois cible (ex. 31 janv + 1 mois → 28/29 févr)
    last_day = (date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(d.day, last_day))


def compute_next_pm(last_pm: date, value: int, unit: PeriodUnit) -> date:
    if unit == PeriodUnit.days:
        return last_pm + timedelta(days=value)
    if unit == PeriodUnit.weeks:
        return last_pm + timedelta(weeks=value)
    return add_months(last_pm, value)


def _to_entry(row: PMSchedule) -> CalendarEntry:
    return CalendarEntry(
        id=f"PM-{row.id:04d}",
        equipment=row.equipment,
        last_pm_date=row.last_pm_date,
        period_value=row.period_value,
        period_unit=PeriodUnit(row.period_unit),
        next_pm_date=row.next_pm_date,
        # recalculé à la lecture pour rester juste au fil des jours
        days_remaining=(row.next_pm_date - date.today()).days,
        assigned_to=row.assigned_to,
        notes=row.notes,
    )


def schedule(session: Session, req: ScheduleRequest) -> CalendarEntry:
    row = PMSchedule(
        equipment=req.equipment,
        last_pm_date=req.last_pm_date,
        period_value=req.period_value,
        period_unit=req.period_unit.value,
        next_pm_date=compute_next_pm(req.last_pm_date, req.period_value, req.period_unit),
        assigned_to=req.assigned_to,
        notes=req.notes,
    )
    session.add(row)
    session.commit()
    return _to_entry(row)


def get_calendar(session: Session) -> list[CalendarEntry]:
    rows = session.scalars(select(PMSchedule).order_by(PMSchedule.next_pm_date)).all()
    return [_to_entry(r) for r in rows]


def _parse_id(pm_id: str) -> int | None:
    """`PM-0004` → 4. None si le format est invalide."""
    prefix, _, num = pm_id.partition("-")
    if prefix != "PM" or not num.isdigit():
        return None
    return int(num)


def update(session: Session, pm_id: str, req: ScheduleRequest) -> CalendarEntry | None:
    """Remplace les champs d'une PM et recalcule la prochaine échéance.
    None si l'entrée n'existe pas (→ 404 côté route)."""
    row_id = _parse_id(pm_id)
    row = session.get(PMSchedule, row_id) if row_id is not None else None
    if row is None:
        return None
    row.equipment = req.equipment
    row.last_pm_date = req.last_pm_date
    row.period_value = req.period_value
    row.period_unit = req.period_unit.value
    row.next_pm_date = compute_next_pm(req.last_pm_date, req.period_value, req.period_unit)
    row.assigned_to = req.assigned_to
    row.notes = req.notes
    session.commit()
    return _to_entry(row)


def delete(session: Session, pm_id: str) -> bool:
    """True si une entrée a été supprimée, False si elle n'existait pas."""
    row_id = _parse_id(pm_id)
    row = session.get(PMSchedule, row_id) if row_id is not None else None
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True
