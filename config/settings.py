from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Boujuron"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Kafka
    KAFKA_BOOTSTRAP_SERVER: str
    KAFKA_TOPIC_EVENTS: str = "user_events"

    # ✅ MAKE OPTIONAL
    KAFKA_API_KEY: Optional[str] = None
    KAFKA_API_SECRET: Optional[str] = None

    # Database
    DATABASE_URL: str

    # ✅ MAKE OPTIONAL
    API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
