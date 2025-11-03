"""
Configuration Management
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "AML Screening API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # GeoIP Service
    GEOIP_API_URL: str = "http://ip-api.com/json"
    GEOIP_TIMEOUT: int = 2  # seconds
    
    # High-Risk Countries (ISO 3166-1 alpha-2 codes)
    HIGH_RISK_COUNTRIES: List[str] = [
        "AF",  # Afghanistan
        "MM",  # Myanmar
        "KP",  # North Korea
        "PK",  # Pakistan
        "IR",  # Iran
        "SY",  # Syria
        "YE",  # Yemen
        "IQ",  # Iraq
        "SO",  # Somalia
        "LY",  # Libya
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()