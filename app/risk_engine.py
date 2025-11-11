# app/risk_engine.py (CORRECTED VERSION)

from typing import List, Tuple
from app.models import RiskLevel, TriggeredRule
from app.config import settings
import logging
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Redis Connection
try:
    redis_pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL, decode_responses=True
    )
except Exception as e:
    logger.error(f"CRITICAL: Failed to create Redis pool. Error: {e}")
    redis_pool = None

# Fallback data (if Redis fails)
FALLBACK_NEIGHBORS = {
    "US": ["CA", "MX"],
    "CA": ["US"],
    "MX": ["US"],
    "GB": ["IE"],
    "IE": ["GB"],
    "FR": ["BE", "DE", "ES", "IT", "CH"],
    "DE": ["FR", "NL", "BE", "AT", "CH", "PL", "CZ"],
}

FALLBACK_REGIONS = {
    "US": "North America", "CA": "North America", "MX": "North America",
    "GB": "Europe", "FR": "Europe", "DE": "Europe", "ES": "Europe",
    # Add more as needed
}

# Helper Functions
async def get_country_data(country_code: str) -> dict:
    """Get country data from Redis with error handling."""
    if not redis_pool or not country_code:
        return {}
    try:
        async with aioredis.Redis(connection_pool=redis_pool) as r:
            return await r.hgetall(f"geo:{country_code}")
    except Exception as e:
        logger.error(f"Redis error for {country_code}: {e}")
        return {}

async def get_country_region(country_code: str) -> str:
    """Get country region with Redis fallback."""
    data = await get_country_data(country_code)
    if data:
        return data.get("region", "Unknown")
    # Fallback
    return FALLBACK_REGIONS.get(country_code, "Unknown")

async def are_neighbors(country1: str, country2: str) -> bool:
    """Check if countries are neighbors with Redis fallback."""
    data1 = await get_country_data(country1)
    
    if data1:  # Redis success
        neighbors_str = data1.get("neighbors", "")
        return country2 in neighbors_str.split(",")
    
    # Redis failed, use fallback
    return country2 in FALLBACK_NEIGHBORS.get(country1, [])

async def are_same_region(country1: str, country2: str) -> bool:
    """Check if countries in same region with fallback."""
    region1 = await get_country_region(country1)
    region2 = await get_country_region(country2)
    return region1 == region2 and region1 != "Unknown"


