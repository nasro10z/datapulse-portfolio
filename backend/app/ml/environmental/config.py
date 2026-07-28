"""
Configuration centralisée du modèle "environmental" (HMM température/humidité).
Repris fidèlement des constantes du notebook environmental_fixed.ipynb.
"""
from pathlib import Path
import os 

# Vendorisé sous app/ml/ : parents[1] = app/ml (racine du package ML vendorisé).
ROOT_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)
DB_PATH = os.path.join(
    BASE_DIR,"..","datapulse.db"
)
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
MODELS_DIR = ROOT_DIR / "models"

MODEL_NAME = "environmental"
MODEL_DIR = MODELS_DIR / MODEL_NAME

MODEL_PATH = MODEL_DIR / "hmm.joblib"
SCALER_PATH = MODEL_DIR / "scaler.joblib"
ANOMALOUS_STATES_PATH = MODEL_DIR / "anomalous_states.json"
THRESHOLDS_PATH = MODEL_DIR / "thresholds.json"
METADATA_PATH = MODEL_DIR / "metadata.json"

DATA_CSV_FILENAME = "temp_humid_last.csv"

TIMESTAMP_COL = "ts"
TEMP_COL = "temperature"
HUMIDITY_COL = "humidity"

# --- Continuité des lectures ------------------------------------------------
EXPECTED_INTERVAL_SECONDS = 120
MAX_CONTINUOUS_GAP_SECONDS = 125

# --- Fenêtres glissantes : (taille de fenêtre, min_periods) ----------------
WINDOW_CONFIG = {
    "court": (12, 6),
    "moyen": (36, 18),
    "long": (78, 39),
}
# Nombre de lectures conseillé en historique pour une prédiction fiable
# (un peu plus que la fenêtre "long" pour laisser une marge de sécurité).
MIN_HISTORY_FOR_PREDICTION = WINDOW_CONFIG["long"][1]  # 39, minimum absolu
RECOMMENDED_HISTORY_SIZE = 100  # taille conseillée du buffer en streaming

# --- Hystérésis pour la détection d'épisodes (entraînement uniquement) -----
TEMP_HYSTERESIS_MARGIN = 0.5
HUMIDITY_HYSTERESIS_MARGIN = 2.0

# --- Les 19 features utilisées par le modèle (ordre important !) -----------
FEATURE_COLS = [
    "temperature", "humidity",
    "temperature_mean_court", "temperature_mean_moyen", "temperature_mean_long",
    "humidity_mean_court", "humidity_mean_moyen", "humidity_mean_long",
    "temperature_std_court", "humidity_std_court",
    "temp_short_long_delta", "humidity_short_long_delta",
    "temp_change", "humidity_change",
    "temp_change_10min", "humidity_change_10min",
    "segment_freshness_court", "segment_freshness_moyen",
    "segment_freshness_long",
]

# --- Sélection du modèle HMM (entraînement uniquement) ----------------------
N_STATES_CANDIDATES = [2, 3, 4, 5, 6]
PROP_CUTOFF_CANDIDATES = [0.05, 0.10, 0.20, 0.30]
HMM_SEEDS = (0, 7, 21, 42, 99)
HMM_N_ITER = 500
MIN_STATE_SIZE = 20  # une config HMM n'est retenue que si chaque état a >= 20 points