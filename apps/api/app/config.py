"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the project root for .env file (local dev only)
try:
    _PROJECT_ROOT = Path(__file__).resolve().parents[3]
    _ENV_FILE = _PROJECT_ROOT / ".env"
except IndexError:
    _ENV_FILE = Path("/nonexistent")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "FakturaAI API"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "postgresql+asyncpg://fakturaai:fakturaai_dev@localhost:5433/fakturaai"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # JWT Authentication
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # Storage (S3/R2)
    storage_endpoint: str | None = None
    storage_public_endpoint: str | None = (
        None  # Browser-accessible URL (e.g. http://localhost:9010)
    )
    storage_bucket: str = "fakturaai-documents"
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_region: str = "auto"

    # APR Integration
    apr_api_url: str = "https://api.apr.gov.rs"
    apr_api_timeout: int = 10
    apr_cache_ttl: int = 86400  # 24 hours

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Sentry
    sentry_dsn: str | None = None

    # Email (Resend)
    resend_api_key: str = ""
    resend_from_email: str = "noreply@fakturaai.rs"
    frontend_url: str = "http://localhost:3000"

    # SEF (eFaktura)
    sef_api_base_url: str = "https://efaktura.mfin.gov.rs/api/v1"
    sef_environment: str = "test"
    sef_sync_interval_minutes: int = 15
    sef_demo_mode: bool = True

    # ML Processing
    ocr_confidence_threshold: float = 0.80
    ocr_max_file_size_mb: int = 20
    ocr_supported_formats: list[str] = ["pdf", "png", "jpg", "jpeg", "tiff", "webp"]
    ocr_min_image_width: int = 600
    ocr_min_image_height: int = 400


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
