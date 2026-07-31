"""Aiguillage source mock ↔ live des données métier.

Point unique où l'application choisit entre les générateurs mockés (Phases 1–7)
et le pipeline ML validé (Phase 8), selon `settings.data_source`. Les routes
appellent *toujours* ce module, jamais `mocks/` ni `ml/` directement — brancher
le pipeline réel devient alors un changement de configuration (`DATA_SOURCE=live`),
pas une réécriture des routes.

La production des épisodes / overview / forecast est spécifique à la source ;
la surcharge de statut, le filtrage et les agrégations sont partagés
(`services/anomaly_aggregation.py`).
"""
from datetime import datetime

from app.config import settings
from app.ml import anomalies as ml_anomalies
from app.ml import health as ml_health
from app.mocks import anomalies as mock_anomalies
from app.mocks import health as mock_health
from app.models.anomalies import (
    AnomalyEpisode,
    AnomalyHistogram,
    AnomalyStats,
    AnomalyStatus,
    AnomalyWindow,
    HistogramBucket,
    Severity,
    WindowStats,
)
from app.models.health import (
    ForecastHorizon,
    ForecastResponse,
    HealthHistoryResponse,
    HealthOverview,
    HistoryRange,
    PredictedFaultsResponse,
    SubScoreForecastResponse,
)
from app.services import anomaly_aggregation as agg


def _anomaly_source():
    return ml_anomalies if settings.resolved_anomalies_source == "live" else mock_anomalies


def _health_source():
    return ml_health if settings.resolved_health_source == "live" else mock_health


# ---- Santé / forecast ----

def health_overview() -> HealthOverview:
    return _health_source().get_overview()


def health_forecast(horizon: ForecastHorizon) -> ForecastResponse:
    return _health_source().get_forecast(horizon)


def health_history(range_: HistoryRange) -> HealthHistoryResponse:
    return _health_source().get_history(range_)


def health_predicted_faults(horizon: ForecastHorizon) -> PredictedFaultsResponse:
    return _health_source().get_predicted_faults(horizon)


def health_subscore_forecast(horizon: ForecastHorizon) -> SubScoreForecastResponse:
    return _health_source().get_subscore_forecast(horizon)


# ---- Anomalies (source brute + agrégations partagées) ----

def anomaly_episodes(
    overrides: dict[str, AnomalyStatus] | None = None,
    equipment: str | None = None,
    severity: Severity | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[AnomalyEpisode]:
    eps = agg.apply_overrides(_anomaly_source().raw_episodes(), overrides)
    return agg.filter_episodes(eps, equipment, severity, date_from, date_to)


def anomaly_episode_ids() -> frozenset[str]:
    return frozenset(e.id for e in _anomaly_source().raw_episodes())


def anomaly_stats(overrides: dict[str, AnomalyStatus] | None = None) -> AnomalyStats:
    src = _anomaly_source()
    eps = agg.apply_overrides(src.raw_episodes(), overrides)
    return agg.compute_stats(eps, src.window_days())


def anomaly_histogram(bucket: HistogramBucket) -> AnomalyHistogram:
    return agg.compute_histogram(_anomaly_source().raw_episodes(), bucket)


def anomaly_window_stats(window: AnomalyWindow) -> WindowStats:
    # Borne haute = fin de la période observée (donnée par la source), pas l'heure
    # de la requête : cf. `ml/anomalies.reference_now`.
    src = _anomaly_source()
    return agg.compute_window_stats(src.raw_episodes(), window, src.reference_now())
