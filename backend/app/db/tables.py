"""Tables de l'état applicatif DataPulse.

Ces tables vivent dans la base SQLite locale (voir `app_db.py`), pas dans
`datacenter_ops` : elles portent ce que l'utilisateur saisit dans l'outil, ce
qui n'a rien à faire dans la base source du data center.
"""
from datetime import date, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PMSchedule(Base):
    """Maintenance préventive planifiée.

    `days_remaining` n'est pas stocké : il est recalculé à chaque lecture pour
    rester juste au fil des jours.
    """

    __tablename__ = "pm_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    equipment: Mapped[str] = mapped_column(String(64))
    last_pm_date: Mapped[date]
    period_value: Mapped[int]
    period_unit: Mapped[str] = mapped_column(String(16))
    next_pm_date: Mapped[date]
    assigned_to: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)


class AnomalyAction(Base):
    """Acquittement/résolution d'un épisode d'anomalie par l'utilisateur.

    Les épisodes eux-mêmes viennent du pipeline (mockés en attendant) et restent
    en lecture seule ; seul le statut décidé par l'utilisateur est stocké ici,
    et vient surcharger le statut simulé au moment de la lecture. Clé = id de
    l'épisode (`EP-0001`), stable d'un redémarrage à l'autre.
    """

    __tablename__ = "anomaly_actions"

    episode_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    status: Mapped[str] = mapped_column(String(16))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReminderAction(Base):
    """Snooze / acquittement d'un rappel par l'utilisateur.

    Les rappels sont *dérivés* (PM à venir, seuils, anomalies non acquittées) et
    non stockés ; on ne persiste ici que l'action de l'utilisateur, qui vient
    filtrer la liste dérivée à la lecture. Clé = id du rappel (`RM-AN-EP-0003`,
    `RM-PM-PM-0004`, `RM-TH-0001`), stable car adossé à un id sous-jacent stable.
    Un rappel acquitté est masqué ; un rappel snoozé est masqué jusqu'à
    `snoozed_until`.
    """

    __tablename__ = "reminder_actions"

    reminder_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    acknowledged: Mapped[bool] = mapped_column(default=False)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
