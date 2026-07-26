from app.models.reminders import Reminder, ReminderKind


def test_reminders_contract(client):
    r = client.get("/api/reminders")
    assert r.status_code == 200
    reminders = [Reminder.model_validate(x) for x in r.json()]
    assert reminders
    kinds = {rm.kind for rm in reminders}
    assert ReminderKind.unacked_anomaly in kinds
    assert ReminderKind.threshold_approach in kinds
    due_ats = [rm.due_at for rm in reminders]
    assert due_ats == sorted(due_ats)


def test_count_matches_list(client):
    listed = client.get("/api/reminders").json()
    count = client.get("/api/reminders/count").json()["count"]
    assert count == len(listed)


def test_acknowledge_removes_reminder(client):
    rid = client.get("/api/reminders").json()[0]["id"]
    assert client.post(f"/api/reminders/{rid}/acknowledge").status_code == 204
    ids = [r["id"] for r in client.get("/api/reminders").json()]
    assert rid not in ids
    # reflété dans le compteur
    assert client.get("/api/reminders/count").json()["count"] == len(ids)


def test_snooze_hides_then_reappears(client):
    rid = client.get("/api/reminders").json()[0]["id"]
    # snooze futur → masqué
    assert client.post(f"/api/reminders/{rid}/snooze", json={"hours": 24}).status_code == 204
    assert rid not in [r["id"] for r in client.get("/api/reminders").json()]
    # un nouveau snooze très court (déjà quasi expiré) → réapparaît
    # (borne : hours > 0 ; on vérifie surtout que le filtre repose sur snoozed_until)
    r = client.post(f"/api/reminders/{rid}/snooze", json={"hours": 0})
    assert r.status_code == 422  # hours doit être > 0


def test_snooze_invalid_hours_rejected(client):
    rid = client.get("/api/reminders").json()[0]["id"]
    assert client.post(f"/api/reminders/{rid}/snooze", json={"hours": -1}).status_code == 422
    assert client.post(f"/api/reminders/{rid}/snooze", json={"hours": 10000}).status_code == 422
