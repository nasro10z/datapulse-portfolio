from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    alert = "alert"
    critical = "critical"


class AnomalyType(str, Enum):
    collective = "collective"
    duration = "duration"
    sequence = "sequence"


class Direction(str, Enum):
    high = "high"
    low = "low"


class AnomalyStatus(str, Enum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"


class AnomalyEpisode(BaseModel):
    id: str
    equipment: str
    type: AnomalyType
    severity: Severity
    direction: Direction
    start: datetime
    duration_min: float = Field(gt=0)
    peak_value: float
    status: AnomalyStatus


class HistogramBucket(str, Enum):
    day = "day"
    week = "week"
    month = "month"


class HistogramBin(BaseModel):
    """Un intervalle de temps et le nombre d'épisodes qui y démarrent."""

    period_start: datetime
    total: int
    alert: int
    critical: int


class HistogramResponse(BaseModel):
    bucket: HistogramBucket
    bins: list[HistogramBin]


class StatusUpdate(BaseModel):
    status: AnomalyStatus


class AnomalyStats(BaseModel):
    total: int
    anomaly_rate_pct: float
    mtba_hours: float
    by_type: dict[AnomalyType, int]
    by_severity: dict[Severity, int]
    by_direction: dict[Direction, int]
    by_status: dict[AnomalyStatus, int]
    top_equipment: str
    top_equipment_count: int


class StatusUpdate(BaseModel):
    """Corps du PATCH d'acquittement/résolution — action de l'utilisateur."""
    status: AnomalyStatus


class HistogramBucket(str, Enum):
    day = "day"
    week = "week"
    month = "month"


class HistogramBin(BaseModel):
    period_start: date
    total: int
    by_severity: dict[Severity, int]


class AnomalyHistogram(BaseModel):
    bucket: HistogramBucket
    bins: list[HistogramBin]
