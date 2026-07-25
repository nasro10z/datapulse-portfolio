"""Connexion PostgreSQL via SQLAlchemy URL.create().

URL.create() échappe correctement les caractères spéciaux du mot de passe —
ne jamais construire l'URL par concaténation de chaînes ni utiliser psycopg2
en direct. Non branché sur les endpoints en Phase 1 (données mockées).
"""
from functools import lru_cache

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine

from app.config import settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=settings.db_user,
        password=settings.db_password,
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
    )
    return create_engine(url, pool_pre_ping=True)
