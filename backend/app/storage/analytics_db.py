"""Stockage analytique : SQLite local ou PostgreSQL pour le gold déployé.

Distincte de :
  - `db/engine.py` (base SOURCE PostgreSQL, non joignable — source réelle = CSV) ;
  - `db/app_db.py` (état applicatif : plannings de PM, actions utilisateur).

L'ETL écrit bronze/silver/gold dans SQLite. L'API peut lire les cinq tables gold
depuis PostgreSQL en déploiement. Comme ailleurs, les URL sont analysées par
SQLAlchemy, jamais assemblées par concaténation de chaînes.
"""
import os
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import URL, create_engine, event, make_url
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.storage.schema import Base
from app.storage.schema.gold import (
    AnomalyEpisodeRow,
    ForecastPointRow,
    GoldMetaRow,
    HealthScoreHourlyRow,
    HealthScoreRow,
)

_POSTGRES_ALIASES = {"postgres", "postgresql"}
_GOLD_TABLES = [
    AnomalyEpisodeRow.__table__,
    ForecastPointRow.__table__,
    GoldMetaRow.__table__,
    HealthScoreHourlyRow.__table__,
    HealthScoreRow.__table__,
]


def resolve_analytics_db_url() -> URL:
    """Resolve the optional PostgreSQL URL, otherwise use local SQLite."""
    raw = (settings.analytics_db_url or "").strip()
    if not raw:
        return URL.create(drivername="sqlite", database=str(settings.analytics_db_path))

    url = make_url(raw)
    if url.drivername in _POSTGRES_ALIASES:
        url = url.set(drivername="postgresql+psycopg2")
    if not url.drivername.startswith("postgresql"):
        raise ValueError("ANALYTICS_DB_URL must use PostgreSQL")
    return url


def is_analytics_postgres() -> bool:
    return resolve_analytics_db_url().drivername.startswith("postgresql")


def is_read_only() -> bool:
    """La base analytique est-elle en lecture seule ?

    Cas de l'hébergement serverless : le gold est embarqué dans le déploiement, sur
    un système de fichiers non inscriptible. SQLite doit alors être traité
    différemment — voir `get_analytics_engine`.
    """
    if is_analytics_postgres():
        return False

    path = settings.analytics_db_path
    return path.exists() and not os.access(path, os.W_OK)


@lru_cache(maxsize=1)
def get_analytics_engine() -> Engine:
    url = resolve_analytics_db_url()
    if url.drivername.startswith("postgresql"):
        return create_engine(
            url,
            poolclass=NullPool,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )

    path = settings.analytics_db_path
    read_only = is_read_only()

    if not read_only:
        path.parent.mkdir(parents=True, exist_ok=True)

    # check_same_thread=False : FastAPI sert les routes sync dans un threadpool.
    engine = create_engine(
        URL.create(drivername="sqlite", database=str(path)),
        connect_args={"check_same_thread": False},
    )

    if not read_only:
        # WAL : autorise la lecture concurrente (API) pendant l'écriture (ETL) sans
        # verrou global — indispensable puisque l'ETL et l'API partagent le fichier.
        #
        # Surtout PAS en lecture seule : passer une base en WAL est une écriture, et
        # même la lire ensuite suppose de créer des fichiers `-wal`/`-shm` à côté
        # d'elle. Sur un disque non inscriptible l'ouverture échoue avant la
        # première requête. L'export de déploiement est donc figé en journal
        # `DELETE` (cf. `etl/export_gold.py`), qui se lit sans rien écrire.
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _record):  # noqa: ANN001
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.close()

    return engine


@lru_cache(maxsize=1)
def get_analytics_sessionmaker() -> sessionmaker[Session]:
    # expire_on_commit=False : entités lisibles après commit (pas de SELECT de
    # relecture juste pour sérialiser une réponse).
    return sessionmaker(bind=get_analytics_engine(), expire_on_commit=False)


def init_analytics_db() -> None:
    """Crée les tables manquantes (bronze/silver/gold). Idempotent.

    Sans effet sur une base en lecture seule : elle arrive déjà peuplée par l'ETL,
    et tenter d'y écrire ferait échouer le démarrage de l'API.
    """
    if is_analytics_postgres():
        Base.metadata.create_all(get_analytics_engine(), tables=_GOLD_TABLES)
        return

    if is_read_only():
        return
    Base.metadata.create_all(get_analytics_engine())


def get_analytics_session() -> Iterator[Session]:
    """Dépendance FastAPI : une session analytique par requête (lecture gold)."""
    with get_analytics_sessionmaker()() as session:
        yield session
