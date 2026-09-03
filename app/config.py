"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    discord_token: str
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/au_faceit"
    faceit_api_key: str = ""
    environment: str = "development"
    log_level: str = "INFO"

    # Default matchmaking constants
    default_elo: int = 1000
    win_elo: int = 8
    loss_elo: int = -6
    queue_size: int = 15
    nickname_format: str = "[L{level}] {name}"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
