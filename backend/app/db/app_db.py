"""Base applicative SQLite — état saisi par l'utilisateur (plannings de PM).

Distincte de `engine.py`, qui ouvre la base source PostgreSQL
`datacenter_ops` en lecture. Comme pour la base source, l'URL est construite
avec `URL.create()` et jamais par concaténation de chaînes.
"""
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.tables import Base


@lru_cache(maxsize=1)
def get_app_engine() -> Engine:
    settings.app_db_path.parent.mkdir(parents=True, exist_ok=True)
    url = URL.create(drivername="sqlite", database=str(settings.app_db_path))
    # check_same_thread=False : FastAPI exécute les routes sync dans un threadpool,
    # la connexion peut donc être servie à un thread différent de celui qui l'a ouverte.
    return create_engine(url, connect_args={"check_same_thread": False})


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    # expire_on_commit=False : les entités restent lisibles après commit, ce qui
    # évite un SELECT de relecture juste pour sérialiser la réponse.
    return sessionmaker(bind=get_app_engine(), expire_on_commit=False)


def init_db() -> None:
    """Crée les tables manquantes. Idempotent."""
    Base.metadata.create_all(get_app_engine())


def get_session() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête."""
    with get_sessionmaker()() as session:
        yield session
