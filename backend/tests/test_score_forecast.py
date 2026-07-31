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
from app.ml.health_score import config as cfg
from app.ml.health_score import forecasting
from app.ml.health_score.forecast_features import build_dynamic_features, sources_used_by
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
@pytest.fixture(scope="module")
def trained():
    """Scores + artefacts entraînés une seule fois pour tout le module.

    L'entraînement enchaîne six ajustements XGBoost sur ~1 000 features : le refaire
    par test ferait passer la suite de quelques minutes à une dizaine.
    """
    scores = compute_health_scores(_synthetic_env(1200), _synthetic_scada(1200))
    return scores, forecasting.train(scores)


def test_training_selects_the_feature_count_that_wins_on_validation(trained):
    """Le nombre de features est choisi sur la validation, pas décidé d'avance."""
    _scores, artifacts = trained

    validation_maes = artifacts["metrics"]["validation_by_feature_count"]
    best = min(validation_maes, key=validation_maes.get)
    assert artifacts["feature_count"] == int(best)
    assert artifacts["selected_model"] == f"xgboost_top_{best}"
    assert len(artifacts["feature_columns"]) == artifacts["feature_count"]
    assert artifacts["residual_std"] > 0


def test_target_is_the_delta_so_persistence_is_delta_zero():
    """La cible apprise est la **variation** à 6 h : c'est ce qui permet de battre
    la persistance, qui n'est alors rien d'autre que « delta = 0 »."""
    scores = compute_health_scores(_synthetic_env(400), _synthetic_scada(400))
    frame = forecasting.build_forecast_features(scores)

    reconstructed = frame["overall_site_health"] + frame["target_health_change_6h"]
    pd.testing.assert_series_equal(
        reconstructed.dropna(), frame["target_health_6h"].dropna(),
        check_names=False, atol=1e-9, rtol=0,
    )


def test_dynamic_features_do_not_look_into_the_future():
    """Aucune feature dynamique ne doit dépendre d'une ligne future : sinon le
    modèle « prédit » en lisant la réponse, et la validation ne veut plus rien dire."""
    scores = compute_health_scores(_synthetic_env(400), _synthetic_scada(400))
    frame = forecasting.build_forecast_features(scores)
    full = build_dynamic_features(frame)

    cutoff = len(frame) - 30
    truncated = build_dynamic_features(frame.iloc[:cutoff])
    row = truncated.index[-1]

    common = [c for c in truncated.columns if c in full.columns]
    pd.testing.assert_series_equal(
        full.loc[row, common], truncated.loc[row, common], check_names=False, atol=1e-9, rtol=0,
    )


def test_prediction_only_needs_the_sources_its_features_use():
    """Au déroulé, seules les variables sources utiles au modèle sont dérivées —
    recalculer les ~1 200 features candidates à chaque pas serait du travail jeté."""
    selected = ["energy_risk_score_rollmax_6h", "battery_risk_score_lag_24h",
                "interaction_environmental_energy_risk"]
    assert sources_used_by(selected) == ["energy_risk_score", "battery_risk_score"]


def test_training_refuses_a_history_too_short_to_learn_from():
    scores = compute_health_scores(_synthetic_env(200), _synthetic_scada(200))
    with pytest.raises(ValueError, match="Historique insuffisant"):
        forecasting.train(scores)


def test_recursive_forecast_covers_the_horizon_with_a_widening_band(trained):
    scores, artifacts = trained
    trajectory = forecasting.forecast_recursive(scores, artifacts, hours=24)

    assert len(trajectory) == 4  # 24 h par pas de 6 h
    assert trajectory["timestamp"].iloc[0] > scores.index[-1]
    assert trajectory["value"].between(0, 100).all()
    widths = trajectory["upper"] - trajectory["lower"]
    assert widths.is_monotonic_increasing, "l'incertitude doit croître avec l'horizon"


def test_recursive_forecast_is_damped_and_cannot_run_away(trained):
    """Sans amortissement, le delta se compose pas après pas et la trajectoire
    finit par saturer à 0 ou 100 — « site parfait pendant un mois » est un pire
    mensonge qu'une droite plate."""
    scores, artifacts = trained
    trajectory = forecasting.forecast_recursive(scores, artifacts, hours=30 * 24)

    last_observed = float(scores["overall_site_health"].iloc[-1])
    first_step = abs(trajectory["value"].iloc[0] - last_observed)
    excursion = (trajectory["value"] - last_observed).abs().max()

    # Somme géométrique bornée : delta / (1 - amortissement), plus une marge.
    bound = first_step / (1 - cfg.RECURSIVE_DELTA_DAMPING) + 1.0
    assert excursion <= bound, f"excursion {excursion:.2f} > borne {bound:.2f}"
    assert trajectory["value"].max() < 100.0
    assert trajectory["value"].min() > 0.0
