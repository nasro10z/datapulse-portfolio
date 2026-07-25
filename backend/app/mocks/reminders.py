"""Rappels dérivés des autres mocks : PM à venir, seuils approchants,
anomalies non acquittées. Couche d'aide à la décision — les rappels
informent, ils ne déclenchent aucune action."""
from datetime import datetime, time, timedelta, timezone

from app.mocks import anomalies as mock_anomalies
from app.mocks import maintenance as mock_maintenance
from app.mocks.equipment import MILD_UPPER
from app.models.anomalies import AnomalyStatus, Severity
from app.models.reminders import Reminder, ReminderKind, ReminderSeverity


def get_reminders() -> list[Reminder]:
    now = datetime.now(timezone.utc)
    reminders: list[Reminder] = []

    for entry in mock_maintenance.get_calendar():
        if entry.days_remaining <= 14:
            overdue = entry.days_remaining < 0
            reminders.append(Reminder(
                id=f"RM-PM-{entry.id}",
                kind=ReminderKind.upcoming_pm,
                equipment=entry.equipment,
                message=(
                    f"PM en retard de {-entry.days_remaining} j pour {entry.equipment}"
                    if overdue else
                    f"PM prévue dans {entry.days_remaining} j pour {entry.equipment}"
                ),
                due_at=datetime.combine(entry.next_pm_date, time.min, tzinfo=timezone.utc),
                severity=ReminderSeverity.warning if overdue else ReminderSeverity.info,
            ))

    for ep in mock_anomalies.get_episodes():
        if ep.status == AnomalyStatus.open:
            reminders.append(Reminder(
                id=f"RM-AN-{ep.id}",
                kind=ReminderKind.unacked_anomaly,
                equipment=ep.equipment,
                message=f"Anomalie {ep.severity.value} non acquittée sur {ep.equipment} "
                        f"(pic {ep.peak_value}°C)",
                due_at=ep.start,
                severity=(ReminderSeverity.critical if ep.severity == Severity.critical
                          else ReminderSeverity.warning),
            ))

    reminders.append(Reminder(
        id="RM-TH-0001",
        kind=ReminderKind.threshold_approach,
        equipment="SALLE_SWITCH",
        message=f"Température prévue proche du seuil alerte ({MILD_UPPER}°C) sous 24h",
        due_at=now + timedelta(hours=18),
        severity=ReminderSeverity.warning,
    ))

    return sorted(reminders, key=lambda r: r.due_at)
