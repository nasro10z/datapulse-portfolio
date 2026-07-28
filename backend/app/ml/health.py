"""Source LIVE santé + forecast — lecture du gold, aucun calcul.

Tout ce qui est servi ici a été calculé par l'ETL (`etl/score.py`,
`etl/forecast.py`) à partir du scoring validé (`ml/health_score`, portage du
notebook `health_scores.ipynb`). Cette couche ne fait que **traduire des lignes
gold en modèles Pydantic** : aucun modèle n'est chargé, aucun DataFrame n'est
calculé sur le chemin de requête.

Si le gold est vide (ETL jamais lancé), les getters lèvent `NotImplementedError`
avec la marche à suivre — l'API répond alors 501, pas un 500 opaque.
"""
from datetime import timedelta

import pandas as pd

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
)
from app.storage.analytics_db import get_analytics_sessionmaker
from app.storage.repositories import gold_repo

_NO_GOLD = (
    "Gold santé vide : lancer le pipeline ETL (`python -m app.etl.run --train` "
    "depuis backend/) avant de servir la source live."
)

# Seuils de statut sur le score de santé — mêmes bornes que le scoring
# (`ml/health_score/config.STATUS_BINS`), ramenées aux 3 niveaux de l'API.
_HEALTHY_MIN = 90.0
_WATCH_MIN = 60.0

_HISTORY_DAYS = {HistoryRange.d7: 7, HistoryRange.d30: 30, HistoryRange.d90: 90}

# Domaine ↔ clé `family` — miroir de `etl/score.DOMAIN_TO_FAMILY` (l'interface
# libelle ces trois cartes par domaine, cf. docstring de ce module ETL).
_DOMAIN_COLUMN = {
    HealthDomain.environment: "environmental_health_score",
    HealthDomain.energy: "energy_health_score",
    HealthDomain.battery: "battery_health_score",
}
_FAMILY_DOMAIN = {
    EquipmentFamily.stulz: HealthDomain.environment,
    EquipmentFamily.socomec: HealthDomain.energy,
    EquipmentFamily.yanan: HealthDomain.battery,
}
_DOMAIN_FAMILY = {domain: family for family, domain in _FAMILY_DOMAIN.items()}

_DOMAIN_LABELS = {
    HealthDomain.environment: "Environnement — température et humidité de salle",
    HealthDomain.energy: "Énergie — alimentation secteur, basculements et groupe",
    HealthDomain.battery: "Batterie — chaînes batterie des onduleurs",
}

# Écart de score (24 h) au-delà duquel on parle de dégradation — même seuil que
# le libellé de tendance du scoring.
_TREND_THRESHOLD = 5.0


def _status_for(score: float) -> HealthStatus:
    if score >= _HEALTHY_MIN:
        return HealthStatus.healthy
    if score >= _WATCH_MIN:
        return HealthStatus.watch
    return HealthStatus.critical


def _session():
    return get_analytics_sessionmaker()()


def _require(value, message: str = _NO_GOLD):
    if value is None or (hasattr(value, "__len__") and len(value) == 0):
        raise NotImplementedError(message)
    return value


