from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    # Chemin absolu vers backend/.env (où vit `.env.example`) : un chemin relatif
    # serait résolu depuis le répertoire de lancement, et `uvicorn --app-dir backend`
    # démarre depuis la racine du dépôt — le fichier n'était alors jamais lu.
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env", env_file_encoding="utf-8"
    )

    # Source des données métier (santé, forecast, anomalies) :
    #   "mock" — générateurs seedés (Phases 1–7, défaut)
    #   "live" — pipeline ML validé, lecture du gold précalculé (Phase 8)
    # Le basculement se fait par cette seule variable ; voir app/providers.py.
    data_source: Literal["mock", "live"] = "mock"

    # Dérogation par domaine, pour ne basculer qu'une partie de l'application.
    # Non renseignée → le domaine suit `data_source`. Utile en démo : les données
    # réelles s'arrêtent en mai 2026, donc les vues d'anomalies bornées à une
    # fenêtre récente n'ont rien à montrer, alors que les scores de santé, eux,
    # se lisent très bien sur la dernière heure disponible.
    anomalies_source: Literal["mock", "live"] | None = None
    health_source: Literal["mock", "live"] | None = None

    @property
    def resolved_anomalies_source(self) -> str:
        return self.anomalies_source or self.data_source

    @property
    def resolved_health_source(self) -> str:
        return self.health_source or self.data_source

    # Préfixe des messages UPS reconstruits par l'ingestion. Il doit reproduire
    # **à l'identique** celui du fichier de référence livré, sinon le golden test
    # de fidélité compare des chaînes différentes (cf. tests/test_ingestion_fidelity).
    # Ce préfixe porte le nom réel du site : il vit donc avec les données brutes,
    # qui sont privées et hors dépôt. Défaut neutre ; valeur réelle à poser dans
    # `backend/.env` (RAW_UPS_MESSAGE_PREFIX) sur la machine qui détient les exports.
    raw_ups_message_prefix: str = r"\MSC-10\ UPS "

    # Source de données (lecture) — PostgreSQL datacenter_ops
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "datacenter_ops"
    db_user: str = ""
    db_password: str = ""

    # État applicatif (écriture) — SQLite local, volontairement distinct de la
    # base source : ce que l'utilisateur saisit dans DataPulse n'a pas à être
    # écrit dans la base du data center.
    app_db_path: Path = BACKEND_ROOT / "data" / "datapulse.db"

    # Démo publique : les plannings de PM sont servis en **lecture seule**.
    # Sans authentification, la moindre saisie d'un visiteur modifierait
    # durablement le calendrier que voient tous les autres. Les trois routes
    # d'écriture répondent alors 403, et l'interface présente le formulaire
    # désactivé plutôt que de le laisser échouer à la soumission.
    pm_read_only: bool = False

    # URL complète de la base applicative, quand ce n'est pas SQLite : PostgreSQL
    # managé en déploiement, parce qu'un hébergement serverless n'a pas de disque
    # persistant — une PM planifiée sur `/tmp` survit à la requête, pas au
    # conteneur. Renseignée, elle **prime** sur `app_db_path`.
    # ⚠️ Secret (identifiants) : uniquement dans `backend/.env` (gitignoré) ou dans
    # les variables du dashboard d'hébergement. Jamais dans le dépôt.
    app_db_url: str | None = None

    # Stockage analytique (écriture par l'ETL uniquement) — SQLite local, distinct
    # de l'état applicatif : couches bronze/silver/gold du pipeline de données.
    # Voir docs/data-architecture.md. Un seul écrivain (ETL) par fichier.
    analytics_db_path: Path = BACKEND_ROOT / "data" / "datapulse_analytics.db"

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://0.0.0.0:5173",
    ]


settings = Settings()
