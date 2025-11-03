"""
GeoIP Service - IP to Country Lookup
"""
import httpx
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class GeoIPResult:
    """GeoIP lookup result."""
    
    def __init__(
        self,
        country_code: Optional[str],
        country_name: Optional[str],
        confidence: float = 1.0,
        error: Optional[str] = None
    ):
        self.country_code = country_code
        self.country_name = country_name
        self.confidence = confidence
        self.error = error
    
    @property
    def success(self) -> bool:
        """Whether lookup was successful."""
        return self.country_code is not None


class GeoIPService:
    """Service for IP geolocation lookups."""
    
    def __init__(self):
        self.api_url = settings.GEOIP_API_URL
        self.timeout = settings.GEOIP_TIMEOUT
    
    async def lookup(self, ip_address: str) -> GeoIPResult:
        """
        Look up country for an IP address.
        
        Uses ip-api.com free tier (no API key required).
        Rate limit: 45 requests/minute.
        
        Args:
            ip_address: IP address to look up
            
        Returns:
            GeoIPResult with country information
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # ip-api.com endpoint: http://ip-api.com/json/{ip}
                url = f"{self.api_url}/{ip_address}"
                
                logger.info(f"Looking up IP: {ip_address}")
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                
                # Check if lookup was successful
                if data.get("status") == "success":
                    country_code = data.get("countryCode")
                    country_name = data.get("country")
                    
                    logger.info(
                        f"GeoIP success: {ip_address} -> {country_code} ({country_name})"
                    )
                    
                    return GeoIPResult(
                        country_code=country_code,
                        country_name=country_name,
                        confidence=0.95  # ip-api.com is generally accurate
                    )
                else:
                    # API returned error
                    error_msg = data.get("message", "Unknown error")
                    logger.warning(f"GeoIP lookup failed: {error_msg}")
                    
                    return GeoIPResult(
                        country_code=None,
                        country_name=None,
                        confidence=0.0,
                        error=error_msg
                    )
        
        except httpx.TimeoutException:
            logger.error(f"GeoIP timeout for IP: {ip_address}")
            return GeoIPResult(
                country_code=None,
                country_name=None,
                confidence=0.0,
                error="GeoIP service timeout"
            )
        
        except Exception as e:
            logger.error(f"GeoIP error for IP {ip_address}: {str(e)}")
            return GeoIPResult(
                country_code=None,
                country_name=None,
                confidence=0.0,
                error=f"GeoIP service error: {str(e)}"
            )


# Global service instance
geoip_service = GeoIPService()