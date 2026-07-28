"""Repository SILVER — lectures nettoyées/segmentées + journal SCADA catégorisé."""
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.storage.schema.silver import ScadaClean, ThClean

_COLS = ["ts", "temperature", "humidity", "sensor", "segment_id",
         "segment_position", "is_discontinuity"]

_SCADA_COLS = ["log_time", "send_time", "state", "message", "category"]


def replace_th_clean(session: Session, df: pd.DataFrame) -> int:
    """Remplace `th_clean` par `df` (sortie de dedupe_and_index + add_segments,
    indexé par ts)."""
    out = df.reset_index()  # ts (index) → colonne
    if "sensor" not in out.columns:
        out["sensor"] = "SITE01_SALLE_SWITCH"
    out = out[[c for c in _COLS if c in out.columns]].copy()
    out["is_discontinuity"] = out["is_discontinuity"].astype(bool)
    out["computed_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

    session.execute(delete(ThClean))
    out.to_sql("th_clean", session.connection(), if_exists="append",
               index=False, chunksize=10_000)
    session.commit()
    return len(out)


def read_th_clean(session: Session) -> pd.DataFrame:
    df = pd.read_sql(select(ThClean), session.connection())
    df["ts"] = pd.to_datetime(df["ts"])
    return df


def replace_scada_clean(session: Session, df: pd.DataFrame) -> int:
    """Remplace `scada_clean` par `df` (sortie de `clean_and_dedupe`).

    Les colonnes de commodité produites en aval par le package (`date`,
    `time_since_last`) ne sont pas persistées : dérivables de `log_time`.
    """
    out = df.copy()
    for col in _SCADA_COLS:
        if col not in out.columns:
            out[col] = None
    out = out[_SCADA_COLS]
    out["log_time"] = pd.to_datetime(out["log_time"], errors="coerce")
    out["send_time"] = pd.to_datetime(out["send_time"], errors="coerce")
    out = out.dropna(subset=["log_time", "message"])
    out["computed_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

    session.execute(delete(ScadaClean))
    out.to_sql("scada_clean", session.connection(), if_exists="append",
               index=False, chunksize=10_000)
    session.commit()
    return len(out)


def read_scada_clean(session: Session) -> pd.DataFrame:
    """Journal SCADA nettoyé (entrée du scoring énergie/batterie)."""
    stmt = select(ScadaClean.log_time, ScadaClean.send_time, ScadaClean.state,
                  ScadaClean.message, ScadaClean.category)
    df = pd.read_sql(stmt, session.connection())
    df["log_time"] = pd.to_datetime(df["log_time"])
    df["send_time"] = pd.to_datetime(df["send_time"])
    return df


def last_ts(session: Session) -> datetime | None:
    """Dernière lecture capteur du silver = fin de la période observée.

    Sert de borne haute aux fenêtres glissantes servies à l'API (cf.
    `ml/anomalies.reference_now`). `None` si le silver est vide.
    """
    ts = session.scalar(select(func.max(ThClean.ts)))
    return pd.to_datetime(ts).to_pydatetime() if ts is not None else None


def span_days(session: Session) -> int:
    """Étendue temporelle du silver (jours) — fenêtre d'observation pour le taux
    d'anomalies. 1 si le silver est vide."""
    lo, hi = session.execute(select(func.min(ThClean.ts), func.max(ThClean.ts))).one()
    if lo is None or hi is None:
        return 1
    return max((pd.to_datetime(hi) - pd.to_datetime(lo)).days, 1)
