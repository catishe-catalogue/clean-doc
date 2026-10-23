from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Системные параметры
    ENVIRONMENT: Literal["dev", "test", "prod"] = "dev"
    DEBUG: bool = False
    PROJECT_NAME: str = "Чистый документ"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(default="dev_secret_key_insecure_replace_in_prod_64_characters_min_len")
    ALLOWED_HOSTS: list[str] = ["*"]

    # PostgreSQL 18
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "cleandoc"
    POSTGRES_PASSWORD: str = "secure_pg_password"
    POSTGRES_DB: str = "cleandoc_db"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis 7.2
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # S3 Хранилище (MinIO dev / Selectel prod)
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_REGION: str = "ru-1"
    S3_BUCKET_NAME: str = "cleandoc-dev"
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = "minioadmin"

    # SMTP для Magic Link
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USE_TLS: bool = False
    SMTP_USER: str = "no-reply@clean-doc.ru"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "no-reply@clean-doc.ru"

    # Мониторинг
    PROMETHEUS_ENABLED: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
