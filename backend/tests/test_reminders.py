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
