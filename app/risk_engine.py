

from typing import List, Tuple
from app.models import RiskLevel, TriggeredRule
from app.config import settings
import logging
import redis.asyncio as aioredis  
from functools import lru_cache 

logger = logging.getLogger(__name__)

try:
    redis_pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL, decode_responses=True
    )
    logger.info("Redis connection pool created.")
except Exception as e:
    logger.error(f"CRITICAL: Failed to create Redis pool. Error: {e}")
    redis_pool = None



async def get_country_data(country_code: str) -> dict:
    """Get geo-data for a country code from Redis."""
    if not redis_pool:
        return {} # Fail safe
    try:
        async with aioredis.Redis(connection_pool=redis_pool) as r:
            # Get the entire HASH for the country
            data = await r.hgetall(f"geo:{country_code}")
            return data
    except Exception as e:
        logger.error(f"Redis get_country_data error: {e}")
        return {}

async def get_country_region(country_code: str) -> str:
    """Get region for a country code."""
    data = await get_country_data(country_code)
    return data.get("region", "Unknown")

async def are_neighbors(country1: str, country2: str) -> bool:
    """Check if two countries are neighbors."""
    data1 = await get_country_data(country1)
    # Get the neighbor string ("CA,MX") and check if country2 is in it
    neighbors_str = data1.get("neighbors", "")
    return country2 in neighbors_str.split(",")

async def are_same_region(country1: str, country2: str) -> bool:
    """Check if two countries are in the same region."""
    region1 = await get_country_region(country1)
    region2 = await get_country_region(country2)
    return region1 == region2 and region1 != "Unknown"

class RiskEngine:
    """Risk assessment engine."""
    
    def __init__(self):
        self.high_risk_countries = settings.HIGH_RISK_COUNTRIES
    
    async def assess_risk(
        self,
        user_country: str,
        ip_country: str,
        geoip_confidence: float
    ) -> Tuple[int, RiskLevel, List[TriggeredRule], str]:
        """
        Assess risk based on country mismatch.
        """
        triggered_rules: List[TriggeredRule] = []
        risk_score = 0
        
        # Rule 1: Check if countries match
        if user_country == ip_country:
            logger.info(f"Same country: {user_country}")
            recommendation = "Transaction from registered country - proceed normally"
            risk_level = RiskLevel.LOW
            return risk_score, risk_level, triggered_rules, recommendation
        
        logger.info(f"Country mismatch: {user_country} -> {ip_country}")
        
        # Rule 2: Check for high-risk countries
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
        if await are_neighbors(user_country, ip_country):
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
        if await are_same_region(user_country, ip_country):
            score = 35
            region = await get_country_region(user_country)
            risk_score += score 
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
        user_region = await get_country_region(user_country)
        ip_region = await get_country_region(ip_country)
        risk_score += score 
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
            risk_score = int(risk_score * 0.8)
            recommendation += " (Note: GeoIP confidence is low, verify manually)"
        
        return risk_score, risk_level, triggered_rules, recommendation

# Global engine instance
risk_engine = RiskEngine()