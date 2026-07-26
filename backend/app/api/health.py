from fastapi import APIRouter

from app import providers
from app.models.health import ForecastHorizon, ForecastResponse, HealthOverview

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/overview", response_model=HealthOverview)
def get_overview() -> HealthOverview:
    return providers.health_overview()


@router.get("/forecast", response_model=ForecastResponse)
def get_forecast(horizon: ForecastHorizon = ForecastHorizon.h24) -> ForecastResponse:
    return providers.health_forecast(horizon)
