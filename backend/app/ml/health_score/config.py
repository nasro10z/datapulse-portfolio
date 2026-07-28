"""Constantes du score de santé — reprises **à l'identique** du notebook
`health_scores.ipynb` (section « Adjustable Scoring Weights » + cellules de
features). Source unique de vérité : rien ne doit re-coder ces valeurs en dur
ailleurs dans le backend.

Toute évolution des poids passe par `WEIGHT_VERSION` (versionné avec le gold),
pour qu'un score servi reste traçable jusqu'à la configuration qui l'a produit.
"""
from pathlib import Path

import pandas as pd

# Versions embarquées dans chaque ligne gold — traçabilité score ↔ configuration.
WEIGHT_VERSION = "v1.0"
SCORE_VERSION = "health_score_v1.0"

MODELS_DIR = Path(__file__).resolve().parents[1] / "models" / "health_forecast"

# --- Poids ------------------------------------------------------------------
# Chaque groupe somme à 1 (vérifié par `scoring.validate_weights`).
WEIGHTS: dict[str, dict[str, float]] = {
    "environmental": {
        "temperature": 0.40,
        "humidity": 0.25,
        "temperature_variability": 0.20,
        "humidity_variability": 0.15,
    },
    "energy": {
        "outage": 0.35,
        "supply_instability": 0.20,
        "generator": 0.15,
        "backup_transfer": 0.15,
        "persistence": 0.15,
    },
    "battery": {
        # 6 termes : `persistence` (durée continue de l'alarme) a été ajouté au
        # formalisme initial à 5 termes et porte le poids le plus fort — le
        # comptage brut d'alarmes ne distingue pas un défaut qui s'efface
        # immédiatement d'un défaut qui ne s'efface pas.
        "check_battery": 0.20,
        "discharge": 0.20,
        "low_battery": 0.15,
        "chatter": 0.10,
        "recurrence": 0.10,
        "persistence": 0.25,
    },
    "overall": {
        "environmental": 0.30,
        "energy": 0.35,
        "battery": 0.35,
    },
}

# Poids de groupe → colonne de feature effectivement présente dans les frames
# horaires. Seule table de correspondance du projet.
ENV_TERM_MAP = {
    "temperature": "temp_term",
    "humidity": "humidity_term",
    "temperature_variability": "temp_change_term",
    "humidity_variability": "humidity_change_term",
}

ENERGY_TERM_MAP = {
    "outage": "outage_term",
    "supply_instability": "supply_term",
    "generator": "generator_term",
    "backup_transfer": "transfer_term",
    "persistence": "persistence_term",
}

BATTERY_TERM_MAP = {
    "check_battery": "check_battery_component",
    "discharge": "discharge_component",
    "low_battery": "low_battery_component",
    "chatter": "chatter_component",
    "recurrence": "recurrence_component",
    "persistence": "persistence_component",
}

REQUIRED_WEIGHT_KEYS = {
    "environmental": set(ENV_TERM_MAP),
    "energy": set(ENERGY_TERM_MAP),
    "battery": set(BATTERY_TERM_MAP),
    "overall": {"environmental", "energy", "battery"},
}

# --- Multiplicateurs anomalie / maintenance (fixes, par sous-système) --------
# `risque_final = risque_base × (1 + wa·anomalie) × (1 + wm·risque_PM)`.
ANOMALY_PM_MULTIPLIERS = {
    "environmental": {"anomaly_weight": 0.50, "maintenance_weight": 0.30},
    "energy": {"anomaly_weight": 0.50, "maintenance_weight": 0.35},
    "battery": {"anomaly_weight": 0.50, "maintenance_weight": 0.50},
}

# --- Maintenance préventive -------------------------------------------------
# Dernières PM connues par famille + intervalle attendu. Le risque PM croît
# linéairement de 0 à 1 sur l'intervalle puis plafonne.
ENV_LAST_PM_DATE = pd.Timestamp("2026-03-01")       # climatisation
ENV_MAINTENANCE_INTERVAL_DAYS = 90
ENERGY_LAST_PM_DATE = pd.Timestamp("2022-12-13")    # onduleurs / groupes
ENERGY_MAINTENANCE_INTERVAL_DAYS = 180
BATTERY_MAINTENANCE_INTERVAL_DAYS = 90
# Batteries : aucune date de service connue → ancrage sur le 1er point de données
# (résolu à l'exécution, cf. `scoring.build_battery_scores`).

# --- Plausibilité physique des lectures capteur -----------------------------
# Bornes hors desquelles une lecture est traitée comme **manquante**, pas comme
# une mesure. Deux défauts bien identifiés dans l'export brut :
#   - repli capteur : humidité qui tombe à 0-11 % puis remonte à 44 % à la lecture
#     suivante — physiquement impossible dans une salle, et le fichier de référence
#     livré (`temp_humid_last.csv`) porte NaN à ces timestamps ;
#   - champs concaténés : quelques lignes où humidité et température se retrouvent
#     collées (ex. « 4523.9 »), écartées par la borne haute.
# Repères du fichier de référence livré : humidité min 23.5 %, température min
# 17.9 °C — les bornes ci-dessous restent donc largement en deçà du vécu réel et
# n'écartent aucune mesure valide.
ENV_PLAUSIBLE_TEMP_RANGE = (5.0, 60.0)
ENV_PLAUSIBLE_HUMIDITY_RANGE = (15.0, 100.0)

