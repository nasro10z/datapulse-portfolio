"""Étape F2 — prévision de santé : gold horaire → gold `forecast_point`.

Deux responsabilités, dans cet ordre :

  1. **Entraîner** les modèles de prévision (`ml/health_score/forecasting`) sur la
     table horaire des scores, et enregistrer les artefacts + les métriques de
     test sous `ml/models/health_forecast/`. L'entraînement est explicite (option
     `--train`) et jamais déclenché par une requête API.
  2. **Dérouler** la trajectoire prévue pour chaque horizon de l'interface
     (24 h / 7 j / 30 j) et écrire les points dans le gold, historique inclus, de
     sorte que l'API n'ait plus qu'à lire.

Rappel de cadrage produit : la trajectoire est une **fenêtre de risque
indicative** à conditions inchangées, pas une alarme ni une certitude — au-delà
du pas validé (+6 h) elle est obtenue par déroulé récursif du même modèle, et la
bande de confiance s'élargit à chaque pas pour l'indiquer.

    python -m app.etl.forecast --train   (première exécution / réentraînement)
    python -m app.etl.forecast           (déroulé avec les artefacts existants)
"""
import sys
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from app.ml.health_score import forecasting
from app.models.health import ForecastHorizon
from app.storage.analytics_db import get_analytics_sessionmaker, init_analytics_db
from app.storage.repositories import gold_repo

# Horizon → (durée prévue en heures, pas d'échantillonnage servi, nb de points
# d'historique servis). Le modèle avance par pas de 6 h ; les points servis sont
# rééchantillonnés à ce pas d'affichage.
HORIZON_CONFIG = {
    ForecastHorizon.h24: (24, pd.Timedelta(hours=1), 24),
    ForecastHorizon.d7: (7 * 24, pd.Timedelta(hours=6), 28),
    ForecastHorizon.d30: (30 * 24, pd.Timedelta(days=1), 30),
}


def _history_points(scores: pd.DataFrame, step: pd.Timedelta, count: int) -> list[dict]:
    """Derniers scores observés, rééchantillonnés au pas d'affichage.

    `origin="end"` cale la grille sur la **dernière** observation : l'historique se
    termine exactement là où la prévision démarre, sans décalage d'une demi-période.
    """
    series = scores["overall_site_health"].resample(step, origin="end").mean().dropna().tail(count)
    return [
        {"timestamp": ts.to_pydatetime(), "value": round(float(v), 2),
         "lower": round(float(v), 2), "upper": round(float(v), 2), "is_forecast": False}
        for ts, v in series.items()
    ]


def _forecast_points(scores: pd.DataFrame, trajectory: pd.DataFrame, step: pd.Timedelta) -> list[dict]:
    """Trajectoire prévue (pas de 6 h) → points au pas d'affichage.

    La dernière observation sert d'**ancre** : elle amorce la grille pour que la
    courbe prévue reparte du point observé sans trou, puis elle est retirée (elle
    appartient à l'historique). Quand le pas d'affichage est plus fin que celui du
    modèle (horizon 24 h, points horaires), les points intermédiaires sont
    **interpolés** entre deux prédictions — on ne fabrique pas de prédictions
    supplémentaires.
    """
    anchor_ts = scores.index[-1]
    anchor_value = float(scores["overall_site_health"].iloc[-1])
    anchor = pd.DataFrame(
        {"value": [anchor_value], "lower": [anchor_value], "upper": [anchor_value]},
        index=[anchor_ts],
    )
    df = pd.concat([anchor, trajectory.set_index("timestamp")]).sort_index()

    resampled = df.resample(step, origin=anchor_ts).mean().interpolate(limit_direction="both")
    resampled = resampled.loc[(resampled.index > anchor_ts) & (resampled.index <= df.index.max())]
    return [
        {"timestamp": ts.to_pydatetime(), "value": round(float(row["value"]), 2),
         "lower": round(float(row["lower"]), 2), "upper": round(float(row["upper"]), 2),
         "is_forecast": True}
        for ts, row in resampled.iterrows()
    ]


def build_forecast_points(scores: pd.DataFrame, artifacts: dict) -> list[dict]:
    """Historique + prévision pour les trois horizons servis."""
    points: list[dict] = []
    for horizon, (hours, step, history_count) in HORIZON_CONFIG.items():
        trajectory = forecasting.forecast_recursive(scores, artifacts, hours)
        for point in (_history_points(scores, step, history_count)
                      + _forecast_points(scores, trajectory, step)):
            points.append({"horizon": horizon.value, **point})
    return points


def forecast_site_health(session: Session, train: bool = False) -> dict:
    scores = gold_repo.read_health_hourly(session)
    if scores.empty:
        raise ValueError(
            "Gold horaire vide : lancer `python -m app.etl.score` avant la prévision."
        )

    metadata = None
    if train:
        artifacts = forecasting.train(scores)
        metadata = forecasting.save_artifacts(artifacts)
    else:
        artifacts = forecasting.load_artifacts()

    run_id = datetime.now(timezone.utc).strftime("fcst-%Y%m%d%H%M%S")
    points = build_forecast_points(scores, artifacts)
    n = gold_repo.replace_forecast_points(session, run_id, points)

    result = {"forecast_point": n, "run_id": run_id}
    if metadata:
        result["metrics"] = metadata["metrics"]
    return result


def run_forecast(train: bool = False) -> dict:
    init_analytics_db()
    with get_analytics_sessionmaker()() as session:
        return forecast_site_health(session, train=train)


if __name__ == "__main__":
    print(run_forecast(train="--train" in sys.argv))
