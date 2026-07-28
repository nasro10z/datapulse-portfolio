"""
Registre CENTRAL de tous les modèles du projet -- 100% agnostique de l'API.

Ce fichier ne connaît NI FastAPI NI Pydantic : il doit pouvoir être importé
et utilisé depuis un script, un notebook, un test, sans jamais dépendre de
la couche web (api/). C'est api/api_registry.py qui fait le lien entre un
nom de modèle et son schéma Pydantic -- pas ici.

Chaque entrée du registre doit fournir :
- "predictor_builder"      : fonction sans argument -> objet avec .predict_one(dict) -> dict
- "load_historical_events" : fonction sans argument -> pandas.DataFrame trié par date
- "features"               : liste ordonnée des noms de colonnes attendues par le modèle
- "date_column"            : nom de la colonne date (pour le tri/affichage en simulation)
- "api_path"                : chemin de l'endpoint FastAPI, ex "/predict/alarm-anomaly"
- "metadata_path"           : chemin vers metadata.json du modèle (traçabilité/version)
"""

# --- Modèle 1 : alarm_anomaly (existant) ---------------------------------
from app.ml.alarm_anomaly.predict import AnomalyPredictor
from app.ml.alarm_anomaly.config import (
    DATA_RAW_DIR as ALARM_DATA_RAW_DIR,
    MODEL_FEATURES as ALARM_FEATURES,
    METADATA_PATH as ALARM_METADATA_PATH,
    LOGS_CSV_FILENAME,
    ALARMS_EXCEL_FILENAME,
    UPS_CSV_FILENAME,
)
from app.ml.alarm_anomaly.data_loading import load_full_dataset
from app.ml.alarm_anomaly.event_detection import build_events
from app.ml.alarm_anomaly.feature_engineering import build_event_features


def _load_alarm_anomaly_historical_events():
    df_combined = load_full_dataset(
        csv_path=ALARM_DATA_RAW_DIR / LOGS_CSV_FILENAME,
        excel_path=ALARM_DATA_RAW_DIR / ALARMS_EXCEL_FILENAME,
        ups_csv_path=ALARM_DATA_RAW_DIR / UPS_CSV_FILENAME,
    )
    df_events = build_events(df_combined)
    event_features = build_event_features(df_events).reset_index()
    return event_features.sort_values("start_time")


# --- Modèle 2 : environmental (HMM température/humidité) ------------------
from app.ml.environmental.predict import EnvironmentalPredictor
from app.ml.environmental.config import (
    DATA_RAW_DIR as ENV_DATA_RAW_DIR,
    DATA_CSV_FILENAME as ENV_CSV_FILENAME,
    METADATA_PATH as ENV_METADATA_PATH,
)
from app.ml.environmental.preprocessing import load_raw_readings, dedupe_and_index


def _load_environmental_historical_events():
    df = load_raw_readings(ENV_DATA_RAW_DIR / ENV_CSV_FILENAME)
    df = dedupe_and_index(df)
    return df.reset_index().sort_values("ts")


# --- Modèle 3 : à compléter quand le code sera prêt -----------------------
# from model_3.predict import Model3Predictor
# from model_3.config import MODEL_FEATURES as MODEL_3_FEATURES, METADATA_PATH as MODEL_3_METADATA_PATH
#
# def _load_model_3_historical_events():
#     ...
#     return df_sorted_by_date


MODEL_REGISTRY = {
    "alarm_anomaly": {
        "predictor_builder": lambda: AnomalyPredictor(),
        "load_historical_events": _load_alarm_anomaly_historical_events,
        "features": ALARM_FEATURES + ["dominant_category"],
        "date_column": "start_time",
        "api_path": "/predict/alarm-anomaly",
        "metadata_path": ALARM_METADATA_PATH,
    },
    "environmental": {
        "predictor_builder": lambda: EnvironmentalPredictor(),
        "load_historical_events": _load_environmental_historical_events,
        "features": ["ts", "temperature", "humidity"],
        "date_column": "ts",
        "api_path": "/predict/environmental",
        "metadata_path": ENV_METADATA_PATH,
    },
    # "model_3": {
    #     "predictor_builder": lambda: Model3Predictor(),
    #     "load_historical_events": _load_model_3_historical_events,
    #     "features": MODEL_3_FEATURES,
    #     "date_column": "...",
    #     "api_path": "/predict/model-3",
    #     "metadata_path": MODEL_3_METADATA_PATH,
    # },
}