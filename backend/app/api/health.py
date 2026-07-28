from fastapi import APIRouter

from app import providers
from app.models.health import (
    ForecastHorizon,
    ForecastResponse,
    HealthHistoryResponse,
    HealthOverview,
    HistoryRange,
    PredictedFaultsResponse,
    SubScoreForecastResponse,
)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/overview", response_model=HealthOverview)
def get_overview() -> HealthOverview:
    return providers.health_overview()


@router.get("/forecast", response_model=ForecastResponse)
def get_forecast(horizon: ForecastHorizon = ForecastHorizon.h24) -> ForecastResponse:
    return providers.health_forecast(horizon)


@router.get("/history", response_model=HealthHistoryResponse)
def get_history(range: HistoryRange = HistoryRange.d7) -> HealthHistoryResponse:
    return providers.health_history(range)


@router.get("/predicted-faults", response_model=PredictedFaultsResponse)
def get_predicted_faults(horizon: ForecastHorizon = ForecastHorizon.h24) -> PredictedFaultsResponse:
    return providers.health_predicted_faults(horizon)


@router.get("/forecast/sub-scores", response_model=SubScoreForecastResponse)
def get_subscore_forecast(horizon: ForecastHorizon = ForecastHorizon.h24) -> SubScoreForecastResponse:
    return providers.health_subscore_forecast(horizon)
