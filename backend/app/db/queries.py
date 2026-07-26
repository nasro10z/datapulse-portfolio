"""Lecture des tables sources PostgreSQL (`datacenter_ops`) — entrée du pipeline ML.

⚠️ NON TESTÉ : écrit sans accès à la base réelle. Les noms de colonnes sont à
CONFIRMER contre le schéma réel avant usage (marqués « à confirmer »). Ces
fonctions renvoient des DataFrames pandas, consommés par le pipeline validé une
fois branché (`app/ml/`). Elles ne sont appelées que si `DATA_SOURCE=live`.

Tables (cf. CLAUDE.md) :
  - temp_humidity : ~107k lignes, capteurs `SITE01_SALLE_SWITCH`
  - scada_logs    : événements SCADA (dont `scenario_6_label` pour la validation)
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
    secteur/communication) et porte `scenario_6_label` pour la validation finale."""
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


def read_scenario_6_labels() -> pd.DataFrame:
    """Ground-truth `scenario_6_label` depuis SCADA, pour la validation finale
    (Phase 8). Colonnes à confirmer : `ts`, `scenario_6_label`."""
    sql = text("SELECT ts, scenario_6_label FROM scada_logs WHERE scenario_6_label IS NOT NULL ORDER BY ts")
    with get_engine().connect() as conn:
        return pd.read_sql(sql, conn)


__all__ = [
    "read_temp_humidity",
    "read_scada_logs",
    "read_ups_events",
    "read_scenario_6_labels",
    "SALLE_SWITCH_SENSOR",
]
