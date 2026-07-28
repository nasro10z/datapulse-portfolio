"""Features horaires du score de santé — portage fidèle du notebook.

Trois familles de features, une par domaine, toutes ramenées au **pas horaire** :
  - environnement : température / humidité (capteur salle switch) ;
  - énergie       : alarmes coupure / réseau / groupe / basculement ;
  - batterie      : alarmes batterie des onduleurs.

Toutes les fonctions sont pures (DataFrame → DataFrame). Aucune lecture de
fichier ni de base : les entrées viennent du silver via `etl/score.py`.
"""
import re

import numpy as np
import pandas as pd

from app.ml.health_score import config as cfg


# --------------------------------------------------------------------- helpers
def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def normalise_p95(series: pd.Series) -> pd.Series:
    """Série ramenée à 0-1 par son 95e percentile (écrêtage dur au-delà)."""
    values = safe_numeric(series).fillna(0).clip(lower=0)
    p95 = values.quantile(0.95)
    if pd.isna(p95) or p95 <= 0:
        return pd.Series(0.0, index=series.index)
    return (values / p95).clip(0, 1)


def saturating_ratio(series: pd.Series, scale: float | None = None) -> pd.Series:
    """Approche 1 en douceur (`1 - exp(-x/scale)`) au lieu de l'écrêtage dur de
    `normalise_p95` : un événement isolé ne colle plus le terme à son plafond, et
    le terme continue de monter au lieu de plafonner — c'est ce qui permet aux
    scores de se dégrader progressivement.

    Sans `scale`, l'échelle est déduite des données (95e percentile), donc adaptée
    à l'activité réelle du journal considéré.
    """
    values = safe_numeric(series).fillna(0).clip(lower=0)
    if scale is None:
        scale = values.quantile(0.95)
    if pd.isna(scale) or scale <= 0:
        return pd.Series(0.0, index=series.index)
    return 1 - np.exp(-values / scale)


def decayed_sum(series: pd.Series, halflife_hours: float) -> pd.Series:
    """Total glissant pondéré par la récence : chaque événement fait monter le
    total immédiatement puis s'estompe avec la demi-vie donnée. Équivalent continu
    d'une somme glissante 24 h (qui, elle, garde le poids plein 24 h puis le lâche
    d'un coup — une fonction en escalier)."""
    decay = 0.5 ** (1 / halflife_hours)
    values = series.fillna(0).to_numpy(dtype=float)
    decayed = np.empty_like(values)
    running = 0.0
    for i, value in enumerate(values):
        running = running * decay + value
        decayed[i] = running
    return pd.Series(decayed, index=series.index)


def consecutive_run_length(binary_series: pd.Series) -> pd.Series:
    """Longueur de la série courante de 1 consécutifs (remise à 0 dès un 0) :
    depuis combien de temps le problème est **continûment** actif, par opposition
    à sa fréquence."""
    reset_groups = (binary_series == 0).cumsum()
    return binary_series.groupby(reset_groups).cumsum()


def pm_risk_from_last_pm(index: pd.DatetimeIndex, last_pm_date, interval_days: float) -> pd.Series:
    """Risque de maintenance préventive : `min(jours depuis la dernière PM /
    intervalle, 1)`. Croît linéairement à partir de `last_pm_date` et plafonne à 1
    une fois l'intervalle dépassé sans intervention."""
    days_since = (index - last_pm_date) / pd.Timedelta(days=1)
    days_since = np.clip(days_since, 0, None)
    return pd.Series(np.minimum(days_since / interval_days, 1.0), index=index)


def keyword_flag(series: pd.Series, keywords: list[str]) -> pd.Series:
    """Drapeau 0/1 par ligne selon la présence d'un mot-clé, avec **frontières de
    mot** : un token court comme « ats » ne peut pas matcher au milieu d'un autre
    mot."""
    pattern = "|".join(r"\b" + re.escape(k.lower()) + r"\b" for k in keywords)
    return (
        series.fillna("").astype(str).str.lower()
        .str.contains(pattern, regex=True, na=False)
        .astype(int)
    )


