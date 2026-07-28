"""Lecture des tables sources PostgreSQL (`datacenter_ops`).

⚠️ OBSOLÈTE / NON UTILISÉ : la base `datacenter_ops` n'est **pas joignable
directement** (plateforme isolée). La source réelle est constituée d'**exports
CSV** des tables, ingérés par `etl/ingest/` vers la couche bronze (voir
`docs/data-architecture.md`). Ce module est conservé au cas où un accès
SQLAlchemy deviendrait possible ; sinon il sera retiré.

Tables :
  - temp_humidity : ~107k lignes, capteur `SITE01_SALLE_SWITCH`
  - scada_logs    : événements SCADA
  - ups_events    : événements onduleurs SOCOMEC

Règle projet : URL via `URL.create()` (voir `engine.py`), jamais psycopg2 direct.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from app.db.engine import get_engine

SALLE_SWITCH_SENSOR = "SITE01_SALLE_SWITCH"


def read_temp_humidity(sensor: str = SALLE_SWITCH_SENSOR, since=None) -> pd.DataFrame:
    """Séries température/humidité pour un capteur, triées par timestamp.

    Colonnes à confirmer : `ts` (timestamp), `sensor`, `temperature`, `humidity`.
    """
    sql = text(
        "SELECT * FROM temp_humidity WHERE sensor = :sensor"
        + (" AND ts >= :since" if since is not None else "")
        + " ORDER BY ts"
    )
    params = {"sensor": sensor}
    if since is not None:
        params["since"] = since
    with get_engine().connect() as conn:
        return pd.read_sql(sql, conn, params=params)


def read_scada_logs(since=None) -> pd.DataFrame:
    """Logs SCADA (colonnes à confirmer). Sert au preprocessing (discontinuités
    secteur/communication)."""
    sql = text("SELECT * FROM scada_logs" + (" WHERE ts >= :since" if since is not None else "") + " ORDER BY ts")
    params = {"since": since} if since is not None else {}
    with get_engine().connect() as conn:
        return pd.read_sql(sql, conn, params=params)


def read_ups_events(since=None) -> pd.DataFrame:
    """Événements onduleurs SOCOMEC (colonnes à confirmer). Extension Phase 9."""
    sql = text("SELECT * FROM ups_events" + (" WHERE ts >= :since" if since is not None else "") + " ORDER BY ts")
    params = {"since": since} if since is not None else {}
    with get_engine().connect() as conn:
        return pd.read_sql(sql, conn, params=params)


__all__ = [
    "read_temp_humidity",
    "read_scada_logs",
    "read_ups_events",
    "SALLE_SWITCH_SENSOR",
]
