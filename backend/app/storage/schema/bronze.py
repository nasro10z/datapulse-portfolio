"""Couche BRONZE — copie brute, append-only, de la source.

« Le brut » : on ne nettoie rien ici (doublons, trous, valeurs de repli inclus).
Les données arrivent en **exports CSV** (PostgreSQL non joignable) et sont
ingérées telles quelles par `etl/ingest`. Chaque ligne porte `ingested_at` et
`batch_id` pour la traçabilité et l'idempotence de l'ingestion.

Tables :
  - `raw_temp_humidity` : lectures capteur salle switch (temp/humidité).
  - `raw_scada_log`     : lignes de log d'alarmes SCADA (schéma indicatif — à
                          ajuster aux CSV SCADA une fois fournis).

`raw_ups_event` sera ajouté à l'ingestion des événements onduleurs (Phase 9).
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.schema import Base


class RawTempHumidity(Base):
    """Lecture brute température/humidité (mirroir de `temp_humid_last`).

    Append-only : aucune contrainte d'unicité sur `ts` (le brut contient des
    doublons de timestamp — la déduplication a lieu en silver, pas ici).
    """

    __tablename__ = "raw_temp_humidity"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    sensor: Mapped[str] = mapped_column(String(48), default="SITE01_SALLE_SWITCH")
    # Traçabilité de l'ingestion
    ingested_at: Mapped[datetime] = mapped_column(DateTime)
    batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class RawScadaLog(Base):
    """Ligne de log d'alarme SCADA brute (schéma indicatif).

    Colonnes alignées sur les loaders du package mlops-api
    (`state`, `log_time`, `message`, `send_time`) — à confirmer/ajuster contre
    les CSV SCADA une fois fournis.
    """

    __tablename__ = "raw_scada_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    log_time: Mapped[datetime | None] = mapped_column(DateTime, index=True, nullable=True)
    send_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    state: Mapped[str | None] = mapped_column(String(8), nullable=True)  # 'A' active / 'D' cleared
    message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime)
    batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class IngestWatermark(Base):
    """Dernier `ts` ingéré par table source — support de l'ingestion incrémentale.

    Une ligne par table bronze : l'ingestion incrémentale lit la source au-delà
    de `last_ts` puis met à jour ce repère (idempotence côté ingestion).
    """

    __tablename__ = "ingest_watermark"

    table_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_ts: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    rows_ingested: Mapped[int] = mapped_column(Integer, default=0)
