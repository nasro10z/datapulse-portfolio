"""Source LIVE santé + forecast — contrat d'intégration du pipeline ML validé.

⚠️ Non implémenté : contrat pour la Phase 8. Lève `NotImplementedError` tant que
la logique de scoring composite et de forecasting réelle n'est pas branchée.
**Ne pas réécrire la logique ML ici** — brancher le pipeline existant.

Attendu :
  - `get_overview()` : score de santé global + sous-scores par famille
    (STULZ / SOCOMEC / YANAN, pour Forecast) + sous-scores par domaine
    (environment / energy / battery, pour Site Health, avec `previous_score`
    pour le delta affiché), calculés à partir des indicateurs réels une fois
    la logique de scoring composite arrêtée (point ouvert Phase 8). YANAN reste
    en baseline (installés 2025).
  - `get_forecast(horizon)` : historique + prévision + bande de confiance, avec
    franchissements de seuil prévus (seuils Tukey 26.75 / 28.65 °C).
  - `get_history(range_)` : série temporelle quotidienne du score global et des
    3 domaines, pour les graphiques d'évolution de Site Health.
  - `get_predicted_faults(horizon)` : prochaine panne estimée par famille
    d'équipement (timing + sévérité alert/critical) — couche d'aide à la
    décision, jamais présentée comme une alarme automatique.
  - `get_subscore_forecast(horizon)` : prévision de score (0-100) par famille
    d'équipement, même fenêtre que `get_forecast`.
"""
from app.models.health import (
    ForecastHorizon,
    ForecastResponse,
    HealthHistoryResponse,
    HealthOverview,
    HistoryRange,
    PredictedFaultsResponse,
    SubScoreForecastResponse,
)

_NOT_WIRED = (
    "Source live santé/forecast non branchée : fournir le pipeline ML validé "
    "(voir app/ml/README.md) puis passer DATA_SOURCE=live."
)


def get_overview() -> HealthOverview:
    raise NotImplementedError(_NOT_WIRED)


def get_forecast(horizon: ForecastHorizon) -> ForecastResponse:
    raise NotImplementedError(_NOT_WIRED)


def get_history(range_: HistoryRange) -> HealthHistoryResponse:
    raise NotImplementedError(_NOT_WIRED)


def get_predicted_faults(horizon: ForecastHorizon) -> PredictedFaultsResponse:
    raise NotImplementedError(_NOT_WIRED)


def get_subscore_forecast(horizon: ForecastHorizon) -> SubScoreForecastResponse:
    raise NotImplementedError(_NOT_WIRED)
