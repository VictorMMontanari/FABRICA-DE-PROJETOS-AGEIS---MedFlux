"""Configuração central da aplicação, carregada de variáveis de ambiente / `.env`."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Aplicação
    APP_NAME: str = "MedFlux API"
    APP_ENV: Literal["development", "test", "production"] = "development"
    APP_PORT: int = 5000
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    FRONTEND_URL: str = "http://localhost:5173"

    # MySQL. DATABASE_URL, quando definido, tem prioridade (ex.: SQLite nos testes).
    DATABASE_URL: str | None = None
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "medflux"
    DB_PASSWORD: str = ""
    DB_NAME: str = "medflux"
    DB_ECHO: bool = False

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_PUBLIC_ENDPOINT: str | None = None
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_SECURE: bool = False
    MINIO_REGION: str = "us-east-1"
    MINIO_BUCKET: str = "medflux-documents"
    PRESIGNED_URL_EXPIRE_MINUTES: int = Field(default=60, ge=1, le=10080)

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str | None = None
    EMBEDDING_DIM: int = Field(default=384, ge=32, le=4096)

    # Redis (opcional): sem REDIS_HOST o rate limit de login fica desativado.
    REDIS_HOST: str | None = None
    REDIS_PORT: int = 6379
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_SECONDS: int = 900

    # OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_TIMEOUT: float = Field(default=20.0, gt=0)

    # Agentes: "custom" (cliente próprio) ou "ag2" (framework AG2)
    AGENT_RUNTIME: Literal["custom", "ag2"] = "custom"

    # JWT
    JWT_SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, ge=1)
    BCRYPT_ROUNDS: int = Field(default=12, ge=4, le=16)

    # Seed
    SEED_DEMO_USER: bool = True
    SEED_ADMIN_EMAIL: str | None = None
    SEED_ADMIN_PASSWORD: str | None = None

    @field_validator("API_V1_PREFIX")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return URL.create(
            "mysql+aiomysql",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query={"charset": "utf8mb4"},
        ).render_as_string(hide_password=False)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.FRONTEND_URL.split(",") if origin.strip()]

    @property
    def openrouter_enabled(self) -> bool:
        return bool(self.OPENROUTER_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
