"""
Risk Assessment Engine
"""
from typing import List, Tuple
from app.models import RiskLevel, TriggeredRule
from app.config import settings
import logging

logger = logging.getLogger(__name__)


# Geographic regions (simplified for V1)
REGIONS = {
    "North America": ["US", "CA", "MX"],
    "Europe": [
        "GB", "FR", "DE", "ES", "IT", "NL", "BE", "PT", "IE", "AT", 
        "CH", "SE", "NO", "DK", "FI", "PL", "CZ", "GR", "HU"
    ],
    "South America": ["BR", "AR", "CL", "CO", "PE", "VE", "UY", "EC"],
    "Asia Pacific": ["AU", "NZ", "JP", "SG", "HK", "KR", "MY", "TH"],
    "Middle East": ["AE", "SA", "IL", "QA", "KW", "OM", "BH"],
    "South Asia": ["IN", "BD", "LK", "NP"],
    "Africa": ["ZA", "EG", "NG", "KE", "GH", "MA"],
}

# Neighboring countries (share border or very close)
NEIGHBORS = {
    "US": ["CA", "MX"],
    "CA": ["US"],
    "MX": ["US"],
    "GB": ["IE"],
    "IE": ["GB"],
    "FR": ["BE", "DE", "ES", "IT", "CH", "LU"],
    "DE": ["FR", "NL", "BE", "AT", "CH", "PL", "CZ"],
    "ES": ["FR", "PT"],
    "PT": ["ES"],
    "IT": ["FR", "CH", "AT"],
    "AU": ["NZ"],
    "NZ": ["AU"],
    # Add more as needed
}


def get_country_region(country_code: str) -> str:
    """Get region for a country code."""
    for region, countries in REGIONS.items():
        if country_code in countries:
            return region
    return "Unknown"


def are_neighbors(country1: str, country2: str) -> bool:
    """Check if two countries are neighbors."""
    return (
        country2 in NEIGHBORS.get(country1, []) or
        country1 in NEIGHBORS.get(country2, [])
    )


def are_same_region(country1: str, country2: str) -> bool:
    """Check if two countries are in the same region."""
    region1 = get_country_region(country1)
    region2 = get_country_region(country2)
    return region1 == region2 and region1 != "Unknown"


class RiskEngine:
    """Risk assessment engine."""
    
    def __init__(self):
        self.high_risk_countries = settings.HIGH_RISK_COUNTRIES
    
    def assess_risk(
        self,
        user_country: str,
        ip_country: str,
        geoip_confidence: float
    ) -> Tuple[int, RiskLevel, List[TriggeredRule], str]:
        """
        Assess risk based on country mismatch.
        
        Args:
            user_country: User's registered country
            ip_country: Country detected from IP
            geoip_confidence: Confidence in GeoIP lookup (0-1)
            
        Returns:
            Tuple of (risk_score, risk_level, triggered_rules, recommendation)
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