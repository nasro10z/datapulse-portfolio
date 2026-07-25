from app.models.health import ForecastResponse, HealthOverview


def test_overview_contract(client):
    r = client.get("/api/health/overview")
    assert r.status_code == 200
    overview = HealthOverview.model_validate(r.json())
    assert {s.family.value for s in overview.sub_scores} == {"stulz", "socomec", "yanan"}
    assert sum(s.unit_count for s in overview.sub_scores) == 14


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