class RiskEngine:
    """Risk assessment engine with layered security checks."""
    
    def __init__(self):
        self.high_risk_countries = settings.HIGH_RISK_COUNTRIES
    
    async def assess_risk(
        self,
        user_country: str,
        ip_country: str,
        geoip_confidence: float,
        is_vpn: bool = False,
        is_proxy: bool = False,
        is_tor: bool = False
    ) -> Tuple[int, RiskLevel, List[TriggeredRule], str]:
        """
        Assess transaction risk with layered security + geographic checks.
        
        Returns: (risk_score, risk_level, triggered_rules, recommendation)
        """
        triggered_rules: List[TriggeredRule] = []
        risk_score = 0
        
        # ═══════════════════════════════════════════════════════════
        # LAYER 1: CRITICAL SECURITY THREATS (Instant Block)
        # ═══════════════════════════════════════════════════════════
        
        # Rule 1a: TOR Network (Highest Priority)
        if is_tor:
            score = 100
            triggered_rules.append(TriggeredRule(
                rule_name="Anonymizer Detection (TOR)",
                severity=RiskLevel.CRITICAL,
                description="Traffic routed through TOR anonymity network",
                score_contribution=score
            ))
            logger.critical(f"TOR DETECTED: user={user_country}, ip={ip_country}")
            return 100, RiskLevel.CRITICAL, triggered_rules, "BLOCK - Anonymizer network detected"
        
        # Rule 1b: IP from High-Risk Country
        if ip_country in self.high_risk_countries:
            score = 100
            triggered_rules.append(TriggeredRule(
                rule_name="High-Risk Jurisdiction (IP Location)",
                severity=RiskLevel.CRITICAL,
                description=f"Transaction originates from high-risk country: {ip_country}",
                score_contribution=score
            ))
            logger.critical(f"HIGH-RISK IP: {ip_country}")
            return 100, RiskLevel.CRITICAL, triggered_rules, "BLOCK - High-risk jurisdiction detected"
        
        # Rule 1c: User Registered in High-Risk Country
        if user_country in self.high_risk_countries:
            score = 100
            triggered_rules.append(TriggeredRule(
                rule_name="High-Risk Jurisdiction (User Registration)",
                severity=RiskLevel.CRITICAL,
                description=f"User registered in high-risk country: {user_country}",
                score_contribution=score
            ))
            logger.critical(f"HIGH-RISK USER: {user_country}")
            return 100, RiskLevel.CRITICAL, triggered_rules, "BLOCK - User from high-risk jurisdiction"
        
        # ═══════════════════════════════════════════════════════════
        # LAYER 2: SECURITY FLAGS (Additive Risk)
        # ═══════════════════════════════════════════════════════════
        
        # Rule 2: VPN/Proxy Detection
        if is_vpn or is_proxy:
            score = 75
            risk_score = min(100, risk_score + score)
            
            triggered_rules.append(TriggeredRule(
                rule_name="Proxy/VPN Detection",
                severity=RiskLevel.HIGH,
                description="Traffic routed through VPN or proxy service",
                score_contribution=score
            ))
            logger.warning(f"VPN/PROXY DETECTED: user={user_country}, ip={ip_country}")
            # Don't return yet - continue to geographic checks
        
        # ═══════════════════════════════════════════════════════════
        # LAYER 3: GEOGRAPHIC RISK ASSESSMENT
        # ═══════════════════════════════════════════════════════════
        
        # Rule 3a: Same Country (Base Case)
        if user_country == ip_country:
            # If no security flags were triggered, this is LOW risk
            if risk_score == 0:
                logger.info(f"SAME COUNTRY: {user_country} (no security flags)")
                return 0, RiskLevel.LOW, [], "Transaction from registered country - proceed normally"
            
            # Same country BUT security flags exist (e.g., VPN)
            # Score already set by security checks above (e.g., 75 for VPN)
            risk_level = self._score_to_level(risk_score)
            recommendation = "Same country but security concerns detected - flag for review"
            logger.warning(f"SAME COUNTRY + SECURITY FLAGS: {user_country}, score={risk_score}")
            return risk_score, risk_level, triggered_rules, recommendation
        
        # Countries don't match - assess geographic distance
        logger.info(f"COUNTRY MISMATCH: {user_country} -> {ip_country}")
        
        # Rule 3b: Neighboring Countries
        if await are_neighbors(user_country, ip_country):
            score = 20
            risk_score = min(100, risk_score + score)
            
            triggered_rules.append(TriggeredRule(
                rule_name="Neighboring Country Access",
                severity=RiskLevel.MEDIUM,
                description=f"Transaction from neighboring country: {user_country} -> {ip_country}",
                score_contribution=score
            ))
            logger.info(f"NEIGHBORS: {user_country} <-> {ip_country}")
            
            risk_level = self._score_to_level(risk_score)
            recommendation = "Neighboring country access - likely legitimate travel"
            return risk_score, risk_level, triggered_rules, recommendation
        
        # Rule 3c: Same Region (e.g., both EU countries)
        if await are_same_region(user_country, ip_country):
            score = 35
            risk_score = min(100, risk_score + score)
            
            region = await get_country_region(user_country)
            triggered_rules.append(TriggeredRule(
                rule_name="Same Region Access",
                severity=RiskLevel.MEDIUM,
                description=f"Transaction within {region}: {user_country} -> {ip_country}",
                score_contribution=score
            ))
            logger.info(f"SAME REGION ({region}): {user_country} -> {ip_country}")
            
            risk_level = self._score_to_level(risk_score)
            recommendation = "Same region access - monitor for patterns"
            return risk_score, risk_level, triggered_rules, recommendation
        
        # Rule 3d: Different Regions (Distant Countries)
        score = 60
        risk_score = min(100, risk_score + score)
        
        user_region = await get_country_region(user_country)
        ip_region = await get_country_region(ip_country)
        
        triggered_rules.append(TriggeredRule(
            rule_name="Cross-Region Access",
            severity=RiskLevel.HIGH,
            description=f"Transaction across regions: {user_region} ({user_country}) -> {ip_region} ({ip_country})",
            score_contribution=score
        ))
        logger.warning(f"CROSS-REGION: {user_country} ({user_region}) -> {ip_country} ({ip_region})")
        
        risk_level = self._score_to_level(risk_score)
        recommendation = "Cross-region transaction - flag for manual review"
        
        # Adjust for GeoIP confidence
        if geoip_confidence < 0.8:
            recommendation += " (Low GeoIP confidence - verify location)"
        
        return risk_score, risk_level, triggered_rules, recommendation
    
    def _score_to_level(self, score: int) -> RiskLevel:
        """
        Map risk score to risk level.
        
        Scoring:
        - 0-19: LOW
        - 20-59: MEDIUM
        - 60-89: HIGH
        - 90-100: CRITICAL
        """
        if score >= 90:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 20:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW


# Global instance
risk_engine = RiskEngine()