from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "datacenter_ops"
    db_user: str = ""
    db_password: str = ""

    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
