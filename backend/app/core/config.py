"""Carga y validación de configuración (Pydantic Settings)."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno con validación al instanciar."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: Literal["local", "test", "staging", "production"] = Field(
        default="local",
        description="Entorno de ejecución; `test` relaja validaciones de secretos.",
    )

    log_level: str = Field(default="INFO")

    cors_allow_origins: str = Field(
        default=(
            "http://localhost:3000,http://localhost,http://127.0.0.1:3000," "http://127.0.0.1"
        ),
    )

    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)

    jwt_secret: str = Field(default="", repr=False)
    jwt_alg: str = Field(default="HS256")
    jwt_access_token_expires_seconds: int = Field(default=900, ge=1)
    jwt_refresh_token_expires_seconds: int = Field(default=2_592_000, ge=60)

    password_pepper: str = Field(default="", repr=False)

    auth_login_max_attempts_per_ip_per_minute: int = Field(default=30, ge=1)
    auth_login_max_attempts_per_email_per_minute: int = Field(default=15, ge=1)
    auth_failed_password_threshold: int = Field(default=5, ge=1)
    auth_lockout_base_seconds: int = Field(default=60, ge=1)
    auth_lockout_max_seconds: int = Field(default=3600, ge=1)

    database_url: str = Field(
        default="postgresql+psycopg://rag:rag_password_local@postgres:5432/rag",
        repr=False,
    )

    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379)

    qdrant_host: str = Field(default="qdrant")
    qdrant_port: int = Field(default=6333)

    ollama_host: str = Field(default="ollama")
    ollama_port: int = Field(default=11434)

    health_http_timeout_seconds: float = Field(default=3.0)

    upload_storage_dir: str = Field(
        default="",
        description="Directorio absoluto o vacío (<raíz repo>/uploads).",
    )
    max_upload_mb: int = Field(default=50, ge=1, le=512)
    allowed_mime_types: str = Field(
        default=(
            "application/pdf,"
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
            "text/plain"
        ),
    )

    celery_broker_url: str = Field(default="", repr=False)
    celery_result_backend: str = Field(default="", repr=False)
    celery_task_always_eager: bool = Field(default=False)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def qdrant_http_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ollama_http_url(self) -> str:
        return f"http://{self.ollama_host}:{self.ollama_port}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_mime_type_list(self) -> list[str]:
        return [m.strip() for m in self.allowed_mime_types.split(",") if m.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_celery_broker_url(self) -> str:
        if self.celery_broker_url.strip():
            return self.celery_broker_url.strip()
        return self.redis_url

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_celery_result_backend(self) -> str | None:
        s = self.celery_result_backend.strip()
        return s if s else None

    @model_validator(mode="after")
    def validate_boot(self) -> Settings:
        if self.environment == "test" and not self.jwt_secret.strip():
            self.jwt_secret = "test_jwt_secret_" + "x" * 32
        elif self.environment in ("staging", "production") and len(self.jwt_secret) < 32:
            msg = "JWT_SECRET debe tener al menos 32 caracteres en staging/production."
            raise ValueError(msg)
        elif self.environment == "local" and len(self.jwt_secret) < 16:
            msg = "JWT_SECRET debe tener al menos 16 caracteres en local (fail-fast)."
            raise ValueError(msg)

        if self.environment == "test" and not self.password_pepper.strip():
            self.password_pepper = "test_password_pepper_" + "x" * 32
        elif self.environment in ("staging", "production") and len(self.password_pepper) < 32:
            msg = "PASSWORD_PEPPER debe tener al menos 32 caracteres en staging/production."
            raise ValueError(msg)
        elif self.environment == "local" and len(self.password_pepper) < 16:
            msg = "PASSWORD_PEPPER debe tener al menos 16 caracteres en local (fail-fast)."
            raise ValueError(msg)

        if not _looks_like_sqlalchemy_postgres(self.database_url):
            msg = "DATABASE_URL debe ser un DSN PostgreSQL (postgresql+psycopg o postgresql)."
            raise ValueError(msg)

        if self.environment == "test":
            self.celery_task_always_eager = True

        return self


def _looks_like_sqlalchemy_postgres(url: str) -> bool:
    return bool(re.match(r"^postgresql(\+[\w]+)?://", url.strip()))


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
