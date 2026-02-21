"""Centralized configuration via pydantic-settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Odoo
    ODOO_URL: str = "https://otca.odoo.com"
    ODOO_DB: str = "otca"
    ODOO_USERNAME: str
    ODOO_API_KEY: str

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once per process)."""
    return Settings()
