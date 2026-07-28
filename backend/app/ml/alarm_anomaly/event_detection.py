"""
Découpage des alarmes individuelles en "events" (cellule 42 du notebook).
Un event = un groupe d'alarmes consécutives séparées de moins de
EVENT_GAP_THRESHOLD_SECONDS.
"""
import pandas as pd

from app.ml.alarm_anomaly.config import EVENT_GAP_THRESHOLD_SECONDS


def build_events(df_combined: pd.DataFrame,
                  gap_threshold: int = EVENT_GAP_THRESHOLD_SECONDS) -> pd.DataFrame:
    """Ajoute une colonne event_id à df_combined en regroupant les alarmes proches."""
    df_events = (
        df_combined
        .dropna(subset=["log_time"])
        .sort_values("log_time")
        .reset_index(drop=True)
        .copy()
    )
    df_events["gap_seconds"] = df_events["log_time"].diff().dt.total_seconds()
    df_events["event_id"] = df_events["gap_seconds"].gt(gap_threshold).cumsum()
    return df_events
