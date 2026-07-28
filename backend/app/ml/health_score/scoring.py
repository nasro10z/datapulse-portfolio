"""Score de santé du site — risques de base, calibration, score global.

Chaîne de calcul (identique au notebook `health_scores.ipynb`) :

    risque_base   = 100 × Σ(poids × terme)                    par domaine
    risque_final  = risque_base × (1 + wa·anomalie) × (1 + wm·risque_PM)
    risque_énergie= compression douce + plancher si coupure persistante
    risque_global = Σ(poids_domaine × risque_domaine)
    santé         = 100 − risque

Aucune I/O : `compute_health_scores` prend les lectures environnementales et le
journal SCADA (silver) et renvoie la table horaire complète — l'équivalent du
`site_health_scores.csv` produit par le notebook.
"""
import numpy as np
import pandas as pd

from app.ml.health_score import config as cfg
from app.ml.health_score.features import (
    add_env_anomaly_burden,
    build_battery_hourly,
    build_energy_hourly,
    build_env_hourly,
    flag_events,
    pm_risk_from_last_pm,
)


# ------------------------------------------------------------------- validation
def validate_weights(weights: dict, tolerance: float = 1e-6) -> bool:
    """Valide une configuration de poids : groupes et clés présents, valeurs
    numériques finies non négatives, somme de chaque groupe = 1. Lève `ValueError`
    en nommant le groupe fautif et son total courant."""
    for group, required_keys in cfg.REQUIRED_WEIGHT_KEYS.items():
        if group not in weights:
            raise ValueError(f"WEIGHTS : groupe requis manquant « {group} ».")
        group_weights = weights[group]
        missing = required_keys - set(group_weights)
        if missing:
            raise ValueError(f"WEIGHTS['{group}'] : clés manquantes {sorted(missing)}.")
        for key in required_keys:
            value = group_weights[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(
                    f"WEIGHTS['{group}']['{key}'] doit être numérique, reçu {type(value).__name__}."
                )
            if not np.isfinite(value):
                raise ValueError(f"WEIGHTS['{group}']['{key}'] doit être fini, reçu {value}.")
            if value < 0:
                raise ValueError(f"WEIGHTS['{group}']['{key}'] ne peut être négatif, reçu {value}.")
        total = sum(group_weights[key] for key in required_keys)
        if abs(total - 1.0) > tolerance:
            raise ValueError(
                f"WEIGHTS['{group}'] doit sommer à 1 (± {tolerance}) ; total actuel {total:.6f}."
            )
    return True


def active_weights(frame: pd.DataFrame, weights: dict, label: str) -> dict:
    """Retire les composantes sans signal puis renormalise le reste à 1.

    Une composante dont les mots-clés ne matchent jamais vaut 0 à chaque heure :
    laissée en place, son poids est mort — le risque de base ne peut plus atteindre
    100 et le site paraît systématiquement plus sain qu'il ne l'est.
    """
    active = {term: w for term, w in weights.items() if frame[term].max() > 0}
    if not active:
        raise ValueError(f"{label} : aucune composante ne porte de signal.")
    total = sum(active.values())
    return {term: w / total for term, w in active.items()}


def weighted_risk(frame: pd.DataFrame, weights: dict) -> pd.Series:
    return 100 * sum(w * frame[term] for term, w in weights.items())


def calculate_final_risk(
    base_risk: pd.Series,
    anomaly_burden: pd.Series,
    maintenance_risk: pd.Series,
    anomaly_weight: float,
    maintenance_weight: float,
) -> pd.Series:
    """Risque de base amplifié par la charge d'anomalie et le retard de PM."""
    anomaly_factor = 1 + anomaly_weight * anomaly_burden.clip(0, 1)
    maintenance_factor = 1 + maintenance_weight * maintenance_risk.clip(0, 1)
    return (base_risk * anomaly_factor * maintenance_factor).clip(0, 100)


def _base_risk(frame: pd.DataFrame, weights: dict, term_map: dict, label: str):
    mapped = {term_map[k]: v for k, v in weights.items()}
    effective = active_weights(frame, mapped, label)
    return weighted_risk(frame, effective).clip(0, 100), effective


def calculate_environmental_base_risk(env_hourly, weights):
    return _base_risk(env_hourly, weights, cfg.ENV_TERM_MAP, "environmental")


def calculate_energy_base_risk(energy_hourly, weights):
    return _base_risk(energy_hourly, weights, cfg.ENERGY_TERM_MAP, "energy")


def calculate_battery_base_risk(battery_hourly, weights):
    return _base_risk(battery_hourly, weights, cfg.BATTERY_TERM_MAP, "battery")


# ------------------------------------------------------------- scores par domaine
def build_environmental_scores(env_hourly: pd.DataFrame, weights: dict) -> pd.DataFrame:
    df = add_env_anomaly_burden(env_hourly)
    df["environmental_base_risk"], _ = calculate_environmental_base_risk(df, weights["environmental"])
    df["environmental_pm_risk"] = pm_risk_from_last_pm(
        df.index, cfg.ENV_LAST_PM_DATE, cfg.ENV_MAINTENANCE_INTERVAL_DAYS
    )
    mult = cfg.ANOMALY_PM_MULTIPLIERS["environmental"]
    df["environmental_risk_score"] = calculate_final_risk(
        df["environmental_base_risk"], df["environmental_anomaly_burden"],
        df["environmental_pm_risk"], mult["anomaly_weight"], mult["maintenance_weight"],
    )
    df["environmental_health_score"] = 100 - df["environmental_risk_score"]
    return df


def build_energy_scores(energy_hourly: pd.DataFrame, weights: dict) -> pd.DataFrame:
    df = energy_hourly.copy()
    df["energy_base_risk"], effective = calculate_energy_base_risk(df, weights["energy"])
    # Combien de types d'événements sont simultanément élevés, et à quel point —
    # moyenne continue des termes actifs plutôt qu'un comptage binaire, pour que
    # l'indicateur redescende en douceur.
    df["energy_sequence_anomaly"] = df[list(effective)].mean(axis=1).clip(0, 1)
    df["energy_anomaly_burden"] = (
        0.40 * df["energy_frequency_anomaly"]
        + 0.35 * df["energy_duration_anomaly"]
        + 0.25 * df["energy_sequence_anomaly"]
    ).clip(0, 1)
    df["energy_pm_risk"] = pm_risk_from_last_pm(
        df.index, cfg.ENERGY_LAST_PM_DATE, cfg.ENERGY_MAINTENANCE_INTERVAL_DAYS
    )
    mult = cfg.ANOMALY_PM_MULTIPLIERS["energy"]
    df["energy_risk_score"] = calculate_final_risk(
        df["energy_base_risk"], df["energy_anomaly_burden"], df["energy_pm_risk"],
        mult["anomaly_weight"], mult["maintenance_weight"],
    )
    df["energy_health_score"] = 100 - df["energy_risk_score"]
    return df


def build_battery_scores(battery_hourly: pd.DataFrame, weights: dict) -> pd.DataFrame:
    df = battery_hourly.copy()
    df["battery_base_risk"], _ = calculate_battery_base_risk(df, weights["battery"])
    # Aucune date de service batterie connue → ancrage sur la 1re date de données.
    df["battery_pm_risk"] = pm_risk_from_last_pm(
        df.index, df.index.min(), cfg.BATTERY_MAINTENANCE_INTERVAL_DAYS
    )
    mult = cfg.ANOMALY_PM_MULTIPLIERS["battery"]
    df["battery_risk_score"] = calculate_final_risk(
        df["battery_base_risk"], df["battery_anomaly_burden"], df["battery_pm_risk"],
        mult["anomaly_weight"], mult["maintenance_weight"],
    )
    df["battery_health_score"] = 100 - df["battery_risk_score"]
    return df


# ------------------------------------------------------------------ calibration
def calibrate_energy_risk(df: pd.DataFrame) -> pd.DataFrame:
    """Compression douce du risque énergie + plancher pour coupure persistante.

    Sans compression, un risque brut de 100 force la santé énergie à 0 dès la
    moindre rafale d'alarmes. La compression garde les risques faibles et moyens
    lisibles ; le plancher garantit qu'une coupure **réellement persistante** reste
    traitée comme sévère malgré la compression.
    """
    out = df.copy()
    if "energy_risk_score_raw" not in out.columns:
        out["energy_risk_score_raw"] = out["energy_risk_score"]
        out["energy_health_score_raw"] = out["energy_health_score"]

    raw = out["energy_risk_score_raw"].replace([np.inf, -np.inf], np.nan).fillna(0).clip(0, 100)
    out["energy_risk_score_calibrated"] = (
        100 * (1 - np.exp(-raw / cfg.ENERGY_COMPRESSION_SCALE))
    ).clip(0, 100)

    def _duration(name: str) -> pd.Series:
        return out.get(name, pd.Series(0.0, index=out.index)).fillna(0).clip(lower=0)

    outage = _duration("outage_duration_hours")
    # `generator_hours` / `power_transfer_hours` ne sont pas suivies (la durée n'est
    # tracée que pour les coupures) : elles valent 0, comme dans le notebook.
    generator = _duration("generator_hours")
    transfer = _duration("power_transfer_hours")

    severe = (
        (outage >= 4)
        | ((outage >= 2) & (generator >= 2))
        | ((outage >= 2) & (transfer >= 3))
    )
    floor = (cfg.ENERGY_SEVERE_FLOOR + 3 * (outage - 4).clip(lower=0)).clip(upper=100)
    out.loc[severe, "energy_risk_score_calibrated"] = np.maximum(
        out.loc[severe, "energy_risk_score_calibrated"], floor.loc[severe]
    )
    out["energy_risk_score_calibrated"] = out["energy_risk_score_calibrated"].clip(0, 100)
    out["energy_health_score_calibrated"] = 100 - out["energy_risk_score_calibrated"]

    out["energy_risk_score"] = out["energy_risk_score_calibrated"]
    out["energy_health_score"] = out["energy_health_score_calibrated"]
    return out


# ------------------------------------------------------------ lecture opérateur
def recommend_action(row: pd.Series) -> str:
    """Action conseillée à partir du domaine dominant et de la durée du problème.

    Aide à la décision : un point d'entrée d'inspection, jamais une consigne
    automatique. Texte en français (interface opérateur) ; la logique de
    branchement est celle du notebook.
    """
    health = row["overall_site_health"]
    driver = row["main_risk_driver"]
    outage_hours = row.get("outage_duration_hours", 0) or 0
    battery_hours = row.get("battery_alarm_duration_hours", 0) or 0
    if pd.isna(outage_hours):
        outage_hours = 0
    if pd.isna(battery_hours):
        battery_hours = 0

    if health >= 90:
        return "Poursuivre la surveillance de routine"

    if driver == "Battery":
        if battery_hours >= 12:
            return ("Inspection urgente des batteries onduleur : capacité, "
                    "fonctionnement du chargeur, persistance des décharges")
        if battery_hours >= 4:
            return ("Inspecter les batteries onduleur et le système de charge ; "
                    "revoir les décharges récentes")
        return "Revoir les alarmes batterie, l'état des onduleurs et l'historique de récurrence"

    if driver == "Energy":
        if outage_hours >= 4:
            return ("Investigation urgente de l'alimentation secteur : vérifier groupe "
                    "électrogène, inverseur (ATS) et alimentation de secours")
        if outage_hours >= 1:
            return "Investiguer la coupure récente et vérifier le basculement secteur → secours"
        return ("Inspecter l'instabilité d'alimentation, l'activité du groupe "
                "et les basculements répétés")

    if driver == "Environmental":
        temperature = row.get("temperature", np.nan)
        humidity = row.get("humidity", np.nan)
        if pd.notna(temperature) and temperature > 30:
            return "Inspecter la climatisation et le refroidissement : température élevée"
        if pd.notna(humidity) and (humidity < 35 or humidity > 60):
            return "Inspecter la ventilation et le contrôle d'humidité"
        return "Inspecter la climatisation, la stabilité des capteurs et les conditions ambiantes"

    return "Revoir les sous-scores et les alarmes récentes du site"


def add_operational_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Contributions, domaine dominant, statut, tendance, priorité, action."""
    out = df.copy()
    weights = cfg.WEIGHTS["overall"]

    for col in ("environmental_risk_score", "energy_risk_score", "battery_risk_score"):
        out[col] = out[col].replace([np.inf, -np.inf], np.nan).fillna(0).clip(0, 100)

    out["environmental_contribution"] = weights["environmental"] * out["environmental_risk_score"]
    out["energy_contribution"] = weights["energy"] * out["energy_risk_score"]
    out["battery_contribution"] = weights["battery"] * out["battery_risk_score"]

    contributions = ["environmental_contribution", "energy_contribution", "battery_contribution"]
    out["overall_site_risk"] = out[contributions].sum(axis=1).clip(0, 100)
    out["overall_site_health"] = 100 - out["overall_site_risk"]

    out["main_risk_driver"] = np.where(
        out["overall_site_risk"] < 5,
        "None",
        out[contributions].idxmax(axis=1).map({
            "environmental_contribution": "Environmental",
            "energy_contribution": "Energy",
            "battery_contribution": "Battery",
        }),
    )
    out["main_driver_share"] = (
        out[contributions].max(axis=1) / out["overall_site_risk"].replace(0, np.nan)
    ).fillna(0).clip(0, 1)

    out["site_health_status"] = pd.cut(
        out["overall_site_health"],
        bins=[-np.inf, *cfg.STATUS_BINS, np.inf],
        labels=cfg.STATUS_LABELS,
        right=False,
    ).astype(str)

    out = out.sort_index()
    for column in [*cfg.SUBSYSTEM_HEALTH_COLUMNS, "overall_site_health"]:
        out[f"{column}_trend_6h"] = out[column].diff(cfg.TREND_SHORT_HOURS)
        out[f"{column}_trend_24h"] = out[column].diff(cfg.TREND_LONG_HOURS)
        out[f"{column}_volatility_24h"] = (
            out[column].rolling(cfg.VOLATILITY_WINDOW_HOURS, min_periods=6).std()
        )

    # Le score brut peut osciller d'une heure à l'autre (une alarme qui apparaît
    # et disparaît suffit) : on expose une série lissée pour l'affichage sans
    # toucher au score brut, qui reste la référence d'analyse.
    out["overall_site_health_smoothed"] = (
        out["overall_site_health"].rolling(cfg.OVERALL_SMOOTHING_WINDOW_HOURS, min_periods=1).mean()
    )
    out["overall_site_health_smoothed_6h"] = out["overall_site_health_smoothed"]

    trend = out["overall_site_health_trend_24h"]
    out["health_trend_status"] = np.select(
        [trend <= -15, trend <= -5, trend >= 15, trend >= 5],
        ["Rapidly Deteriorating", "Deteriorating", "Rapidly Improving", "Improving"],
        default="Stable",
    )
    out["maintenance_priority"] = np.select(
        [out["overall_site_health"] < b for b in cfg.STATUS_BINS],
        cfg.PRIORITY_LABELS,
        default=cfg.PRIORITY_DEFAULT,
    )
    out["recommended_action"] = out.apply(recommend_action, axis=1)
    return out


def add_score_confidence(df: pd.DataFrame) -> pd.DataFrame:
    """Confiance 0-100 : dégradée quand l'heure est peu observée ou incomplète.

    Le score reste calculé — c'est sa **fiabilité** qui baisse, information que
    l'interface doit pouvoir afficher plutôt que de masquer la valeur.
    """
    out = df.copy()
    out["score_confidence"] = 100
    if "observation_count" in out.columns:
        out.loc[out["observation_count"] < 10, "score_confidence"] -= 15
    if "humidity" in out.columns:
        out.loc[out["humidity"].isna(), "score_confidence"] -= 20
    out["score_confidence"] = out["score_confidence"].clip(0, 100)
    return out


# ------------------------------------------------------------------- pipeline
def compute_health_scores(
    df_env: pd.DataFrame,
    df_log: pd.DataFrame,
    weights: dict | None = None,
) -> pd.DataFrame:
    """Lectures env. + journal SCADA → table horaire des scores de santé.

    `df_env` : silver `th_clean` (`ts, temperature, humidity`).
    `df_log`  : silver `scada_clean` (`log_time, state, message, category`).

    Fenêtre de calcul = **intersection** des trois sources. L'union obligerait à
    inventer des features énergie/batterie pour les heures hors journal : un 0 y
    signifierait « aucune alarme » alors qu'il signifie « aucune donnée », et le
    site paraîtrait parfaitement sain pendant des mois.
    """
    weights = weights or cfg.WEIGHTS
    validate_weights(weights)

    env = build_environmental_scores(build_env_hourly(df_env), weights)

    events = flag_events(df_log)
    events["log_time"] = pd.to_datetime(events["log_time"], errors="coerce")
    events = events.dropna(subset=["log_time"]).sort_values("log_time")
    energy = build_energy_scores(build_energy_hourly(events), weights)
    battery = build_battery_scores(build_battery_hourly(events), weights)

    start = max(env.index.min(), energy.index.min(), battery.index.min())
    end = min(env.index.max(), energy.index.max(), battery.index.max())
    if pd.isna(start) or pd.isna(end) or start >= end:
        raise ValueError(
            f"Aucune période commune entre les sources (début le plus tardif {start}, "
            f"fin la plus précoce {end})."
        )

    index = pd.date_range(start=start.ceil("h"), end=end.floor("h"), freq="1h", name="timestamp")
    scores = (
        env.reindex(index)
        .join(energy.reindex(index), rsuffix="_energy")
        .join(battery.reindex(index), rsuffix="_battery")
    )

    scores = calibrate_energy_risk(scores)
    scores = add_operational_columns(scores)
    scores = add_score_confidence(scores)
    scores["weight_version"] = cfg.WEIGHT_VERSION
    scores["score_version"] = cfg.SCORE_VERSION
    return scores
