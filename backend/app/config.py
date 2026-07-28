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
    #   "live" — pipeline ML validé branché sur PostgreSQL (Phase 8)
    # Le basculement se fait par cette seule variable ; voir app/providers.py.
    data_source: Literal["mock", "live"] = "mock"

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

    # Stockage analytique (écriture par l'ETL uniquement) — SQLite local, distinct
    # de l'état applicatif : couches bronze/silver/gold du pipeline de données.
    # Voir docs/data-architecture.md. Un seul écrivain (ETL) par fichier.
    analytics_db_path: Path = BACKEND_ROOT / "data" / "datapulse_analytics.db"

    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
