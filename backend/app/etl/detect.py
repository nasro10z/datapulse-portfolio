"""Étape E — détection → épisodes (couche gold).

Déroule le **HMM environnemental validé** sur tout le silver, groupe les lectures
en état anormal en **épisodes par salle**, et écrit la couche gold
(`anomaly_episode`). Réutilise le préprocessing + le modèle livrés (`app/ml`) —
jamais réimplémentés : `compute_rolling_features`, `prepare_hmm_sequences`, le
scaler + le HMM + `anomalous_states.json`.

Décisions de mapping « run HMM → AnomalyEpisode » (champs non portés nativement
par l'état HMM — à confirmer) :
  - **direction / pic / sévérité** : dérivés de la TEMPÉRATURE du run vs seuils
    livrés (`thresholds.json`) — excursion dominante (haut si le dépassement de
    `mild_upper` l'emporte sur le passage sous `mild_lower`) ; pic = température
    extrême du run ; sévérité `critical` si le seuil `extreme` est franchi.
  - **filtre** : un run dont la température ne franchit aucun seuil (anomalie
    humidité/contextuelle du HMM) n'est PAS surfacé — décision « HMM + franchissement
    de seuil réel » (réduit ~1383 runs bruts à ~388 épisodes de vraie excursion).
  - **type** = `collective` (le HMM détecte des anomalies contextuelles multivariées).
  - **equipment** = `SALLE_SWITCH` (granularité salle).
  - **status** par ancienneté (`resolved` >72 h, `acknowledged` >24 h, sinon `open`),
    mesurée contre la **fin de la période observée** — pas contre l'horloge, qui
    marquerait tout un export historique comme « résolu ».
  - **id** = `EP-{n:04d}` par ordre chronologique (stable sur données figées).
  - **dimension** = `environment` (seul le pipeline HMM est branché ; `scada`
    viendra avec l'ingestion des CSV SCADA, cf. `models/anomalies.AnomalyDimension`).

    python -m app.etl.detect   (depuis backend/, PYTHONPATH=.)
"""
import json
from datetime import datetime

import joblib
import numpy as np
import pandas as pd

from app.ml.environmental.config import (
    ANOMALOUS_STATES_PATH, FEATURE_COLS, HUMIDITY_COL, MODEL_PATH,
    SCALER_PATH, TEMP_COL, THRESHOLDS_PATH,
)
from app.ml.environmental.preprocessing import compute_rolling_features, prepare_hmm_sequences
from app.models.anomalies import (
    AnomalyDimension,
    AnomalyEpisode,
    AnomalyStatus,
    AnomalyType,
    Direction,
    Severity,
)
from app.storage.analytics_db import get_analytics_sessionmaker, init_analytics_db
from app.storage.repositories import gold_repo, silver_repo

ROOM = "SALLE_SWITCH"


def _status_for(start: datetime, now: datetime) -> AnomalyStatus:
    """Statut par ancienneté, mesurée contre la **fin de la période observée**.

    Mesurée contre l'horloge, tout épisode d'un export historique figé serait
    « résolu » d'office — l'ancienneté refléterait l'âge du fichier, pas celle de
    l'événement.
    """
    age_h = (now - start).total_seconds() / 3600.0
    if age_h > 72:
        return AnomalyStatus.resolved
    if age_h > 24:
        return AnomalyStatus.acknowledged
    return AnomalyStatus.open


def _characterize(run: pd.DataFrame, temp_thr: dict) -> dict | None:
    """Caractérise un run anormal via la température. Renvoie **None** si la
    température ne franchit AUCUN seuil (anomalie humidité/contextuelle — non
    surfacée, cf. décision « HMM + franchissement de seuil réel »)."""
    temps = run[TEMP_COL].dropna()
    if temps.empty:
        return None
    tmax, tmin = float(temps.max()), float(temps.min())
    high_cross = tmax >= temp_thr["mild_upper"]
    low_cross = tmin <= temp_thr["mild_lower"]
    if not (high_cross or low_cross):
        return None

    high_exc = tmax - temp_thr["mild_upper"]
    low_exc = temp_thr["mild_lower"] - tmin
    if high_cross and (not low_cross or high_exc >= low_exc):
        direction, peak = Direction.high, tmax
        severity = Severity.critical if tmax >= temp_thr["extreme_upper"] else Severity.alert
    else:
        direction, peak = Direction.low, tmin
        severity = Severity.critical if tmin <= temp_thr["extreme_lower"] else Severity.alert

    start = run.index.min().to_pydatetime()
    end = run.index.max().to_pydatetime()
    return {
        "start": start, "direction": direction, "peak": round(peak, 2), "severity": severity,
        "duration_min": round(max((end - start).total_seconds() / 60.0, 2.0), 1),
    }


def run_hmm_episodes(silver: pd.DataFrame) -> list[AnomalyEpisode]:
    """Silver `th_clean` → épisodes : runs d'état anormal du HMM **filtrés** sur un
    franchissement réel de seuil de température (les anomalies humidité/contextuelles
    du HMM ne sont pas surfacées ici)."""
    if silver.empty:
        return []
    df = silver.set_index("ts").sort_index()
    df = compute_rolling_features(df)                       # LEUR feature engineering
    X = df[FEATURE_COLS].replace([np.inf, -np.inf], np.nan).dropna()
    if X.empty:
        return []
    X_seq, lengths = prepare_hmm_sequences(X, df)           # LEUR séquençage

    hmm = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    with open(ANOMALOUS_STATES_PATH) as f:
        anomalous = set(json.load(f)["anomalous_states"])
    with open(THRESHOLDS_PATH) as f:
        temp_thr = json.load(f)["temperature"]

    states = hmm.predict(scaler.transform(X_seq), lengths=lengths)
    s = pd.DataFrame({"state": states}, index=X_seq.index)
    s["is_anom"] = s["state"].isin(anomalous)
    s = s.join(df[["segment_id", TEMP_COL, HUMIDITY_COL]])

    # épisode candidat = run contigu de lectures anormales dans un même segment
    brk = (s["is_anom"] != s["is_anom"].shift()) | (s["segment_id"] != s["segment_id"].shift())
    s["run"] = brk.cumsum()

    # Fin de la période observée — même repère que les fenêtres servies à l'API
    # (cf. `ml/anomalies.reference_now`), pour que « ouverte / acquittée / résolue »
    # se lise par rapport aux données et non par rapport à l'âge de l'export.
    now = df.index.max().to_pydatetime()
    cands = [_characterize(r, temp_thr) for _, r in s[s["is_anom"]].groupby("run")]
    cands = sorted((c for c in cands if c is not None), key=lambda c: c["start"])
    return [
        AnomalyEpisode(
            id=f"EP-{i:04d}", equipment=ROOM, type=AnomalyType.collective,
            severity=c["severity"], direction=c["direction"], start=c["start"],
            duration_min=c["duration_min"], peak_value=c["peak"],
            status=_status_for(c["start"], now), dimension=AnomalyDimension.environment,
        )
        for i, c in enumerate(cands, 1)
    ]


def detect_environmental_episodes(session) -> int:
    episodes = run_hmm_episodes(silver_repo.read_th_clean(session))
    return gold_repo.replace_episodes(session, episodes)


def run_detect() -> dict[str, int]:
    init_analytics_db()
    with get_analytics_sessionmaker()() as session:
        return {"anomaly_episode": detect_environmental_episodes(session)}


if __name__ == "__main__":
    print(run_detect())
