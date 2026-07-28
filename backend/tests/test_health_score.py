"""Tests du scoring de santé (`app/ml/health_score`).

Deux niveaux :
  - **unitaires** sur données synthétiques : les briques (poids, décroissance,
    persistance, calibration) font bien ce qu'elles annoncent ;
  - **golden** sur les fichiers de référence livrés : le portage reproduit à
    l'identique la sortie du notebook `health_scores.ipynb`. C'est le garde-fou
    contre une dérive silencieuse du portage — skippé si les données ne sont pas
    déposées (`app/ml/data/raw/`, gitignoré), jamais faux-positif.
"""
import numpy as np
import pandas as pd
import pytest

from app.etl.ingest.sources import DATA_RAW
from app.ml.health_score import config as cfg
from app.ml.health_score.features import (
    consecutive_run_length,
    decayed_sum,
    keyword_flag,
    pm_risk_from_last_pm,
    saturating_ratio,
)
from app.ml.health_score.scoring import compute_health_scores, validate_weights

REF = DATA_RAW / "reference"
TH_REF = REF / "temp_humid_last.csv"
SCADA_REF = REF / "msc10_combined_ups.csv"
SCORES_REF = REF / "site_health_scores_v1_0.csv"


# ------------------------------------------------------------------ unitaires
def test_validate_weights_accepts_shipped_configuration():
    assert validate_weights(cfg.WEIGHTS) is True


def test_validate_weights_rejects_group_not_summing_to_one():
    broken = {**cfg.WEIGHTS, "overall": {"environmental": 0.5, "energy": 0.5, "battery": 0.5}}
    with pytest.raises(ValueError, match="overall"):
        validate_weights(broken)


def test_decayed_sum_halves_after_one_halflife():
    s = pd.Series([1.0, 0.0, 0.0, 0.0])
    out = decayed_sum(s, halflife_hours=1)
    assert out.iloc[0] == pytest.approx(1.0)
    assert out.iloc[1] == pytest.approx(0.5)
    assert out.iloc[2] == pytest.approx(0.25)


def test_consecutive_run_length_resets_on_zero():
    s = pd.Series([1, 1, 1, 0, 1, 1])
    assert list(consecutive_run_length(s)) == [1, 2, 3, 0, 1, 2]


def test_saturating_ratio_stays_below_one_and_is_monotone():
    out = saturating_ratio(pd.Series([0.0, 1.0, 5.0, 50.0]), scale=6)
    assert out.iloc[0] == 0
    assert out.is_monotonic_increasing
    assert out.max() < 1.0


def test_pm_risk_grows_then_plateaus():
    index = pd.DatetimeIndex(["2026-01-01", "2026-02-15", "2026-06-01"])
    risk = pm_risk_from_last_pm(index, pd.Timestamp("2026-01-01"), interval_days=90)
    assert risk.iloc[0] == 0
    assert 0 < risk.iloc[1] < 1
    assert risk.iloc[2] == 1.0


def test_keyword_flag_respects_word_boundaries():
    messages = pd.Series([r"\MSC-10\ ATS TRANSFER", "STATS COLLECTION"])
    assert list(keyword_flag(messages, ["ats"])) == [1, 0]


def _synthetic_sources(hours: int = 240):
    """Une salle stable, un journal d'alarmes clairsemé — de quoi exercer la
    chaîne complète sans dépendre des données réelles."""
    ts = pd.date_range("2026-01-01", periods=hours * 30, freq="2min")
    rng = np.random.default_rng(0)
    env = pd.DataFrame({
        "ts": ts,
        "temperature": 24.5 + rng.normal(0, 0.1, len(ts)),
        "humidity": 46 + rng.normal(0, 0.3, len(ts)),
    })
    alarms = pd.date_range("2026-01-01", periods=hours, freq="1h")
    log = pd.DataFrame({
        "log_time": alarms,
        "state": "A",
        "message": [
            r"\MSC-10\ UPS UNIT 1 GENERAL ALARM" if i % 5 == 0
            else (r"\MSC-10\ ABSENCE DE TENSION" if i % 17 == 0
                  else r"\MSC-10\ RECTIFIER FAULT")
            for i in range(len(alarms))
        ],
        "category": "UPS",
    })
    return env, log


def test_compute_health_scores_produces_bounded_complete_scores():
    env, log = _synthetic_sources()
    scores = compute_health_scores(env, log)

    health_columns = ["environmental_health_score", "energy_health_score",
                      "battery_health_score", "overall_site_health"]
    assert not scores.empty
    assert scores[health_columns].notna().all().all(), "trous dans les scores"
    assert scores[health_columns].ge(0).all().all()
    assert scores[health_columns].le(100).all().all()
    assert set(scores["site_health_status"]).issubset(set(cfg.STATUS_LABELS))
    assert scores["main_risk_driver"].isin(
        ["None", "Environmental", "Energy", "Battery"]).all()
    assert scores["recommended_action"].notna().all()
    assert (scores["weight_version"] == cfg.WEIGHT_VERSION).all()


def test_compute_health_scores_requires_overlapping_period():
    env, log = _synthetic_sources()
    log["log_time"] = log["log_time"] + pd.Timedelta(days=365)
    with pytest.raises(ValueError, match="période commune"):
        compute_health_scores(env, log)


def test_implausible_humidity_is_treated_as_missing_not_as_a_reading():
    """Un repli capteur à 0 % ne doit pas être compté comme une mesure : sinon
    l'écart-type horaire explose et le terme de variabilité part avec lui."""
    env, log = _synthetic_sources()
    clean = compute_health_scores(env, log)["environmental_health_score"].mean()

    degraded = env.copy()
    degraded.loc[degraded.index % 500 == 0, "humidity"] = 0.0
    with_dropouts = compute_health_scores(degraded, log)["environmental_health_score"].mean()

    assert with_dropouts == pytest.approx(clean, abs=1.0)


# --------------------------------------------------------------------- golden
_have_reference = TH_REF.exists() and SCADA_REF.exists() and SCORES_REF.exists()


@pytest.mark.skipif(not _have_reference, reason="fichiers de référence du notebook absents")
def test_scoring_reproduces_notebook_output():
    """Sur les entrées livrées, le portage rend **exactement** les scores du
    notebook (`site_health_scores_v1_0.csv`).

    Toute divergence ici signifie que le portage a dérivé : c'est le test qui
    autorise à faire évoluer `ml/health_score` sans reperdre la validation faite
    par l'équipe data science.
    """
    env = pd.read_csv(TH_REF, parse_dates=["ts"])[["ts", "temperature", "humidity"]]
    log = pd.read_csv(SCADA_REF, parse_dates=["log_time"])
    reference = pd.read_csv(SCORES_REF, parse_dates=["timestamp"]).set_index("timestamp")

    scores = compute_health_scores(env, log)

    assert len(scores) == len(reference)
    assert scores.index.equals(reference.index)
    for column in ["environmental_health_score", "energy_health_score",
                   "battery_health_score", "overall_site_health"]:
        pd.testing.assert_series_equal(
            scores[column], reference[column],
            check_names=False, check_freq=False, atol=1e-6, rtol=0,
        )
