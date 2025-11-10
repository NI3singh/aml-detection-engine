
# app/risk_engine.py

from typing import List, Tuple, Optional
from app.models import RiskLevel, TriggeredRule
from app.config import settings
import logging
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# --- Redis Connection (Unchanged from V2) ---
try:
    redis_pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL, decode_responses=True
    )
except Exception as e:
    logger.error(f"CRITICAL: Failed to create Redis pool. Error: {e}")
    redis_pool = None
# -------------------------------------------

# --- ASYNC Helper Functions (Unchanged from V2) ---
async def get_country_data(country_code: str) -> dict:
    if not redis_pool or not country_code: return {}
    try:
        async with aioredis.Redis(connection_pool=redis_pool) as r:
            return await r.hgetall(f"geo:{country_code}")
    except Exception as e:
        logger.error(f"Redis error: {e}")
        return {}

async def get_country_region(country_code: str) -> str:
    data = await get_country_data(country_code)
    return data.get("region", "Unknown")

async def are_neighbors(country1: str, country2: str) -> bool:
    data1 = await get_country_data(country1)
    neighbors_str = data1.get("neighbors", "")
    return country2 in neighbors_str.split(",")

async def are_same_region(country1: str, country2: str) -> bool:
    region1 = await get_country_region(country1)
    region2 = await get_country_region(country2)
    return region1 == region2 and region1 != "Unknown"
# --------------------------------------------------


class RiskEngine:
    """Risk assessment engine."""
    
    def __init__(self):
        self.high_risk_countries = settings.HIGH_RISK_COUNTRIES
    
    async def assess_risk(
        self,
        user_country: str,
        ip_country: str,
        geoip_confidence: float,
        # --- NEW PARAMETERS ---
        is_vpn: bool = False,
        is_tor: bool = False,
        is_proxy: bool = False
        # ----------------------
    ) -> Tuple[int, RiskLevel, List[TriggeredRule], str]:
        """
        Assess risk based on location and security flags.
        """
        triggered_rules: List[TriggeredRule] = []
        risk_score = 0

        # --- NEW SECURITY RULES (THESE RUN FIRST) ---
        
        # Security Rule 1: TOR Network (Instant Block)
        if is_tor:
            score = 100
            risk_score += score
            triggered_rules.append(TriggeredRule(
                rule_name="Anonymizer Detection (TOR)",
                severity=RiskLevel.CRITICAL,
                description="Traffic from TOR anonymity network",
                score_contribution=score
            ))
            logger.warning(f"CRITICAL THREAT: TOR detected for user from {user_country}")
            return risk_score, RiskLevel.CRITICAL, triggered_rules, "BLOCK - Anonymizer detected"
        if ip_country in self.high_risk_countries:
            score = 100
            risk_score = min(100, risk_score + score)
            triggered_rules.append(TriggeredRule(
                rule_name="High-Risk Jurisdiction (IP)",
                severity=RiskLevel.CRITICAL,
                description=f"Activity from high-risk jurisdiction: {ip_country}",
                score_contribution=score
            ))
            return risk_score, RiskLevel.CRITICAL, triggered_rules, "BLOCK - High-risk IP detected"

        # Check 2b: Is the USER from a blocked country?
        if user_country in self.high_risk_countries:
            score = 100
            risk_score = min(100, risk_score + score)
            triggered_rules.append(TriggeredRule(
                rule_name="High-Risk Jurisdiction (User)",
                severity=RiskLevel.CRITICAL,
                description=f"User registered in high-risk jurisdiction: {user_country}",
                score_contribution=score
            ))
            return risk_score, RiskLevel.CRITICAL, triggered_rules, "BLOCK - High-risk user detected"
        
        # Security Rule 2: VPN/Proxy (High Risk Flag)
        if is_vpn or is_proxy:
            score = 75
            risk_score += score
            triggered_rules.append(TriggeredRule(
                rule_name="Proxy/VPN Detection",
                severity=RiskLevel.HIGH,
                description="Traffic from known VPN or Proxy service",
                score_contribution=score
            ))
            # We don't return immediately here, we let it continue to check geo-location too.
            # This might result in a score > 100 if they also have a geo-mismatch, which is fine.
            logger.warning(f"VPN detected for user from {user_country}")

        # --------------------------------------------
        
        # --- EXISTING GEOGRAPHIC RULES BELOW ---
        
        # (Geo Rule 1: Same Country - Moved down slightly to accommodate VPN check)
        if user_country == ip_country:
            if risk_score == 0: # Only return Low Risk if NO VPN was detected above
                return 0, RiskLevel.LOW, [], "Transaction from registered country - proceed normally"
            else:
                 # If VPN was detected but country matches, it's still high risk
                 return risk_score, RiskLevel.HIGH, triggered_rules, "Flag for review - VPN used from correct country"

        # Geo Rule 2: High Risk Country
        if ip_country in self.high_risk_countries:
            score = 100
            risk_score = min(100, risk_score + score) # Cap score at 100
            triggered_rules.append(TriggeredRule(
                rule_name="High-Risk Country Detection",
                severity=RiskLevel.CRITICAL,
                description=f"Transaction from high-risk jurisdiction: {ip_country}",
                score_contribution=score
            ))
            return risk_score, RiskLevel.CRITICAL, triggered_rules, "BLOCK - High-risk jurisdiction"
            
        # ... (The rest of your existing rules for neighbors/regions remain mostly the same)
        # Just ensure you add 'await' as we did in V2.
        
        # Geo Rule 3: Neighbors
        if await are_neighbors(user_country, ip_country):
             score = 20
             risk_score = min(100, risk_score + score)
             triggered_rules.append(TriggeredRule(rule_name="Neighboring Country", severity=RiskLevel.MEDIUM, description=f"Neighbor: {user_country}->{ip_country}", score_contribution=score))
             return risk_score, RiskLevel(self._get_level(risk_score)), triggered_rules, "Allow with monitoring"

        # Geo Rule 4: Same Region
        if await are_same_region(user_country, ip_country):
             score = 35
             risk_score = min(100, risk_score + score)
             triggered_rules.append(TriggeredRule(rule_name="Same Region", severity=RiskLevel.MEDIUM, description=f"Same Region: {user_country}->{ip_country}", score_contribution=score))
             return risk_score, RiskLevel(self._get_level(risk_score)), triggered_rules, "Allow with monitoring"

        # Geo Rule 5: Different Region
        score = 60
        risk_score = min(100, risk_score + score)
        triggered_rules.append(TriggeredRule(rule_name="Cross-Region Access", severity=RiskLevel.HIGH, description=f"Cross-Region: {user_country}->{ip_country}", score_contribution=score))
        
        return risk_score, RiskLevel(self._get_level(risk_score)), triggered_rules, "Flag for review - Location mismatch"

    def _get_level(self, score: int) -> RiskLevel:
        """Helper to determine risk level from total score."""
        if score >= 90: return RiskLevel.CRITICAL
        if score >= 60: return RiskLevel.HIGH
        if score >= 20: return RiskLevel.MEDIUM
        return RiskLevel.LOW

risk_engine = RiskEngine()