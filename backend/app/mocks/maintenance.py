"""Jeu de démonstration du calendrier de PM.

Contenu de démo uniquement : le calcul de date et la persistance vivent dans
`app/services/maintenance.py` (données saisies par l'utilisateur, pas mockées).
"""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.tables import PMSchedule
from app.models.maintenance import PeriodUnit, ScheduleRequest
from app.services import maintenance as maintenance_service

# (équipement, ancienneté de la dernière PM en jours, période, unité)
_SEEDS = [
    ("STULZ-03", 80, 3, PeriodUnit.months),
    ("STULZ-07", 55, 3, PeriodUnit.months),
    ("UPS-01", 150, 6, PeriodUnit.months),
    ("GEN-01", 20, 4, PeriodUnit.weeks),
]


def seed_demo_calendar(session: Session) -> None:
    """Insère le jeu de démo si le calendrier est vide. Sans effet sinon —
    les PM saisies par l'utilisateur ne sont jamais écrasées."""
    if session.scalar(select(PMSchedule.id).limit(1)) is not None:
        return
    today = date.today()
    for equipment, days_ago, value, unit in _SEEDS:
        maintenance_service.schedule(session, ScheduleRequest(
            equipment=equipment,
            last_pm_date=today - timedelta(days=days_ago),
            period_value=value,
            period_unit=unit,
        ))
