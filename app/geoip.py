# """
# GeoIP Service - IP to Country Lookup
# """
# import httpx
# from typing import Optional
# import logging

# from app.config import settings

# logger = logging.getLogger(__name__)


# class GeoIPResult:
#     """GeoIP lookup result."""
    
#     def __init__(
#         self,
#         country_code: Optional[str],
#         country_name: Optional[str],
#         confidence: float = 1.0,
#         error: Optional[str] = None
#     ):
#         self.country_code = country_code
#         self.country_name = country_name
#         self.confidence = confidence
#         self.error = error
    
#     @property
#     def success(self) -> bool:
#         """Whether lookup was successful."""
#         return self.country_code is not None


# class GeoIPService:
#     """Service for IP geolocation lookups."""
    
#     def __init__(self):
#         self.api_url = settings.GEOIP_API_URL
#         self.timeout = settings.GEOIP_TIMEOUT
    
#     async def lookup(self, ip_address: str) -> GeoIPResult:
#         """
#         Look up country for an IP address.
        
#         Uses ip-api.com free tier (no API key required).
#         Rate limit: 45 requests/minute.
        
#         Args:
#             ip_address: IP address to look up
            
#         Returns:
#             GeoIPResult with country information
#         """
#         try:
#             async with httpx.AsyncClient(timeout=self.timeout) as client:
#                 # ip-api.com endpoint: http://ip-api.com/json/{ip}
#                 url = f"{self.api_url}/{ip_address}"
                
#                 logger.info(f"Looking up IP: {ip_address}")
#                 response = await client.get(url)
#                 response.raise_for_status()
                
#                 data = response.json()
                
#                 # Check if lookup was successful
#                 if data.get("status") == "success":
#                     country_code = data.get("countryCode")
#                     country_name = data.get("country")
                    
#                     logger.info(
#                         f"GeoIP success: {ip_address} -> {country_code} ({country_name})"
#                     )
                    
#                     return GeoIPResult(
#                         country_code=country_code,
#                         country_name=country_name,
#                         confidence=0.95  # ip-api.com is generally accurate
#                     )
#                 else:
#                     # API returned error
#                     error_msg = data.get("message", "Unknown error")
#                     logger.warning(f"GeoIP lookup failed: {error_msg}")
                    
#                     return GeoIPResult(
#                         country_code=None,
#                         country_name=None,
#                         confidence=0.0,
#                         error=error_msg
#                     )
        
#         except httpx.TimeoutException:
#             logger.error(f"GeoIP timeout for IP: {ip_address}")
#             return GeoIPResult(
#                 country_code=None,
#                 country_name=None,
#                 confidence=0.0,
#                 error="GeoIP service timeout"
#             )
        
#         except Exception as e:
#             logger.error(f"GeoIP error for IP {ip_address}: {str(e)}")
#             return GeoIPResult(
#                 country_code=None,
#                 country_name=None,
#                 confidence=0.0,
#                 error=f"GeoIP service error: {str(e)}"
#             )


# # Global service instance
# geoip_service = GeoIPService()

# app/geoip.py

"""
GeoIP & Security Service - VPN/Proxy Detection
"""
import httpx
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class GeoIPResult:
    """
    GeoIP lookup result with security flags.
    """
    def __init__(
        self,
        country_code: Optional[str] = None,
        country_name: Optional[str] = None,
        # --- NEW SECURITY FLAGS ---
        is_vpn: bool = False,
        is_proxy: bool = False,
        is_tor: bool = False,
        is_relay: bool = False,
        # --------------------------
        confidence: float = 1.0,
        error: Optional[str] = None
    ):
        self.country_code = country_code
        self.country_name = country_name
        self.is_vpn = is_vpn
        self.is_proxy = is_proxy
        self.is_tor = is_tor
        self.is_relay = is_relay
        self.confidence = confidence
        self.error = error
    
    @property
    def success(self) -> bool:
        """Whether lookup was successful."""
        return self.country_code is not None


class GeoIPService:
    """Service for IP geolocation and security lookups."""
    
    def __init__(self):
        self.base_url = settings.GEOIP_API_URL
        self.api_key = settings.VPNAPI_KEY
        self.timeout = settings.GEOIP_TIMEOUT
    
    async def lookup(self, ip_address: str) -> GeoIPResult:
        """
        Look up IP address using vpnapi.io for geo and security data.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # URL format: https://vpnapi.io/api/{ip}?key={key}
                url = f"{self.base_url}/{ip_address}?key={self.api_key}"
                
                logger.info(f"Scanning IP: {ip_address}")
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                
                # vpnapi.io groups data into 'location' and 'security' objects
                location = data.get("location", {})
                security = data.get("security", {})
                
                country_code = location.get("country_code")
                country_name = location.get("country")
                
                if not country_code:
                     raise ValueError("No country code in response")

                result = GeoIPResult(
                    country_code=country_code,
                    country_name=country_name,
                    # Map the security flags directly
                    is_vpn=security.get("vpn", False),
                    is_proxy=security.get("proxy", False),
                    is_tor=security.get("tor", False),
                    is_relay=security.get("relay", False),
                    confidence=0.98 # Paid/Specialized APIs have high confidence
                )
                
                # Log significant threats immediately
                if result.is_tor or result.is_vpn:
                     logger.warning(f"THREAT DETECTED for {ip_address}: VPN={result.is_vpn}, TOR={result.is_tor}")
                
                return result

        except httpx.HTTPStatusError as e:
             # Handle specific API errors (like 401 invalid key, 429 rate limit)
             error_msg = f"API Error {e.response.status_code}"
             logger.error(f"GeoIP lookup failed for {ip_address}: {error_msg}")
             return GeoIPResult(confidence=0.0, error=error_msg)
             
        except Exception as e:
            logger.error(f"GeoIP error for IP {ip_address}: {str(e)}")
            return GeoIPResult(confidence=0.0, error=f"Service error: {str(e)}")


# Global service instance
geoip_service = GeoIPService()