# --- Paramètres des features ------------------------------------------------
ENERGY_HALFLIFE_HOURS = 8           # décroissance de la charge événementielle
BATTERY_HALFLIFE_HOURS = 8
ENERGY_DURATION_SCALE_HOURS = 6     # coupure continue considérée comme sévère
BATTERY_DURATION_SCALE_HOURS = 6

TREND_SHORT_HOURS = 6
TREND_LONG_HOURS = 24
VOLATILITY_WINDOW_HOURS = 24
OVERALL_SMOOTHING_WINDOW_HOURS = 6

# Calibration énergie : compression douce puis plancher pour coupure persistante.
ENERGY_COMPRESSION_SCALE = 60.0
ENERGY_SEVERE_FLOOR = 85.0

# --- Mots-clés d'alarmes ----------------------------------------------------
OUTAGE_KEYWORDS = [
    "absence de tension", "absence tension", "power failure", "mains failure",
    "utility failure", "coupure", "perte secteur",
]

SUPPLY_KEYWORDS = [
    "rectifier", "redresseur", "bypass", "input voltage", "supply fault",
    "alimentation", "tension reseau", "tension réseau",
]

GENERATOR_KEYWORDS = [
    "generator", "groupe electrogene", "groupe électrogène", "genset", "diesel",
]

# « switch » a été retiré (matchait « Salle Switch Temperature Haute », une alarme
# de température de salle) et « on battery » aussi (déjà revendiqué par
# DISCHARGE_KEYWORDS : compter l'événement des deux côtés le facturait à la fois
# à l'énergie et à la batterie).
TRANSFER_KEYWORDS = ["transfer", "ats", "basculement", "backup supply", "secours"]

CHECK_BATTERY_KEYWORDS = [
    "check battery", "battery test", "replace battery", "battery fault",
    "battery general alarm", "ups unit 1 general alarm", "ups unit 2 general alarm",
    "batterie à vérifier", "verifier batterie", "vérifier batterie",
    "défaut batterie", "defaut batterie",
]

DISCHARGE_KEYWORDS = [
    "battery discharge", "discharging", "operating on battery", "on battery",
    "décharge batterie", "decharge batterie", "sur batterie",
]

LOW_BATTERY_KEYWORDS = [
    "low battery", "battery low", "low capacity", "battery capacity",
    "batterie faible", "faible autonomie",
]

BATTERY_CHATTER_KEYWORDS = [
    "battery connect", "battery disconnect", "battery connected",
    "battery disconnected", "connexion batterie", "déconnexion batterie",
    "deconnexion batterie",
]

# --- Classification des scores ---------------------------------------------
# Bornes de statut (santé 0-100, `right=False`) et priorité de maintenance.
STATUS_BINS = [40, 60, 75, 90]
STATUS_LABELS = ["Critical", "High Risk", "Warning", "Minor Degradation", "Healthy"]
PRIORITY_LABELS = ["P1 - Immediate", "P2 - Urgent", "P3 - Investigate", "P4 - Monitor"]
PRIORITY_DEFAULT = "P5 - Routine"

# --- Prévision --------------------------------------------------------------
FORECAST_HORIZON_HOURS = 6          # cible : santé globale à +6 h
HEALTH_LAGS = [1, 2, 3, 6, 12, 24, 48, 72, 168]
ROLLING_WINDOWS = [6, 12, 24, 72, 168]
SUBSYSTEM_LAGS = [1, 6, 12, 24]
CHANGE_PERIODS = [1, 3, 6, 12, 24]
MAJOR_DROP_THRESHOLD = -10.0        # chute de santé (points) sur 6 h
SEVERE_DROP_THRESHOLD = -20.0
DEGRADATION_THRESHOLD = 60.0        # santé sous laquelle on parle de « risque élevé »

SUBSYSTEM_HEALTH_COLUMNS = [
    "environmental_health_score",
    "energy_health_score",
    "battery_health_score",
]

CURRENT_NUMERIC_FEATURES = [
    "overall_site_health",
    "environmental_health_score", "energy_health_score", "battery_health_score",
    "environmental_risk_score", "energy_risk_score", "battery_risk_score",
    "environmental_base_risk", "energy_base_risk", "battery_base_risk",
    "environmental_pm_risk", "energy_pm_risk", "battery_pm_risk",
    "environmental_anomaly_burden", "energy_anomaly_burden", "battery_anomaly_burden",
    "overall_site_health_trend_24h", "overall_site_health_volatility_24h",
    "overall_site_health_smoothed_6h",
    "battery_alarm_duration_hours", "outage_duration_hours",
    "temperature", "humidity", "score_confidence",
]

# Features sans lesquelles une ligne n'est pas modélisable (pas d'historique).
REQUIRED_FORECAST_FEATURES = [
    "overall_site_health",
    "overall_health_lag_1h",
    "overall_health_lag_6h",
    "overall_health_lag_24h",
]
