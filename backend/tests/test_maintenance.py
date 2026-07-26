from datetime import date

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.models.maintenance import CalendarEntry
from app.services.maintenance import add_months, get_calendar


def test_schedule_months_calculation(client):
    r = client.post("/api/maintenance/schedule", json={
        "equipment": "STULZ-01",
        "last_pm_date": "2026-07-01",
        "period_value": 3,
        "period_unit": "months",
    })
    assert r.status_code == 201
    entry = CalendarEntry.model_validate(r.json())
    assert entry.next_pm_date == date(2026, 10, 1)


def test_schedule_days_and_weeks(client):
    r = client.post("/api/maintenance/schedule", json={
        "equipment": "UPS-02", "last_pm_date": "2026-07-20",
        "period_value": 10, "period_unit": "days",
    })
    assert r.json()["next_pm_date"] == "2026-07-30"
    r = client.post("/api/maintenance/schedule", json={
        "equipment": "GEN-02", "last_pm_date": "2026-07-20",
        "period_value": 2, "period_unit": "weeks",
    })
    assert r.json()["next_pm_date"] == "2026-08-03"


def test_month_end_clamping():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 10, 31), 2) == date(2026, 12, 31)


def test_scheduled_entry_appears_in_calendar(client):
    r = client.post("/api/maintenance/schedule", json={
        "equipment": "STULZ-09", "last_pm_date": "2026-07-15",
        "period_value": 6, "period_unit": "months",
    })
    entry_id = r.json()["id"]
    calendar = client.get("/api/maintenance/calendar").json()
    entries = [CalendarEntry.model_validate(e) for e in calendar]
    assert any(e.id == entry_id for e in entries)
    dates = [e.next_pm_date for e in entries]
    assert dates == sorted(dates)


def test_schedule_persists_on_disk(client):
    """Une PM planifiée doit survivre au redémarrage du process — ce que le
    store en mémoire ne garantissait pas."""
    r = client.post("/api/maintenance/schedule", json={
        "equipment": "STULZ-05", "last_pm_date": "2026-06-10",
        "period_value": 90, "period_unit": "days",
    })
    entry_id = r.json()["id"]

    # moteur neuf sur le même fichier : prouve l'écriture disque, pas un cache de session
    engine = create_engine(URL.create(drivername="sqlite", database=str(settings.app_db_path)))
    try:
        with Session(engine) as session:
            assert any(e.id == entry_id for e in get_calendar(session))
    finally:
        engine.dispose()


def test_invalid_period_rejected(client):
    r = client.post("/api/maintenance/schedule", json={
        "equipment": "STULZ-01", "last_pm_date": "2026-07-01",
        "period_value": 0, "period_unit": "days",
    })
    assert r.status_code == 422


def test_update_recomputes_next_pm(client):
    created = client.post("/api/maintenance/schedule", json={
        "equipment": "STULZ-05", "last_pm_date": "2026-07-01",
        "period_value": 1, "period_unit": "months",
    }).json()
    r = client.patch(f"/api/maintenance/schedule/{created['id']}", json={
        "equipment": "STULZ-05", "last_pm_date": "2026-07-01",
        "period_value": 2, "period_unit": "months",
    })
    assert r.status_code == 200
    assert r.json()["next_pm_date"] == "2026-09-01"  # recalculé depuis la nouvelle période
    # persisté : relu depuis le calendrier
    entry = next(e for e in client.get("/api/maintenance/calendar").json() if e["id"] == created["id"])
    assert entry["next_pm_date"] == "2026-09-01"


def test_delete_removes_entry(client):
    created = client.post("/api/maintenance/schedule", json={
        "equipment": "STULZ-06", "last_pm_date": "2026-07-01",
        "period_value": 3, "period_unit": "months",
    }).json()
    assert client.delete(f"/api/maintenance/schedule/{created['id']}").status_code == 204
    ids = [e["id"] for e in client.get("/api/maintenance/calendar").json()]
    assert created["id"] not in ids


def test_update_delete_unknown_404(client):
    assert client.patch("/api/maintenance/schedule/PM-9999", json={
        "equipment": "X", "last_pm_date": "2026-07-01",
        "period_value": 1, "period_unit": "days",
    }).status_code == 404
    assert client.delete("/api/maintenance/schedule/PM-9999").status_code == 404
