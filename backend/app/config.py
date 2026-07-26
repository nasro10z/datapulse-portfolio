from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

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

    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
