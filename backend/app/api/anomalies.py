from datetime import datetime

from fastapi import APIRouter, Query

from app.mocks import anomalies as mock_anomalies
from app.models.anomalies import AnomalyEpisode, AnomalyStats, Severity

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("", response_model=list[AnomalyEpisode])
def list_anomalies(
    equipment: str | None = None,
    severity: Severity | None = None,
    date_from: datetime | None = Query(None, alias="from"),
    date_to: datetime | None = Query(None, alias="to"),
) -> list[AnomalyEpisode]:
    return mock_anomalies.get_episodes(equipment, severity, date_from, date_to)


@router.get("/stats", response_model=AnomalyStats)
def get_stats() -> AnomalyStats:
    return mock_anomalies.get_stats()
