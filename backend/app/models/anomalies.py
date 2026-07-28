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


class AnomalyDimension(str, Enum):
    """Modèle de détection à l'origine de l'épisode — `environment` (HMM
    temp/humidité, capteur salle) ou `scada` (IsolationForest, alarmes UPS/CLIM/
    ENERGY). Distinct de l'équipement/famille concerné : les deux modèles
    peuvent en principe toucher le même équipement (ex. CLIM via alarme SCADA)."""

    environment = "environment"
    scada = "scada"


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
    # Défaut = environment : seul le pipeline HMM environnemental est branché à
    # ce jour (cf. app/ml/README.md) — aucune anomalie SCADA n'existe encore.
    dimension: AnomalyDimension = AnomalyDimension.environment


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


class AnomalyWindow(str, Enum):
    h24 = "24h"
    d7 = "7d"


class WindowStats(BaseModel):
    """Stats bornées à une fenêtre glissante (24h/7j) — pour le KPI d'ouverture
    de la page Anomalies : total + tendance vs la période précédente de même
    durée, taux sur la fenêtre, famille la plus contributrice, et répartition
    par dimension de détection."""

    window: AnomalyWindow
    total: int
    previous_total: int
    rate_pct: float
    top_family: str | None = None
    top_family_count: int = 0
    by_dimension: dict[AnomalyDimension, int]
    # Fin de la fenêtre réellement utilisée = fin de la période observée, pas
    # l'heure courante. Sur un export historique figé, les deux diffèrent de
    # plusieurs semaines : sans cette date, un « 0 anomalie » se lit comme une
    # page cassée alors qu'il veut dire « rien à signaler sur la période ».
    reference_at: datetime
