from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    session_secret: str = "dev-insecure-secret-change-me"
    panel_base_url: str = "http://localhost:8000"
    tz: str = "America/Argentina/Buenos_Aires"
    database_url: str = "sqlite:///./data/sitewatch.db"

    admin_username: str = "admin"
    admin_password: str = "admin"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    wpscan_api_key: str = ""
    google_safe_browsing_api_key: str = ""
    virustotal_api_key: str = ""

    healthchecks_url: str = ""

    log_level: str = "INFO"
    log_dir: str = "./data/logs"

    @property
    def data_dir(self) -> Path:
        return Path(self.database_url.removeprefix("sqlite:///")).parent


settings = Settings()