# ------------------------------------------------------------- environnemental
def build_env_hourly(df_env: pd.DataFrame) -> pd.DataFrame:
    """Lectures température/humidité → features horaires environnementales.

    `df_env` : colonnes `ts, temperature, humidity` (silver `th_clean`). Les
    lectures physiquement invraisemblables (repli capteur, champs concaténés) sont
    traitées comme **manquantes** — cf. `config.ENV_PLAUSIBLE_*_RANGE`. Sans cela,
    une humidité à 0 % au milieu d'une heure à 44 % fait exploser l'écart-type
    horaire et, par l'échelle p95, dérègle le terme de variabilité sur toute la
    série.
    """
    df = df_env.copy()
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    df["temperature"] = safe_numeric(df["temperature"])
    df["humidity"] = safe_numeric(df["humidity"])
    df = (df.dropna(subset=["ts"]).sort_values("ts")
            .drop_duplicates(subset=["ts"], keep="last"))
    df.loc[~df["temperature"].between(*cfg.ENV_PLAUSIBLE_TEMP_RANGE), "temperature"] = np.nan
    df.loc[~df["humidity"].between(*cfg.ENV_PLAUSIBLE_HUMIDITY_RANGE), "humidity"] = np.nan
    df = df.set_index("ts")

    hourly = pd.DataFrame()
    hourly["temperature"] = df["temperature"].resample("1h").mean()
    hourly["humidity"] = df["humidity"].resample("1h").mean()
    hourly["temp_std_1h"] = df["temperature"].resample("1h").std()
    hourly["humidity_std_1h"] = df["humidity"].resample("1h").std()
    hourly["observation_count"] = df["temperature"].resample("1h").count()

    # Trous courts (≤ 3 h) comblés par interpolation ; au-delà on laisse NaN.
    hourly[["temperature", "humidity"]] = hourly[["temperature", "humidity"]].interpolate(limit=3)
    hourly[["temp_std_1h", "humidity_std_1h"]] = hourly[["temp_std_1h", "humidity_std_1h"]].fillna(0)

    # Termes de risque 0-1 : au-delà de 26 °C (plage de 10 °C), écart d'humidité
    # au-delà de ±4 points autour de 46 % (plage de 15 points).
    hourly["temp_term"] = ((hourly["temperature"] - 26) / 10).clip(0, 1)
    hourly["humidity_term"] = (((hourly["humidity"] - 46).abs() - 4) / 15).clip(0, 1)
    hourly["temp_change_term"] = normalise_p95(hourly["temp_std_1h"])
    hourly["humidity_change_term"] = normalise_p95(hourly["humidity_std_1h"])

    hourly.index.name = "timestamp"
    return hourly


