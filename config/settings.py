from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Phantore Sentinel"
    ENVIRONMENT: str = "development"
    DEBUG: bool = "true"

    # Kafka
    KAFKA_BOOTSTRAP_SERVER = str
    KAFKA_TOPIC_EVENTS: str = "user_events"
    KAFKA_API_KEY: str
    KAFKA_API_SECRET: str

    # Database
    DATABASE_URL: str

    # Security
    API_KEY: str

    class Config:
        env_file: ".env"
        case_sensitive: "true"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
