"""
Application Configuration

This module defines all application settings using Pydantic Settings.
Settings are loaded from environment variables with validation.

Why Pydantic Settings:
- Type validation at startup (fail fast if misconfigured)
- Auto-completion in IDE
- Easy to test with different configs
- Self-documenting with type hints
"""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import secrets


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings have sensible defaults for development.
    Override via .env file or environment variables.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # ============================================================================
    # Project Information
    # ============================================================================
    PROJECT_NAME: str = "AML Transaction Monitoring"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    
    # ============================================================================
    # Database Configuration (Async PostgreSQL)
    # ============================================================================
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:elaunch_2025@localhost:5432/aml_monitoring",
        description="Async database URL using asyncpg driver"
    )
    
    # Sync URL for Alembic migrations (can't use async)
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://postgres:elaunch_2025@localhost:5432/aml_monitoring",
        description="Sync database URL for migrations"
    )
    
    # Connection pool settings
    DB_POOL_SIZE: int = Field(
        default=20,
        description="Number of permanent connections in the pool"
    )
    DB_MAX_OVERFLOW: int = Field(
        default=10,
        description="Max connections beyond pool_size"
    )
    DB_POOL_TIMEOUT: int = Field(
        default=30,
        description="Seconds to wait for a connection"
    )
    DB_POOL_RECYCLE: int = Field(
        default=3600,
        description="Recycle connections after this many seconds"
    )
    DB_ECHO: bool = Field(
        default=False,
        description="Log all SQL statements (useful for debugging)"
    )
    
    # ============================================================================
    # Redis Configuration
    # ============================================================================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching and pub/sub"
    )
    
    # ============================================================================
    # Security & Authentication
    # ============================================================================
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT token generation"
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440,  # 24 hours
        description="JWT token expiration time in minutes"
    )
    
    # Password validation
    MIN_PASSWORD_LENGTH: int = 8
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure SECRET_KEY is strong enough for production."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    # ============================================================================
    # CORS Configuration
    # ============================================================================
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed origins for CORS"
    )
    
    # ============================================================================
    # File Upload Configuration
    # ============================================================================
    MAX_UPLOAD_SIZE: int = Field(
        default=104_857_600,  # 100 MB
        description="Maximum file upload size in bytes"
    )
    UPLOAD_DIR: str = Field(
        default="./uploads",
        description="Directory to store uploaded files temporarily"
    )
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".csv"],
        description="Allowed file extensions for upload"
    )
    
    # ============================================================================
    # Celery Configuration
    # ============================================================================
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL"
    )
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 30 * 60  # 30 minutes
    
    # ============================================================================
    # Business Logic Configuration
    # ============================================================================
    TRANSACTION_BATCH_SIZE: int = Field(
        default=1000,
        description="Number of transactions to insert in a single batch"
    )
    
    RULE_CACHE_TTL: int = Field(
        default=3600,  # 1 hour
        description="Time to cache rule configurations in seconds"
    )
    
    # High-risk countries (ISO 3166-1 alpha-2 codes)
    HIGH_RISK_COUNTRIES: List[str] = Field(
        default=[
            "KP",  # North Korea
            "IR",  # Iran
            "SY",  # Syria
            "CU",  # Cuba
            "VE",  # Venezuela
            "MM",  # Myanmar
            "BY",  # Belarus
            "ZW",  # Zimbabwe
        ],
        description="ISO 3166-1 alpha-2 country codes for high-risk jurisdictions"
    )
    
    # Default rule parameters (can be overridden per organization)
    DEFAULT_LARGE_TRANSACTION_THRESHOLD: float = 10_000.00
    DEFAULT_HIGH_FREQUENCY_MAX_TXN: int = 10
    DEFAULT_HIGH_FREQUENCY_WINDOW_MIN: int = 60
    DEFAULT_RAPID_MOVEMENT_MAX_HOPS: int = 3
    DEFAULT_RAPID_MOVEMENT_WINDOW_MIN: int = 30
    DEFAULT_ROUND_AMOUNT_THRESHOLD: float = 1_000.00
    DEFAULT_VELOCITY_CHANGE_MULTIPLIER: float = 3.0
    DEFAULT_VELOCITY_CHANGE_WINDOW_DAYS: int = 30
    
    # ============================================================================
    # Logging Configuration
    # ============================================================================
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # ============================================================================
    # Pagination
    # ============================================================================
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 1000
    
    # ============================================================================
    # Feature Flags (for future features)
    # ============================================================================
    ENABLE_WEBSOCKET_UPDATES: bool = Field(
        default=False,
        description="Enable real-time WebSocket updates (future feature)"
    )
    ENABLE_ML_SCORING: bool = Field(
        default=False,
        description="Enable ML risk scoring (future feature)"
    )
    ENABLE_AUDIT_LOG: bool = Field(
        default=True,
        description="Enable audit logging for compliance"
    )
    
    # ============================================================================
    # Helper Properties
    # ============================================================================
    @property
    def database_url_async(self) -> str:
        """Get async database URL."""
        return self.DATABASE_URL
    
    @property
    def database_url_sync(self) -> str:
        """Get sync database URL for Alembic."""
        return self.DATABASE_URL_SYNC


# Singleton instance
settings = Settings()


# Expose settings for easy import
__all__ = ["settings", "Settings"]