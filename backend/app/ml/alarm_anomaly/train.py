"""
Script d'entraînement du modèle de détection d'anomalies.

Usage :
    python -m alarm_anomaly.train

Ce script :
1. charge et fusionne les données brutes
2. construit les events puis les event_features
3. entraîne un StandardScaler + IsolationForest
4. sauvegarde model.joblib, scaler.joblib et metadata.json

Il ne fait PAS partie de l'API : on l'exécute une fois (ou périodiquement
pour ré-entraîner), jamais à chaque requête.
"""
import json
from datetime import datetime, timezone

import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.ml.alarm_anomaly.config import (
    DATA_RAW_DIR,
    LOGS_CSV_FILENAME,
    ALARMS_EXCEL_FILENAME,
    UPS_CSV_FILENAME,
    MODEL_NAME,
    MODEL_PATH,
    SCALER_PATH,
    METADATA_PATH,
    MODEL_DIR,
    MODEL_FEATURES,
    ISOLATION_FOREST_PARAMS,
)
from app.ml.alarm_anomaly.data_loading import load_full_dataset
from app.ml.alarm_anomaly.event_detection import build_events
from app.ml.alarm_anomaly.feature_engineering import build_event_features


def train():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("1/4 - Chargement des données...")
    df_combined = load_full_dataset(
        csv_path=DATA_RAW_DIR / LOGS_CSV_FILENAME,
        excel_path=DATA_RAW_DIR / ALARMS_EXCEL_FILENAME,
        ups_csv_path=DATA_RAW_DIR / UPS_CSV_FILENAME,
    )

    print("2/4 - Construction des events et des features...")
    df_events = build_events(df_combined)
    event_features = build_event_features(df_events)

    X = event_features[MODEL_FEATURES].fillna(0)

    print("3/4 - Entraînement du scaler et du modèle...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(**ISOLATION_FOREST_PARAMS)
    model.fit(X_scaled)

    print("4/4 - Sauvegarde des artefacts...")
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    metadata = {
        "model_name": MODEL_NAME,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_events_trained_on": len(event_features),
        "features": MODEL_FEATURES,
        "model_type": "IsolationForest",
        "model_params": ISOLATION_FOREST_PARAMS,
        
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Modèle sauvegardé : {MODEL_PATH}")
    print(f"Scaler sauvegardé : {SCALER_PATH}")
    print(f"Métadonnées : {METADATA_PATH}")
    print(f"Entraîné sur {len(event_features)} événements.")


if __name__ == "__main__":
    train()
