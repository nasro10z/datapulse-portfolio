"""Tests de fumée de la couche de stockage analytique (bronze/silver/gold).

Vérifie que les schémas se créent et qu'un aller-retour d'écriture/lecture
fonctionne, sur une base SQLite temporaire (indépendante du fichier réel).
"""
from datetime import datetime, timezone

import pytest
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


def test_analytics_defaults_to_local_sqlite(monkeypatch, tmp_path):
    from app.config import settings
    from app.storage import analytics_db

    monkeypatch.setattr(settings, "analytics_db_url", None)
    monkeypatch.setattr(settings, "analytics_db_path", tmp_path / "analytics.db")
    analytics_db.get_analytics_engine.cache_clear()
    try:
        engine = analytics_db.get_analytics_engine()
        assert engine.dialect.name == "sqlite"
        assert engine.url.database == str(tmp_path / "analytics.db")
    finally:
        analytics_db.get_analytics_engine().dispose()
        analytics_db.get_analytics_engine.cache_clear()
        analytics_db.get_analytics_sessionmaker.cache_clear()


@pytest.mark.parametrize("scheme", ["postgresql", "postgres"])
def test_analytics_postgres_url_uses_serverless_pool(monkeypatch, scheme):
    from app.config import settings
    from app.storage import analytics_db

    monkeypatch.setattr(
        settings,
        "analytics_db_url",
        f"{scheme}://user:secret@db.example.com/datapulse?sslmode=require",
    )
    analytics_db.get_analytics_engine.cache_clear()
    try:
        url = analytics_db.resolve_analytics_db_url()
        assert url.drivername == "postgresql+psycopg2"
        assert url.host == "db.example.com"
        assert url.query.get("sslmode") == "require"
        assert analytics_db.get_analytics_engine().pool.__class__.__name__ == "NullPool"
    finally:
        analytics_db.get_analytics_engine.cache_clear()
        analytics_db.get_analytics_sessionmaker.cache_clear()


def test_versioned_gold_export_is_not_in_wal_mode():
    """L'export gold versionné doit rester en journal `DELETE`.

    Piège vécu : lancer l'API en local en la pointant sur cet export le repasse en
    WAL (le fichier est inscriptible sur un poste de dev, donc le pragma
    s'applique). Or une base en WAL a besoin de créer ses fichiers `-wal`/`-shm`
    à l'ouverture — impossible sur le disque en lecture seule du déploiement, où
    elle devient illisible **même en lecture**. Cette bascule ne se voit pas dans
    un diff : le fichier est binaire, et tout marche encore en local.

    Réparer : `python -m app.etl.export_gold`.
    """
    import sqlite3

    from app.config import BACKEND_ROOT

    # Emplacement canonique du fichier versionné, pas `settings.analytics_db_path` :
    # la conftest redirige les settings vers un dossier temporaire, et le test se
    # skipperait silencieusement — sans jamais regarder le fichier qu'on expédie.
    export = BACKEND_ROOT / "data" / "datapulse_gold.db"
    if not export.exists():
        pytest.skip("export gold absent (généré par `python -m app.etl.export_gold`)")

    connection = sqlite3.connect(export)
    try:
        mode = connection.execute("pragma journal_mode").fetchone()[0]
    finally:
        connection.close()

    assert mode.lower() != "wal", (
        f"{export.name} est en journal '{mode}' : il sera illisible en déploiement "
        "lecture seule. Relancer `python -m app.etl.export_gold`."
    )


def test_read_only_analytics_db_is_served_without_writing_to_it(tmp_path, monkeypatch):
    """Déploiement serverless : le gold est embarqué sur un disque non inscriptible.

    Deux pièges, tous deux fatals au démarrage s'ils ne sont pas traités : passer la
    base en WAL est une écriture, et `create_all` en est une autre. On vérifie ici
    qu'une base en lecture seule se lit sans qu'on tente ni l'une ni l'autre.
    """
    import os
    import stat

    from sqlalchemy import text

    from app.config import settings
    from app.storage import analytics_db

    path = tmp_path / "gold.db"
    engine = create_engine(URL.create("sqlite", database=str(path)))
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("pragma journal_mode=DELETE"))  # comme l'export de déploiement
    engine.dispose()
    os.chmod(path, stat.S_IREAD)

    monkeypatch.setattr(settings, "analytics_db_path", path)
    monkeypatch.setattr(settings, "analytics_db_url", None)
    analytics_db.get_analytics_engine.cache_clear()
    analytics_db.get_analytics_sessionmaker.cache_clear()
    try:
        assert analytics_db.is_read_only() is True
        analytics_db.init_analytics_db()  # doit être un no-op, pas une erreur
        with analytics_db.get_analytics_sessionmaker()() as session:
            assert session.execute(text("select count(*) from health_score_hourly")).scalar() == 0
            assert session.execute(text("pragma journal_mode")).scalar() != "wal"
    finally:
        analytics_db.get_analytics_engine().dispose()
        analytics_db.get_analytics_engine.cache_clear()
        analytics_db.get_analytics_sessionmaker.cache_clear()
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)


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
