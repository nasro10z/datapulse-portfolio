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
from app.models.anomalies import Severity
from app.models.health import (
    DomainScore,
    EquipmentFamily,
    ForecastHorizon,
    ForecastPoint,
    ForecastResponse,
    HealthDomain,
    HealthHistoryPoint,
    HealthHistoryResponse,
    HealthOverview,
    HealthStatus,
    HistoryRange,
    PredictedFault,
    PredictedFaultsResponse,
    SubScore,
    SubScoreForecastResponse,
    SubScoreSeries,
    ThresholdCrossing,
    Trend,
)

_BASELINE_TEMP = 24.6  # °C moyen salle switch, sous le seuil mild_upper

# Seuils de statut par score (0-100), alignés sur la référence de design Identity v2.
_HEALTHY_MIN = 82.0
_WATCH_MIN = 68.0

# Poids des domaines dans le score global (somme = 100) — décomposition Site Health,
# distincte de la décomposition par famille d'équipement (Forecast).
_DOMAIN_WEIGHTS = {
    HealthDomain.environment: 0.40,
    HealthDomain.energy: 0.35,
    HealthDomain.battery: 0.25,
}

# Scores de démonstration par domaine (courant, précédent) + note contextuelle.
_DOMAIN_DEMO = {
    HealthDomain.environment: (87.0, 85.0, "Temp 23,4 °C · HR 46 % · 10 salles dans la plage"),
    HealthDomain.energy: (81.0, 83.0, "Charge onduleur 68 % · FP 0,98 · secteur stable"),
    HealthDomain.battery: (66.0, 69.0, "2 chaînes · capacité UPS-2 en dégradation"),
}

# Démo par famille d'équipement (score courant, tendance) — décomposition Forecast.
_FAMILY_LABEL = {
    EquipmentFamily.stulz: "Climatisation — STULZ ASD 522 AS",
    EquipmentFamily.socomec: "Onduleurs — SOCOMEC 200kVA",
    EquipmentFamily.yanan: "Groupes électrogènes — YANAN",
}
_FAMILY_UNIT_COUNT = {
    EquipmentFamily.stulz: len(STULZ_UNITS),
    EquipmentFamily.socomec: len(SOCOMEC_UNITS),
    EquipmentFamily.yanan: len(YANAN_UNITS),
}
_FAMILY_SCORE = {EquipmentFamily.stulz: 82.0, EquipmentFamily.socomec: 91.0, EquipmentFamily.yanan: 70.0}
_FAMILY_STATUS = {
    EquipmentFamily.stulz: HealthStatus.healthy,
    EquipmentFamily.socomec: HealthStatus.healthy,
    EquipmentFamily.yanan: HealthStatus.watch,
}
_FAMILY_TREND = {EquipmentFamily.stulz: Trend.stable, EquipmentFamily.socomec: Trend.up, EquipmentFamily.yanan: Trend.stable}
_FAMILY_NOTE = {
    EquipmentFamily.yanan: "Baseline en cours d'établissement (installés 2025) — score indicatif",
}

# Seeds fixes (déterministes, indépendants du hash aléatoire du process) par fenêtre.
_RANGE_SEED = {"7d": 701, "30d": 730, "90d": 790}
_HORIZON_SEED = {"24h": 124, "7d": 107, "30d": 130}


def _status_for(score: float) -> HealthStatus:
    if score >= _HEALTHY_MIN:
        return HealthStatus.healthy
    if score >= _WATCH_MIN:
        return HealthStatus.watch
    return HealthStatus.critical


def _weighted(scores: dict[HealthDomain, float]) -> float:
    return round(sum(scores[d] * w for d, w in _DOMAIN_WEIGHTS.items()), 1)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)


def get_overview() -> HealthOverview:
    sub_scores = [
        SubScore(
            family=family,
            label=_FAMILY_LABEL[family],
            score=_FAMILY_SCORE[family],
            status=_FAMILY_STATUS[family],
            trend=_FAMILY_TREND[family],
            unit_count=_FAMILY_UNIT_COUNT[family],
            note=_FAMILY_NOTE.get(family),
        )
        for family in EquipmentFamily
    ]
    domain_scores = [
        DomainScore(
            domain=domain,
            score=score,
            status=_status_for(score),
            previous_score=previous,
            note=note,
        )
        for domain, (score, previous, note) in _DOMAIN_DEMO.items()
    ]
    global_score = _weighted({d.domain: d.score for d in domain_scores})
    previous_score = _weighted({d.domain: d.previous_score for d in domain_scores})
    return HealthOverview(
        global_score=global_score,
        previous_score=previous_score,
        status=_status_for(global_score),
        sub_scores=sub_scores,
        domain_scores=domain_scores,
        updated_at=_now(),
    )


