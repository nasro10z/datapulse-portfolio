"""Prévision du score de santé — portage du notebook `health_scores.ipynb`.

**Cible = la variation, pas le niveau.** `overall_site_health` se comporte comme
un processus AR(1) : son PACF est dominé par le retard 1, et la persistance (« la
santé dans 6 h = la santé maintenant ») est de ce fait une référence redoutable —
aucun modèle du notebook prédisant le **niveau** ne la battait. Prédire le
**delta** renverse le problème : la persistance devient simplement « delta = 0 »,
et le modèle n'a plus à réapprendre le niveau (ce que les arbres ne savent pas
extrapoler), seulement l'écart à la persistance.

    delta_prévu  = modèle(features)
    santé_prévue = clip(santé_courante + delta_prévu, 0, 100)

Modèle servi : **XGBoost top 20**. Il est entraîné sur le jeu de features
dynamiques étendu (~1 200 colonnes : retards, variations, vitesses, statistiques
et pentes glissantes, accélération, dégradation continue, interactions entre
sous-systèmes), puis **réentraîné sur les N features les plus importantes** avec
N choisi sur la validation. C'est la sélection qui fait le travail : moins de
features, moins de place pour surapprendre sur ~2 100 heures.

Résultats du notebook (test) : XGBoost top 20 MAE 5,03 · RMSE 9,39 · R² 0,394,
contre persistance MAE 6,00 · RMSE 10,03 · R² 0,308.

Second modèle, inchangé : un classifieur de **chute majeure** (≥ 10 points perdus
sur 6 h), seuil de décision choisi sur la validation.

Au-delà de +6 h (horizons 7 j / 30 j de l'interface), la trajectoire est produite
par **déroulé récursif** : chaque delta prédit devient l'observation suivante, les
conditions sont maintenues en l'état, et seuls le calendrier et le risque de
maintenance préventive évoluent. C'est une projection « à conditions inchangées »,
pas une certitude — et la bande de confiance s'élargit à chaque pas pour le dire.
"""
import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
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
from xgboost import XGBRegressor

from app.ml.health_score import config as cfg
from app.ml.health_score.features import pm_risk_from_last_pm
from app.ml.health_score.forecast_features import build_dynamic_features, sources_used_by

REGRESSOR_PATH = cfg.MODELS_DIR / "health_forecast_regressor.joblib"
CLASSIFIER_PATH = cfg.MODELS_DIR / "health_drop_classifier.joblib"
METADATA_PATH = cfg.MODELS_DIR / "metadata.json"


