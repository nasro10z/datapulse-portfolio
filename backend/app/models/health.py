from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EquipmentFamily(str, Enum):
    stulz = "stulz"
    socomec = "socomec"
    yanan = "yanan"


class HealthStatus(str, Enum):
    healthy = "healthy"
    watch = "watch"
    critical = "critical"


class Trend(str, Enum):
    up = "up"
    stable = "stable"
    down = "down"


class SubScore(BaseModel):
    family: EquipmentFamily
    label: str
    score: float = Field(ge=0, le=100)
    status: HealthStatus
    trend: Trend
    unit_count: int
    note: str | None = None


class HealthOverview(BaseModel):
    global_score: float = Field(ge=0, le=100)
    status: HealthStatus
    sub_scores: list[SubScore]
    updated_at: datetime


class ForecastHorizon(str, Enum):
    h24 = "24h"
    d7 = "7d"
    d30 = "30d"


class ForecastPoint(BaseModel):
    timestamp: datetime
    value: float
    lower: float
    upper: float
    is_forecast: bool


class ThresholdCrossing(BaseModel):
    timestamp: datetime
    threshold: float
    severity: HealthStatus


class ForecastResponse(BaseModel):
    horizon: ForecastHorizon
    points: list[ForecastPoint]
    threshold_crossings: list[ThresholdCrossing]
