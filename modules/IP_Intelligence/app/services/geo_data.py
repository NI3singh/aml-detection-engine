# app/services/geo_data.py

import json
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class GeoDataService:
    """
    Loads static geographic data (borders, regions) from a local JSON file.
    Used to enrich API responses that lack this detail.
    """
    
    def __init__(self):
        self.borders_map: Dict[str, List[str]] = {}
        self.region_map: Dict[str, str] = {}
        self._load_data()

    def _load_data(self):
        """
        Loads app/geodata.json into memory for fast lookup.
        """
        # Path to the file (assuming it's in the app/ directory)
        file_path = Path(__file__).parent.parent / "geodata.json"
        
        try:
            if not file_path.exists():
                logger.warning(f"⚠️ geodata.json not found at {file_path}. Borders will be empty.")
                return

            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            
            # OPTIMIZATION:
            # The JSON might be keyed by "Country Name" (e.g., "United States": {...})
            # But we want to look up by "Code" (e.g., "US").
            # So we iterate once and build a fast lookup map: 'US' -> ['CA', 'MX']
            
            count = 0
            for country_name, details in raw_data.items():
                cca2 = details.get("cca2") # e.g., "US"
                borders = details.get("borders", []) # e.g., ["CA", "MX"]
                region = details.get("region", "Unknown")
                
                if cca2:
                    self.borders_map[cca2] = borders
                    self.region_map[cca2] = region
                    count += 1
            
            logger.info(f"✅ Loaded GeoData for {count} countries.")

        except Exception as e:
            logger.error(f"❌ Failed to load geodata.json: {e}")

    def get_borders(self, country_code: str) -> List[str]:
        """Returns list of border country codes for a given country code."""
        return self.borders_map.get(country_code, [])

    def get_region(self, country_code: str) -> str:
        """Returns the region for a given country code."""
        return self.region_map.get(country_code, "Unknown")

# Global Instance
geo_data_service = GeoDataService()