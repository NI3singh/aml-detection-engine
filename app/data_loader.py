"""
Geo-Data Loader

Run this script once to build the local 'geodata.json' file
from the restcountries.com API.

To run: python -m app.data_loader
"""
import httpx
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# API URL
SOURCE_API_URL = "https://restcountries.com/v3.1/all?fields=cca2,cca3,region,subregion,borders"

# Output file
OUTPUT_FILE = Path(__file__).parent / "geodata.json"


def fetch_country_data():
    """Fetches raw data from the restcountries API."""
    logger.info(f"Fetching data from {SOURCE_API_URL}...")
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(SOURCE_API_URL)
            response.raise_for_status()  # Raise an exception for bad status codes
            logger.info("Successfully fetched raw country data.")
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    return None


def process_data(raw_data: list) -> dict:
    """Processes raw data into the required geo-data format."""
    logger.info("Processing raw data...")
    
    # 1. Build a map of CCA3 -> CCA2 codes (for border conversion)
    # The borders list uses 3-letter codes, but we use 2-letter codes
    cca3_to_cca2_map = {
        country['cca3']: country['cca2']
        for country in raw_data if 'cca3' in country and 'cca2' in country
    }
    
    geo_data = {}
    
    # 2. Build the main data dictionary
    for country in raw_data:
        cca2 = country.get('cca2')
        if not cca2:
            continue
            
        # Convert border cca3 codes to cca2 codes
        neighbor_cca3_list = country.get('borders', [])
        neighbor_cca2_list = [
            cca3_to_cca2_map.get(border_cca3)
            for border_cca3 in neighbor_cca3_list
            if cca3_to_cca2_map.get(border_cca3)  # Ensure the border exists in our map
        ]

        geo_data[cca2] = {
            "region": country.get('region', 'Unknown'),
            "subregion": country.get('subregion', 'Unknown'),
            "neighbors": neighbor_cca2_list
        }
    
    logger.info(f"Processed {len(geo_data)} countries.")
    return geo_data


def save_data(data: dict):
    """Saves the processed data to a JSON file."""
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Successfully saved data to {OUTPUT_FILE}")
    except IOError as e:
        logger.error(f"Failed to write to file: {e}")


def main():
    """Main function to run the data loader."""
    raw_data = fetch_country_data()
    if raw_data:
        processed_data = process_data(raw_data)
        if processed_data:
            save_data(processed_data)


if __name__ == "__main__":
    main()