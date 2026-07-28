from app.models.health import (
    ForecastResponse,
    HealthHistoryResponse,
    HealthOverview,
    HealthStatus,
    PredictedFaultsResponse,
    SubScoreForecastResponse,
)


def test_overview_contract(client):
    r = client.get("/api/health/overview")
    assert r.status_code == 200
    overview = HealthOverview.model_validate(r.json())
    assert {s.family.value for s in overview.sub_scores} == {"stulz", "socomec", "yanan"}
    assert sum(s.unit_count for s in overview.sub_scores) == 14


def test_overview_domain_scores(client):
    overview = HealthOverview.model_validate(client.get("/api/health/overview").json())
    assert {d.domain.value for d in overview.domain_scores} == {"environment", "energy", "battery"}
    for d in overview.domain_scores:
        expected = HealthStatus.healthy if d.score >= 82 else HealthStatus.watch if d.score >= 68 else HealthStatus.critical
        assert d.status == expected
    expected_global_status = (
        HealthStatus.healthy if overview.global_score >= 82
        else HealthStatus.watch if overview.global_score >= 68
        else HealthStatus.critical
    )
    assert overview.status == expected_global_status


def test_history_all_ranges(client):
    expected_points = {"7d": 7, "30d": 30, "90d": 90}
    for r, n in expected_points.items():
        resp = client.get("/api/health/history", params={"range": r})
        assert resp.status_code == 200
        history = HealthHistoryResponse.model_validate(resp.json())
        assert history.range.value == r
        assert len(history.points) == n
        for p in history.points:
            assert 0 <= p.global_score <= 100
        overview = HealthOverview.model_validate(client.get("/api/health/overview").json())
        assert history.points[-1].environment == next(
            d.score for d in overview.domain_scores if d.domain.value == "environment"
        )


def test_history_invalid_range_rejected(client):
    r = client.get("/api/health/history", params={"range": "12h"})
    assert r.status_code == 422


def test_forecast_all_horizons(client):
    for horizon in ("24h", "7d", "30d"):
        r = client.get("/api/health/forecast", params={"horizon": horizon})
        assert r.status_code == 200
        fc = ForecastResponse.model_validate(r.json())
        assert fc.horizon.value == horizon
        assert any(p.is_forecast for p in fc.points)
        assert any(not p.is_forecast for p in fc.points)
        for p in fc.points:
            assert p.lower <= p.value <= p.upper


def test_forecast_band_widens_over_horizon(client):
    fc = ForecastResponse.model_validate(
        client.get("/api/health/forecast", params={"horizon": "24h"}).json()
    )
    fcst = [p for p in fc.points if p.is_forecast]
    assert (fcst[-1].upper - fcst[-1].lower) > (fcst[0].upper - fcst[0].lower)


def test_forecast_invalid_horizon_rejected(client):
    r = client.get("/api/health/forecast", params={"horizon": "12h"})
    assert r.status_code == 422


def test_predicted_faults_all_horizons(client):
    for horizon in ("24h", "7d", "30d"):
        r = client.get("/api/health/predicted-faults", params={"horizon": horizon})
        assert r.status_code == 200
        faults = PredictedFaultsResponse.model_validate(r.json())
        assert faults.horizon.value == horizon
        assert {f.family.value for f in faults.faults} == {"stulz", "socomec", "yanan"}
        for f in faults.faults:
            # sévérité et timing sont tous les deux présents ou tous les deux absents
            assert (f.predicted_at is None) == (f.severity is None)


def test_predicted_faults_stulz_matches_forecast_crossings(client):
    fc = ForecastResponse.model_validate(
        client.get("/api/health/forecast", params={"horizon": "24h"}).json()
    )
    faults = PredictedFaultsResponse.model_validate(
        client.get("/api/health/predicted-faults", params={"horizon": "24h"}).json()
    )
    stulz = next(f for f in faults.faults if f.family.value == "stulz")
    if fc.threshold_crossings:
        assert stulz.predicted_at == fc.threshold_crossings[0].timestamp
    else:
        assert stulz.predicted_at is None


def test_subscore_forecast_all_horizons(client):
    expected_points = {"24h": 24 + 24 + 1, "7d": 28 + 28 + 1, "30d": 30 + 30 + 1}
    for horizon, n in expected_points.items():
        r = client.get("/api/health/forecast/sub-scores", params={"horizon": horizon})
        assert r.status_code == 200
        fc = SubScoreForecastResponse.model_validate(r.json())
        assert fc.horizon.value == horizon
        assert {s.family.value for s in fc.series} == {"stulz", "socomec", "yanan"}
        for s in fc.series:
            assert len(s.points) == n
            assert any(p.is_forecast for p in s.points)
            assert any(not p.is_forecast for p in s.points)
            for p in s.points:
                assert p.lower <= p.value <= p.upper
                assert 0 <= p.value <= 100