def add_env_anomaly_burden(env_hourly: pd.DataFrame) -> pd.DataFrame:
    """Ajoute z-scores 24 h, drapeau/sévérité d'anomalie et charge d'anomalie.

    Anomalie = |z| ≥ 3 sur température ou humidité, contre une moyenne/écart-type
    glissants sur 24 h. La charge combine **fréquence** (part d'heures anormales
    sur 24 h) et **sévérité** (dépassement au-delà de 3σ).
    """
    df = env_hourly.copy()
    temp_mean = df["temperature"].rolling(24, min_periods=6).mean()
    temp_std = df["temperature"].rolling(24, min_periods=6).std()
    hum_mean = df["humidity"].rolling(24, min_periods=6).mean()
    hum_std = df["humidity"].rolling(24, min_periods=6).std()

    df["temp_zscore"] = (df["temperature"] - temp_mean) / temp_std.replace(0, np.nan)
    df["humidity_zscore"] = (df["humidity"] - hum_mean) / hum_std.replace(0, np.nan)
    df[["temp_zscore", "humidity_zscore"]] = (
        df[["temp_zscore", "humidity_zscore"]].replace([np.inf, -np.inf], np.nan).fillna(0)
    )

    df["environmental_anomaly_flag"] = (
        (df["temp_zscore"].abs() >= 3) | (df["humidity_zscore"].abs() >= 3)
    ).astype(int)
    df["environmental_anomaly_ratio"] = df["environmental_anomaly_flag"].rolling(24, min_periods=1).mean()
    df["temp_anomaly_severity"] = ((df["temp_zscore"].abs() - 3) / 3).clip(0, 1)
    df["humidity_anomaly_severity"] = ((df["humidity_zscore"].abs() - 3) / 3).clip(0, 1)
    df["environmental_anomaly_severity"] = (
        df[["temp_anomaly_severity", "humidity_anomaly_severity"]]
        .max(axis=1).rolling(24, min_periods=1).mean()
    )
    df["environmental_anomaly_burden"] = (
        0.60 * df["environmental_anomaly_ratio"] + 0.40 * df["environmental_anomaly_severity"]
    ).clip(0, 1)
    return df


# ---------------------------------------------------------------- journal SCADA
def flag_events(df_log: pd.DataFrame, message_col: str = "message") -> pd.DataFrame:
    """Ajoute les drapeaux 0/1 par type d'alarme (énergie + batterie) au journal.

    `df_log` : journal SCADA nettoyé (silver `scada_clean`), colonnes
    `log_time, state, message, category`.
    """
    df = df_log.copy()
    df[message_col] = df[message_col].fillna("").astype(str)
    df["is_outage"] = keyword_flag(df[message_col], cfg.OUTAGE_KEYWORDS)
    df["is_supply_event"] = keyword_flag(df[message_col], cfg.SUPPLY_KEYWORDS)
    df["is_generator_event"] = keyword_flag(df[message_col], cfg.GENERATOR_KEYWORDS)
    df["is_backup_transfer"] = keyword_flag(df[message_col], cfg.TRANSFER_KEYWORDS)
    df["is_check_battery"] = keyword_flag(df[message_col], cfg.CHECK_BATTERY_KEYWORDS)
    df["is_battery_discharge"] = keyword_flag(df[message_col], cfg.DISCHARGE_KEYWORDS)
    df["is_low_battery"] = keyword_flag(df[message_col], cfg.LOW_BATTERY_KEYWORDS)
    df["is_battery_chatter"] = keyword_flag(df[message_col], cfg.BATTERY_CHATTER_KEYWORDS)
    return df


def build_energy_hourly(df_events: pd.DataFrame, time_col: str = "log_time") -> pd.DataFrame:
    """Journal drapeauté → features horaires énergie (charges décroissantes,
    durée de coupure continue, termes de risque 0-1)."""
    cols = ["is_outage", "is_supply_event", "is_generator_event", "is_backup_transfer"]
    hourly = df_events[[time_col, *cols]].set_index(time_col).resample("1h").sum()
    hourly = hourly.rename(columns={
        "is_outage": "outage_count",
        "is_supply_event": "supply_event_count",
        "is_generator_event": "generator_event_count",
        "is_backup_transfer": "backup_transfer_count",
    })

    hl = cfg.ENERGY_HALFLIFE_HOURS
    hourly["outage_load"] = decayed_sum(hourly["outage_count"], hl)
    hourly["supply_load"] = decayed_sum(hourly["supply_event_count"], hl)
    hourly["generator_load"] = decayed_sum(hourly["generator_event_count"], hl)
    hourly["transfer_load"] = decayed_sum(hourly["backup_transfer_count"], hl)

    hourly["outage_active_hour"] = (hourly["outage_count"] > 0).astype(int)
    # Durée réelle : nombre d'heures consécutives de coupure active *maintenant*,
    # pas le nombre d'alarmes de coupure vues dans la journée.
    hourly["outage_duration_hours"] = consecutive_run_length(hourly["outage_active_hour"])

    hourly["outage_term"] = saturating_ratio(hourly["outage_load"])
    hourly["supply_term"] = saturating_ratio(hourly["supply_load"])
    hourly["generator_term"] = saturating_ratio(hourly["generator_load"])
    hourly["transfer_term"] = saturating_ratio(hourly["transfer_load"])
    hourly["persistence_term"] = saturating_ratio(
        hourly["outage_duration_hours"], scale=cfg.ENERGY_DURATION_SCALE_HOURS
    )

    hourly["total_energy_load"] = (
        hourly["outage_load"] + hourly["supply_load"]
        + hourly["generator_load"] + hourly["transfer_load"]
    )
    hourly["energy_frequency_anomaly"] = saturating_ratio(hourly["total_energy_load"])
    hourly["energy_duration_anomaly"] = saturating_ratio(
        hourly["outage_duration_hours"], scale=cfg.ENERGY_DURATION_SCALE_HOURS
    )
    hourly.index.name = "timestamp"
    return hourly


