from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import providers
from app.db.app_db import get_session
from app.models.anomalies import (
    AnomalyEpisode,
    AnomalyHistogram,
    AnomalyStats,
    AnomalyWindow,
    HistogramBucket,
    Severity,
    StatusUpdate,
    WindowStats,
)
from app.services import anomalies as anomalies_service

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
def get_stats(session: Session = Depends(get_session)) -> AnomalyStats:
    return providers.anomaly_stats(anomalies_service.get_status_overrides(session))


@router.get("/histogram", response_model=AnomalyHistogram)
def get_histogram(bucket: HistogramBucket = HistogramBucket.day) -> AnomalyHistogram:
    return providers.anomaly_histogram(bucket)


@router.get("/window-stats", response_model=WindowStats)
def get_window_stats(window: AnomalyWindow = AnomalyWindow.h24) -> WindowStats:
    return providers.anomaly_window_stats(window)


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
