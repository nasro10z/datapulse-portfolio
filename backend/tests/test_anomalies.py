from app.mocks.equipment import MILD_UPPER
from app.models.anomalies import AnomalyEpisode, AnomalyHistogram, AnomalyStats, WindowStats


def test_list_contract(client):
    r = client.get("/api/anomalies")
    assert r.status_code == 200
    episodes = [AnomalyEpisode.model_validate(e) for e in r.json()]
    assert 27 <= len(episodes) <= 36  # cohérent avec le pipeline validé
    highs = [e for e in episodes if e.direction.value == "high"]
    assert all(e.peak_value >= MILD_UPPER for e in highs)
    assert {e.dimension.value for e in episodes} <= {"environment", "scada"}


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
    assert sum(stats.by_status.values()) == stats.total
    assert stats.mtba_hours > 0


def test_histogram_buckets(client):
    for bucket in ("day", "week", "month"):
        r = client.get("/api/anomalies/histogram", params={"bucket": bucket})
        assert r.status_code == 200
        hist = AnomalyHistogram.model_validate(r.json())
        assert hist.bucket.value == bucket
        assert hist.bins
        # les bacs sont contigus et croissants
        starts = [b.period_start for b in hist.bins]
        assert starts == sorted(starts)
        # le total des comptes = nombre d'épisodes (rien perdu, rien dupliqué)
        assert sum(b.total for b in hist.bins) == len(client.get("/api/anomalies").json())
    # granularité plus fine ⇒ au moins autant de bacs
    day = AnomalyHistogram.model_validate(client.get("/api/anomalies/histogram", params={"bucket": "day"}).json())
    month = AnomalyHistogram.model_validate(client.get("/api/anomalies/histogram", params={"bucket": "month"}).json())
    assert len(day.bins) >= len(month.bins)


def test_acknowledge_persists_and_reflects_in_status(client):
    ep = client.get("/api/anomalies").json()[0]
    r = client.patch(f"/api/anomalies/{ep['id']}", json={"status": "acknowledged"})
    assert r.status_code == 200
    assert r.json()["status"] == "acknowledged"
    # relu depuis la base au fetch suivant
    listed = client.get("/api/anomalies").json()
    assert next(e for e in listed if e["id"] == ep["id"])["status"] == "acknowledged"
    # visible dans la répartition par statut
    stats = client.get("/api/anomalies/stats").json()
    assert stats["by_status"]["acknowledged"] >= 1


def test_patch_unknown_episode_404(client):
    r = client.patch("/api/anomalies/EP-9999", json={"status": "resolved"})
    assert r.status_code == 404


def test_acknowledging_open_anomaly_clears_its_reminder(client):
    # un épisode encore "open" (donc source d'un rappel non acquitté)
    open_ep = next(e for e in client.get("/api/anomalies").json() if e["status"] == "open")
    rid = f"RM-AN-{open_ep['id']}"
    before = {r["id"] for r in client.get("/api/reminders").json()}
    assert rid in before
    client.patch(f"/api/anomalies/{open_ep['id']}", json={"status": "acknowledged"})
    after = {r["id"] for r in client.get("/api/reminders").json()}
    assert rid not in after


def test_window_stats_contract(client):
    for window in ("24h", "7d"):
        r = client.get("/api/anomalies/window-stats", params={"window": window})
        assert r.status_code == 200
        ws = WindowStats.model_validate(r.json())
        assert ws.window.value == window
        assert ws.total >= 0
        assert sum(ws.by_dimension.values()) == ws.total
        assert ws.rate_pct >= 0
        if ws.total > 0:
            assert ws.top_family is not None
            assert ws.top_family_count > 0
        else:
            assert ws.top_family is None


def test_window_stats_7d_covers_at_least_as_much_as_24h(client):
    h24 = WindowStats.model_validate(client.get("/api/anomalies/window-stats", params={"window": "24h"}).json())
    d7 = WindowStats.model_validate(client.get("/api/anomalies/window-stats", params={"window": "7d"}).json())
    assert d7.total >= h24.total


def test_window_stats_invalid_window_rejected(client):
    r = client.get("/api/anomalies/window-stats", params={"window": "30d"})
    assert r.status_code == 422


def test_window_is_anchored_on_observed_data_not_on_the_clock():
    """La fenêtre se termine à la fin des données, pas à l'heure de la requête.

    Sur un export historique figé (données arrêtées il y a des semaines), une
    fenêtre calée sur l'horloge tombe entièrement après la dernière donnée et ne
    peut afficher que zéro — indiscernable d'un pipeline en panne.
    """
    from datetime import datetime, timedelta

    from app.models.anomalies import (
        AnomalyDimension, AnomalyEpisode, AnomalyStatus, AnomalyType, AnomalyWindow,
        Direction, Severity,
    )
    from app.services.anomaly_aggregation import compute_window_stats

    data_end = datetime(2026, 5, 18, 19, 0)
    episodes = [
        AnomalyEpisode(
            id=f"EP-{i:04d}", equipment="SALLE_SWITCH", type=AnomalyType.collective,
            severity=Severity.alert, direction=Direction.high,
            start=data_end - timedelta(hours=h), duration_min=30.0, peak_value=27.5,
            status=AnomalyStatus.open, dimension=AnomalyDimension.environment,
        )
        for i, h in enumerate([2, 10, 100], start=1)  # 2 dans les 24 h, 1 hors
    ]

    anchored = compute_window_stats(episodes, AnomalyWindow.h24, data_end)
    assert anchored.total == 2
    assert anchored.reference_at == data_end
    assert anchored.top_family is not None

    # La même fenêtre calée deux mois plus tard ne verrait plus rien.
    on_the_clock = compute_window_stats(episodes, AnomalyWindow.h24, data_end + timedelta(days=60))
    assert on_the_clock.total == 0
