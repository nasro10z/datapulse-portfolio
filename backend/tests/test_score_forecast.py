"""Tests de l'ETL de scoring/prévision et de la source live santé.

Données synthétiques : on vérifie le **câblage** (silver → gold → API), pas les
maths — la fidélité du scoring aux résultats du notebook est couverte par
`test_health_score.py::test_scoring_reproduces_notebook_output`.
"""
import numpy as np
import pandas as pd
import pytest
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

from app.etl.score import build_snapshot_rows, score_site_health, status_for, trend_for
from app.etl.transform import transform_scada
from app.ml.health_score import forecasting
from app.ml.health_score.scoring import compute_health_scores
from app.models.health import HealthStatus, Trend
from app.storage.repositories import bronze_repo, gold_repo, silver_repo
from app.storage.schema import Base


def _session(tmp_path) -> Session:
    engine = create_engine(URL.create("sqlite", database=str(tmp_path / "analytics.db")))
    Base.metadata.create_all(engine)
    return Session(engine)


def _synthetic_env(hours: int = 400) -> pd.DataFrame:
    ts = pd.date_range("2026-01-01", periods=hours * 30, freq="2min")
    rng = np.random.default_rng(1)
    return pd.DataFrame({
        "ts": ts,
        "temperature": 24.5 + rng.normal(0, 0.1, len(ts)),
        "humidity": 46 + rng.normal(0, 0.3, len(ts)),
        "sensor": "TEST",
    })


def _synthetic_scada(hours: int = 400) -> pd.DataFrame:
    ts = pd.date_range("2026-01-01", periods=hours, freq="1h")
    return pd.DataFrame({
        "state": "A",
        "log_time": ts,
        "message": [
            r"\MSC-10\ UPS UNIT 1 GENERAL ALARM" if i % 4 == 0
            else (r"\MSC-10\ ABSENCE DE TENSION" if i % 11 == 0
                  else r"\MSC-10\ RECTIFIER FAULT")
            for i in range(hours)
        ],
        "send_time": ts,
    })


# ------------------------------------------------------------ bronze → silver
def test_transform_scada_dedupes_and_categorises(tmp_path):
    session = _session(tmp_path)
    raw = _synthetic_scada(50)
    duplicated = pd.concat([raw, raw.iloc[:10]], ignore_index=True)  # doublons exacts
    bronze_repo.replace_scada_log(session, duplicated)

    assert transform_scada(session) == 50, "les doublons (log_time, message) doivent tomber"

    silver = silver_repo.read_scada_clean(session)
    assert silver["category"].notna().all()
    assert set(silver["category"]) <= {"UPS", "CLIM", "ENERGY", "OTHER"}


# --------------------------------------------------------------- silver → gold
def test_score_site_health_writes_hourly_and_snapshot(tmp_path):
    session = _session(tmp_path)
    silver_repo.replace_th_clean(
        session,
        _synthetic_env().assign(segment_id=0, segment_position=0, is_discontinuity=False)
                        .set_index("ts"),
    )
    silver_repo.replace_scada_clean(session, _synthetic_scada())

    result = score_site_health(session)
    assert result["health_score_hourly"] > 300
    assert result["health_score"] == 4  # global + 3 domaines

    hourly = gold_repo.read_health_hourly(session)
    assert hourly["overall_site_health"].between(0, 100).all()
    assert hourly["recommended_action"].notna().all()

    latest = gold_repo.latest_health_hourly(session)
    assert latest.timestamp == hourly.index[-1]

    rows = gold_repo.read_health_scores(session)
    assert {r.scope for r in rows} == {"global", "family"}
    assert {r.family for r in rows if r.scope == "family"} == {"stulz", "socomec", "yanan"}


def test_score_site_health_refuses_empty_silver(tmp_path):
    session = _session(tmp_path)
    with pytest.raises(ValueError, match="Silver incomplet"):
        score_site_health(session)


def test_snapshot_status_matches_the_displayed_rounded_score(tmp_path):
    """Un score affiché « 90,0 » ne peut pas porter un statut « surveillance »."""
    scores = compute_health_scores(_synthetic_env(), _synthetic_scada())
    for row in build_snapshot_rows(scores):
        assert row["status"] == status_for(row["score"]).value


@pytest.mark.parametrize(
    ("change", "expected"),
    [(12.0, Trend.up), (-12.0, Trend.down), (1.0, Trend.stable), (None, Trend.stable)],
)
def test_trend_thresholds(change, expected):
    assert trend_for(change) is expected


def test_status_thresholds():
    assert status_for(95) is HealthStatus.healthy
    assert status_for(70) is HealthStatus.watch
    assert status_for(35) is HealthStatus.critical


# -------------------------------------------------------------------- prévision
def test_training_selects_the_best_candidate_on_validation():
    scores = compute_health_scores(_synthetic_env(1200), _synthetic_scada(1200))
    artifacts = forecasting.train(scores)

    assert artifacts["selected_model"] in {"persistence", "linear", "gradient_boosting"}
    validation_maes = {
        name: metrics["validation_MAE"]
        for name, metrics in artifacts["metrics"].items()
        if isinstance(metrics, dict) and "validation_MAE" in metrics
    }
    assert artifacts["selected_model"] == min(validation_maes, key=validation_maes.get)
    assert artifacts["residual_std"] > 0


def test_training_refuses_a_history_too_short_to_learn_from():
    scores = compute_health_scores(_synthetic_env(200), _synthetic_scada(200))
    with pytest.raises(ValueError, match="Historique insuffisant"):
        forecasting.train(scores)


def test_recursive_forecast_covers_the_horizon_with_a_widening_band():
    scores = compute_health_scores(_synthetic_env(1200), _synthetic_scada(1200))
    artifacts = forecasting.train(scores)
    trajectory = forecasting.forecast_recursive(scores, artifacts, hours=24)

    assert len(trajectory) == 4  # 24 h par pas de 6 h
    assert trajectory["timestamp"].iloc[0] > scores.index[-1]
    assert trajectory["value"].between(0, 100).all()
    widths = trajectory["upper"] - trajectory["lower"]
    assert widths.is_monotonic_increasing, "l'incertitude doit croître avec l'horizon"
