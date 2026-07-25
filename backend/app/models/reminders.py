from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ReminderKind(str, Enum):
    upcoming_pm = "upcoming_pm"
    threshold_approach = "threshold_approach"
    unacked_anomaly = "unacked_anomaly"


class ReminderSeverity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class Reminder(BaseModel):
    id: str
    kind: ReminderKind
    equipment: str
    message: str
    due_at: datetime
    severity: ReminderSeverity
