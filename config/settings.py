from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Boujuron"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Kafka
    KAFKA_BOOTSTRAP_SERVER: str
    KAFKA_TOPIC_EVENTS: str = "user_events"

    KAFKA_API_KEY: Optional[str] = None
    KAFKA_API_SECRET: Optional[str] = None

    # Database
    DATABASE_URL: str

    API_KEY: Optional[str] = None


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()