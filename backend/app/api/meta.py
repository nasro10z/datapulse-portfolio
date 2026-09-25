"""Configuration servie au frontend — ce que l'interface doit savoir de l'instance.

Une même application sert deux contextes très différents : un poste de développement
(données mockées ou pipeline complet, écriture libre) et une **démo publique**
(instantané recalé, plannings en lecture seule). L'interface ne peut pas le deviner :
elle le demande ici.

Volontairement minimal et **sans secret** : la source des données, et le fait que les
plannings soient figés. Rien sur la base, l'hébergement ou les identifiants.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(tags=["meta"])


class AppConfig(BaseModel):
    data_source: str          # mock | live — source effective des données de santé
    anomalies_source: str     # mock | live — peut différer (cf. providers)
    pm_read_only: bool        # plannings de maintenance figés (démo publique)


@router.get("/config", response_model=AppConfig)
def get_config() -> AppConfig:
    return AppConfig(
        data_source=settings.resolved_health_source,
        anomalies_source=settings.resolved_anomalies_source,
        pm_read_only=settings.pm_read_only,
    )
