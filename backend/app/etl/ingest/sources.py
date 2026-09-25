"""Lecteurs des données sources brutes → forme normalisée.

Ces fonctions NE font QUE lire et normaliser (encodage latin-1, en-têtes décalés,
construction de `ts`, filtrage MSC 10, mapping UPS). Elles NE calculent AUCUNE
feature : tout le préprocessing modèle reste dans `app/ml` (package validé) et est
réutilisé tel quel — jamais réimplémenté. Voir `docs/ml-data-integration.md` pour
l'inventaire des pièges de chaque fichier.

Fidélité : la normalisation ci-dessous, suivie des fonctions `app/ml`, doit
reproduire les fichiers de référence livrés (`temp_humid_last.csv` pour
l'environnemental, `msc10_combined_ups.csv` pour le SCADA) — vérifié par
`tests/test_ingestion_fidelity.py`.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import settings

# LEURS fonctions (source de vérité) — dédup + catégorisation identiques à l'entraînement
from app.ml.alarm_anomaly.data_loading import clean_and_dedupe

DATA_RAW = Path(__file__).resolve().parents[2] / "ml" / "data" / "raw"
SENSOR = "SITE01_SALLE_SWITCH"


# ------------------------------------------------------------------ environnemental
def load_temp_humidity(path: Path | None = None) -> pd.DataFrame:
    """`temp_humid_msc10.csv` (brut) → colonnes `ts, temperature, humidity, sensor`.

    Pièges gérés : encodage latin-1 ; colonnes avec espaces/accents ; `ts` absent
    (reconstruit depuis `Date` + `time`, format JJ/MM/AAAA) ; valeurs en texte.
    Les doublons de timestamp sont conservés (le bronze est une copie brute ; la
    déduplication a lieu en silver via `app/ml`).
    """
    df = pd.read_csv(path or DATA_RAW / "temp_humid_msc10.csv", encoding="latin-1")
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={"humidité": "humidity"})
    df["ts"] = pd.to_datetime(df["date"] + " " + df["time"], dayfirst=True, errors="coerce")
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["humidity"] = pd.to_numeric(df["humidity"], errors="coerce")
    df["sensor"] = SENSOR
    return (df.dropna(subset=["ts"])[["ts", "temperature", "humidity", "sensor"]]
              .sort_values("ts").reset_index(drop=True))


# ------------------------------------------------------------------ SCADA / alarmes
def load_scada_logs_2026(path: Path | None = None) -> pd.DataFrame:
    """`logs_msc10.xlsx` (SCADA MSC-10 2026) → `state, log_time, message, send_time`.

    Piège : l'en-tête réel est en **ligne 1** (ligne 0 = faux en-tête).
    """
    df = pd.read_excel(path or DATA_RAW / "logs_msc10.xlsx", header=1)
    df = df.rename(columns={"time": "log_time", "send Time": "send_time"})
    return df[["state", "log_time", "message", "send_time"]]


def load_ups_events(path: Path | None = None) -> pd.DataFrame:
    """`ups_socomec1_msc10_events.csv` → `state, log_time, message, send_time`.

    Pièges : 1re ligne parasite à sauter ; latin-1 ; `ts` reconstruit depuis
    `Date`+`Time`. Le mapping état/message **miroite** `alarm_anomaly.data_loading
    .merge_ups_source` (état `D` si « restored » sinon `A` ; message
    `<RAW_UPS_MESSAGE_PREFIX><description en majuscules>`, cf. `config.Settings`).
    """
    df = pd.read_csv(path or DATA_RAW / "ups_socomec1_msc10_events.csv",
                     skiprows=1, encoding="latin-1")
    desc = df["Description"].fillna("").astype(str)
    out = pd.DataFrame({
        "state": np.where(desc.str.contains("restored", case=False, na=False), "D", "A"),
        "message": (settings.raw_ups_message_prefix
                    + desc.str.replace(" has been restored", "", case=False, regex=False).str.upper()),
    })
    out["log_time"] = pd.to_datetime(df["Date"] + " " + df["Time"], dayfirst=True, errors="coerce")
    out["send_time"] = out["log_time"]
    return out[["state", "log_time", "message", "send_time"]]


def load_scada_alarms_2022(path: Path | None = None) -> pd.DataFrame:
    """`alarmes_scada_2022.xlsx` (multi-sites, historique 2022) → lignes MSC 10.

    ⚠️ **Hors du combiné d'entraînement** : le fichier de référence
    `msc10_combined_ups.csv` est entièrement 2026 (logs + UPS). Ces alarmes 2022
    sont fournies comme historique complémentaire, non utilisées par le modèle
    livré. Chargeur conservé pour un usage futur (ex. backfill historique élargi).
    Piège : multi-sites → filtrer `message` contient « MSC 10 ».
    """
    df = pd.read_excel(path or DATA_RAW / "alarmes_scada_2022.xlsx", sheet_name="Sheet")
    df = df.rename(columns={"time": "log_time", "send Time": "send_time"})
    df = df[df["message"].astype(str).str.contains("MSC 10", case=False, na=False)]
    return df[["state", "log_time", "message", "send_time"]]


def load_scada_raw() -> pd.DataFrame:
    """Concat brut des sources SCADA 2026 (logs + UPS), **sans** dédup/catégorie —
    pour la couche bronze (copie fidèle). La déduplication + catégorisation (silver)
    est faite plus tard par `clean_and_dedupe` (cf. `load_scada_combined`)."""
    df = pd.concat([load_scada_logs_2026(), load_ups_events()], ignore_index=True)
    df["log_time"] = pd.to_datetime(df["log_time"], errors="coerce")
    df["send_time"] = pd.to_datetime(df["send_time"], errors="coerce")
    return df.dropna(subset=["log_time"])[["state", "log_time", "message", "send_time"]]


def load_scada_combined() -> pd.DataFrame:
    """Combiné SCADA 2026 (logs + UPS) → dédupliqué + catégorisé par LEUR
    `clean_and_dedupe` (identique à l'entraînement). Reproduit `msc10_combined_ups.csv`.
    """
    combined = pd.concat([load_scada_logs_2026(), load_ups_events()], ignore_index=True)
    return clean_and_dedupe(combined)
