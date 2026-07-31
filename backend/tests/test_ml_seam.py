"""Seam mock ↔ live (Phase 8) : l'aiguillage se fait par `settings.data_source`,
avec dérogation possible par domaine, lu à chaud par `app/providers.py`."""
import pytest

from app.config import Settings, settings


def test_shipped_default_source_is_mock():
    """Le défaut **livré** reste `mock` : personne ne se retrouve branché sur le
    pipeline réel sans l'avoir demandé. On teste la valeur par défaut du champ,
    pas la valeur résolue — celle-ci dépend du `.env` local du poste."""
    assert Settings.model_fields["data_source"].default == "mock"


def test_domain_override_falls_back_to_the_global_source():
    """Sans dérogation, un domaine suit `data_source` : un seul bouton dans le cas
    général, la granularité ne se paie que si on la demande."""
    assert Settings.model_fields["anomalies_source"].default is None
    assert Settings.model_fields["health_source"].default is None

    both_live = Settings(data_source="live", anomalies_source=None, health_source=None)
    assert both_live.resolved_anomalies_source == "live"
    assert both_live.resolved_health_source == "live"


def test_domain_override_wins_over_the_global_source():
    """Cas démo : santé sur le pipeline réel, anomalies en mock — les épisodes
    réels s'arrêtant en mai 2026, les vues à fenêtre récente n'ont rien à montrer."""
    mixed = Settings(data_source="live", anomalies_source="mock")
    assert mixed.resolved_anomalies_source == "mock"
    assert mixed.resolved_health_source == "live"


@pytest.fixture
def live_source():
    old = (settings.data_source, settings.anomalies_source, settings.health_source)
    settings.data_source = "live"
    # Les dérogations sont neutralisées : ces tests portent sur le seam global.
    settings.anomalies_source = settings.health_source = None
    yield
    settings.data_source, settings.anomalies_source, settings.health_source = old


@pytest.fixture
def scored_gold():
    """Alimente le gold santé (horaire + instantané + prévision) puis le vide.

    Le gold est partagé par la session de test : on le rend à son état vide en
    sortie pour que le test « gold vide → 501 » reste valable quel que soit
    l'ordre d'exécution.
    """
    from app.etl.forecast import build_forecast_points
    from app.etl.score import build_snapshot_rows
    from app.ml.health_score import forecasting
    from app.ml.health_score.scoring import compute_health_scores
    from app.storage.analytics_db import get_analytics_sessionmaker
    from app.storage.repositories import gold_repo
    from tests.test_score_forecast import _synthetic_env, _synthetic_scada

    scores = compute_health_scores(_synthetic_env(1200), _synthetic_scada(1200))
    artifacts = forecasting.train(scores)

    with get_analytics_sessionmaker()() as session:
        gold_repo.replace_health_hourly(session, scores)
        gold_repo.replace_health_scores(session, "test-run", build_snapshot_rows(scores))
        gold_repo.replace_forecast_points(session, "test-run",
                                          build_forecast_points(scores, artifacts))
    yield
    with get_analytics_sessionmaker()() as session:
        gold_repo.replace_health_hourly(session, scores.iloc[0:0])
        gold_repo.replace_health_scores(session, "test-run", [])
        gold_repo.replace_forecast_points(session, "test-run", [])


def test_live_health_returns_501_when_gold_is_empty(client, live_source):
    # Gold non alimenté (ETL jamais lancé) → 501 explicite avec la marche à
    # suivre, pas un 500 opaque ni des zéros qui passeraient pour des mesures.
    for path in ("/api/health/overview", "/api/health/forecast"):
        r = client.get(path)
        assert r.status_code == 501, path
        assert "live" in r.json()["detail"].lower()


def test_live_health_serves_gold_once_scored(client, live_source, scored_gold):
    """Gold alimenté → les cinq routes santé servent le pipeline réel."""
    for path in ("/api/health/overview", "/api/health/history?range=7d",
                 "/api/health/forecast?horizon=24h",
                 "/api/health/predicted-faults?horizon=24h",
                 "/api/health/forecast/sub-scores?horizon=24h"):
        assert client.get(path).status_code == 200, path

    overview = client.get("/api/health/overview").json()
    assert 0 <= overview["global_score"] <= 100
    assert {d["domain"] for d in overview["domain_scores"]} == {"environment", "energy", "battery"}
    assert {s["family"] for s in overview["sub_scores"]} == {"stulz", "socomec", "yanan"}

    forecast = client.get("/api/health/forecast?horizon=24h").json()
    observed = [p for p in forecast["points"] if not p["is_forecast"]]
    predicted = [p for p in forecast["points"] if p["is_forecast"]]
    assert observed and predicted
    # La prévision reprend exactement là où l'observation s'arrête (pas de trou).
    assert predicted[0]["timestamp"] > observed[-1]["timestamp"]
    assert all(p["lower"] <= p["value"] <= p["upper"] for p in predicted)


def test_live_anomalies_read_gold(client, live_source):
    # étape G : anomalies + rappels servis depuis le gold précalculé (gold vide en
    # test → réponses vides mais 200, plus de 501)
    for path in ("/api/anomalies", "/api/anomalies/stats",
                 "/api/anomalies/histogram", "/api/reminders"):
        assert client.get(path).status_code == 200, path


def test_mock_still_default_after_toggle(client):
    # hors fixture live : tout répond normalement
    assert client.get("/api/health/overview").status_code == 200
    assert client.get("/api/anomalies").status_code == 200
