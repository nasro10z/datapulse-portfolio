"""Repository GOLD — lecture/écriture de tout ce que l'API sert.

Le gold miroite les modèles Pydantic : la conversion ligne ↔ `AnomalyEpisode` /
`SubScore` / `ForecastPoint` est directe. C'est la seule surface que `providers`
(mode live) lit — aucun calcul sur le chemin de requête.
"""
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.anomalies import AnomalyEpisode
from app.storage.schema.gold import (
    AnomalyEpisodeRow,
    ForecastPointRow,
    HealthScoreHourlyRow,
    HealthScoreRow,
)


def _naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def replace_episodes(session: Session, episodes: list[AnomalyEpisode]) -> int:
    """Remplace la table `anomaly_episode` par la liste fournie (backfill idempotent)."""
    session.execute(delete(AnomalyEpisodeRow))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for e in episodes:
        session.add(AnomalyEpisodeRow(
            id=e.id, equipment=e.equipment, type=e.type.value, severity=e.severity.value,
            direction=e.direction.value, start=_naive(e.start), duration_min=e.duration_min,
            peak_value=e.peak_value, status=e.status.value, dimension=e.dimension.value, computed_at=now,
        ))
    session.commit()
    return len(episodes)


def read_episodes(session: Session) -> list[AnomalyEpisode]:
    """Épisodes (statut calculé, avant surcharge par l'action utilisateur), plus récents d'abord."""
    rows = session.scalars(select(AnomalyEpisodeRow).order_by(AnomalyEpisodeRow.start.desc())).all()
    return [
        AnomalyEpisode(
            id=r.id, equipment=r.equipment, type=r.type, severity=r.severity,
            direction=r.direction, start=r.start, duration_min=r.duration_min,
            peak_value=r.peak_value, status=r.status, dimension=r.dimension,
        )
        for r in rows
    ]


# ------------------------------------------------------- scores de santé horaires
_HOURLY_COLS = [c.name for c in HealthScoreHourlyRow.__table__.columns
                if c.name not in ("timestamp", "computed_at")]


def replace_health_hourly(session: Session, df: pd.DataFrame) -> int:
    """Remplace `health_score_hourly` par la table horaire calculée par l'ETL.

    `df` est indexé par `timestamp` et porte (au moins) les colonnes du schéma ;
    tout le reste (features intermédiaires du calcul) est ignoré ici — le gold ne
    garde que ce qui est servi ou nécessaire à la prévision.
    """
    out = df.reset_index().rename(columns={"index": "timestamp"})
    for col in _HOURLY_COLS:
        if col not in out.columns:
            out[col] = None
    out = out[["timestamp", *_HOURLY_COLS]].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"])
    out["computed_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

    session.execute(delete(HealthScoreHourlyRow))
    out.to_sql("health_score_hourly", session.connection(), if_exists="append",
               index=False, chunksize=5_000)
    session.commit()
    return len(out)


def read_health_hourly(session: Session, since: datetime | None = None) -> pd.DataFrame:
    """Table horaire des scores, indexée par `timestamp` (ordre chronologique)."""
    stmt = select(HealthScoreHourlyRow)
    if since is not None:
        stmt = stmt.where(HealthScoreHourlyRow.timestamp >= since)
    df = pd.read_sql(stmt.order_by(HealthScoreHourlyRow.timestamp), session.connection())
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.set_index("timestamp")


def latest_health_hourly(session: Session) -> HealthScoreHourlyRow | None:
    """Dernière heure scorée — l'« instantané » servi par l'aperçu."""
    return session.scalars(
        select(HealthScoreHourlyRow).order_by(HealthScoreHourlyRow.timestamp.desc()).limit(1)
    ).first()


# -------------------------------------------------- instantané servi (sous-scores)
def replace_health_scores(session: Session, run_id: str, rows: list[dict]) -> int:
    """Remplace l'instantané `health_score` (score global + sous-scores familles).

    Chaque `row` porte `scope, family, label, score, status, trend, unit_count, note`.
    """
    session.execute(delete(HealthScoreRow))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in rows:
        session.add(HealthScoreRow(run_id=run_id, computed_at=now, **row))
    session.commit()
    return len(rows)


def read_health_scores(session: Session) -> list[HealthScoreRow]:
    return list(session.scalars(select(HealthScoreRow).order_by(HealthScoreRow.id)).all())


# ------------------------------------------------------------ points de prévision
def replace_forecast_points(session: Session, run_id: str, points: list[dict]) -> int:
    """Remplace `forecast_point` par les trajectoires calculées (tous horizons).

    Chaque `point` porte `horizon, timestamp, value, lower, upper, is_forecast`.
    """
    session.execute(delete(ForecastPointRow))
    for point in points:
        session.add(ForecastPointRow(run_id=run_id, **point))
    session.commit()
    return len(points)


def read_forecast_points(session: Session, horizon: str) -> list[ForecastPointRow]:
    return list(session.scalars(
        select(ForecastPointRow)
        .where(ForecastPointRow.horizon == horizon)
        .order_by(ForecastPointRow.timestamp)
    ).all())
