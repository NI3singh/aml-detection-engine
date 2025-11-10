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
    GEOIP_API_URL: str = "https://vpnapi.io/api"
    VPNAPI_KEY: str
    GEOIP_TIMEOUT: int = 5  # seconds

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # High-Risk Countries (ISO 3166-1 alpha-2 codes)
    HIGH_RISK_COUNTRIES: List[str] = [
        "MM",  # Myanmar
        "KP",  # North Korea
        "IR",  # Iran
        "SY",  # Syria
        "YE",  # Yemen
        "DZ",  # Algeria
        "AO",  # Angola
        "BO",  # Bolivia
        "BG",  # Bulgaria
        "CM",  # Cameroon
        "CI",  # Côte d'Ivoire
        "HT",  # Haiti
        "KE",  # Kenya
        "LB",  # Lebanon
        "LA",  # Laos
        "MC",  # Monaco
        "NA",  # Namibia
        "NP",  # Nepal
        "SS",  # South Sudan
        "SY",  # Syria
        "VE",  # Venezuela
        "VN",  # Vietnam

    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()