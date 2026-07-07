"""Application Settings with type-safe environment variable loading."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    All settings are type-safe and validated using Pydantic.
    Environment variables override defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Enterprise Fraud Detection Platform")
    app_version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_prefix: str = Field(default="/v1")
    api_workers: int = Field(default=4)

    # Security
    secret_key: str = Field(default="change-me-in-production")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)
    refresh_token_expire_days: int = Field(default=30)

    # Database
    database_url: str = Field(
        default="postgresql://fraud_user:fraud_password@localhost:5432/fraud_detection"
    )
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)
    database_pool_pre_ping: bool = Field(default=True)
    database_echo: bool = Field(default=False)

    # AWS Configuration
    aws_region: str = Field(default="us-east-1")
    aws_access_key_id: str = Field(default="")
    aws_secret_access_key: str = Field(default="")
    s3_bucket_models: str = Field(default="fraud-detection-models-dev")
    s3_bucket_data: str = Field(default="fraud-detection-data-dev")

    # Secrets Manager
    aws_secrets_manager_enabled: bool = Field(default=False)
    aws_secret_name: str = Field(default="fraud-detection/dev")

    # CloudWatch
    cloudwatch_enabled: bool = Field(default=False)
    cloudwatch_log_group: str = Field(default="/ecs/fraud-detection/api")
    cloudwatch_namespace: str = Field(default="FraudDetection")

    # Redis (Future)
    redis_enabled: bool = Field(default=False)
    redis_url: str = Field(default="redis://localhost:6379/0")

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:8000"])
    cors_credentials: bool = Field(default=True)
    cors_methods: list[str] = Field(default=["*"])
    cors_headers: list[str] = Field(default=["*"])

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests: int = Field(default=100)
    rate_limit_period: int = Field(default=60)

    # Request Timeout
    request_timeout_seconds: int = Field(default=30)

    # Monitoring
    enable_metrics: bool = Field(default=True)
    enable_tracing: bool = Field(default=False)
    xray_enabled: bool = Field(default=False)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of allowed values."""
        allowed = ["development", "testing", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v_upper

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == "testing"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Settings are cached to avoid re-reading environment variables
    on every request. Use this function instead of instantiating
    Settings directly.

    Returns:
        Singleton settings instance
    """
    return Settings()
