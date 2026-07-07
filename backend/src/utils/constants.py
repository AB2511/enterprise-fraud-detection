"""Application Constants."""


class Constants:
    """Application-wide constants.

    Centralized location for all magic numbers and configuration constants.
    """

    # Default pagination
    DEFAULT_PAGE_SIZE: int = 100
    MAX_PAGE_SIZE: int = 1000

    # Timeouts
    DEFAULT_TIMEOUT_SECONDS: int = 30
    DATABASE_QUERY_TIMEOUT: int = 30

    # Retry configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 1

    # Model configuration (future)
    MODEL_CACHE_TTL_SECONDS: int = 3600
    FEATURE_CACHE_TTL_SECONDS: int = 300

    # Risk scoring thresholds
    FRAUD_PROBABILITY_THRESHOLD: float = 0.5
    HIGH_RISK_PROBABILITY_THRESHOLD: float = 0.8

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # API versioning
    API_VERSION: str = "v1"

    # Date formats
    DATE_FORMAT: str = "%Y-%m-%d"
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    ISO_DATETIME_FORMAT: str = "%Y-%m-%dT%H:%M:%SZ"

    # File size limits
    MAX_UPLOAD_SIZE_MB: int = 100
    MAX_BATCH_SIZE: int = 10000

    # Logging
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    REQUEST_ID_HEADER: str = "X-Request-ID"

    # Security
    PASSWORD_MIN_LENGTH: int = 8
    TOKEN_EXPIRY_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRY_DAYS: int = 30

    # Database
    CONNECTION_POOL_SIZE: int = 10
    CONNECTION_MAX_OVERFLOW: int = 20
