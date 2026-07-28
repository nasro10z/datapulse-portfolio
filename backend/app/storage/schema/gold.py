"""Couche GOLD — le prêt-à-servir : ce que l'API renvoie.

« Le prêt-à-servir » : résultat métier calculé par l'ETL, lu directement par
l'API (aucun calcul sur le chemin de requête). Les colonnes miroitent les
modèles Pydantic existants (`AnomalyEpisode`, `SubScore`/`HealthOverview`,
`ForecastPoint`) — le mapping ligne → modèle est donc trivial.

Granularité de détection **par salle** (décidé) : `AnomalyEpisodeRow.equipment`
porte la salle (ex. `SALLE_SWITCH`), pas une unité STULZ individuelle.

Tables :
  - `anomaly_episode`     : épisodes d'anomalie environnementaux (HMM) ;
  - `health_score_hourly` : score de santé du site heure par heure (notebook
                            `health_scores.ipynb`) — base de l'aperçu, de la page
                            Santé du site et de l'entraînement de la prévision ;
  - `health_score`        : instantané servi à l'API (global + sous-scores) ;
  - `forecast_point`      : trajectoire prévue par horizon.

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
    # environment | scada — cette table ne couvre que l'environnemental à ce
    # jour (cf. docstring module) ; défaut cohérent avec la seule source branchée.
    dimension: Mapped[str] = mapped_column(String(16), default="environment")
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


class HealthScoreHourlyRow(Base):
    """Score de santé horaire du site — équivalent servi du `site_health_scores.csv`
    produit par le notebook `health_scores.ipynb`.

    C'est la table de base de tout ce que l'interface montre côté santé : le score
    global et ses trois domaines heure par heure, plus la lecture opérationnelle
    (domaine dominant, statut, priorité, action conseillée). Seules les colonnes
    réellement servies ou nécessaires à la prévision sont matérialisées — la table
    du notebook en compte ~75, dont beaucoup d'intermédiaires recalculables.

    `weight_version` / `score_version` accompagnent chaque ligne : un score servi
    reste traçable jusqu'à la configuration de poids qui l'a produit.
    """

    __tablename__ = "health_score_hourly"

    timestamp: Mapped[datetime] = mapped_column(DateTime, primary_key=True)

    # Scores 0-100 (santé) par domaine + global
    environmental_health_score: Mapped[float] = mapped_column(Float)
    energy_health_score: Mapped[float] = mapped_column(Float)
    battery_health_score: Mapped[float] = mapped_column(Float)
    overall_site_health: Mapped[float] = mapped_column(Float)
    overall_site_health_smoothed: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Risques (0-100) — utiles à la prévision et à l'explication d'un score
    environmental_risk_score: Mapped[float] = mapped_column(Float)
    energy_risk_score: Mapped[float] = mapped_column(Float)
    battery_risk_score: Mapped[float] = mapped_column(Float)
    environmental_base_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_base_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_base_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    environmental_pm_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_pm_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_pm_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    environmental_anomaly_burden: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_anomaly_burden: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_anomaly_burden: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Tendance / volatilité
    overall_site_health_trend_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_site_health_volatility_24h: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Lecture opérationnelle
    main_risk_driver: Mapped[str | None] = mapped_column(String(16), nullable=True)
    main_driver_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    site_health_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    health_trend_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    maintenance_priority: Mapped[str | None] = mapped_column(String(24), nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Contexte physique + fiabilité de l'heure
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    outage_duration_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_alarm_duration_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    observation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    weight_version: Mapped[str] = mapped_column(String(16))
    score_version: Mapped[str] = mapped_column(String(32))
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