def build_battery_hourly(df_events: pd.DataFrame, time_col: str = "log_time") -> pd.DataFrame:
    """Journal drapeauté → features horaires batterie (charges décroissantes,
    récurrence, durée continue d'alarme, composantes de risque 0-1)."""
    cols = ["is_check_battery", "is_battery_discharge", "is_low_battery", "is_battery_chatter"]
    hourly = df_events[[time_col, *cols]].set_index(time_col).resample("1h").sum()
    hourly = hourly.rename(columns={
        "is_check_battery": "check_battery_count",
        "is_battery_discharge": "battery_discharge_count",
        "is_low_battery": "low_battery_count",
        "is_battery_chatter": "battery_chatter_count",
    })
    count_cols = ["check_battery_count", "battery_discharge_count",
                  "low_battery_count", "battery_chatter_count"]
    hourly["battery_alarm_active"] = (hourly[count_cols].sum(axis=1) > 0).astype(int)

    hl = cfg.BATTERY_HALFLIFE_HOURS
    hourly["check_battery_load"] = decayed_sum(hourly["check_battery_count"], hl)
    hourly["discharge_load"] = decayed_sum(hourly["battery_discharge_count"], hl)
    hourly["low_battery_load"] = decayed_sum(hourly["low_battery_count"], hl)
    hourly["chatter_load"] = decayed_sum(hourly["battery_chatter_count"], hl)
    # Récurrence : à quelle fréquence une alarme s'est re-déclenchée récemment.
    hourly["recurrence_load"] = decayed_sum(hourly["battery_alarm_active"], hl)
    # Durée : heures consécutives en état d'alarme. Un défaut qui ne s'efface pas
    # est pire qu'un défaut qui s'efface aussitôt, même à nombre d'alarmes égal.
    hourly["battery_alarm_duration_hours"] = consecutive_run_length(hourly["battery_alarm_active"])

    hourly["check_battery_component"] = saturating_ratio(hourly["check_battery_load"])
    hourly["discharge_component"] = saturating_ratio(hourly["discharge_load"])
    hourly["low_battery_component"] = saturating_ratio(hourly["low_battery_load"])
    hourly["chatter_component"] = saturating_ratio(hourly["chatter_load"])
    hourly["recurrence_component"] = saturating_ratio(hourly["recurrence_load"])
    hourly["persistence_component"] = saturating_ratio(
        hourly["battery_alarm_duration_hours"], scale=cfg.BATTERY_DURATION_SCALE_HOURS
    )

    hourly["battery_anomaly_burden"] = (
        0.50 * hourly["persistence_component"] + 0.50 * hourly["recurrence_component"]
    ).clip(0, 1)
    hourly.index.name = "timestamp"
    return hourly
