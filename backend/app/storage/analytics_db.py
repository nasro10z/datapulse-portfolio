"""Base analytique SQLite — couches bronze/silver/gold du pipeline de données.

Distincte de :
  - `db/engine.py` (base SOURCE PostgreSQL, non joignable — source réelle = CSV) ;
  - `db/app_db.py` (état applicatif : plannings de PM, actions utilisateur).

Séparer physiquement ce fichier garantit un **écrivain unique par base** :
l'ETL écrit ici (bronze/silver/gold), l'API n'y fait que des lectures (gold).
Comme ailleurs, l'URL est construite avec `URL.create()`, jamais par
concaténation de chaînes.
"""
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import URL, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.storage.schema import Base


@lru_cache(maxsize=1)
def get_analytics_engine() -> Engine:
    settings.analytics_db_path.parent.mkdir(parents=True, exist_ok=True)
    url = URL.create(drivername="sqlite", database=str(settings.analytics_db_path))
    # check_same_thread=False : FastAPI sert les routes sync dans un threadpool.
    engine = create_engine(url, connect_args={"check_same_thread": False})

    # WAL : autorise la lecture concurrente (API) pendant l'écriture (ETL) sans
    # verrou global — indispensable puisque l'ETL et l'API partagent le fichier.
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
    """Crée les tables manquantes (bronze/silver/gold). Idempotent."""
    Base.metadata.create_all(get_analytics_engine())


def get_analytics_session() -> Iterator[Session]:
    """Dépendance FastAPI : une session analytique par requête (lecture gold)."""
    with get_analytics_sessionmaker()() as session:
        yield session
