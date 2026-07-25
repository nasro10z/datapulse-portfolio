from datetime import datetime
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


class AnomalyStats(BaseModel):
    total: int
    anomaly_rate_pct: float
    mtba_hours: float
    by_type: dict[AnomalyType, int]
    by_severity: dict[Severity, int]
    by_direction: dict[Direction, int]
    top_equipment: str
    top_equipment_count: int
