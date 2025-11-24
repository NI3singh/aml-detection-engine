# app/services/external_api.py

import httpx
import logging
from typing import Optional, Dict, Any
from app.config import settings
from app.services.geo_data import geo_data_service

logger = logging.getLogger(__name__)

class ExternalAPIService:
    """
    Handles communication with external IP intelligence providers (vpnapi.io).
    """
    
    def __init__(self):
        self.base_url = settings.GEOIP_API_URL
        self.api_key = settings.VPNAPI_KEY
        self.timeout = settings.GEOIP_TIMEOUT

    async def fetch_ip_details(self, ip: str) -> Optional[Dict[str, Any]]:
        """
        Call vpnapi.io to get IP details.
        Returns a standardized dictionary ready for DB insertion or None if failed.
        """
        url = f"{self.base_url}/{ip}?key={self.api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"🌐 Calling External API for IP: {ip}")
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                return self._parse_vpnapi_response(ip, data)

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ External API Error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"❌ Network Error connecting to External API: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected Error in External API service: {e}")
            
        return None

    def _parse_vpnapi_response(self, ip: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converts the raw vpnapi.io response into our internal structure.
        Determines if the IP is 'Risky' (VPN/Proxy) or 'Clean'.
        """
        security = data.get("security", {})
        location = data.get("location", {})
        network = data.get("network", {})
        

        country_code = location.get("country_code", "XX")

        # vpnapi.io doesn't give this, so we grab it from geodata.json
        local_borders = geo_data_service.get_borders(country_code)

        api_region = location.get("region", "")
        if not api_region:
            # Try to get region from our local geodata
            api_region = geo_data_service.get_region(country_code)

        as_val = network.get("autonomous_system_number", 0)
        
        # Determine risk based on security flags
        is_vpn = security.get("vpn", False)
        is_proxy = security.get("proxy", False)
        is_tor = security.get("tor", False)
        is_relay = security.get("relay", False)
        
        is_risk = any([is_vpn, is_proxy, is_tor, is_relay])
        

        # Construct the 'geolocation' object matching app.schemas.Geolocation
        geolocation = {
            "country": location.get("country", "Unknown"),
            "country_code": location.get("country_code", "XX"),
            "region": api_region,
            "isp": network.get("autonomous_system_organization"), # vpnapi puts ISP/Org here usually
            "org": network.get("autonomous_system_organization"),
            "as": network.get("autonomous_system_number"),
            "as": str(as_val),
            "geo_source": "vpnapi.io",
            # We construct a basic country_details since vpnapi doesn't give borders directly
            "country_details": {
                "cca2": location.get("country_code", "XX"),
                "region": location.get("continent", "Unknown"),
                "borders": local_borders
            }
        }

        # Return a bundle containing everything needed for the Brain
        return {
            "ip": ip,
            "is_risk": is_risk,
            "security": {
                "is_vpn": is_vpn,
                "is_proxy": is_proxy,
                "is_tor": is_tor,
                "is_relay": is_relay
            },
            "geolocation": geolocation,
            "raw_source": "vpnapi.io"
        }

# Global Instance
external_api = ExternalAPIService()