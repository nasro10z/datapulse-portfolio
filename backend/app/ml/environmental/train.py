"""
Script d'entraînement du modèle HMM environnemental (température/humidité).
Reproduit fidèlement le pipeline du notebook environmental_fixed.ipynb :
split chronologique, seuils Tukey sur train uniquement, détection d'épisodes
par hystérésis, sélection du nombre d'états HMM sur validation, ré-entraînement
final sur train+validation, évaluation sur test intact.

Usage :
    python -m environmental.train
"""
import json
import warnings
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from sklearn.metrics import classification_report
from sklearn.preprocessing import StandardScaler

from app.ml.environmental.config import (
    MODEL_DIR,
    MODEL_PATH, SCALER_PATH, ANOMALOUS_STATES_PATH, THRESHOLDS_PATH, METADATA_PATH,
    TEMP_COL, HUMIDITY_COL, FEATURE_COLS,
    TEMP_HYSTERESIS_MARGIN, HUMIDITY_HYSTERESIS_MARGIN,
    N_STATES_CANDIDATES, PROP_CUTOFF_CANDIDATES, HMM_SEEDS, HMM_N_ITER, MIN_STATE_SIZE,
)
from app.ml.environmental.preprocessing import (
    load_data_from_db, dedupe_and_index, add_segments,
    tukey_thresholds, compute_rolling_features, prepare_hmm_sequences,
)


def detect_hysteresis(values, enter_threshold, exit_threshold, direction="high", min_exit_points=5):
    episode_ids = pd.Series(0, index=values.index, dtype=int)
    active, exit_count, episode_id = False, 0, 0
    for idx, value in values.items():
        if pd.isna(value):
            active, exit_count = False, 0
            continue
        enter_condition = value >= enter_threshold if direction == "high" else value <= enter_threshold
        exit_condition = value <= exit_threshold if direction == "high" else value >= exit_threshold
        if not active and enter_condition:
            episode_id += 1
            active, exit_count = True, 0
        if active:
            episode_ids.loc[idx] = episode_id
            if exit_condition:
                exit_count += 1
                if exit_count >= min_exit_points:
                    active, exit_count = False, 0
            else:
                exit_count = 0
    return episode_ids


def detect_segmented_episodes(data, value_col, enter_threshold, exit_threshold,
                               direction="high", min_exit_points=5):
    result = pd.Series(0, index=data.index, dtype=int)
    global_episode = 0
    for _, segment in data.groupby("segment_id", sort=True):
        local = detect_hysteresis(segment[value_col], enter_threshold, exit_threshold,
                                   direction=direction, min_exit_points=min_exit_points)
        for local_id in sorted(local[local > 0].unique()):
            global_episode += 1
            result.loc[local.index[local == local_id]] = global_episode
    return result


def fit_best_hmm(X, lengths, n_components, seeds=HMM_SEEDS, n_iter=HMM_N_ITER):
    best_model, best_score = None, -np.inf
    for seed in seeds:
        model = GaussianHMM(n_components=n_components, covariance_type="diag",
                             n_iter=n_iter, tol=1e-4, random_state=seed)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model.fit(X, lengths=lengths)
            score = model.score(X, lengths=lengths)
            if model.monitor_.converged and score > best_score:
                best_model, best_score = model, score
        except Exception:
            continue
    if best_model is None:
        raise RuntimeError(f"Aucun HMM convergé pour K={n_components}.")
    return best_model


def build_state_stats(index, states, source_df, temp_thresholds, humidity_thresholds):
    interp = source_df.loc[index, [TEMP_COL, HUMIDITY_COL]].copy()
    interp["state"] = states
    stats = interp.groupby("state").apply(
        lambda g: pd.Series({
            "n_points": len(g),
            "prop_temp_high": (g[TEMP_COL] >= temp_thresholds["mild_upper"]).mean(),
            "prop_temp_low": (g[TEMP_COL] <= temp_thresholds["mild_lower"]).mean(),
            "prop_humidity_high": (g[HUMIDITY_COL] >= humidity_thresholds["mild_upper"]).mean(),
            "prop_humidity_low": (g[HUMIDITY_COL] <= humidity_thresholds["mild_lower"]).mean(),
        }),
        include_groups=False,
    )
    return stats