# ------------------------------------------------------------------- aperçu
def get_overview() -> HealthOverview:
    """Score global + sous-scores (familles) + scores par domaine.

    Le `previous_score` d'un domaine est sa valeur **24 h plus tôt** : c'est le
    delta que l'interface affiche, et c'est aussi l'horizon sur lequel le scoring
    qualifie une tendance.
    """
    with _session() as session:
        rows = _require(gold_repo.read_health_scores(session))
        hourly = _require(gold_repo.read_health_hourly(session))

    latest_ts = hourly.index[-1]
    previous = hourly.loc[hourly.index <= latest_ts - timedelta(hours=24)]
    previous_row = previous.iloc[-1] if not previous.empty else hourly.iloc[0]
    latest = hourly.iloc[-1]

    global_row = next(r for r in rows if r.scope == "global")
    family_rows = {r.family: r for r in rows if r.scope == "family"}

    sub_scores = [
        SubScore(
            family=family, label=row.label, score=row.score, status=row.status,
            trend=row.trend, unit_count=row.unit_count, note=row.note,
        )
        for family in EquipmentFamily
        if (row := family_rows.get(family.value)) is not None
    ]

    # Statut déduit du score **arrondi**, celui qui est affiché : sinon un 89,96
    # montré « 90,0 » porterait un statut qui contredit la valeur à l'écran.
    domain_scores = [
        DomainScore(
            domain=domain,
            score=(score := round(float(latest[column]), 1)),
            status=_status_for(score),
            previous_score=round(float(previous_row[column]), 1),
            note=getattr(family_rows.get(_DOMAIN_FAMILY[domain].value), "note", None),
        )
        for domain, column in _DOMAIN_COLUMN.items()
    ]

    return HealthOverview(
        global_score=global_row.score,
        previous_score=round(float(previous_row["overall_site_health"]), 1),
        status=global_row.status,
        sub_scores=sub_scores,
        domain_scores=domain_scores,
        updated_at=latest_ts.to_pydatetime(),
    )


# --------------------------------------------------------------- historique
def get_history(range_: HistoryRange) -> HealthHistoryResponse:
    """Série **quotidienne** du score global et des trois domaines.

    Les scores sont horaires en gold ; la moyenne journalière est ce que montrent
    les graphiques d'évolution — une courbe horaire sur 90 jours serait illisible
    et dominée par le bruit intra-journalier.
    """
    with _session() as session:
        hourly = _require(gold_repo.read_health_hourly(session))

    days = _HISTORY_DAYS[range_]
    daily = hourly[
        ["overall_site_health", *(_DOMAIN_COLUMN[d] for d in HealthDomain)]
    ].resample("1D").mean().dropna().tail(days)

    points = [
        HealthHistoryPoint(
            timestamp=ts.to_pydatetime(),
            global_score=round(float(row["overall_site_health"]), 1),
            environment=round(float(row[_DOMAIN_COLUMN[HealthDomain.environment]]), 1),
            energy=round(float(row[_DOMAIN_COLUMN[HealthDomain.energy]]), 1),
            battery=round(float(row[_DOMAIN_COLUMN[HealthDomain.battery]]), 1),
        )
        for ts, row in daily.iterrows()
    ]
    return HealthHistoryResponse(range=range_, points=points)


# ----------------------------------------------------------------- prévision
def get_forecast(horizon: ForecastHorizon) -> ForecastResponse:
    """Historique + trajectoire prévue du score global, et franchissements de seuil.

    Un franchissement est le **moment où la prévision passe sous un seuil qu'elle
    ne franchissait pas encore** (90 = surveillance, 60 = critique), évalué sur la
    borne basse de la bande — le scénario défavorable plausible, celui qui doit
    déclencher une inspection, plutôt que la valeur centrale qui arriverait trop
    tard. Un seuil déjà franchi au départ n'est pas un événement à prévoir : c'est
    l'état courant, et le signaler à chaque point noierait le vrai signal.
    """
    with _session() as session:
        rows = _require(gold_repo.read_forecast_points(session, horizon.value))

    points = [
        ForecastPoint(timestamp=r.timestamp, value=r.value, lower=r.lower,
                      upper=r.upper, is_forecast=r.is_forecast)
        for r in rows
    ]

    observed = [p for p in points if not p.is_forecast]
    anchor = observed[-1].value if observed else 100.0
    crossings: list[ThresholdCrossing] = []
    for threshold, severity in ((_HEALTHY_MIN, HealthStatus.watch),
                                (_WATCH_MIN, HealthStatus.critical)):
        if anchor < threshold:
            continue  # seuil déjà franchi : état courant, pas une prévision
        crossed = next((p for p in points if p.is_forecast and p.lower < threshold), None)
        if crossed is not None:
            crossings.append(ThresholdCrossing(
                timestamp=crossed.timestamp, threshold=threshold, severity=severity
            ))
    crossings.sort(key=lambda c: c.timestamp)
    return ForecastResponse(horizon=horizon, points=points, threshold_crossings=crossings)


