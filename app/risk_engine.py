"""
Risk Assessment Engine
"""
from typing import List, Tuple
from app.models import RiskLevel, TriggeredRule
from app.config import settings
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# --- Data Loading ---
# Load the geo-data from the JSON file on startup
GEODATA_FILE = Path(__file__).parent / "geodata.json"
GEODATA = {}

if GEODATA_FILE.exists():
    try:
        with open(GEODATA_FILE, 'r', encoding='utf-8') as f:
            GEODATA = json.load(f)
        logger.info(f"Successfully loaded geo-data from {GEODATA_FILE}")
    except Exception as e:
        logger.error(f"CRITICAL: Failed to load {GEODATA_FILE}. Risk engine may not work. Error: {e}")
else:
    logger.warning(f"WARNING: {GEODATA_FILE} not found. Run data_loader.py.")
# --- End Data Loading ---


# --- New Helper Functions ---
def get_country_data(country_code: str) -> dict:
    """Get geo-data for a country code."""
    return GEODATA.get(country_code, {})

def get_country_region(country_code: str) -> str:
    """Get region for a country code."""
    return get_country_data(country_code).get("region", "Unknown")

def are_neighbors(country1: str, country2: str) -> bool:
    """Check if two countries are neighbors."""
    country1_data = get_country_data(country1)
    return country2 in country1_data.get("neighbors", [])

def are_same_region(country1: str, country2: str) -> bool:
    """Check if two countries are in the same region."""
    region1 = get_country_region(country1)
    region2 = get_country_region(country2)
    return region1 == region2 and region1 != "Unknown"
# --- End New Helper Functions ---


class RiskEngine:
    """Risk assessment engine."""
    
    def __init__(self):
        # This list is still in config.py, which is fine!
        self.high_risk_countries = settings.HIGH_RISK_COUNTRIES
    
    def assess_risk(
        self,
        user_country: str,
        ip_country: str,
        geoip_confidence: float
    ) -> Tuple[int, RiskLevel, List[TriggeredRule], str]:
        """
        Assess risk based on country mismatch.
        (THIS ENTIRE FUNCTION REMAINS 100% THE SAME AS YOUR ORIGINAL)
        """
        triggered_rules: List[TriggeredRule] = []
        risk_score = 0
        
        # Rule 1: Check if countries match
        if user_country == ip_country:
            # Same country - LOW RISK
            logger.info(f"Same country: {user_country}")
            
            recommendation = "Transaction from registered country - proceed normally"
            risk_level = RiskLevel.LOW
            
            return risk_score, risk_level, triggered_rules, recommendation
        
        # Countries don't match - assess severity
        logger.info(f"Country mismatch: {user_country} -> {ip_country}")
        
        # Rule 2: Check for high-risk countries (This is the correct hierarchy)
        if ip_country in self.high_risk_countries:
            score = 100
            risk_score += score
            
            triggered_rules.append(TriggeredRule(
                rule_name="High-Risk Country Detection",
                severity=RiskLevel.CRITICAL,
                description=f"Transaction from high-risk jurisdiction: {ip_country}",
                score_contribution=score
            ))
            
            logger.warning(f"HIGH-RISK COUNTRY: {ip_country}")
            recommendation = "BLOCK - Transaction from high-risk jurisdiction, require manual verification"
            risk_level = RiskLevel.CRITICAL
            
            return risk_score, risk_level, triggered_rules, recommendation
        
        if user_country in self.high_risk_countries:
            score = 100
            risk_score += score
            
            triggered_rules.append(TriggeredRule(
                rule_name="High-Risk Country Registration",
                severity=RiskLevel.CRITICAL,
                description=f"User registered in high-risk jurisdiction: {user_country}",
                score_contribution=score
            ))
            
            logger.warning(f"USER FROM HIGH-RISK COUNTRY: {user_country}")
            recommendation = "BLOCK - User from high-risk jurisdiction, require manual verification"
            risk_level = RiskLevel.CRITICAL
            
            return risk_score, risk_level, triggered_rules, recommendation
        
        # Rule 3: Check if neighboring countries
        if are_neighbors(user_country, ip_country):
            score = 20
            risk_score += score
            
            triggered_rules.append(TriggeredRule(
                rule_name="Neighboring Country Access",
                severity=RiskLevel.MEDIUM,
                description=f"Transaction from neighboring country: {user_country} -> {ip_country}",
                score_contribution=score
            ))
            
            logger.info(f"Neighboring countries: {user_country} <-> {ip_country}")
            recommendation = "Allow - Transaction from neighboring country, monitor for patterns"
            risk_level = RiskLevel.MEDIUM
            
            return risk_score, risk_level, triggered_rules, recommendation
        
        # Rule 4: Check if same region (e.g., both in EU)
        if are_same_region(user_country, ip_country):
            score = 35
            risk_score += score
            
            region = get_country_region(user_country)
            triggered_rules.append(TriggeredRule(
                rule_name="Same Region Access",
                severity=RiskLevel.MEDIUM,
                description=f"Transaction within same region ({region}): {user_country} -> {ip_country}",
                score_contribution=score
            ))
            
            logger.info(f"Same region ({region}): {user_country} -> {ip_country}")
            recommendation = "Allow - Transaction within same region, likely travel or relocation"
            risk_level = RiskLevel.MEDIUM
            
            return risk_score, risk_level, triggered_rules, recommendation
        
        # Rule 5: Different regions (distant countries)
        score = 60
        risk_score += score
        
        user_region = get_country_region(user_country)
        ip_region = get_country_region(ip_country)
        
        triggered_rules.append(TriggeredRule(
            rule_name="Cross-Region Access",
            severity=RiskLevel.HIGH,
            description=f"Transaction from different region: {user_region} ({user_country}) -> {ip_region} ({ip_country})",
            score_contribution=score
        ))
        
        logger.warning(f"Different regions: {user_country} ({user_region}) -> {ip_country} ({ip_region})")
        recommendation = "Flag for review - Transaction from significantly different location"
        risk_level = RiskLevel.HIGH
        
        # Adjust confidence if GeoIP is uncertain
        if geoip_confidence < 0.8:
            risk_score = int(risk_score * 0.8)  # Reduce score by 20%
            recommendation += " (Note: GeoIP confidence is low, verify manually)"
        
        return risk_score, risk_level, triggered_rules, recommendation


# Global engine instance
risk_engine = RiskEngine()