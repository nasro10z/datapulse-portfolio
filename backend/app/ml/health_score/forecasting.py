"""Prévision du score de santé — portage du notebook `health_scores.ipynb`.

Deux modèles, entraînés sur la table horaire des scores :

  1. **Régression** — santé globale à +6 h. Trois candidats sont entraînés et
     **le meilleur sur la validation est retenu** : persistance (« la santé dans
     6 h = la santé maintenant »), régression linéaire, gradient boosting. Sur une
     série aussi auto-corrélée, la persistance est une référence redoutable — le
     notebook la voit gagner, et servir un modèle qui fait moins bien qu'elle
     serait une régression de qualité déguisée en modèle. La sélection est donc
     faite par les données, pas décidée d'avance ; les métriques des trois
     candidats sont conservées dans les métadonnées.
  2. **Classification** — probabilité d'une **chute majeure** (≥ 10 points de
     santé perdus sur 6 h), seuil de décision choisi sur la validation.

Découpage **chronologique** 70 / 15 / 15 (jamais aléatoire : ce serait laisser le
modèle voir le futur). Toutes les fonctions sont pures ; la persistance des
artefacts passe par `save_artifacts` / `load_artifacts`, appelées par l'ETL.

Au-delà de +6 h (horizons 7 j / 30 j de l'interface), la trajectoire est produite
par **déroulé récursif** du même modèle : à chaque pas de 6 h, la prédiction
devient l'observation suivante, les sous-scores et les conditions sont maintenus
en l'état, et seul le risque de maintenance préventive évolue (il ne dépend que du
temps). C'est une projection « à conditions inchangées », pas une certitude — et
la bande de confiance s'élargit à chaque pas pour le dire.
"""
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)

from app.ml.health_score import config as cfg
from app.ml.health_score.features import pm_risk_from_last_pm

REGRESSOR_PATH = cfg.MODELS_DIR / "health_forecast_regressor.joblib"
CLASSIFIER_PATH = cfg.MODELS_DIR / "health_drop_classifier.joblib"
METADATA_PATH = cfg.MODELS_DIR / "metadata.json"


