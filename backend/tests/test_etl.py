"""Tests de l'ETL : écriture bronze (repositories) + transform bronze→silver.

Données synthétiques (rapides) — la fidélité sur données réelles est couverte par
`test_ingestion_fidelity.py`.
"""
import pandas as pd
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

from app.etl.transform import transform_environmental
from app.storage.repositories import bronze_repo, silver_repo
from app.storage.schema import Base
from app.storage.schema.bronze import RawTempHumidity


def _session(tmp_path) -> Session:
    engine = create_engine(URL.create("sqlite", database=str(tmp_path / "analytics.db")))
    Base.metadata.create_all(engine)
    return Session(engine)


def test_bronze_backfill_is_idempotent_and_sets_watermark(tmp_path):
    session = _session(tmp_path)
    ts = pd.date_range("2026-03-24 00:00", periods=50, freq="2min")
    df = pd.DataFrame({"ts": ts, "temperature": 24.0, "humidity": 38.0, "sensor": "X"})

    assert bronze_repo.replace_temp_humidity(session, df) == 50
    assert bronze_repo.count(session, RawTempHumidity) == 50

    wm = bronze_repo.get_watermark(session, "raw_temp_humidity")
    assert wm.rows_ingested == 50
    assert wm.last_ts == ts[-1].to_pydatetime()

    # relancer le backfill ne double pas les lignes (remplacement idempotent)
    bronze_repo.replace_temp_humidity(session, df)
    assert bronze_repo.count(session, RawTempHumidity) == 50


def test_transform_env_bronze_to_silver_segments(tmp_path):
    session = _session(tmp_path)
    # deux blocs continus séparés par un trou > 125 s → deux segments
    ts = list(pd.date_range("2026-03-24 00:00", periods=20, freq="2min"))
    ts += list(pd.date_range("2026-03-24 02:00", periods=20, freq="2min"))
    df = pd.DataFrame({"ts": ts, "temperature": 24.0, "humidity": 38.0, "sensor": "X"})
    bronze_repo.replace_temp_humidity(session, df)

    n = transform_environmental(session)
    assert n == 40

    silver = silver_repo.read_th_clean(session)
    assert len(silver) == 40
    assert silver["segment_id"].nunique() >= 2          # le trou crée un nouveau segment
    assert bool(silver["is_discontinuity"].any())
