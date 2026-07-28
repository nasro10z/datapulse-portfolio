"""Couche SILVER — données nettoyées et conformées.

« Le nettoyé » : sortie du préprocessing validé (package mlops-api) —
déduplication par timestamp, classification des gaps (>125 s = discontinuité),
segmentation en segments continus. Recalculable à 100 % depuis le bronze.

Note : les features glissantes (moyennes/écarts 12/36/78) ne sont PAS matérialisées
ici — le package mlops-api les recalcule en mémoire au moment de la détection
(`compute_rolling_features`, une seule source de vérité train/predict). Silver
porte donc les lectures propres + le rattachement au segment, ce qui suffit à
`etl/detect`. On pourra matérialiser les features plus tard si besoin de perf.

Tables :
  - `th_clean`    : lectures température/humidité dédupliquées + segmentées ;
  - `scada_clean` : journal d'alarmes SCADA + UPS dédupliqué et catégorisé —
                    équivalent du fichier `msc10_combined_ups.csv` utilisé par le
                    notebook de scoring, produit ici par LEUR `clean_and_dedupe`.
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


class ScadaClean(Base):
    """Ligne de journal SCADA/UPS nettoyée, dédupliquée et catégorisée.

    Sortie de `ml.alarm_anomaly.data_loading.clean_and_dedupe` (dédup sur
    `(log_time, message)`, tri chronologique, catégorie déduite du message) : c'est
    l'entrée du scoring énergie/batterie, qui compte les alarmes par heure.

    Pas de clé naturelle utilisable : deux alarmes distinctes peuvent partager la
    seconde. La clé est donc technique, la table étant remplacée en bloc à chaque
    exécution de l'ETL.
    """

    __tablename__ = "scada_clean"

    id: Mapped[int] = mapped_column(primary_key=True)
    log_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    send_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    state: Mapped[str | None] = mapped_column(String(8), nullable=True)   # A active / D cleared
    message: Mapped[str] = mapped_column(String(512))
    category: Mapped[str | None] = mapped_column(String(16), nullable=True)  # UPS | CLIM | ENERGY | OTHER
    computed_at: Mapped[datetime] = mapped_column(DateTime)
