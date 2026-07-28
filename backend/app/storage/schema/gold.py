"""Couche GOLD — le prêt-à-servir : ce que l'API renvoie.

« Le prêt-à-servir » : résultat métier calculé par l'ETL, lu directement par
l'API (aucun calcul sur le chemin de requête). Les colonnes miroitent les
modèles Pydantic existants (`AnomalyEpisode`, `SubScore`/`HealthOverview`,
`ForecastPoint`) — le mapping ligne → modèle est donc trivial.

Granularité de détection **par salle** (décidé) : `AnomalyEpisodeRow.equipment`
porte la salle (ex. `SALLE_SWITCH`), pas une unité STULZ individuelle.

⚠️ Les anomalies d'alarmes SCADA (`alarm_anomaly`, catégorie UPS/CLIM/ENERGY)
sont une **capacité nouvelle** de forme différente (pas de `peak_value`/`direction`
température) : leur table gold sera ajoutée avec l'ingestion des CSV SCADA. Cette
table-ci couvre les épisodes environnementaux (température/humidité).
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.schema import Base


class AnomalyEpisodeRow(Base):
    """Épisode d'anomalie environnemental — miroir de `models.anomalies.AnomalyEpisode`.

    `id` stable (ex. `EP-0001`) : les actions utilisateur (acquitter/résoudre)
    sont persistées par id dans l'état applicatif (`db/tables.AnomalyAction`) et
    surchargent le statut à la lecture.
    """

    __tablename__ = "anomaly_episode"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    equipment: Mapped[str] = mapped_column(String(48), index=True)  # salle (SALLE_SWITCH)
    type: Mapped[str] = mapped_column(String(16))       # collective | duration | sequence
    severity: Mapped[str] = mapped_column(String(16))   # alert | critical
    direction: Mapped[str] = mapped_column(String(8))   # high | low
    start: Mapped[datetime] = mapped_column(DateTime, index=True)
    duration_min: Mapped[float] = mapped_column(Float)
    peak_value: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16))     # statut calculé (avant surcharge)
    computed_at: Mapped[datetime] = mapped_column(DateTime)


class HealthScoreRow(Base):
    """Score de santé (global ou sous-score par famille) — miroir de `SubScore`.

    `scope='global'` → ligne du score global (family NULL) ; `scope='family'` →
    un sous-score par famille. `run_id` regroupe un même calcul.
    """

    __tablename__ = "health_score"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    scope: Mapped[str] = mapped_column(String(16))          # global | family
    family: Mapped[str | None] = mapped_column(String(16), nullable=True)
    label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16))         # healthy | watch | critical
    trend: Mapped[str] = mapped_column(String(8))           # up | stable | down
    unit_count: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(String(256), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime)


class ForecastPointRow(Base):
    """Point de forecast (historique ou prévision) — miroir de `ForecastPoint`.

    Une exécution de forecast = un `run_id` + un `horizon`.
    """

    __tablename__ = "forecast_point"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    horizon: Mapped[str] = mapped_column(String(8))        # 24h | 7d | 30d
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    value: Mapped[float] = mapped_column(Float)
    lower: Mapped[float] = mapped_column(Float)
    upper: Mapped[float] = mapped_column(Float)
    is_forecast: Mapped[bool] = mapped_column(Boolean, default=False)
