"""Store in-memory des PM planifiées + calcul de la prochaine PM."""
import itertools
from datetime import date, timedelta

from app.models.maintenance import CalendarEntry, PeriodUnit, ScheduleRequest

_counter = itertools.count(1)
_STORE: dict[str, CalendarEntry] = {}


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


def schedule(req: ScheduleRequest) -> CalendarEntry:
    next_pm = compute_next_pm(req.last_pm_date, req.period_value, req.period_unit)
    entry = CalendarEntry(
        id=f"PM-{next(_counter):04d}",
        equipment=req.equipment,
        last_pm_date=req.last_pm_date,
        period_value=req.period_value,
        period_unit=req.period_unit,
        next_pm_date=next_pm,
        days_remaining=(next_pm - date.today()).days,
    )
    _STORE[entry.id] = entry
    return entry


def get_calendar() -> list[CalendarEntry]:
    # days_remaining recalculé à la lecture pour rester juste au fil des jours
    entries = [
        e.model_copy(update={"days_remaining": (e.next_pm_date - date.today()).days})
        for e in _STORE.values()
    ]
    return sorted(entries, key=lambda e: e.next_pm_date)


def _seed() -> None:
    if _STORE:
        return
    today = date.today()
    seeds = [
        ("STULZ-03", today - timedelta(days=80), 3, PeriodUnit.months),
        ("STULZ-07", today - timedelta(days=55), 3, PeriodUnit.months),
        ("UPS-01", today - timedelta(days=150), 6, PeriodUnit.months),
        ("GEN-01", today - timedelta(days=20), 4, PeriodUnit.weeks),
    ]
    for equipment, last_pm, value, unit in seeds:
        schedule(ScheduleRequest(
            equipment=equipment, last_pm_date=last_pm,
            period_value=value, period_unit=unit,
        ))


_seed()
