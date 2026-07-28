"""Tests de la détection (étape E) : filtre de franchissement de seuil + gold_repo.

La caractérisation `_characterize` est testée sur des runs synthétiques (sans HMM) ;
le round-trip gold via `gold_repo`. La détection HMM complète est validée par
l'exécution réelle sur le silver (non rejouée en test unitaire, coûteuse).
"""
from datetime import datetime

import pandas as pd
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

from app.etl.detect import _characterize
from app.models.anomalies import AnomalyEpisode
from app.storage.repositories import gold_repo
from app.storage.schema import Base

TEMP_THR = {"mild_lower": 22.95, "mild_upper": 26.75, "extreme_lower": 21.05, "extreme_upper": 28.65}


def _run(temps: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2026-03-09 10:00", periods=len(temps), freq="2min")
    return pd.DataFrame({"temperature": temps, "humidity": 40.0}, index=idx)


def test_characterize_high_critical():
    c = _characterize(_run([26.0, 27.5, 29.0]), TEMP_THR)   # franchit mild puis extreme
    assert c is not None
    assert c["direction"].value == "high" and c["severity"].value == "critical" and c["peak"] == 29.0


def test_characterize_low_alert():
    c = _characterize(_run([23.5, 22.0, 22.5]), TEMP_THR)   # franchit mild_lower, pas extreme
    assert c["direction"].value == "low" and c["severity"].value == "alert" and c["peak"] == 22.0


def test_characterize_normal_temperature_is_dropped():
    # jamais de franchissement → anomalie humidité/contextuelle non surfacée
    assert _characterize(_run([24.0, 25.0, 25.7]), TEMP_THR) is None


def test_gold_repo_roundtrip(tmp_path):
    engine = create_engine(URL.create("sqlite", database=str(tmp_path / "a.db")))
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        eps = [AnomalyEpisode(
            id="EP-0001", equipment="SALLE_SWITCH", type="collective", severity="critical",
            direction="high", start=datetime(2026, 3, 9, 10, 0), duration_min=42.0,
            peak_value=29.5, status="resolved",
        )]
        assert gold_repo.replace_episodes(session, eps) == 1
        back = gold_repo.read_episodes(session)
        assert len(back) == 1
        assert back[0].equipment == "SALLE_SWITCH" and back[0].severity.value == "critical"
