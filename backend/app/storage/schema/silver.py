"""Couche SILVER — données nettoyées et conformées.

« Le nettoyé » : sortie du préprocessing validé (package mlops-api) —
déduplication par timestamp, classification des gaps (>125 s = discontinuité),
segmentation en segments continus. Recalculable à 100 % depuis le bronze.

Note : les features glissantes (moyennes/écarts 12/36/78) ne sont PAS matérialisées
ici — le package mlops-api les recalcule en mémoire au moment de la détection
(`compute_rolling_features`, une seule source de vérité train/predict). Silver
porte donc les lectures propres + le rattachement au segment, ce qui suffit à
`etl/detect`. On pourra matérialiser les features plus tard si besoin de perf.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.schema import Base


class ThClean(Base):
    """Lecture température/humidité nettoyée et rattachée à un segment continu.

    Clé = `ts` (dédupliqué) : une lecture par timestamp après nettoyage.
    """

    __tablename__ = "th_clean"

    ts: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    segment_id: Mapped[int] = mapped_column(Integer, index=True)
    segment_position: Mapped[int] = mapped_column(Integer)
    is_discontinuity: Mapped[bool] = mapped_column(Boolean, default=False)
    sensor: Mapped[str] = mapped_column(String(48), default="SITE01_SALLE_SWITCH")
    computed_at: Mapped[datetime] = mapped_column(DateTime)
