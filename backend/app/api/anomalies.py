from datetime import datetime

<<<<<<< HEAD
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import providers
from app.db.app_db import get_session
from app.models.anomalies import (
    AnomalyEpisode,
    AnomalyHistogram,
    AnomalyStats,
    HistogramBucket,
    Severity,
    StatusUpdate,
)
from app.services import anomalies as anomalies_service
=======
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
>>>>>>> b9028691a7679fd48982e990d9e01752e3b0c38a

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("", response_model=list[AnomalyEpisode])
def list_anomalies(
    equipment: str | None = None,
    severity: Severity | None = None,
    date_from: datetime | None = Query(None, alias="from"),
    date_to: datetime | None = Query(None, alias="to"),
    session: Session = Depends(get_session),
) -> list[AnomalyEpisode]:
    overrides = anomalies_service.get_status_overrides(session)
    return providers.anomaly_episodes(overrides, equipment, severity, date_from, date_to)


@router.get("/stats", response_model=AnomalyStats)
<<<<<<< HEAD
def get_stats(session: Session = Depends(get_session)) -> AnomalyStats:
    return providers.anomaly_stats(anomalies_service.get_status_overrides(session))


@router.get("/histogram", response_model=AnomalyHistogram)
def get_histogram(bucket: HistogramBucket = HistogramBucket.day) -> AnomalyHistogram:
    return providers.anomaly_histogram(bucket)


@router.patch("/{episode_id}", response_model=AnomalyEpisode)
def update_status(
    episode_id: str,
    update: StatusUpdate,
    session: Session = Depends(get_session),
) -> AnomalyEpisode:
    if episode_id not in providers.anomaly_episode_ids():
        raise HTTPException(status_code=404, detail=f"Épisode {episode_id} introuvable")
    anomalies_service.set_status(session, episode_id, update.status)
    overrides = anomalies_service.get_status_overrides(session)
    # renvoie l'épisode avec son statut à jour
    return next(e for e in providers.anomaly_episodes(overrides) if e.id == episode_id)
=======
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
>>>>>>> b9028691a7679fd48982e990d9e01752e3b0c38a