# ------------------------------------------------------------------- features
def build_forecast_features(scores: pd.DataFrame) -> pd.DataFrame:
    """Table horaire des scores → features de base + cibles.

    Cibles : `target_health_6h` (niveau futur) et `target_health_change_6h` (le
    **delta**, cible réellement apprise). Features de base : retards, statistiques
    glissantes, variations, calendrier (encodé en sinus/cosinus pour que 23 h et
    0 h soient voisines).
    """
    df = scores.copy()
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df.loc[df.index.notna()].sort_index()
    df = df[~df.index.duplicated(keep="last")]

    health = df["overall_site_health"]
    df["target_health_6h"] = health.shift(-cfg.FORECAST_HORIZON_HOURS)
    df["target_health_change_6h"] = df["target_health_6h"] - health

    for lag in cfg.HEALTH_LAGS:
        df[f"overall_health_lag_{lag}h"] = health.shift(lag)
    for window in cfg.ROLLING_WINDOWS_BASIC:
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
    df["month"] = df.index.month
    df["is_weekend"] = (df.index.dayofweek >= 5).astype(int)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["day_of_week_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["day_of_week_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

    df["health_change_6h"] = df["target_health_change_6h"]
    df["major_drop_6h"] = np.where(
        df["health_change_6h"].notna(),
        (df["health_change_6h"] <= cfg.MAJOR_DROP_THRESHOLD).astype(int), np.nan,
    )
    df["severe_drop_6h"] = np.where(
        df["health_change_6h"].notna(),
        (df["health_change_6h"] <= cfg.SEVERE_DROP_THRESHOLD).astype(int), np.nan,
    )
    return df


def build_model_frame(scores: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Features de base **+ features dynamiques étendues**, et la liste des
    colonnes exploitables comme features (cibles et étiquettes exclues)."""
    basic = build_forecast_features(scores)
    dynamic = build_dynamic_features(basic)
    frame = pd.concat([basic, dynamic], axis=1)
    frame = frame.loc[:, ~frame.columns.duplicated(keep="last")]

    candidates = list(dict.fromkeys(
        [c for c in cfg.CURRENT_NUMERIC_FEATURES if c in frame.columns]
        + [c for c in basic.columns if "_lag_" in c or "_change_" in c
           or any(p in c for p in ("_mean_", "_std_", "_min_"))]
        + list(dynamic.columns)
        + [c for c in cfg.CALENDAR_FEATURE_COLUMNS if c in frame.columns]
        + ["month"]
    ))
    feature_columns = [
        c for c in candidates
        if c not in cfg.TARGET_AND_LABEL_COLUMNS
        and pd.api.types.is_numeric_dtype(frame[c])
        and not frame[c].isna().all()
    ]
    return frame, feature_columns


def split_chronological(data: pd.DataFrame, train=0.70, validation=0.85):
    """Découpage temporel 70 / 15 / 15 — l'ordre du temps est préservé."""
    n = len(data)
    train_end, validation_end = int(n * train), int(n * validation)
    return (data.iloc[:train_end].copy(),
            data.iloc[train_end:validation_end].copy(),
            data.iloc[validation_end:].copy())


# ----------------------------------------------------------------- évaluation
def reconstruct_health(current_health, predicted_delta) -> np.ndarray:
    return np.clip(np.asarray(current_health, dtype=float)
                   + np.asarray(predicted_delta, dtype=float), 0, 100)


def evaluate_delta_forecast(current_health, actual_future_health, predicted_delta, name: str) -> dict:
    """Évalue un modèle de delta sur la **santé reconstruite** — l'échelle que
    l'utilisateur voit — et sur le delta lui-même.

    Les métriques conditionnelles (heures de chute majeure / sévère) sont là parce
    qu'une MAE globale basse ne dit rien de la capacité à voir venir les mauvaises
    heures, qui sont les seules qui comptent en exploitation.
    """
    current = np.asarray(current_health, dtype=float)
    actual = np.asarray(actual_future_health, dtype=float)
    predicted = reconstruct_health(current, predicted_delta)
    actual_delta = actual - current

    major = actual_delta <= cfg.MAJOR_DROP_THRESHOLD
    severe = actual_delta <= cfg.SEVERE_DROP_THRESHOLD
    risk_actual = actual < cfg.DEGRADATION_THRESHOLD
    risk_predicted = predicted < cfg.DEGRADATION_THRESHOLD
    tp = int(np.sum(risk_actual & risk_predicted))
    fp = int(np.sum(~risk_actual & risk_predicted))
    fn = int(np.sum(risk_actual & ~risk_predicted))

    return {
        "model": name,
        "MAE": float(mean_absolute_error(actual, predicted)),
        "RMSE": float(np.sqrt(mean_squared_error(actual, predicted))),
        "R2": float(r2_score(actual, predicted)),
        "delta_MAE": float(mean_absolute_error(actual_delta, np.asarray(predicted_delta, dtype=float))),
        "major_drop_MAE": float(mean_absolute_error(actual[major], predicted[major])) if major.any() else None,
        "severe_drop_MAE": float(mean_absolute_error(actual[severe], predicted[severe])) if severe.any() else None,
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


def drop_sample_weights(delta: np.ndarray) -> np.ndarray:
    """Poids d'échantillon croissants sur les heures de dégradation.

    Manquer une chute coûte plus cher qu'une fausse alerte : ces poids le disent au
    modèle. Variante conservée pour comparaison — elle gagne sur les heures de
    chute et perd sur la MAE globale.
    """
    weights = np.ones(len(delta), dtype=float)
    for threshold, weight in sorted(cfg.DROP_SAMPLE_WEIGHTS.items(), reverse=True):
        weights[delta <= threshold] = weight
    return weights


# ---------------------------------------------------------------- entraînement
def train(scores: pd.DataFrame) -> dict:
    """Entraîne le modèle de delta et le classifieur de chute.

    Déroulé : features étendues → split chronologique → XGBoost « large » pour
    **classer** les features → réentraînement sur les top-N → N retenu sur la
    **validation** → métriques finales sur le test, intactes jusque-là.

    Les valeurs manquantes sont comblées par les **médianes d'entraînement**, jamais
    recalculées sur validation/test (ce serait une fuite du futur vers le passé) ;
    les mêmes médianes servent à la prédiction.
    """
    frame, feature_columns = build_model_frame(scores)
    target = "target_health_change_6h"

    # `dict.fromkeys` : `overall_site_health` est à la fois une feature et la
    # référence de reconstruction du delta — le sélectionner deux fois créerait une
    # colonne dupliquée, et toute lecture par nom renverrait un DataFrame.
    model_columns = list(dict.fromkeys(
        feature_columns + ["overall_site_health", "target_health_6h", target]
    ))
    model_data = frame[model_columns]
    model_data = model_data.dropna(subset=cfg.REQUIRED_FORECAST_FEATURES + [target])
    if len(model_data) < 200:
        raise ValueError(
            f"Historique insuffisant pour entraîner la prévision : {len(model_data)} lignes "
            "exploitables (200 minimum)."
        )

    train_data, validation_data, test_data = split_chronological(model_data)
    medians = train_data[feature_columns].replace([np.inf, -np.inf], np.nan).median()
    feature_columns = [c for c in feature_columns if pd.notna(medians[c])]
    medians = medians[feature_columns]

    def _x(frame_: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
        columns = columns or feature_columns
        return (frame_[columns].replace([np.inf, -np.inf], np.nan)
                .fillna(medians[columns]))

    y_train, y_validation = train_data[target], validation_data[target]

    # 1. Modèle « large » : sert uniquement à classer les features par importance.
    ranking_model = XGBRegressor(**cfg.XGB_RANKING_PARAMS)
    ranking_model.fit(_x(train_data), y_train,
                      eval_set=[(_x(validation_data), y_validation)], verbose=False)
    importance = pd.Series(ranking_model.feature_importances_, index=feature_columns)
    ranked = importance.sort_values(ascending=False).index.tolist()

    # 2. Un candidat par taille de jeu de features, comparés sur la validation.
    candidates: dict[int, dict] = {}
    for count in cfg.XGB_FEATURE_COUNTS:
        count = min(count, len(ranked))
        selected = ranked[:count]
        model = XGBRegressor(**cfg.XGB_SELECTION_PARAMS)
        model.fit(_x(train_data, selected), y_train,
                  eval_set=[(_x(validation_data, selected), y_validation)], verbose=False)
        metrics = evaluate_delta_forecast(
            validation_data["overall_site_health"], validation_data["target_health_6h"],
            model.predict(_x(validation_data, selected)), f"XGBoost top {count}",
        )
        candidates[count] = {"model": model, "features": selected, "validation": metrics}

    best_count = min(candidates, key=lambda c: candidates[c]["validation"]["MAE"])
    best = candidates[best_count]
    selected_features = best["features"]

    # 3. Métriques de test — le test n'a servi à aucun choix jusqu'ici.
    test_current, test_actual = test_data["overall_site_health"], test_data["target_health_6h"]
    metrics = {
        "persistence": evaluate_delta_forecast(
            test_current, test_actual, np.zeros(len(test_data)), "Persistance (delta = 0)"
        ),
        "selected": evaluate_delta_forecast(
            test_current, test_actual, best["model"].predict(_x(test_data, selected_features)),
            f"XGBoost top {best_count}",
        ),
        "validation_by_feature_count": {
            str(count): candidate["validation"]["MAE"] for count, candidate in candidates.items()
        },
    }

    # 4. Variante pondérée sur les heures de dégradation — comparaison seulement.
    weighted = XGBRegressor(**cfg.XGB_WEIGHTED_PARAMS)
    weighted.fit(_x(train_data, selected_features), y_train,
                 sample_weight=drop_sample_weights(np.asarray(y_train, dtype=float)),
                 eval_set=[(_x(validation_data, selected_features), y_validation)], verbose=False)
    metrics["weighted_variant"] = evaluate_delta_forecast(
        test_current, test_actual, weighted.predict(_x(test_data, selected_features)),
        "XGBoost pondéré (chutes)",
    )
    metrics["mae_improvement_vs_persistence"] = (
        metrics["persistence"]["MAE"] - metrics["selected"]["MAE"]
    )

    # Écart-type des résidus de test : échelle de la bande de confiance servie à
    # l'interface (pas une valeur choisie à la main).
    predicted_health = reconstruct_health(
        test_current, best["model"].predict(_x(test_data, selected_features))
    )
    residual_std = float(np.std(np.asarray(test_actual, dtype=float) - predicted_health))

    classifier, threshold, classifier_metrics = _train_drop_classifier(
        frame, selected_features, medians[selected_features]
    )

    return {
        "regressor": best["model"],
        "selected_model": f"xgboost_top_{best_count}",
        "feature_count": best_count,
        "classifier": classifier,
        "feature_columns": selected_features,
        "medians": medians[selected_features],
        "dynamic_sources": sources_used_by(selected_features),
        "drop_threshold": threshold,
        "residual_std": residual_std,
        "metrics": {**metrics, "drop_classifier": classifier_metrics},
        "n_rows": {"train": len(train_data), "validation": len(validation_data), "test": len(test_data)},
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "score_version": cfg.SCORE_VERSION,
        "weight_version": cfg.WEIGHT_VERSION,
    }


def _train_drop_classifier(frame: pd.DataFrame, feature_columns: list[str], medians: pd.Series):
    """Classifieur de chute majeure + seuil de décision choisi sur la validation.

    Renvoie `(None, None, {...})` si l'historique ne contient pas les deux classes
    — sans exemple de chute, aucun seuil n'est apprenable et prétendre le contraire
    serait pire que de s'en passer.
    """
    # Les colonnes de `REQUIRED_FORECAST_FEATURES` servent au filtrage des lignes
    # sans historique ; elles ne font pas forcément partie des features retenues,
    # d'où leur inclusion explicite avant le `dropna`.
    columns = list(dict.fromkeys(
        feature_columns + cfg.REQUIRED_FORECAST_FEATURES + ["major_drop_6h"]
    ))
    data = frame[columns].dropna(
        subset=cfg.REQUIRED_FORECAST_FEATURES + ["major_drop_6h"]
    ).copy()
    data["major_drop_6h"] = data["major_drop_6h"].astype(int)
    train_data, validation_data, test_data = split_chronological(data)

    if train_data["major_drop_6h"].nunique() < 2:
        return None, None, {"status": "non entraîné — une seule classe dans l'historique"}

    def _x(frame_):
        return frame_[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(medians)

    classifier = RandomForestClassifier(
        n_estimators=500, max_depth=8, min_samples_leaf=5, max_features="sqrt",
        class_weight="balanced_subsample", random_state=42, n_jobs=-1,
    )
    classifier.fit(_x(train_data), train_data["major_drop_6h"])

    validation_probabilities = classifier.predict_proba(_x(validation_data))[:, 1]
    candidates = [
        evaluate_classifier(validation_data["major_drop_6h"], validation_probabilities, t, "RandomForest")
        for t in np.arange(0.10, 0.91, 0.05)
    ]
    best = max(candidates, key=lambda r: (r["f1"], r["recall"]))
    threshold = best["threshold"]

    test_probabilities = classifier.predict_proba(_x(test_data))[:, 1]
    metrics = evaluate_classifier(
        test_data["major_drop_6h"], test_probabilities, threshold, "RandomForest (test)"
    )
    metrics["selected_on_validation_f1"] = best["f1"]
    return classifier, threshold, metrics


# --------------------------------------------------------------- persistance
_BUNDLE_KEYS = ("regressor", "selected_model", "feature_count", "feature_columns",
                "medians", "dynamic_sources", "residual_std", "drop_threshold")


def save_artifacts(artifacts: dict) -> dict:
    """Écrit les modèles + les métadonnées sous `ml/models/health_forecast/`."""
    cfg.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({k: artifacts[k] for k in _BUNDLE_KEYS}, REGRESSOR_PATH)
    if artifacts.get("classifier") is not None:
        joblib.dump(artifacts["classifier"], CLASSIFIER_PATH)

    metadata = {
        "score_version": artifacts["score_version"],
        "weight_version": artifacts["weight_version"],
        "trained_at": artifacts["trained_at"],
        "selected_model": artifacts["selected_model"],
        "target": "target_health_change_6h (delta)",
        "horizon_hours": cfg.FORECAST_HORIZON_HOURS,
        "n_features": len(artifacts["feature_columns"]),
        "features": artifacts["feature_columns"],
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
            f"Modèle de prévision absent ({REGRESSOR_PATH}). "
            "Lancer `python -m app.etl.forecast --train`."
        )
    bundle = joblib.load(REGRESSOR_PATH)
    bundle["classifier"] = joblib.load(CLASSIFIER_PATH) if CLASSIFIER_PATH.exists() else None
    return bundle


# ----------------------------------------------------------------- prédiction
def _feature_row(window: pd.DataFrame, artifacts: dict) -> pd.DataFrame:
    """Dernière ligne de `window`, réduite aux features du modèle.

    Seules les variables sources dont dépend le modèle retenu sont dérivées : sur
    ~1 200 features candidates, 20 servent — recalculer les autres à chaque pas du
    déroulé serait du travail jeté.
    """
    basic = build_forecast_features(window)
    dynamic = build_dynamic_features(basic, sources=artifacts["dynamic_sources"])
    frame = pd.concat([basic, dynamic], axis=1)
    frame = frame.loc[:, ~frame.columns.duplicated(keep="last")]

    columns = artifacts["feature_columns"]
    missing = [c for c in columns if c not in frame.columns]
    for column in missing:
        frame[column] = np.nan
    return (frame[columns].replace([np.inf, -np.inf], np.nan)
            .fillna(artifacts["medians"]).iloc[[-1]])


def predict_delta(window: pd.DataFrame, artifacts: dict) -> float:
    """Variation de santé prévue à +6 h à partir de la dernière heure de `window`."""
    return float(artifacts["regressor"].predict(_feature_row(window, artifacts))[0])


def predict_next(scores: pd.DataFrame, artifacts: dict) -> float:
    """Santé globale prévue à +6 h (delta reconstruit sur le niveau courant)."""
    delta = predict_delta(scores, artifacts)
    return float(reconstruct_health([scores["overall_site_health"].iloc[-1]], [delta])[0])


def predict_drop_probability(scores: pd.DataFrame, artifacts: dict) -> float | None:
    """Probabilité d'une chute majeure (≥ 10 points) dans les 6 h. `None` si le
    classifieur n'a pas pu être entraîné (aucune chute dans l'historique)."""
    if artifacts.get("classifier") is None:
        return None
    return float(artifacts["classifier"].predict_proba(_feature_row(scores, artifacts))[0, 1])


def _advance_row(previous: pd.Series, timestamp: pd.Timestamp, health: float) -> pd.Series:
    """Ligne d'historique suivante : santé mise à jour, conditions maintenues, temps
    avancé. Les risques de PM ne dépendent que du temps — ils continuent donc de
    monter, ce qui fait apparaître la dérive lente due au vieillissement du parc."""
    row = previous.copy()
    row["overall_site_health"] = health
    row["overall_site_risk"] = 100 - health
    row["environmental_pm_risk"] = float(pm_risk_from_last_pm(
        pd.DatetimeIndex([timestamp]), cfg.ENV_LAST_PM_DATE, cfg.ENV_MAINTENANCE_INTERVAL_DAYS
    ).iloc[0])
    row["energy_pm_risk"] = float(pm_risk_from_last_pm(
        pd.DatetimeIndex([timestamp]), cfg.ENERGY_LAST_PM_DATE, cfg.ENERGY_MAINTENANCE_INTERVAL_DAYS
    ).iloc[0])
    return row


def forecast_recursive(scores: pd.DataFrame, artifacts: dict, hours: int) -> pd.DataFrame:
    """Trajectoire de santé prévue sur `hours`, par pas de 6 h (horizon du modèle).

    Déroulé récursif : le delta prédit est appliqué, la santé obtenue devient
    l'observation du pas suivant. Ce qui est **maintenu en l'état** (hypothèse
    « conditions inchangées ») : sous-scores, charges d'anomalie, durées de
    coupure/alarme, température, humidité. Ce qui **évolue** : la santé globale, sa
    tendance et sa volatilité (recalculées), le calendrier, et le risque de
    maintenance préventive.

    Le premier pas est la prédiction validée du modèle ; les suivants sont
    **amortis** géométriquement (`config.RECURSIVE_DELTA_DAMPING`), le modèle
    n'étant validé qu'à +6 h. Sans cet amortissement la trajectoire se compose et
    s'emballe jusqu'à saturer à 100/100 sur 7 jours.

    Renvoie `timestamp, value, lower, upper` ; la bande s'élargit en `√pas` à
    partir de l'écart-type des résidus de test.
    """
    step = cfg.FORECAST_HORIZON_HOURS
    n_steps = max(1, int(np.ceil(hours / step)))
    # Assez d'historique pour le retard le plus long et les fenêtres glissantes.
    lookback = max(cfg.HEALTH_LAGS) + max(cfg.ROLLING_WINDOWS_BASIC) + 24
    history = scores.tail(lookback).copy()
    residual_std = artifacts.get("residual_std") or 1.0

    rows = []
    for i in range(1, n_steps + 1):
        delta = predict_delta(history, artifacts) * cfg.RECURSIVE_DELTA_DAMPING ** (i - 1)
        current = float(history["overall_site_health"].iloc[-1])
        value = float(reconstruct_health([current], [delta])[0])

        timestamp = history.index[-1] + pd.Timedelta(hours=step)
        band = residual_std * np.sqrt(i)
        rows.append({
            "timestamp": timestamp,
            "value": round(value, 2),
            "lower": round(max(0.0, value - band), 2),
            "upper": round(min(100.0, value + band), 2),
        })

        history = pd.concat([history, pd.DataFrame([_advance_row(history.iloc[-1], timestamp, value)],
                                                   index=[timestamp])])
        history.index.name = "timestamp"
        # Tendance et volatilité sont des features : les laisser figées ferait
        # croire au modèle que la santé n'a pas bougé alors qu'on vient de la
        # faire bouger.
        health = history["overall_site_health"]
        history["overall_site_health_trend_24h"] = health.diff(cfg.TREND_LONG_HOURS)
        history["overall_site_health_volatility_24h"] = (
            health.rolling(cfg.VOLATILITY_WINDOW_HOURS, min_periods=6).std()
        )

    return pd.DataFrame(rows)
