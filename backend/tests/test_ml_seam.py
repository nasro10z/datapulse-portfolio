"""Seam mock ↔ live (Phase 8) : l'aiguillage se fait par `settings.data_source`,
lu à chaud par `app/providers.py`."""
import pytest

from app.config import settings


def test_default_source_is_mock():
    assert settings.data_source == "mock"


@pytest.fixture
def live_source():
    old = settings.data_source
    settings.data_source = "live"
    yield
    settings.data_source = old


def test_live_endpoints_return_501_until_pipeline_wired(client, live_source):
    # tant que les stubs ml/ ne sont pas implémentés : 501 explicite, pas de 500 opaque
    for path in (
        "/api/health/overview",
        "/api/health/forecast",
        "/api/anomalies",
        "/api/anomalies/stats",
        "/api/anomalies/histogram",
        "/api/reminders",
    ):
        r = client.get(path)
        assert r.status_code == 501, path
        assert "live" in r.json()["detail"].lower()


def test_mock_still_default_after_toggle(client):
    # hors fixture live : tout répond normalement
    assert client.get("/api/health/overview").status_code == 200
    assert client.get("/api/anomalies").status_code == 200
