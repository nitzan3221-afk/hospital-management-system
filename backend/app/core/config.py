"""Application configuration, loaded from environment variables (or a local .env file)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime settings in one place. Every field can be overridden by an env var
    with the same name in upper case (e.g. ``MONGO_URI``)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Hospital Management API"

    # Database
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "hospital"

    # Auth
    jwt_secret: str = "change-me-in-production-use-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # Artificial delay on the patient-list endpoint (simulates a slow overview query)
    patient_list_delay_seconds: float = 4.0

    # Insert demo data when the database is empty
    seed_on_startup: bool = True

    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:4200"]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read the environment only once)."""
    return Settings()
