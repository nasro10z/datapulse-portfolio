"""Features dynamiques de prévision — portage de l'étape 2 du notebook.

Pour chaque variable source (santé, risque, charge d'anomalie, risque de PM,
température/humidité, durées d'alarme), on dérive la **forme de sa trajectoire
récente** : retards, variations, vitesses, statistiques et pentes glissantes,
accélération. S'y ajoutent les compteurs de dégradation continue et les
interactions entre sous-systèmes.

C'est ce jeu élargi qui donne au modèle de quoi battre la persistance : le niveau
courant à lui seul ne dit pas si le site est en train de décrocher, alors qu'une
pente négative qui s'accélère sur trois sous-systèmes à la fois, si.

**Aucune fuite du futur** : les retards et différences ne décalent que vers le
passé (périodes positives) ; les fenêtres glissantes incluent la ligne courante
— l'heure en cours est connue au moment de prédire — mais jamais une ligne
future.
"""
import numpy as np
import pandas as pd

from app.ml.health_score import config as cfg
from app.ml.health_score.features import consecutive_run_length

_HEALTH_COLUMNS = ["environmental_health_score", "energy_health_score", "battery_health_score"]
_RISK_COLUMNS = ["environmental_risk_score", "energy_risk_score", "battery_risk_score"]


def rolling_slope(series: pd.Series, window: int) -> pd.Series:
    """Pente (unités par heure) d'un ajustement linéaire sur la fenêtre glissante,
    ligne courante incluse. Forme fermée des moindres carrés pour des abscisses
    régulières — bien plus rapide qu'un `polyfit` par fenêtre."""
    x = np.arange(window, dtype=float)
    x_centered = x - x.mean()
    denominator = (x_centered ** 2).sum()

    def _slope(y: np.ndarray) -> float:
        return float((x_centered * (y - y.mean())).sum() / denominator)

    return series.rolling(window, min_periods=window).apply(_slope, raw=True)


def _trajectory_features(series: pd.Series, prefix: str, out: dict) -> None:
    """Retards / variations / vitesses / stats glissantes / pentes / accélération."""
    for lag in cfg.LAG_HOURS:
        out[f"{prefix}_lag_{lag}h"] = series.shift(lag)
    for period in cfg.CHANGE_HOURS:
        out[f"{prefix}_change_{period}h"] = series.diff(period)
    for period in cfg.RATE_HOURS:
        out[f"{prefix}_rate_{period}h"] = series.diff(period) / period
    for window in cfg.ROLLING_WINDOWS:
        rolling = series.rolling(window, min_periods=window)
        minimum, maximum = rolling.min(), rolling.max()
        out[f"{prefix}_rollmean_{window}h"] = rolling.mean()
        out[f"{prefix}_rollstd_{window}h"] = rolling.std()
        out[f"{prefix}_rollmin_{window}h"] = minimum
        out[f"{prefix}_rollmax_{window}h"] = maximum
        out[f"{prefix}_rollrange_{window}h"] = maximum - minimum
    for window in cfg.SLOPE_WINDOWS:
        out[f"{prefix}_slope_{window}h"] = rolling_slope(series, window)
    for period in cfg.ACCELERATION_HOURS:
        out[f"{prefix}_accel_{period}h"] = series.diff(period).diff(period)


def _deterioration_streaks(frame: pd.DataFrame, out: dict) -> None:
    """Depuis combien d'heures la dégradation est **continue**.

    Une baisse de 2 points étalée sur six heures consécutives ne se lit pas comme
    six baisses isolées de même amplitude : c'est la continuité qui signale une
    dérive plutôt qu'un soubresaut.
    """
    if "overall_site_health" in frame:
        declining = (frame["overall_site_health"].diff() < 0).astype(int)
        out["overall_health_consecutive_decline_hours"] = consecutive_run_length(declining)
    for column in _HEALTH_COLUMNS:
        if column in frame:
            declining = (frame[column].diff() < 0).astype(int)
            out[f"{column}_consecutive_decline_hours"] = consecutive_run_length(declining)
    for column in _RISK_COLUMNS:
        if column in frame:
            increasing = (frame[column].diff() > 0).astype(int)
            out[f"{column}_consecutive_increase_hours"] = consecutive_run_length(increasing)


def _cross_subsystem_features(frame: pd.DataFrame, out: dict) -> None:
    """Interactions entre domaines : deux sous-systèmes qui se dégradent ensemble
    est un signal différent de la somme de leurs dégradations séparées."""
    pairs = [
        ("energy_risk_score", "battery_risk_score", "interaction_energy_battery_risk"),
        ("environmental_risk_score", "energy_risk_score", "interaction_environmental_energy_risk"),
        ("environmental_risk_score", "battery_risk_score", "interaction_environmental_battery_risk"),
        ("energy_anomaly_burden", "battery_anomaly_burden", "interaction_energy_battery_anomaly_burden"),
    ]
    for left, right, name in pairs:
        if left in frame and right in frame:
            out[name] = frame[left] * frame[right]

    risks = [c for c in _RISK_COLUMNS if c in frame]
    if len(risks) >= 2:
        out["max_subsystem_risk"] = frame[risks].max(axis=1)

    healths = [c for c in _HEALTH_COLUMNS if c in frame]
    if len(healths) >= 2:
        health_frame = frame[healths]
        out["min_subsystem_health"] = health_frame.min(axis=1)
        out["subsystem_health_spread"] = health_frame.max(axis=1) - health_frame.min(axis=1)
        out["subsystems_below_80"] = (health_frame < 80).sum(axis=1)
        out["subsystems_below_60"] = (health_frame < 60).sum(axis=1)


def build_dynamic_features(
    frame: pd.DataFrame,
    sources: list[str] | None = None,
) -> pd.DataFrame:
    """Table horaire → features dynamiques (nouvelles colonnes uniquement).

    `sources` restreint les variables sources traitées. Au déroulé de la prévision,
    seules celles qui apparaissent dans les features retenues sont utiles :
    recalculer les ~1 200 features à chaque pas serait du travail jeté.
    """
    wanted = sources if sources is not None else cfg.DYNAMIC_SOURCE_VARIABLES
    available = [c for c in wanted if c in frame.columns]

    columns: dict[str, pd.Series] = {}
    for source in available:
        _trajectory_features(frame[source], source, columns)
    _deterioration_streaks(frame, columns)
    _cross_subsystem_features(frame, columns)

    features = pd.DataFrame(columns, index=frame.index)
    # Les vitesses et interactions peuvent exploser si une grandeur au dénominateur
    # vaut exactement 0 en amont : un ±inf n'est pas une mesure, c'est un trou.
    features = features.replace([np.inf, -np.inf], np.nan)
    features = features.drop(columns=features.columns[features.isna().all()])
    # Une feature dérivée ne doit jamais masquer une colonne réelle du pipeline.
    return features.drop(columns=[c for c in features.columns if c in frame.columns])


def sources_used_by(feature_names: list[str]) -> list[str]:
    """Variables sources dont dépendent `feature_names`.

    Sert à ne recalculer, au déroulé de la prévision, que les features réellement
    nécessaires au modèle retenu (20 sur ~1 200).
    """
    return [
        source for source in cfg.DYNAMIC_SOURCE_VARIABLES
        if any(name.startswith(f"{source}_") for name in feature_names)
    ]
