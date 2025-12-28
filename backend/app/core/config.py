"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "UAPK Gateway"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False

    # Database
    database_url: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://uapk:uapk@localhost:5432/uapk"
    )

    # Security
    secret_key: str = "CHANGE-ME-IN-PRODUCTION-USE-SECURE-RANDOM-VALUE"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24  # 24 hours
    api_key_header: str = "X-API-Key"

    # CORS - strict defaults, configure via environment for production
    cors_origins: list[str] = []  # Empty = deny all by default
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["Authorization", "Content-Type", "X-API-Key"]

    # Gateway settings
    gateway_fernet_key: str | None = None  # For secret encryption, generate with Fernet.generate_key()
    gateway_default_daily_budget: int = 1000  # Default daily action cap per UAPK
    gateway_approval_expiry_hours: int = 24  # Hours until approval tasks expire
    gateway_connector_timeout_seconds: int = 30  # Timeout for connector HTTP calls
    gateway_allowed_webhook_domains: list[str] = []  # Allowlist for webhook URLs
    gateway_max_connector_response_bytes: int = 1_000_000  # Max response size from connectors
    gateway_max_request_bytes: int = 1_000_000  # Max request body size

    # Audit Export (S3 Object Lock for immutable storage)
    audit_export_enabled: bool = False  # Enable immutable audit export
    audit_export_s3_bucket: str | None = None  # S3 bucket for audit exports
    audit_export_s3_region: str = "us-east-1"  # AWS region
    audit_export_s3_endpoint: str | None = None  # Custom S3 endpoint (for S3-compatible storage)
    audit_export_s3_access_key: str | None = None  # AWS access key ID
    audit_export_s3_secret_key: str | None = None  # AWS secret access key
    audit_export_object_lock_retention_days: int = 2555  # 7 years (default for compliance)
    audit_export_object_lock_mode: Literal["GOVERNANCE", "COMPLIANCE"] = "COMPLIANCE"  # Object Lock mode
    audit_export_auto_export_enabled: bool = False  # Auto-export records in real-time
    audit_export_batch_interval_minutes: int = 60  # Batch export interval (if not real-time)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            msg = f"Invalid log level: {v}. Must be one of {allowed}"
            raise ValueError(msg)
        return v_upper

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Enforce security requirements in staging/production."""
        if self.environment in ("staging", "production"):
            # Enforce SECRET_KEY is set to a secure value
            if "CHANGE-ME" in self.secret_key.upper() or len(self.secret_key) < 32:
                raise ValueError(
                    "SECRET_KEY must be set to a secure random value (min 32 chars) in staging/production. "
                    "Generate with: openssl rand -hex 32"
                )

            # Enforce Fernet key is set if using secrets storage
            if not self.gateway_fernet_key:
                raise ValueError(
                    "GATEWAY_FERNET_KEY is required in staging/production for secrets encryption. "
                    "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )

        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
