"""Plannings de maintenance en lecture seule — le cas de la démo publique.

L'instance publiée n'a pas d'authentification : la saisie d'un visiteur modifierait
durablement le calendrier que voient tous les autres. `PM_READ_ONLY=1` ferme les
trois routes d'écriture, **sans rien changer à la consultation** — c'est cette
asymétrie que ces tests vérifient, plus le fait que l'interface puisse connaître
l'état de l'instance pour ne pas présenter un formulaire piégé.
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

PAYLOAD = {
    "equipment": "STULZ-01", "last_pm_date": str(date(2026, 1, 1)),
    "period_value": 90, "period_unit": "days",
}


@pytest.fixture
def read_only(monkeypatch):
    monkeypatch.setattr(settings, "pm_read_only", True)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def writable(monkeypatch):
    monkeypatch.setattr(settings, "pm_read_only", False)
    with TestClient(app) as client:
        yield client


def test_write_routes_are_refused_with_an_explicit_message(read_only):
    created = read_only.post("/api/maintenance/schedule", json=PAYLOAD)
    assert created.status_code == 403
    assert "lecture seule" in created.json()["detail"].lower()

    assert read_only.patch("/api/maintenance/schedule/PM-0001", json=PAYLOAD).status_code == 403
    assert read_only.delete("/api/maintenance/schedule/PM-0001").status_code == 403


def test_consultation_is_untouched(read_only):
    """La démo reste une démo : tout ce qui se lit se lit."""
    assert read_only.get("/api/maintenance/calendar").status_code == 200
    assert read_only.get("/api/maintenance/equipment").status_code == 200


def test_the_guard_is_off_by_default(writable):
    created = writable.post("/api/maintenance/schedule", json=PAYLOAD)
    assert created.status_code == 201
    writable.delete(f"/api/maintenance/schedule/{created.json()['id']}")


def test_config_tells_the_interface_which_instance_it_talks_to(read_only):
    """Sans cette information, le formulaire s'afficherait actif puis échouerait."""
    config = read_only.get("/api/config").json()
    assert config["pm_read_only"] is True
    assert config["data_source"] in {"mock", "live"}
    assert config["anomalies_source"] in {"mock", "live"}


def test_config_carries_no_secret(read_only):
    """La route est publique : elle ne doit rien dire de la base ni de l'hébergement."""
    body = read_only.get("/api/config").text.lower()
    for leak in ("postgres", "neon", "password", "sslmode", "sqlite", "/tmp", "http"):
        assert leak not in body
