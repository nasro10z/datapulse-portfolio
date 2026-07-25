from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.mocks import anomalies as mock_anomalies
from app.models.anomalies import (
    AnomalyEpisode,
    AnomalyStats,
    HistogramBucket,
    HistogramResponse,
    Severity,
    StatusUpdate,
)

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


@router.get("/histogram", response_model=HistogramResponse)
def get_histogram(bucket: HistogramBucket = HistogramBucket.day) -> HistogramResponse:
    return mock_anomalies.get_histogram(bucket)


@router.patch("/{episode_id}", response_model=AnomalyEpisode)
def update_status(episode_id: str, payload: StatusUpdate) -> AnomalyEpisode:
    episode = mock_anomalies.set_status(episode_id, payload.status)
    if episode is None:
        raise HTTPException(status_code=404, detail=f"Épisode inconnu : {episode_id}")
    return episode
