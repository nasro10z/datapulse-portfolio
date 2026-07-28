"""
Configuration centralisée du projet.
Toute valeur "réglable" (chemin, seuil, hyperparamètre) vit ici,
jamais en dur dans le code métier.
"""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]  # app/ml (racine du package ML vendorisé)
# --- Chemins -----------------------------------------------------------
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
MODELS_DIR = ROOT_DIR / "models"

# Nom de ce modèle -> utilisé comme nom de sous-dossier dans models/
# et comme clé dans le registre de l'API (voir api/model_loader.py).
# Un futur 2e modèle aura son propre MODEL_NAME et son propre sous-dossier.
MODEL_NAME = "alarm_anomaly"
MODEL_DIR = MODELS_DIR / MODEL_NAME

MODEL_PATH = MODEL_DIR / "isolation_forest.joblib"
SCALER_PATH = MODEL_DIR / "scaler.joblib"
METADATA_PATH = MODEL_DIR / "metadata.json"

# --- Noms des fichiers sources (centralisés, plus en dur ailleurs) ------
LOGS_CSV_FILENAME = "logs_msc10.csv"
ALARMS_EXCEL_FILENAME = "ALARMES SCADA 2022.xlsx"
UPS_CSV_FILENAME = "ups_clean.csv"

# --- Paramètres de découpage en "events" --------------------------------
EVENT_GAP_THRESHOLD_SECONDS = 120  # écart max entre 2 alarmes du même event

# --- Mots-clés de catégorisation -----------------------------------------
UPS_KEYWORDS = ["UPS", "SOCOMEC", "BATTERY", "RECTIFIER", "BYPASS", "INVERTER"]
GENERATOR_KEYWORDS = ["GROUPE", "DEMARRAGE", "ABSENCE TENSION"]
TEMPERATURE_KEYWORDS = ["TEMPERATURE"]

CATEGORY_KEYWORDS = {
    "UPS": ["UPS", "SOCOMEC", "BATTERY"],
    "CLIM": ["CLIM", "STULZ", "LIEBERT", "TEMPERATURE"],
    "ENERGY": ["TENSION", "GROUPE ELECTROGENE", "ELECTROGENE"],
}

# --- Features utilisées par le modèle (ordre important !) ---------------
MODEL_FEATURES = [
    "duration_sec",
    "total_alarms",
    "unique_alarm_types",
    "active_alarms",
    "cleared_alarms",
    "alarm_rate",
    "alarm_diversity",
    "repetition_factor",
    "active_ratio",
    "hour",
]

# --- Hyperparamètres du modèle -------------------------------------------
ISOLATION_FOREST_PARAMS = {
    "n_estimators": 300,
    "contamination": 0.03,
    "random_state": 42,
}
