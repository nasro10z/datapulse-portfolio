from app.mocks.equipment import MILD_UPPER
from app.models.anomalies import AnomalyEpisode, AnomalyStats


def test_list_contract(client):
    r = client.get("/api/anomalies")
    assert r.status_code == 200
    episodes = [AnomalyEpisode.model_validate(e) for e in r.json()]
    assert 27 <= len(episodes) <= 36  # cohérent avec le pipeline validé
    highs = [e for e in episodes if e.direction.value == "high"]
    assert all(e.peak_value >= MILD_UPPER for e in highs)


def test_filter_by_equipment_and_severity(client):
    all_eps = client.get("/api/anomalies").json()
    equipment = all_eps[0]["equipment"]
    r = client.get("/api/anomalies", params={"equipment": equipment, "severity": "critical"})
    assert r.status_code == 200
    for e in r.json():
        assert e["equipment"] == equipment
        assert e["severity"] == "critical"


def test_filter_by_date_range(client):
    all_eps = client.get("/api/anomalies").json()
    pivot = all_eps[len(all_eps) // 2]["start"]
    r = client.get("/api/anomalies", params={"from": pivot})
    assert r.status_code == 200
    assert 0 < len(r.json()) < len(all_eps)
    assert all(e["start"] >= pivot for e in r.json())


def test_stats_contract(client):
    r = client.get("/api/anomalies/stats")
    assert r.status_code == 200
    stats = AnomalyStats.model_validate(r.json())
    total = client.get("/api/anomalies").json()
    assert stats.total == len(total)
    assert sum(stats.by_severity.values()) == stats.total
    assert sum(stats.by_type.values()) == stats.total
    assert stats.mtba_hours > 0
