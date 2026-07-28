"""
Construction des features au niveau événement (cellules 43-50 du notebook).
build_event_features() est LA fonction critique : elle doit produire
exactement les mêmes colonnes à l'entraînement et à la prédiction.
"""
import numpy as np
import pandas as pd

from app.ml.alarm_anomaly.config import UPS_KEYWORDS, GENERATOR_KEYWORDS, TEMPERATURE_KEYWORDS


def _count_keyword(group: pd.DataFrame, keywords: list) -> int:
    pattern = "|".join(keywords)
    return group["message"].fillna("").astype(str).str.contains(
        pattern, case=False, regex=True, na=False
    ).sum()


def build_event_features(df_events: pd.DataFrame) -> pd.DataFrame:
    """
    Prend df_events (avec colonne event_id) et retourne event_features :
    une ligne par événement, avec toutes les colonnes utilisées par le modèle.
    """
    event_features = (
        df_events.groupby("event_id")
        .agg(
            start_time=("log_time", "min"),
            end_time=("log_time", "max"),
            duration_sec=("log_time", lambda x: (x.max() - x.min()).total_seconds()),
            total_alarms=("message", "count"),
            unique_alarm_types=("message", "nunique"),
            active_alarms=("state", lambda x: (x == "A").sum()),
            cleared_alarms=("state", lambda x: (x == "D").sum()),
        )
    )

    grouped = df_events.groupby("event_id", group_keys=False)

    # --- Features supplémentaires réservées aux futurs modèles ---------------
    # Ces colonnes sont calculées ici (une seule source de vérité pour tous les
    # modèles) mais ne sont PAS dans MODEL_FEATURES du modèle alarm_anomaly :
    # elles sont candidates pour les modèles 2/3 à venir. Ne pas les supprimer.
    event_features["ups_alarm_count"] = grouped.apply(
        lambda g: _count_keyword(g, UPS_KEYWORDS), include_groups=False
    )
    event_features["generator_alarm_count"] = grouped.apply(
        lambda g: _count_keyword(g, GENERATOR_KEYWORDS), include_groups=False
    )
    event_features["temperature_alarm_count"] = grouped.apply(
        lambda g: _count_keyword(g, TEMPERATURE_KEYWORDS), include_groups=False
    )

    event_features["hour"] = event_features["start_time"].dt.hour
    event_features["weekday"] = event_features["start_time"].dt.dayofweek
    event_features["month"] = event_features["start_time"].dt.month

    event_features["alarm_diversity"] = (
        event_features["unique_alarm_types"] / event_features["total_alarms"]
    )
    event_features["active_ratio"] = (
        event_features["active_alarms"]
        / (event_features["active_alarms"] + event_features["cleared_alarms"] + 1e-6)
    )
    event_features["alarm_rate"] = (
        event_features["total_alarms"] / (event_features["duration_sec"] + 1)
    )
    event_features["complexity"] = (
        event_features["unique_alarm_types"] * event_features["duration_sec"]
    )
    event_features["ups_ratio"] = (
        event_features["ups_alarm_count"] / event_features["total_alarms"]
    )
    event_features["generator_present"] = (
        event_features["generator_alarm_count"] > 0
    ).astype(int)
    event_features["repetition_factor"] = (
        event_features["total_alarms"] / event_features["unique_alarm_types"]
    )
    event_features["event_intensity"] = (
        event_features["alarm_rate"] * event_features["unique_alarm_types"]
    )
   
    event_features = event_features.replace([np.inf, -np.inf], np.nan)

    # --- Catégorie dominante de l'événement (UPS / CLIM / ENERGY / OTHER) ---
    if "category" in df_events.columns:
        dominant = (
            df_events.groupby("event_id")["category"]
            .agg(lambda s: s.value_counts().idxmax())
        )
        event_features["dominant_category"] = dominant
    else:
        event_features["dominant_category"] = "OTHER"

    return event_features