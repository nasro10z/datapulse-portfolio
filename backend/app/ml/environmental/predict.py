"""
Prédicteur HMM avec historique en mémoire (Option A retenue avec l'équipe) :
l'API reçoit UNE lecture à la fois {ts, temperature, humidity}, et c'est CE
module qui garde le buffer des dernières lectures pour calculer les features
glissantes et faire une vraie prédiction HMM à chaque nouvelle lecture.

⚠️ Limite connue : l'historique est en mémoire (perdu si l'API redémarre).
Suffisant pour la démo / le développement. À remplacer par une vraie base de
données quand elle sera disponible (voir roadmap du projet).
"""
import json

import joblib
import numpy as np
import pandas as pd

from app.ml.environmental.config import (
    MODEL_PATH, SCALER_PATH, ANOMALOUS_STATES_PATH, FEATURE_COLS,
    TEMP_COL, HUMIDITY_COL, MAX_CONTINUOUS_GAP_SECONDS,
    MIN_HISTORY_FOR_PREDICTION, RECOMMENDED_HISTORY_SIZE,
)
from app.ml.environmental.preprocessing import add_segments, compute_rolling_features


class EnvironmentalPredictor:
    """
    Garde un buffer des dernières lectures température/humidité et prédit
    l'état HMM (anomalie ou non) du point le plus récent à chaque appel.
    """

    def __init__(self, model_path=MODEL_PATH, scaler_path=SCALER_PATH,
                 anomalous_states_path=ANOMALOUS_STATES_PATH,
                 buffer_size: int = RECOMMENDED_HISTORY_SIZE):
        self.hmm = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        with open(anomalous_states_path) as f:
            self.anomalous_states = set(json.load(f)["anomalous_states"])
        self.buffer_size = buffer_size
        self._buffer = pd.DataFrame(columns=["ts", TEMP_COL, HUMIDITY_COL]).set_index("ts")

    def add_reading(self, ts, temperature: float, humidity: float) -> None:
        """Ajoute une nouvelle lecture au buffer, purge les plus anciennes."""
        ts = pd.to_datetime(ts)
        new_row = pd.DataFrame(
            {TEMP_COL: [temperature], HUMIDITY_COL: [humidity]},
            index=pd.DatetimeIndex([ts], name="ts"),
        )
        self._buffer = pd.concat([self._buffer, new_row])
        self._buffer = self._buffer[~self._buffer.index.duplicated(keep="last")].sort_index()

        if len(self._buffer) > self.buffer_size:
            self._buffer = self._buffer.iloc[-self.buffer_size:]

    def predict_latest(self) -> dict:
        """
        Calcule les features sur le buffer actuel et prédit l'état HMM
        du point le plus RÉCENT. Lève ValueError si l'historique est
        encore insuffisant.
        """
        if len(self._buffer) < MIN_HISTORY_FOR_PREDICTION:
            raise ValueError(
                f"Historique insuffisant : {len(self._buffer)} lectures, "
                f"minimum {MIN_HISTORY_FOR_PREDICTION} requis pour une prédiction fiable."
            )

        df = self._buffer.copy()
        df = add_segments(df)
        df = compute_rolling_features(df)

        X = df[FEATURE_COLS].replace([np.inf, -np.inf], np.nan).dropna()
        if X.empty:
            raise ValueError("Impossible de calculer les features sur le buffer actuel.")

        latest_ts = self._buffer.index[-1]
        if latest_ts not in X.index:
            # La lecture la plus récente n'a pas encore assez d'historique
            # CONTINU derrière elle (ex: coupure récente qui a démarré un
            # nouveau segment) -> on ne doit JAMAIS prédire silencieusement
            # sur une lecture plus ancienne à la place.
            raise ValueError(
                "La lecture la plus récente n'a pas encore assez d'historique "
                "continu (probable coupure récente) pour une prédiction fiable. "
                "Réessayer après quelques lectures supplémentaires."
            )

        X_scaled = self.scaler.transform(X)
        # Séquence unique = tout le buffer disponible, pour exploiter la
        # dynamique temporelle (transitions) du HMM au maximum.
        states = self.hmm.predict(X_scaled, lengths=[len(X_scaled)])
        latest_position_in_X = X.index.get_loc(latest_ts)
        latest_state = int(states[latest_position_in_X])

        return {
            "is_anomaly": latest_state in self.anomalous_states,
            "state": latest_state,
            "score": float(self.hmm.score(
                X_scaled[latest_position_in_X:latest_position_in_X + 1], lengths=[1]
            )),
            "history_size": len(self._buffer),
        }

    def predict_one(self, reading: dict) -> dict:
        """
        Interface unifiée avec AnomalyPredictor (modèle 1) : reçoit UNE
        lecture, l'ajoute au buffer, et retourne la prédiction du point
        le plus récent. Utilisée par l'API.
        """
        self.add_reading(reading["ts"], reading["temperature"], reading["humidity"])
        return self.predict_latest()