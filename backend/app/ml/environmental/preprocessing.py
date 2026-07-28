"""
Fonctions de prétraitement reprises du notebook environmental_fixed.ipynb.

⚠️ Point critique : compute_rolling_features() DOIT être utilisée à l'identique
à l'entraînement (train.py, sur tout l'historique) et à la prédiction
(predict.py, sur le buffer récent) -- une seule source de vérité, jamais
deux implémentations différentes.
"""
import numpy as np
import pandas as pd
import sqlite3
    

from app.ml.environmental.config import (
    DB_PATH,
    TEMP_COL,
    HUMIDITY_COL,
    MAX_CONTINUOUS_GAP_SECONDS,
    WINDOW_CONFIG,
)


def load_data_from_db() -> pd.DataFrame:
    """Charge la table temp_humid_last depuis la base de données SQLite."""
    conn = sqlite3.connect(DB_PATH)
    df_raw = pd.read_sql_query("SELECT * FROM temp_humid_last", conn)
    conn.close()
    required_cols = {"ts", TEMP_COL, HUMIDITY_COL}
    missing = required_cols.difference(df_raw.columns)
    if missing:
        raise KeyError(f"Colonnes manquantes: {sorted(missing)}")

    df = df_raw.copy()
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    df[TEMP_COL] = pd.to_numeric(df[TEMP_COL], errors="coerce")
    df[HUMIDITY_COL] = pd.to_numeric(df[HUMIDITY_COL], errors="coerce")
    df = df.dropna(subset=["ts"])
    return df


def dedupe_and_index(df: pd.DataFrame) -> pd.DataFrame:
    """Garde la ligne la plus complète par timestamp, indexe par date."""
    df = df.copy()
    df["_completeness"] = df[[TEMP_COL, HUMIDITY_COL]].notna().sum(axis=1)
    df = (
        df.sort_values(["ts", "_completeness"], ascending=[True, False])
          .drop_duplicates(subset="ts", keep="first")
          .drop(columns="_completeness")
          .set_index("ts")
          .sort_index()
    )
    df.index.name = "ts"
    return df


def add_segments(df: pd.DataFrame) -> pd.DataFrame:
    """Détecte les coupures de communication et numérote les segments continus."""
    df = df.copy()
    df["gap_seconds"] = df.index.to_series().diff().dt.total_seconds()
    df["is_discontinuity"] = (
        df["gap_seconds"].isna() | df["gap_seconds"].gt(MAX_CONTINUOUS_GAP_SECONDS)
    )
    df["segment_id"] = df["is_discontinuity"].cumsum().astype(int)
    df["segment_position"] = df.groupby("segment_id").cumcount()
    return df


def tukey_thresholds(series: pd.Series, mild_factor=0.5, strong_factor=1.0, extreme_factor=1.5) -> dict:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        raise ValueError("Impossible de calculer les seuils sur une série vide.")
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    return {
        "q1": q1, "q3": q3, "iqr": iqr,
        "mild_lower": q1 - mild_factor * iqr,
        "mild_upper": q3 + mild_factor * iqr,
        "strong_lower": q1 - strong_factor * iqr,
        "strong_upper": q3 + strong_factor * iqr,
        "extreme_lower": q1 - extreme_factor * iqr,
        "extreme_upper": q3 + extreme_factor * iqr,
    }


def compute_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les 19 features glissantes (moyennes, écarts-types, deltas,
    fraîcheur de segment) à partir d'un DataFrame indexé par ts, avec
    colonnes temperature, humidity, segment_id, segment_position.

    Fonctionne aussi bien sur tout l'historique (entraînement) que sur
    un petit buffer récent (prédiction en streaming).
    """
    df = df.copy()

    for variable in [TEMP_COL, HUMIDITY_COL]:
        grouped = df.groupby("segment_id")[variable]
        for label, (window, min_periods) in WINDOW_CONFIG.items():
            df[f"{variable}_mean_{label}"] = grouped.transform(
                lambda s, w=window, mp=min_periods: s.rolling(w, min_periods=mp).mean()
            )
            df[f"{variable}_std_{label}"] = grouped.transform(
                lambda s, w=window, mp=min_periods: s.rolling(w, min_periods=mp).std(ddof=0)
            )
            df[f"segment_freshness_{label}"] = np.minimum(
                df["segment_position"] / max(window - 1, 1), 1.0
            )

    df["temp_short_long_delta"] = df["temperature_mean_court"] - df["temperature_mean_long"]
    df["humidity_short_long_delta"] = df["humidity_mean_court"] - df["humidity_mean_long"]
    df["temp_change"] = df.groupby("segment_id")[TEMP_COL].diff()
    df["humidity_change"] = df.groupby("segment_id")[HUMIDITY_COL].diff()
    df["temp_change_10min"] = df.groupby("segment_id")[TEMP_COL].diff(5)
    df["humidity_change_10min"] = df.groupby("segment_id")[HUMIDITY_COL].diff(5)

    return df


def prepare_hmm_sequences(feature_data: pd.DataFrame, source_data: pd.DataFrame,
                           min_sequence_length: int = 2):
    """Regroupe les observations en séquences continues pour le HMM."""
    data = feature_data.sort_index().copy()
    source_segment = source_data.loc[data.index, "segment_id"]

    time_gap = data.index.to_series().diff().dt.total_seconds()
    starts_new_sequence = (
        time_gap.isna()
        | time_gap.gt(MAX_CONTINUOUS_GAP_SECONDS)
        | source_segment.ne(source_segment.shift())
    )
    sequence_id = starts_new_sequence.cumsum()

    parts, lengths = [], []
    for _, part in data.groupby(sequence_id, sort=True):
        if len(part) >= min_sequence_length:
            parts.append(part)
            lengths.append(len(part))

    if not parts:
        raise ValueError("Aucune séquence HMM valide.")

    ordered = pd.concat(parts).sort_index()
    return ordered, lengths