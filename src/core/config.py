from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["dev", "staging", "prod"] = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8099
    app_title: str = "EDO-Adapter Enterprise"
    app_version: str = "0.1.0"
    debug: bool = False

    postgres_host: str = "localhost"
    postgres_port: int = 5499
    postgres_db: str = "edo_adapter"
    postgres_user: str = "edo"
    postgres_password: str = "edo"
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_echo: bool = False

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    redis_host: str = "localhost"
    redis_port: int = 6399
    redis_password: str = "change-me"
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"

    paseto_secret_key: str = Field(default="replace-with-32-byte-secret-key!!")
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 14

    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3099", "http://localhost:8099"]
    )

    otel_exporter_otlp_endpoint: str = "http://localhost:4399"
    otel_service_name: str = "edo-adapter-api"
    enable_log_masking: bool = True

    default_retry_max_attempts: int = 5
    default_retry_base_seconds: float = 10.0
    default_retry_max_seconds: float = 900.0
    circuit_failure_threshold: int = 5
    circuit_recovery_timeout_seconds: int = 60
    circuit_half_open_max_calls: int = 2

    provider_request_timeout_seconds: float = 30.0
    provider_connect_timeout_seconds: float = 5.0

    webhook_dedup_ttl_seconds: int = 86_400
    idempotency_key_ttl_seconds: int = 604_800

    @model_validator(mode="after")
    def _validate_secret_length(self) -> Settings:
        if len(self.paseto_secret_key) < 32:
            raise ValueError("paseto_secret_key must be at least 32 characters")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
