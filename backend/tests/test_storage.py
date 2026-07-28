"""Tests de fumée de la couche de stockage analytique (bronze/silver/gold).

Vérifie que les schémas se créent et qu'un aller-retour d'écriture/lecture
fonctionne, sur une base SQLite temporaire (indépendante du fichier réel).
"""
from datetime import datetime, timezone

from sqlalchemy import URL, create_engine, select
from sqlalchemy.orm import Session

from app.storage.schema import Base
from app.storage.schema.bronze import IngestWatermark, RawTempHumidity
from app.storage.schema.gold import AnomalyEpisodeRow, ForecastPointRow, HealthScoreRow
from app.storage.schema.silver import ThClean


def _engine(tmp_path):
    url = URL.create(drivername="sqlite", database=str(tmp_path / "analytics.db"))
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return engine


def test_all_layer_tables_created(tmp_path):
    engine = _engine(tmp_path)
    tables = set(Base.metadata.tables)
    assert {
        "raw_temp_humidity", "raw_scada_log", "ingest_watermark",  # bronze
        "th_clean", "scada_clean",                                  # silver
        "anomaly_episode", "health_score_hourly",                   # gold
        "health_score", "forecast_point",
    } <= tables
    # Les tables existent réellement dans le fichier
    from sqlalchemy import inspect
    assert set(inspect(engine).get_table_names()) >= tables


def test_bronze_roundtrip(tmp_path):
    engine = _engine(tmp_path)
    now = datetime(2026, 3, 24, 5, 54, 3)
    with Session(engine) as s:
        s.add(RawTempHumidity(ts=now, temperature=24.3, humidity=38.6,
                              ingested_at=datetime.now(timezone.utc), batch_id="b1"))
        s.commit()
    with Session(engine) as s:
        row = s.scalars(select(RawTempHumidity)).one()
        assert row.temperature == 24.3 and row.humidity == 38.6
        assert row.sensor == "SITE01_SALLE_SWITCH"  # défaut appliqué


def test_gold_episode_mirrors_pydantic(tmp_path):
    """La ligne gold porte tous les champs du modèle AnomalyEpisode (mapping trivial)."""
    from app.models.anomalies import AnomalyEpisode

    engine = _engine(tmp_path)
    start = datetime(2026, 7, 1, 10, 0, 0)
    with Session(engine) as s:
        s.add(AnomalyEpisodeRow(
            id="EP-0001", equipment="SALLE_SWITCH", type="duration", severity="critical",
            direction="high", start=start, duration_min=42.0, peak_value=30.8,
            status="open", computed_at=datetime.now(timezone.utc),
        ))
        s.commit()
    with Session(engine) as s:
        row = s.get(AnomalyEpisodeRow, "EP-0001")
        # reconstruction du modèle Pydantic depuis la ligne gold
        ep = AnomalyEpisode(
            id=row.id, equipment=row.equipment, type=row.type, severity=row.severity,
            direction=row.direction, start=row.start, duration_min=row.duration_min,
            peak_value=row.peak_value, status=row.status,
        )
        assert ep.equipment == "SALLE_SWITCH" and ep.peak_value == 30.8


def test_watermark_and_silver(tmp_path):
    engine = _engine(tmp_path)
    ts = datetime(2026, 3, 24, 6, 0, 0)
    with Session(engine) as s:
        s.add(ThClean(ts=ts, temperature=24.5, humidity=38.0, segment_id=1,
                      segment_position=0, computed_at=datetime.now(timezone.utc)))
        s.add(IngestWatermark(table_name="raw_temp_humidity", last_ts=ts,
                              updated_at=datetime.now(timezone.utc), rows_ingested=1))
        s.commit()
    with Session(engine) as s:
        assert s.get(ThClean, ts).segment_id == 1
        assert s.get(IngestWatermark, "raw_temp_humidity").rows_ingested == 1