# ------------------------------------------------------------------- features
def build_forecast_features(scores: pd.DataFrame) -> pd.DataFrame:
    """Table horaire des scores → table d'apprentissage (cible + features).

    Cible `target_health_6h` = santé globale décalée de −6 h (donc la valeur
    future). Features : retards, statistiques glissantes, variations, calendrier
    (encodé en sinus/cosinus pour que 23 h et 0 h soient voisins).
    """
    df = scores.copy()
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df.loc[df.index.notna()].sort_index()
    df = df[~df.index.duplicated(keep="last")]

    health = df["overall_site_health"]
    df["target_health_6h"] = health.shift(-cfg.FORECAST_HORIZON_HOURS)

    for lag in cfg.HEALTH_LAGS:
        df[f"overall_health_lag_{lag}h"] = health.shift(lag)
    for window in cfg.ROLLING_WINDOWS:
        rolling = health.rolling(window, min_periods=window)
        df[f"health_mean_{window}h"] = rolling.mean()
        df[f"health_std_{window}h"] = rolling.std()
        df[f"health_min_{window}h"] = rolling.min()
    for column in cfg.SUBSYSTEM_HEALTH_COLUMNS:
        for lag in cfg.SUBSYSTEM_LAGS:
            df[f"{column}_lag_{lag}h"] = df[column].shift(lag)
    for period in cfg.CHANGE_PERIODS:
        df[f"overall_health_change_{period}h"] = health.diff(period)

    df["hour"] = df.index.hour
    df["day_of_week"] = df.index.dayofweek
    df["day_of_month"] = df.index.day
    df["month"] = df.index.month
    df["is_weekend"] = (df.index.dayofweek >= 5).astype(int)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["day_of_week_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["day_of_week_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

    df["health_change_6h"] = df["target_health_6h"] - health
    df["major_drop_6h"] = np.where(
        df["health_change_6h"].notna(),
        (df["health_change_6h"] <= cfg.MAJOR_DROP_THRESHOLD).astype(int),
        np.nan,
    )
    df["severe_drop_6h"] = np.where(
        df["health_change_6h"].notna(),
        (df["health_change_6h"] <= cfg.SEVERE_DROP_THRESHOLD).astype(int),
        np.nan,
    )
    return df


def select_feature_columns(forecast_data: pd.DataFrame) -> list[str]:
    """Colonnes numériques exploitables : indicateurs courants + retards +
    statistiques glissantes + calendrier, dédupliquées en conservant l'ordre."""
    lag_features = [c for c in forecast_data.columns if "_lag_" in c]
    rolling_features = [
        c for c in forecast_data.columns
        if any(p in c for p in ("_mean_", "_std_", "_min_", "_max_", "_change_"))
        and not c.startswith("health_change_6h")
    ]
    calendar = ["hour_sin", "hour_cos", "day_of_week_sin", "day_of_week_cos", "is_weekend", "month"]
    current = [c for c in cfg.CURRENT_NUMERIC_FEATURES if c in forecast_data.columns]

    columns = list(dict.fromkeys(current + lag_features + rolling_features + calendar))
    return [
        c for c in columns
        if c in forecast_data.columns
        and pd.api.types.is_numeric_dtype(forecast_data[c])
        and not forecast_data[c].isna().all()
    ]


def split_chronological(data: pd.DataFrame, train=0.70, validation=0.85):
    """Découpage temporel 70 / 15 / 15 — l'ordre du temps est préservé."""
    n = len(data)
    train_end, validation_end = int(n * train), int(n * validation)
    return (data.iloc[:train_end].copy(),
            data.iloc[train_end:validation_end].copy(),
            data.iloc[validation_end:].copy())


# ----------------------------------------------------------------- évaluation
def evaluate_forecast(actual, predicted, model_name: str) -> dict:
    """MAE / RMSE / R², plus précision et rappel sur le régime « risque élevé »
    (santé < 60) : une erreur moyenne faible ne dit rien de la capacité à voir
    venir les mauvaises heures, qui sont les seules qui comptent en exploitation."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    actual_risk = actual < cfg.DEGRADATION_THRESHOLD
    predicted_risk = predicted < cfg.DEGRADATION_THRESHOLD
    tp = int(np.sum(actual_risk & predicted_risk))
    fp = int(np.sum(~actual_risk & predicted_risk))
    fn = int(np.sum(actual_risk & ~predicted_risk))

    return {
        "model": model_name,
        "MAE": float(mean_absolute_error(actual, predicted)),
        "RMSE": float(np.sqrt(mean_squared_error(actual, predicted))),
        "R2": float(r2_score(actual, predicted)),
        "high_risk_precision": float(tp / (tp + fp)) if tp + fp else None,
        "high_risk_recall": float(tp / (tp + fn)) if tp + fn else None,
        "predicted_min": float(predicted.min()),
        "predicted_max": float(predicted.max()),
    }


def evaluate_classifier(actual, probabilities, threshold: float, model_name: str) -> dict:
    predicted = (np.asarray(probabilities) >= threshold).astype(int)
    actual = np.asarray(actual)
    single_class = len(np.unique(actual)) < 2
    return {
        "model": model_name,
        "threshold": float(threshold),
        "precision": float(precision_score(actual, predicted, zero_division=0)),
        "recall": float(recall_score(actual, predicted, zero_division=0)),
        "f1": float(f1_score(actual, predicted, zero_division=0)),
        "roc_auc": None if single_class else float(roc_auc_score(actual, probabilities)),
        "pr_auc": None if single_class else float(average_precision_score(actual, probabilities)),
        "predicted_alerts": int(predicted.sum()),
        "actual_events": int(actual.sum()),
    }


# ---------------------------------------------------------------- entraînement
class PersistenceRegressor:
    """Prédicteur « rien ne change » : la santé dans 6 h = la santé maintenant.

    Ce n'est pas un modèle par défaut mais un **candidat à part entière** : sur une
    série horaire fortement auto-corrélée, il est difficile à battre, et le retenir
    quand il gagne est le résultat honnête de la comparaison. Il expose l'interface
    scikit-learn (`predict`) pour être interchangeable avec les autres candidats.
    """

    name = "Persistance"

    def __init__(self, column: str = "overall_site_health"):
        self.column = column

    def fit(self, X, y=None):  # noqa: ARG002 — présent pour l'interface commune
        return self

    def predict(self, X):
        return np.asarray(X[self.column], dtype=float)


def train(scores: pd.DataFrame) -> dict:
    """Entraîne les candidats, retient le meilleur sur la validation, et renvoie
    les artefacts + les métriques de tous les candidats.

    Les valeurs manquantes sont comblées par les **médianes d'entraînement** (et
    jamais recalculées sur validation/test : ce serait une fuite du futur vers le
    passé). Les mêmes médianes servent à la prédiction.
    """
    forecast_data = build_forecast_features(scores)
    feature_columns = select_feature_columns(forecast_data)

    model_data = forecast_data[feature_columns + ["target_health_6h"]].dropna(
        subset=cfg.REQUIRED_FORECAST_FEATURES + ["target_health_6h"]
    )
    if len(model_data) < 200:
        raise ValueError(
            f"Historique insuffisant pour entraîner la prévision : {len(model_data)} lignes "
            "exploitables (200 minimum)."
        )

    train_data, validation_data, test_data = split_chronological(model_data)
    medians = train_data[feature_columns].median()
    feature_columns = [c for c in feature_columns if pd.notna(medians[c])]
    medians = medians[feature_columns]

    def _x(frame):
        return frame[feature_columns].fillna(medians)

    y_train, y_validation, y_test = (
        train_data["target_health_6h"], validation_data["target_health_6h"],
        test_data["target_health_6h"],
    )

    candidates = {
        "persistence": PersistenceRegressor(),
        "linear": LinearRegression(),
        "gradient_boosting": HistGradientBoostingRegressor(
            learning_rate=0.05, max_iter=300, max_leaf_nodes=20,
            min_samples_leaf=15, l2_regularization=1.0, random_state=42,
        ),
    }

    metrics: dict = {}
    validation_mae: dict[str, float] = {}
    for name, model in candidates.items():
        model.fit(_x(train_data), y_train)
        validation_predictions = np.clip(model.predict(_x(validation_data)), 0, 100)
        test_predictions = np.clip(model.predict(_x(test_data)), 0, 100)
        validation_mae[name] = float(mean_absolute_error(y_validation, validation_predictions))
        metrics[name] = {
            "validation_MAE": validation_mae[name],
            **evaluate_forecast(y_test, test_predictions, name),
        }

    # Sélection sur la VALIDATION : le test reste intact pour l'estimation finale.
    selected = min(validation_mae, key=validation_mae.get)
    regressor = candidates[selected]
    test_predictions = np.clip(regressor.predict(_x(test_data)), 0, 100)
    metrics["selected_model"] = selected
    metrics["mae_improvement_vs_persistence"] = (
        metrics["persistence"]["MAE"] - metrics[selected]["MAE"]
    )
    # Écart-type des résidus de test : c'est lui qui donne l'échelle de la bande
    # de confiance servie à l'interface (pas une valeur choisie à la main).
    residual_std = float(np.std(np.asarray(y_test, dtype=float) - test_predictions))

    classifier, threshold, classifier_metrics = _train_drop_classifier(
        forecast_data, feature_columns, medians
    )

    return {
        "regressor": regressor,
        "selected_model": selected,
        "classifier": classifier,
        "feature_columns": feature_columns,
        "medians": medians,
        "drop_threshold": threshold,
        "residual_std": residual_std,
        "metrics": {**metrics, "drop_classifier": classifier_metrics},
        "n_rows": {"train": len(train_data), "validation": len(validation_data), "test": len(test_data)},
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "score_version": cfg.SCORE_VERSION,
        "weight_version": cfg.WEIGHT_VERSION,
    }


def _train_drop_classifier(forecast_data, feature_columns, medians):
    """Classifieur de chute majeure + seuil de décision choisi sur la validation.

    Renvoie `(None, None, {...})` si l'historique ne contient pas les deux classes
    — sans exemple de chute, aucun seuil n'est apprenable et prétendre le contraire
    serait pire que de s'en passer.
    """
    data = forecast_data[feature_columns + ["major_drop_6h"]].dropna(
        subset=cfg.REQUIRED_FORECAST_FEATURES + ["major_drop_6h"]
    )
    data["major_drop_6h"] = data["major_drop_6h"].astype(int)
    train_data, validation_data, test_data = split_chronological(data)

    if train_data["major_drop_6h"].nunique() < 2:
        return None, None, {"status": "non entraîné — une seule classe dans l'historique"}

    x_train = train_data[feature_columns].fillna(medians)
    classifier = RandomForestClassifier(
        n_estimators=500, max_depth=8, min_samples_leaf=5, max_features="sqrt",
        class_weight="balanced_subsample", random_state=42, n_jobs=-1,
    )
    classifier.fit(x_train, train_data["major_drop_6h"])

    validation_probabilities = classifier.predict_proba(
        validation_data[feature_columns].fillna(medians)
    )[:, 1]
    candidates = [
        evaluate_classifier(validation_data["major_drop_6h"], validation_probabilities, t, "RandomForest")
        for t in np.arange(0.10, 0.91, 0.05)
    ]
    best = max(candidates, key=lambda r: (r["f1"], r["recall"]))
    threshold = best["threshold"]

    test_probabilities = classifier.predict_proba(test_data[feature_columns].fillna(medians))[:, 1]
    metrics = evaluate_classifier(
        test_data["major_drop_6h"], test_probabilities, threshold, "RandomForest (test)"
    )
    metrics["selected_on_validation_f1"] = best["f1"]
    return classifier, threshold, metrics


# --------------------------------------------------------------- persistance
def save_artifacts(artifacts: dict) -> dict:
    """Écrit les modèles + les métadonnées sous `ml/models/health_forecast/`."""
    import json

    cfg.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {k: artifacts[k] for k in ("regressor", "selected_model", "feature_columns",
                                   "medians", "residual_std", "drop_threshold")},
        REGRESSOR_PATH,
    )
    if artifacts.get("classifier") is not None:
        joblib.dump(artifacts["classifier"], CLASSIFIER_PATH)

    metadata = {
        "score_version": artifacts["score_version"],
        "weight_version": artifacts["weight_version"],
        "trained_at": artifacts["trained_at"],
        "selected_model": artifacts["selected_model"],
        "horizon_hours": cfg.FORECAST_HORIZON_HOURS,
        "n_features": len(artifacts["feature_columns"]),
        "n_rows": artifacts["n_rows"],
        "drop_threshold": artifacts["drop_threshold"],
        "residual_std": artifacts["residual_std"],
        "metrics": artifacts["metrics"],
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return metadata


def load_artifacts() -> dict:
    """Recharge les artefacts entraînés. Lève `FileNotFoundError` si absents."""
    if not REGRESSOR_PATH.exists():
        raise FileNotFoundError(
            f"Modèle de prévision absent ({REGRESSOR_PATH}). Lancer `python -m app.etl.forecast`."
        )
    bundle = joblib.load(REGRESSOR_PATH)
    bundle["classifier"] = joblib.load(CLASSIFIER_PATH) if CLASSIFIER_PATH.exists() else None
    return bundle


# ----------------------------------------------------------------- prédiction
def predict_next(scores: pd.DataFrame, artifacts: dict) -> float:
    """Santé globale prévue à +6 h à partir de la dernière heure disponible."""
    features = build_forecast_features(scores)
    row = features[artifacts["feature_columns"]].fillna(artifacts["medians"]).iloc[[-1]]
    return float(np.clip(artifacts["regressor"].predict(row)[0], 0, 100))


def predict_drop_probability(scores: pd.DataFrame, artifacts: dict) -> float | None:
    """Probabilité d'une chute majeure (≥ 10 points) dans les 6 h. `None` si le
    classifieur n'a pas pu être entraîné (aucune chute dans l'historique)."""
    if artifacts.get("classifier") is None:
        return None
    features = build_forecast_features(scores)
    row = features[artifacts["feature_columns"]].fillna(artifacts["medians"]).iloc[[-1]]
    return float(artifacts["classifier"].predict_proba(row)[0, 1])


def forecast_recursive(scores: pd.DataFrame, artifacts: dict, hours: int) -> pd.DataFrame:
    """Trajectoire de santé prévue sur `hours`, par pas de 6 h (horizon du modèle).

    Déroulé récursif : la prédiction devient l'observation du pas suivant. Ce qui
    est **maintenu en l'état** (hypothèse « conditions inchangées ») : sous-scores,
    charges d'anomalie, durées de coupure/alarme, température, humidité. Ce qui
    **évolue** : le calendrier et le risque de maintenance préventive, qui ne
    dépendent que du temps — c'est ce qui fait apparaître la dérive lente due au
    vieillissement du parc.

    Renvoie `timestamp, value, lower, upper` ; la bande s'élargit en `√pas` à
    partir de l'écart-type des résidus de test.
    """
    step = cfg.FORECAST_HORIZON_HOURS
    n_steps = max(1, int(np.ceil(hours / step)))
    # Assez d'historique pour le retard le plus long (168 h) + les fenêtres.
    history = scores.tail(max(cfg.HEALTH_LAGS) + max(cfg.ROLLING_WINDOWS) + 24).copy()
    residual_std = artifacts.get("residual_std") or 1.0

    rows = []
    for i in range(1, n_steps + 1):
        features = build_forecast_features(history)
        row = features[artifacts["feature_columns"]].fillna(artifacts["medians"]).iloc[[-1]]
        value = float(np.clip(artifacts["regressor"].predict(row)[0], 0, 100))

        timestamp = history.index[-1] + pd.Timedelta(hours=step)
        band = residual_std * np.sqrt(i)
        rows.append({
            "timestamp": timestamp,
            "value": round(value, 2),
            "lower": round(max(0.0, value - band), 2),
            "upper": round(min(100.0, value + band), 2),
        })

        # Nouvelle ligne d'historique : conditions maintenues, temps avancé.
        new_row = history.iloc[-1].copy()
        new_row["overall_site_health"] = value
        new_row["overall_site_risk"] = 100 - value
        new_row["environmental_pm_risk"] = float(pm_risk_from_last_pm(
            pd.DatetimeIndex([timestamp]), cfg.ENV_LAST_PM_DATE, cfg.ENV_MAINTENANCE_INTERVAL_DAYS
        ).iloc[0])
        new_row["energy_pm_risk"] = float(pm_risk_from_last_pm(
            pd.DatetimeIndex([timestamp]), cfg.ENERGY_LAST_PM_DATE, cfg.ENERGY_MAINTENANCE_INTERVAL_DAYS
        ).iloc[0])
        history = pd.concat([history, pd.DataFrame([new_row], index=[timestamp])])
        history.index.name = "timestamp"

    return pd.DataFrame(rows)
