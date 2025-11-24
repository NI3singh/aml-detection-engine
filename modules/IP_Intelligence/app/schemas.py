# app/schemas.py

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

# --- Nested Models (The inner parts of your JSON) ---

class CountryDetails(BaseModel):
    """Details about the country (borders, codes)."""
    cca2: str
    region: str
    borders: List[str] = []

class Geolocation(BaseModel):
    """Location and ISP data."""
    country: str
    country_code: str
    region: Optional[str] = None
    city: Optional[str] = None
    isp: Optional[str] = None
    org: Optional[str] = None
    # We allow these to be optional because sometimes APIs don't return them
    as_number: Optional[int] = Field(None, alias="as") 
    geo_source: str = "vpnapi.io"
    country_details: Optional[CountryDetails] = None

# app/schemas.py (Add this Class)

class TorGeo(BaseModel):
    """The nested 'geo' object inside the Tor document."""
    country: Optional[str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    isp: Optional[str] = None
    # We map 'asn' from JSON to 'as_number' in Python
    as_number: Optional[str] = Field(None, alias="asn")

class TorDocument(BaseModel):
    """
    Schema for the 'tor_ips' collection.
    Matches the specific JSON structure provided by the user.
    """
    ip: str
    source: str = "torproject"
    geo: TorGeo
    # We use aliases because your DB has 'geo_source' but maybe we want consistency later
    geo_source: Optional[str] = None
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    
    # We might need to ignore the "__v" field from Mongoose/NodeJS if it exists
    class Config:
        populate_by_name = True
        extra = "ignore" # Ignore fields we don't define (like __v)

# --- Main Model (The Document itself) ---

class IPDocument(BaseModel):
    """
    The main document structure for 'vpn_ips' and 'clean_ips'.
    This matches exactly what goes into MongoDB.
    """
    ip: str
    # ip_hash is useful for faster comparison if needed later, 
    # but for now we generate it or accept it.
    ip_hash: Optional[str] = None
    
    type: str = "ipv4"
    
    # "source" is the specific detection (e.g., "vpnapi.io")
    source: str
    
    # "sources" tracks history (e.g., ["vpnapi.io", "manual_review"])
    sources: List[str] = []
    
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    
    # 0 to 1 score (1 = definitely a VPN/Clean IP)
    confidence: int = 1
    
    is_active: bool = True
    fetch_count: int = 1
    
    geolocation: Geolocation

    class Config:
        # This allows using field names like 'as' (which is a reserved keyword in Python)
        # by mapping them to 'as_number' in our code but 'as' in JSON.
        populate_by_name = True

    @field_validator('ip')
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Basic validation to ensure IP is not empty."""
        if not v.strip():
            raise ValueError("IP address cannot be empty")
        return v