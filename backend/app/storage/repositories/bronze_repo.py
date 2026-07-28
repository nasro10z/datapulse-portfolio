"""Repository BRONZE — écriture/lecture de la couche brute.

Le backfill remplace la table entière (idempotent : relancer ne double pas les
lignes) ; l'insertion en masse passe par `DataFrame.to_sql` pour la performance.
pandas n'est utilisé ici que comme utilitaire de (dé)sérialisation en masse, pas
pour de la logique métier.
"""
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.storage.schema.bronze import IngestWatermark, RawScadaLog, RawTempHumidity


def _naive_utc_now() -> datetime:
    # SQLite ne gère pas les datetimes tz-aware : on stocke un UTC naïf.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _set_watermark(session: Session, table: str, last_ts, n_rows: int) -> None:
    row = session.get(IngestWatermark, table)
    if row is None:
        row = IngestWatermark(table_name=table)
        session.add(row)
    row.last_ts = last_ts
    row.rows_ingested = int(n_rows)
    row.updated_at = _naive_utc_now()


def _max_ts(series: pd.Series):
    ts = pd.to_datetime(series, errors="coerce").max()
    return ts.to_pydatetime() if pd.notna(ts) else None


def replace_temp_humidity(session: Session, df: pd.DataFrame, batch_id: str | None = None) -> int:
    """Remplace `raw_temp_humidity` par `df` (colonnes ts, temperature, humidity, sensor)."""
    session.execute(delete(RawTempHumidity))
    out = df[["ts", "temperature", "humidity", "sensor"]].copy()
    out["ingested_at"] = _naive_utc_now()
    out["batch_id"] = batch_id
    out.to_sql("raw_temp_humidity", session.connection(), if_exists="append",
               index=False, chunksize=10_000)
    _set_watermark(session, "raw_temp_humidity", _max_ts(df["ts"]), len(out))
    session.commit()
    return len(out)


def replace_scada_log(session: Session, df: pd.DataFrame, batch_id: str | None = None) -> int:
    """Remplace `raw_scada_log` par `df` (colonnes state, log_time, message, send_time)."""
    session.execute(delete(RawScadaLog))
    out = df[["state", "log_time", "message", "send_time"]].copy()
    out["ingested_at"] = _naive_utc_now()
    out["batch_id"] = batch_id
    out.to_sql("raw_scada_log", session.connection(), if_exists="append",
               index=False, chunksize=10_000)
    _set_watermark(session, "raw_scada_log", _max_ts(df["log_time"]), len(out))
    session.commit()
    return len(out)


def read_temp_humidity(session: Session) -> pd.DataFrame:
    """Lecture bronze temp/humidité (entrée du transform environnemental)."""
    stmt = select(RawTempHumidity.ts, RawTempHumidity.temperature,
                  RawTempHumidity.humidity, RawTempHumidity.sensor)
    df = pd.read_sql(stmt, session.connection())
    df["ts"] = pd.to_datetime(df["ts"])
    return df


def read_scada_log(session: Session) -> pd.DataFrame:
    """Lecture bronze SCADA/UPS (entrée du transform `scada_clean`)."""
    stmt = select(RawScadaLog.state, RawScadaLog.log_time,
                  RawScadaLog.message, RawScadaLog.send_time)
    df = pd.read_sql(stmt, session.connection())
    df["log_time"] = pd.to_datetime(df["log_time"])
    df["send_time"] = pd.to_datetime(df["send_time"])
    return df


def get_watermark(session: Session, table: str) -> IngestWatermark | None:
    return session.get(IngestWatermark, table)


def count(session: Session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))
