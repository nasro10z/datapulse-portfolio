"""Source LIVE santé + forecast — contrat d'intégration du pipeline ML validé.

⚠️ Non implémenté : contrat pour la Phase 8. Lève `NotImplementedError` tant que
la logique de scoring composite et de forecasting réelle n'est pas branchée.
**Ne pas réécrire la logique ML ici** — brancher le pipeline existant.

Attendu :
  - `get_overview()` : score de santé global + sous-scores par famille
    (STULZ / SOCOMEC / YANAN), calculés à partir des indicateurs réels une fois
    la logique de scoring composite arrêtée (point ouvert Phase 8). YANAN reste
    en baseline (installés 2025).
  - `get_forecast(horizon)` : historique + prévision + bande de confiance, avec
    franchissements de seuil prévus (seuils Tukey 26.75 / 28.65 °C).
"""
from app.models.health import ForecastHorizon, ForecastResponse, HealthOverview

_NOT_WIRED = (
    "Source live santé/forecast non branchée : fournir le pipeline ML validé "
    "(voir app/ml/README.md) puis passer DATA_SOURCE=live."
)


def get_overview() -> HealthOverview:
    raise NotImplementedError(_NOT_WIRED)


def get_forecast(horizon: ForecastHorizon) -> ForecastResponse:
    raise NotImplementedError(_NOT_WIRED)
