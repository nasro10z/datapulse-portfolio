"""La suite tourne sur une base SQLite jetable.

`APP_DB_PATH` doit être posée **avant** l'import de `app.config` : les settings
sont lues à l'import du module, pas à l'appel.
"""
import os
import shutil
import tempfile
from pathlib import Path

_TMP_DIR = Path(tempfile.mkdtemp(prefix="datapulse-tests-"))
os.environ["APP_DB_PATH"] = str(_TMP_DIR / "app.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from app.db.app_db import get_app_engine, get_sessionmaker  # noqa: E402
from app.db.tables import AnomalyAction  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    # le context manager déclenche le lifespan : création des tables + seed de démo
    with TestClient(app) as c:
        yield c
    # libère le fichier SQLite avant suppression (Windows verrouille les fichiers ouverts)
    get_app_engine().dispose()
    shutil.rmtree(_TMP_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_anomaly_actions():
    """La base est partagée sur la session : on efface les acquittements après
    chaque test pour qu'un test de mutation ne pollue pas les suivants."""
    yield
    with get_sessionmaker()() as s:
        s.execute(delete(AnomalyAction))
        s.commit()