def get_predicted_faults(horizon: ForecastHorizon) -> PredictedFaultsResponse:
    """Première fenêtre de risque prévue par domaine sur l'horizon demandé.

    Couche d'aide à la décision : une fenêtre indicative, jamais une alarme. Un
    domaine sans franchissement prévu renvoie `predicted_at=None` — l'absence de
    prévision est une information, pas un trou à combler par une date inventée.
    """
    forecast = get_forecast(horizon)
    with _session() as session:
        hourly = _require(gold_repo.read_health_hourly(session))
    latest = hourly.iloc[-1]

    # La trajectoire prévue porte sur le score GLOBAL ; on attribue sa fenêtre de
    # risque au domaine qui pèse le plus dans le risque courant (`main_risk_driver`),
    # et on ne prédit rien pour les autres.
    driver_domain = {
        "Environmental": HealthDomain.environment,
        "Energy": HealthDomain.energy,
        "Battery": HealthDomain.battery,
    }.get(latest.get("main_risk_driver"))
    first_crossing = next(iter(forecast.threshold_crossings), None)

    faults = []
    for family, domain in _FAMILY_DOMAIN.items():
        score = float(latest[_DOMAIN_COLUMN[domain]])
        is_driver = domain == driver_domain
        if is_driver and first_crossing is not None:
            faults.append(PredictedFault(
                family=family,
                label=_DOMAIN_LABELS[domain],
                predicted_at=first_crossing.timestamp,
                severity=(Severity.critical if first_crossing.severity == HealthStatus.critical
                          else Severity.alert),
                note=(f"Domaine dominant du risque actuel (score {score:.0f}/100). "
                      "Fenêtre indicative issue de la prévision du score global, "
                      "à conditions inchangées."),
            ))
        else:
            faults.append(PredictedFault(
                family=family,
                label=_DOMAIN_LABELS[domain],
                predicted_at=None,
                severity=None,
                note=f"Score {score:.0f}/100 — aucun franchissement de seuil prévu sur cet horizon.",
            ))
    return PredictedFaultsResponse(horizon=horizon, faults=faults)


def get_subscore_forecast(horizon: ForecastHorizon) -> SubScoreForecastResponse:
    """Séries par domaine sur la même fenêtre que le forecast global.

    Historique réel par domaine, puis projection **à conditions inchangées** :
    faute d'un modèle validé par domaine, chaque domaine est prolongé à son dernier
    niveau observé, avec une bande qui s'élargit comme celle du score global. Dire
    « on ne sait pas prédire ce domaine séparément » par une bande large est plus
    honnête que d'exhiber une courbe inventée.
    """
    global_forecast = get_forecast(horizon)
    forecast_points = [p for p in global_forecast.points if p.is_forecast]
    history_stamps = [p.timestamp for p in global_forecast.points if not p.is_forecast]

    with _session() as session:
        hourly = _require(gold_repo.read_health_hourly(session))

    series = []
    for family, domain in _FAMILY_DOMAIN.items():
        column = _DOMAIN_COLUMN[domain]
        observed = hourly[column].reindex(
            pd.DatetimeIndex(history_stamps), method="nearest", tolerance=pd.Timedelta("12h")
        )
        points = [
            ForecastPoint(timestamp=ts, value=round(float(v), 1), lower=round(float(v), 1),
                          upper=round(float(v), 1), is_forecast=False)
            for ts, v in observed.dropna().items()
        ]
        last_value = float(hourly[column].iloc[-1])
        points += [
            ForecastPoint(
                timestamp=p.timestamp,
                value=round(last_value, 1),
                lower=round(max(0.0, last_value - (p.value - p.lower)), 1),
                upper=round(min(100.0, last_value + (p.upper - p.value)), 1),
                is_forecast=True,
            )
            for p in forecast_points
        ]
        series.append(SubScoreSeries(family=family, label=_DOMAIN_LABELS[domain], points=points))
    return SubScoreForecastResponse(horizon=horizon, series=series)
