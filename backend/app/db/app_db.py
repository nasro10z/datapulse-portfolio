"""Base applicative — état saisi par l'utilisateur (plannings de PM, acquittements).

Distincte de `engine.py`, qui ouvre la base source PostgreSQL `datacenter_ops`
en lecture. Comme pour la base source, l'URL est construite avec `URL.create()`
/ `make_url()` et jamais par concaténation de chaînes.

**Deux cibles, une seule différence de configuration** :

- par défaut, SQLite dans `backend/data/` — le développement local ne demande
  aucun service externe ;
- `APP_DB_URL` renseignée, PostgreSQL managé — le cas du déploiement. Un
  hébergement serverless n'a pas de disque persistant : une PM planifiée sur
  `/tmp` survit à la requête, pas au conteneur. Six routes d'écriture en
  dépendent, sur trois pages.

Les repositories et les services ne voient pas la différence : ils reçoivent une
`Session`, quel que soit le moteur derrière.
"""
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import URL, create_engine, make_url
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db.tables import Base

# `postgres://` est encore émis par plusieurs hébergeurs ; SQLAlchemy ne le
# reconnaît plus depuis la 1.4. On le normalise, avec le pilote déjà embarqué.
_POSTGRES_DRIVER = "postgresql+psycopg2"
_POSTGRES_ALIASES = {"postgres", "postgresql"}


def resolve_app_db_url() -> URL:
    """URL de la base applicative : PostgreSQL si configuré, SQLite sinon.

    Fonction pure (aucune connexion, aucun effet de bord) : c'est elle que testent
    les cas de normalisation, sans qu'une base soit nécessaire.
    """
    raw = (settings.app_db_url or "").strip()
    if not raw:
        return URL.create(drivername="sqlite", database=str(settings.app_db_path))

    url = make_url(raw)
    if url.drivername in _POSTGRES_ALIASES:
        url = url.set(drivername=_POSTGRES_DRIVER)
    return url


def is_postgres() -> bool:
    return resolve_app_db_url().drivername.startswith("postgresql")


@lru_cache(maxsize=1)
def get_app_engine() -> Engine:
    url = resolve_app_db_url()

    if url.drivername.startswith("sqlite"):
        settings.app_db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False : FastAPI exécute les routes sync dans un threadpool,
        # la connexion peut donc être servie à un thread différent de celui qui l'a ouverte.
        return create_engine(url, connect_args={"check_same_thread": False})

    # PostgreSQL managé, servi depuis une fonction serverless :
    #   - NullPool : un pool ne survit pas à l'invocation, et le garder ouvert
    #     consommerait des connexions côté hébergeur pour rien ;
    #   - pool_pre_ping : quand le conteneur *est* réutilisé, la connexion peut
    #     avoir été coupée entre-temps (les offres managées ferment les
    #     connexions inactives) — sans ce contrôle, la première requête échoue ;
    #   - connect_timeout : échouer vite plutôt que de tenir la requête ouverte
    #     jusqu'au délai maximum de la fonction.
    return create_engine(
        url, poolclass=NullPool, pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    # expire_on_commit=False : les entités restent lisibles après commit, ce qui
    # évite un SELECT de relecture juste pour sérialiser la réponse.
    return sessionmaker(bind=get_app_engine(), expire_on_commit=False)


def init_db() -> None:
    """Crée les tables manquantes. Idempotent.

    Appelé au démarrage de l'application, donc aussi à chaque démarrage à froid
    d'une fonction serverless : quelques requêtes sur le catalogue, rien de plus,
    puisque les tables existent déjà après la première.

        python -c "from app.db.app_db import init_db; init_db()"   # initialisation manuelle
    """
    Base.metadata.create_all(get_app_engine())


def get_session() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête."""
    with get_sessionmaker()() as session:
        yield session
