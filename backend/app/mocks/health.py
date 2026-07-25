"""Mocks health score + forecast — seed fixe pour des réponses stables."""
import math
import random
from datetime import datetime, timedelta, timezone

from app.mocks.equipment import (
    EXTREME_UPPER,
    MILD_UPPER,
    SOCOMEC_UNITS,
    STULZ_UNITS,
    YANAN_UNITS,
)
from app.models.health import (
    ForecastHorizon,
    ForecastPoint,
    ForecastResponse,
    HealthOverview,
    HealthStatus,
    SubScore,
    ThresholdCrossing,
    Trend,
)

_BASELINE_TEMP = 24.6  # °C moyen salle switch, sous le seuil mild_upper


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)


def get_overview() -> HealthOverview:
    sub_scores = [
        SubScore(
            family="stulz",
            label="Climatisation — STULZ ASD 522 AS",
            score=82.0,
            status=HealthStatus.healthy,
            trend=Trend.stable,
            unit_count=len(STULZ_UNITS),
        ),
        SubScore(
            family="socomec",
            label="Onduleurs — SOCOMEC 200kVA",
            score=91.0,
            status=HealthStatus.healthy,
            trend=Trend.up,
            unit_count=len(SOCOMEC_UNITS),
        ),
        SubScore(
            family="yanan",
            label="Groupes électrogènes — YANAN",
            score=70.0,
            status=HealthStatus.watch,
            trend=Trend.stable,
            unit_count=len(YANAN_UNITS),
            note="Baseline en cours d'établissement (installés 2025) — score indicatif",
        ),
    ]
    global_score = round(sum(s.score * s.unit_count for s in sub_scores)
                         / sum(s.unit_count for s in sub_scores), 1)
    return HealthOverview(
        global_score=global_score,
        status=HealthStatus.healthy if global_score >= 75 else HealthStatus.watch,
        sub_scores=sub_scores,
        updated_at=_now(),
    )


_HORIZON_CONFIG = {
    # horizon: (step, nb points historiques, nb points prévus)
    ForecastHorizon.h24: (timedelta(hours=1), 24, 24),
    ForecastHorizon.d7: (timedelta(hours=6), 28, 28),
    ForecastHorizon.d30: (timedelta(days=1), 30, 30),
}


def get_forecast(horizon: ForecastHorizon) -> ForecastResponse:
    rng = random.Random(42)
    step, n_hist, n_fcst = _HORIZON_CONFIG[horizon]
    now = _now()
    points: list[ForecastPoint] = []

    for i in range(-n_hist, n_fcst + 1):
        ts = now + i * step
        # cycle journalier + dérive légère sur la fenêtre de prévision
        hours = (ts - now).total_seconds() / 3600
        daily = 1.1 * math.sin(2 * math.pi * (ts.hour - 15) / 24)
        drift = max(0.0, hours) * 0.010
        value = _BASELINE_TEMP + daily + drift + rng.uniform(-0.25, 0.25)
        is_forecast = i > 0
        band = 0.15 if not is_forecast else 0.3 + 0.9 * (i / n_fcst)
        points.append(ForecastPoint(
            timestamp=ts,
            value=round(value, 2),
            lower=round(value - band, 2),
            upper=round(value + band, 2),
            is_forecast=is_forecast,
        ))

    crossings = [
        ThresholdCrossing(
            timestamp=p.timestamp,
            threshold=MILD_UPPER if p.upper < EXTREME_UPPER else EXTREME_UPPER,
            severity=HealthStatus.watch if p.upper < EXTREME_UPPER else HealthStatus.critical,
        )
        for p in points
        if p.is_forecast and p.upper >= MILD_UPPER
    ]
    return ForecastResponse(horizon=horizon, points=points, threshold_crossings=crossings)
