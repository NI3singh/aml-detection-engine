# app/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """
    Application Configuration.
    Validates and loads environment variables on startup.
    """
    
    # App Info
    APP_NAME: str
    VERSION: str
    DEBUG: bool = False
    
    # Database (MongoDB)
    MONGODB_URL: str
    DB_NAME: str
    
    # External API (VPNAPI.io)
    GEOIP_API_URL: str
    VPNAPI_KEY: str
    GEOIP_TIMEOUT: int = 5
    
    # Server Settings
    API_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        # This tells Pydantic to read from the .env file
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    """
    Creates a cached instance of settings.
    This prevents reading the .env file for every single request.
    """
    return Settings()

# Global instance for easy import
settings = get_settings()