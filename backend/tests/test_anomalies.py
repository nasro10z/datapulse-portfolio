import pytest

from app.mocks.equipment import MILD_UPPER
from app.models.anomalies import AnomalyEpisode, AnomalyStats, HistogramResponse


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


@pytest.mark.parametrize("bucket", ["day", "week", "month"])
def test_histogram_contract(client, bucket):
    r = client.get("/api/anomalies/histogram", params={"bucket": bucket})
    assert r.status_code == 200
    hist = HistogramResponse.model_validate(r.json())
    assert hist.bucket.value == bucket
    assert hist.bins

    total = len(client.get("/api/anomalies").json())
    assert sum(b.total for b in hist.bins) == total
    assert all(b.total == b.alert + b.critical for b in hist.bins)
    # intervalles contigus et croissants, creux compris
    starts = [b.period_start for b in hist.bins]
    assert starts == sorted(starts)


def test_histogram_rejects_unknown_bucket(client):
    assert client.get("/api/anomalies/histogram", params={"bucket": "hour"}).status_code == 422


def test_update_status(client):
    episode = client.get("/api/anomalies").json()[0]
    original = episode["status"]
    try:
        r = client.patch(f"/api/anomalies/{episode['id']}", json={"status": "resolved"})
        assert r.status_code == 200
        assert AnomalyEpisode.model_validate(r.json()).status.value == "resolved"
        # la mise à jour est bien persistée côté API
        refetched = next(e for e in client.get("/api/anomalies").json() if e["id"] == episode["id"])
        assert refetched["status"] == "resolved"
    finally:
        client.patch(f"/api/anomalies/{episode['id']}", json={"status": original})


def test_update_status_errors(client):
    episode_id = client.get("/api/anomalies").json()[0]["id"]
    assert client.patch("/api/anomalies/EP-9999", json={"status": "resolved"}).status_code == 404
    assert client.patch(f"/api/anomalies/{episode_id}", json={"status": "nope"}).status_code == 422