def train():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("1/6 - Chargement depuis SQLite et prétraitement...")
    df = load_data_from_db()  # <--- Utilisation de la base SQLite
    df = dedupe_and_index(df)
    df = add_segments(df)

    print("2/6 - Split chronologique et seuils (train uniquement)...")
    unique_days = pd.Series(df.index.normalize().unique()).sort_values().reset_index(drop=True)
    if len(unique_days) < 10:
        raise ValueError("Pas assez de jours pour créer train/validation/test.")
    train_end_day = unique_days.iloc[int(len(unique_days) * 0.70) - 1]
    validation_end_day = unique_days.iloc[int(len(unique_days) * 0.85) - 1]
    train_mask = df.index.normalize() <= train_end_day
    validation_mask = (df.index.normalize() > train_end_day) & (df.index.normalize() <= validation_end_day)
    test_mask = df.index.normalize() > validation_end_day

    temp_thresholds = tukey_thresholds(df.loc[train_mask, TEMP_COL])
    humidity_thresholds = tukey_thresholds(df.loc[train_mask, HUMIDITY_COL])

    print("3/6 - Détection des épisodes de référence (hystérésis) et features...")
    df["episode_id_temp_high"] = detect_segmented_episodes(
        df, TEMP_COL, temp_thresholds["mild_upper"],
        temp_thresholds["mild_upper"] - TEMP_HYSTERESIS_MARGIN, "high")
    df["episode_id_temp_low"] = detect_segmented_episodes(
        df, TEMP_COL, temp_thresholds["mild_lower"],
        temp_thresholds["mild_lower"] + TEMP_HYSTERESIS_MARGIN, "low")
    df["episode_id_humidity_high"] = detect_segmented_episodes(
        df, HUMIDITY_COL, humidity_thresholds["mild_upper"],
        humidity_thresholds["mild_upper"] - HUMIDITY_HYSTERESIS_MARGIN, "high")
    df["episode_id_humidity_low"] = detect_segmented_episodes(
        df, HUMIDITY_COL, humidity_thresholds["mild_lower"],
        humidity_thresholds["mild_lower"] + HUMIDITY_HYSTERESIS_MARGIN, "low")
    for suffix in ["temp_high", "temp_low", "humidity_high", "humidity_low"]:
        df[f"target_{suffix}"] = (df[f"episode_id_{suffix}"] > 0).astype(int)
    df["target_any_environmental"] = df[
        ["target_temp_high", "target_temp_low", "target_humidity_high", "target_humidity_low"]
    ].max(axis=1)

    df = compute_rolling_features(df)

    X_full = df[FEATURE_COLS].replace([np.inf, -np.inf], np.nan).dropna().sort_index()

    train_mask_hmm = pd.Series(train_mask, index=df.index).reindex(X_full.index, fill_value=False)
    validation_mask_hmm = pd.Series(validation_mask, index=df.index).reindex(X_full.index, fill_value=False)
    test_mask_hmm = pd.Series(test_mask, index=df.index).reindex(X_full.index, fill_value=False)

    X_train, lengths_train = prepare_hmm_sequences(X_full.loc[train_mask_hmm], df)
    X_validation, lengths_validation = prepare_hmm_sequences(X_full.loc[validation_mask_hmm], df)
    X_test, lengths_test = prepare_hmm_sequences(X_full.loc[test_mask_hmm], df)

    print("4/6 - Sélection du nombre d'états HMM sur validation...")
    scaler_search = StandardScaler()
    X_train_scaled = scaler_search.fit_transform(X_train)
    X_validation_scaled = scaler_search.transform(X_validation)

    validation_results = []
    for n_states in N_STATES_CANDIDATES:
        model_k = fit_best_hmm(X_train_scaled, lengths_train, n_components=n_states)
        train_states_k = model_k.predict(X_train_scaled, lengths=lengths_train)
        validation_states_k = model_k.predict(X_validation_scaled, lengths=lengths_validation)
        train_state_stats_k = build_state_stats(X_train.index, train_states_k, df,
                                                  temp_thresholds, humidity_thresholds)

        for prop_cutoff in PROP_CUTOFF_CANDIDATES:
            anomalous_states_k = train_state_stats_k.index[
                train_state_stats_k[
                    ["prop_temp_high", "prop_temp_low", "prop_humidity_high", "prop_humidity_low"]
                ].max(axis=1) >= prop_cutoff
            ].tolist()
            y_val = df.loc[X_validation.index, "target_any_environmental"].astype(int)
            pred_val = pd.Series(np.isin(validation_states_k, anomalous_states_k).astype(int),
                                  index=X_validation.index)
            report = classification_report(y_val, pred_val, output_dict=True, zero_division=0)
            anomaly_metrics = report.get("1", {"precision": 0, "recall": 0, "f1-score": 0})
            validation_results.append({
                "n_states": n_states, "prop_cutoff": prop_cutoff,
                "f1": anomaly_metrics["f1-score"],
                "converged": bool(model_k.monitor_.converged),
                "min_state_size": int(train_state_stats_k["n_points"].min()),
            })

    results_df = pd.DataFrame(validation_results).sort_values("f1", ascending=False)
    stable = results_df[(results_df["converged"]) & (results_df["min_state_size"] >= MIN_STATE_SIZE)]
    if stable.empty:
        raise RuntimeError("Aucune configuration HMM suffisamment stable.")
    best_config = stable.iloc[0]
    best_n_states = int(best_config["n_states"])
    best_prop_cutoff = float(best_config["prop_cutoff"])
    print(f"   -> Config choisie : n_states={best_n_states}, prop_cutoff={best_prop_cutoff}, f1={best_config['f1']:.3f}")

    print("5/6 - Ré-entraînement final sur train+validation...")
    X_trainval_raw = pd.concat([X_train, X_validation]).sort_index()
    X_trainval, lengths_trainval = prepare_hmm_sequences(X_trainval_raw, df)

    scaler_final = StandardScaler()
    X_trainval_scaled = scaler_final.fit_transform(X_trainval)
    X_test_scaled_final = scaler_final.transform(X_test)

    hmm_final = fit_best_hmm(X_trainval_scaled, lengths_trainval, n_components=best_n_states)
    trainval_states = hmm_final.predict(X_trainval_scaled, lengths=lengths_trainval)
    test_states_final = hmm_final.predict(X_test_scaled_final, lengths=lengths_test)

    trainval_state_stats = build_state_stats(X_trainval.index, trainval_states, df,
                                               temp_thresholds, humidity_thresholds)
    anomalous_states_final = trainval_state_stats.index[
        trainval_state_stats[
            ["prop_temp_high", "prop_temp_low", "prop_humidity_high", "prop_humidity_low"]
        ].max(axis=1) >= best_prop_cutoff
    ].tolist()

    y_test = df.loc[X_test.index, "target_any_environmental"].astype(int)
    pred_test = pd.Series(np.isin(test_states_final, anomalous_states_final).astype(int), index=X_test.index)
    test_report = classification_report(y_test, pred_test, output_dict=True, zero_division=0)
    test_metrics = test_report.get("1", {"precision": 0.0, "recall": 0.0, "f1-score": 0.0})
    test_f1 = test_metrics["f1-score"]
    print(f"   -> Precision sur test : {test_metrics['precision']:.3f}")
    print(f"   -> Recall sur test    : {test_metrics['recall']:.3f}")
    print(f"   -> F1 sur test (jamais vu) : {test_f1:.3f}")

    print("6/6 - Sauvegarde des artefacts...")
    joblib.dump(hmm_final, MODEL_PATH)
    joblib.dump(scaler_final, SCALER_PATH)
    with open(ANOMALOUS_STATES_PATH, "w") as f:
        json.dump({"anomalous_states": [int(s) for s in anomalous_states_final]}, f, indent=2)
    with open(THRESHOLDS_PATH, "w") as f:
        json.dump({
            "temperature": {k: float(v) for k, v in temp_thresholds.items()},
            "humidity": {k: float(v) for k, v in humidity_thresholds.items()},
        }, f, indent=2)
    metadata = {
        "model_name": "environmental",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_states": best_n_states,
        "prop_cutoff": best_prop_cutoff,
        "test_f1_anomaly": test_f1,
        "features": FEATURE_COLS,
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Modèle sauvegardé dans {MODEL_DIR}")


if __name__ == "__main__":
    train()