from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.models.anomalies import Severity


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


class HealthDomain(str, Enum):
    """Répartition du score global par domaine (Site Health), distincte de la
    répartition par famille d'équipement (Forecast) — deux vues d'un même score."""

    environment = "environment"
    energy = "energy"
    battery = "battery"


class DomainScore(BaseModel):
    domain: HealthDomain
    score: float = Field(ge=0, le=100)
    status: HealthStatus
    previous_score: float = Field(ge=0, le=100)
    note: str | None = None


class HealthOverview(BaseModel):
    global_score: float = Field(ge=0, le=100)
    previous_score: float = Field(ge=0, le=100)
    status: HealthStatus
    sub_scores: list[SubScore]
    domain_scores: list[DomainScore]
    updated_at: datetime


class HistoryRange(str, Enum):
    d7 = "7d"
    d30 = "30d"
    d90 = "90d"


class HealthHistoryPoint(BaseModel):
    timestamp: datetime
    global_score: float = Field(ge=0, le=100)
    environment: float = Field(ge=0, le=100)
    energy: float = Field(ge=0, le=100)
    battery: float = Field(ge=0, le=100)


class HealthHistoryResponse(BaseModel):
    range: HistoryRange
    points: list[HealthHistoryPoint]


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


class PredictedFault(BaseModel):
    """Prochaine panne estimée pour une famille d'équipement — couche d'aide à la
    décision : une fenêtre de risque indicative, pas une alarme ni une certitude."""

    family: EquipmentFamily
    label: str
    predicted_at: datetime | None = None
    severity: Severity | None = None
    note: str | None = None


class PredictedFaultsResponse(BaseModel):
    horizon: ForecastHorizon
    faults: list[PredictedFault]


class SubScoreSeries(BaseModel):
    family: EquipmentFamily
    label: str
    points: list[ForecastPoint]


class SubScoreForecastResponse(BaseModel):
    horizon: ForecastHorizon
    series: list[SubScoreSeries]
