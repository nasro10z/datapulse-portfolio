"""
Chargement du modèle entraîné et prédiction sur de nouveaux événements.
Ce module est utilisé à la fois par l'API (étape 4) et par les tests.
"""
import joblib
import pandas as pd

from app.ml.alarm_anomaly.config import MODEL_PATH, SCALER_PATH, MODEL_FEATURES


class AnomalyPredictor:
    """Encapsule le modèle + le scaler pour éviter de les recharger à chaque appel."""

    def __init__(self, model_path=MODEL_PATH, scaler_path=SCALER_PATH):
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)

    def predict_one(self, event_features: dict) -> dict:
        """
        event_features : dict contenant AU MOINS les clés de MODEL_FEATURES,
        typiquement déjà calculées par feature_engineering.build_event_features
        sur un seul événement.
        """
        row = pd.DataFrame([event_features])[MODEL_FEATURES].fillna(0)
        X_scaled = self.scaler.transform(row)

        prediction = self.model.predict(X_scaled)[0]     # -1 = anomalie, 1 = normal
        score = self.model.decision_function(X_scaled)[0]  # plus c'est bas, plus c'est anormal

        return {
            "is_anomaly": bool(prediction == -1),
            "score": float(score),
            "dominant_category": event_features.get("dominant_category", "OTHER"),
        }