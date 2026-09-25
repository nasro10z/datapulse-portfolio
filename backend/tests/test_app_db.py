"""Base applicative : résolution de l'URL, et aller-retour réel si PostgreSQL.

La bascule SQLite ↔ PostgreSQL est un **changement de configuration** : c'est la
propriété qui fait tenir le déploiement serverless, où l'état applicatif ne peut
pas vivre sur un disque local. Ces tests vérifient la résolution d'URL sans
qu'aucune base soit nécessaire ; le test d'intégration, lui, ne s'exécute que si
`TEST_APP_DB_URL` est fournie (base jetable, jamais la base de production).
"""
import os
from datetime import date

import pytest
from sqlalchemy import text

from app.config import settings
from app.db import app_db
from app.db.tables import Base, PMSchedule

INTEGRATION_URL = os.getenv("TEST_APP_DB_URL")


@pytest.fixture(autouse=True)
def _reset_engine_cache():
    """Les moteurs sont mémoïsés : sans purge, un test servirait celui d'un autre."""
    app_db.get_app_engine.cache_clear()
    app_db.get_sessionmaker.cache_clear()
    yield
    app_db.get_app_engine.cache_clear()
    app_db.get_sessionmaker.cache_clear()


def test_defaults_to_local_sqlite(monkeypatch):
    monkeypatch.setattr(settings, "app_db_url", None)
    url = app_db.resolve_app_db_url()
    assert url.drivername == "sqlite"
    assert url.database == str(settings.app_db_path)
    assert not app_db.is_postgres()


@pytest.mark.parametrize("scheme", ["postgresql", "postgres"])
def test_postgres_url_gets_an_explicit_driver(monkeypatch, scheme):
    """`postgres://` est encore émis par des hébergeurs ; SQLAlchemy le refuse."""
    monkeypatch.setattr(settings, "app_db_url",
                        f"{scheme}://user:secret@db.example.com/datapulse?sslmode=require")
    url = app_db.resolve_app_db_url()
    assert url.drivername == "postgresql+psycopg2"
    assert url.host == "db.example.com"
    assert url.database == "datapulse"
    # Les options de connexion (TLS notamment) doivent survivre à la normalisation.
    assert url.query.get("sslmode") == "require"
    assert app_db.is_postgres()


def test_explicit_driver_is_left_alone(monkeypatch):
    monkeypatch.setattr(settings, "app_db_url", "postgresql+psycopg://u:p@h/db")
    assert app_db.resolve_app_db_url().drivername == "postgresql+psycopg"


def test_credentials_never_leak_into_the_string_form(monkeypatch):
    """`repr()`/`str()` d'une URL masquent le mot de passe — une URL peut finir
    dans un log ou une trace d'erreur."""
    monkeypatch.setattr(settings, "app_db_url", "postgresql://user:s3cr3t@h/db")
    assert "s3cr3t" not in str(app_db.resolve_app_db_url())


def test_postgres_engine_is_built_without_a_pool(monkeypatch):
    """Serverless : un pool ne survit pas à l'invocation et retient des connexions
    côté hébergeur pour rien. Le moteur se construit sans se connecter."""
    monkeypatch.setattr(settings, "app_db_url", "postgresql://user:secret@db.example.com/dp")
    engine = app_db.get_app_engine()
    assert engine.pool.__class__.__name__ == "NullPool"


@pytest.mark.skipif(not INTEGRATION_URL, reason="TEST_APP_DB_URL non fournie")
def test_schedules_survive_on_postgres(monkeypatch):
    """Aller-retour réel : c'est ce que le déploiement doit garantir — une PM
    planifiée reste là après l'invocation qui l'a créée."""
    monkeypatch.setattr(settings, "app_db_url", INTEGRATION_URL)
    engine = app_db.get_app_engine()
    with engine.connect() as connection:
        assert connection.execute(text("select 1")).scalar() == 1

    Base.metadata.create_all(engine)
    try:
        with app_db.get_sessionmaker()() as session:
            session.add(PMSchedule(
                equipment="STULZ-01", last_pm_date=date(2026, 1, 1), period_value=90,
                period_unit="days", next_pm_date=date(2026, 4, 1), assigned_to="test",
            ))
            session.commit()

        # Nouvelle session = nouvelle connexion (NullPool) : la lecture prouve que
        # la donnée est côté serveur, pas dans un cache de processus.
        app_db.get_sessionmaker.cache_clear()
        with app_db.get_sessionmaker()() as session:
            rows = session.query(PMSchedule).filter_by(assigned_to="test").all()
            assert rows and rows[0].equipment == "STULZ-01"
    finally:
        with engine.begin() as connection:
            connection.execute(text("delete from pm_schedules where assigned_to = 'test'"))