_HISTORY_CONFIG = {
    HistoryRange.d7: (timedelta(days=1), 7),
    HistoryRange.d30: (timedelta(days=1), 30),
    HistoryRange.d90: (timedelta(days=1), 90),
}


def get_history(range_: HistoryRange) -> HealthHistoryResponse:
    """Historique quotidien par domaine, se terminant exactement sur les scores
    courants (marche aléatoire seedée en amont pour rester stable entre appels)."""
    rng = random.Random(_RANGE_SEED[range_.value])
    step, n = _HISTORY_CONFIG[range_]
    now = _now()

    series: dict[HealthDomain, list[float]] = {}
    for domain, (current, _previous, _note) in _DOMAIN_DEMO.items():
        walk = [current]
        for _ in range(n - 1):
            walk.append(max(0.0, min(100.0, walk[-1] + rng.uniform(-1.4, 1.4))))
        walk.reverse()  # du plus ancien au plus récent
        walk[-1] = current  # se termine exactement sur le score courant
        series[domain] = walk

    points = [
        HealthHistoryPoint(
            timestamp=now - (n - 1 - i) * step,
            global_score=_weighted({d: series[d][i] for d in HealthDomain}),
            environment=round(series[HealthDomain.environment][i], 1),
            energy=round(series[HealthDomain.energy][i], 1),
            battery=round(series[HealthDomain.battery][i], 1),
        )
        for i in range(n)
    ]
    return HealthHistoryResponse(range=range_, points=points)


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


_HEALTH_TO_SEVERITY = {HealthStatus.watch: Severity.alert, HealthStatus.critical: Severity.critical}


def get_predicted_faults(horizon: ForecastHorizon) -> PredictedFaultsResponse:
    """Prochaine panne estimée par famille — couche d'aide à la décision, pas une
    alarme automatique. STULZ (climatisation) est dérivé du forecast environnemental
    réel (HMM, seuils Tukey) ; SOCOMEC/YANAN sont des démonstrations le temps que
    des modèles de prévision équivalents soient validés pour ces familles."""
    env_forecast = get_forecast(horizon)
    first_crossing = next(iter(env_forecast.threshold_crossings), None)

    step, _, n_fcst = _HORIZON_CONFIG[horizon]
    faults = [
        PredictedFault(
            family=EquipmentFamily.stulz,
            label=_FAMILY_LABEL[EquipmentFamily.stulz],
            predicted_at=first_crossing.timestamp if first_crossing else None,
            severity=_HEALTH_TO_SEVERITY[first_crossing.severity] if first_crossing else None,
            note=(
                "Basé sur le modèle de prévision température (HMM, seuils Tukey 26,75 / 28,65 °C)."
                if first_crossing else
                "Aucun franchissement de seuil de température prévu sur cet horizon."
            ),
        ),
        PredictedFault(
            family=EquipmentFamily.socomec,
            label=_FAMILY_LABEL[EquipmentFamily.socomec],
            predicted_at=None,
            severity=None,
            note="Aucune dégradation prévue sur cet horizon.",
        ),
        PredictedFault(
            family=EquipmentFamily.yanan,
            label=_FAMILY_LABEL[EquipmentFamily.yanan],
            predicted_at=_now() + step * max(1, n_fcst // 2),
            severity=Severity.alert,
            note="Baseline en cours d'établissement (installés 2025) — estimation indicative.",
        ),
    ]
    return PredictedFaultsResponse(horizon=horizon, faults=faults)


def get_subscore_forecast(horizon: ForecastHorizon) -> SubScoreForecastResponse:
    """Prévision de score (0-100) par famille d'équipement, même fenêtre que le
    forecast global — historique plein + prévision avec bande élargie."""
    step, n_hist, n_fcst = _HORIZON_CONFIG[horizon]
    now = _now()
    seed = _HORIZON_SEED[horizon.value]

    series = []
    for offset, family in enumerate(EquipmentFamily):
        rng = random.Random(seed + offset * 13)
        baseline = _FAMILY_SCORE[family]
        points: list[ForecastPoint] = []
        for i in range(-n_hist, n_fcst + 1):
            ts = now + i * step
            drift = -0.03 * max(0, i) if family != EquipmentFamily.socomec else 0.02 * max(0, i)
            value = max(0.0, min(100.0, baseline + drift + rng.uniform(-1.2, 1.2)))
            is_forecast = i > 0
            band = 0.5 if not is_forecast else 1.2 + 2.5 * (i / n_fcst)
            points.append(ForecastPoint(
                timestamp=ts,
                value=round(value, 1),
                lower=round(max(0.0, value - band), 1),
                upper=round(min(100.0, value + band), 1),
                is_forecast=is_forecast,
            ))
        series.append(SubScoreSeries(family=family, label=_FAMILY_LABEL[family], points=points))
    return SubScoreForecastResponse(horizon=horizon, series=series)
