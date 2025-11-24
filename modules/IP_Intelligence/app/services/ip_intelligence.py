# app/services/ip_intelligence.py

from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

from app.database import (
    get_vpn_collection, 
    get_clean_collection, 
    get_tor_collection
)
from app.services.external_api import external_api
from app.models import RiskLevel, TriggeredRule, SecurityFlags
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# --- Helper Lists (hardcoded for speed, or could be in config) ---
HIGH_RISK_COUNTRIES = [
    "MM", "KP", "IR", "SY", "YE", "DZ", "AO", "BO", "BG",
    "CM", "CI", "HT", "KE", "LB", "LA", "MC", "NA", "NP",
    "SS", "VE", "VN", "RU"
]

# Simplified regions map for Rule 3/4
REGIONS = {
    "North America": ["US", "CA", "MX"],
    "Europe": ["GB", "FR", "DE", "ES", "IT", "NL", "SE", "NO", "DK", "FI", "PL"],
    # ... add more as needed
}

class IPIntelligenceService:
    """
    The Brain. Orchestrates DB lookups, API calls, and Risk Logic.
    """

    async def analyze_ip(self, ip: str, user_country: str) -> Dict[str, Any]:
        """
        Main entry point.
        Returns a dictionary compliant with ScreeningResponse fields.
        """
        
        # 1. DATABASE LOOKUP (The Waterfall)
        ip_data, source_type = await self._lookup_databases(ip)
        
        # 2. FALLBACK (External API)
        if not ip_data:
            logger.info(f"❓ IP {ip} not in DB. Calling API...")
            api_result = await external_api.fetch_ip_details(ip)
            
            if api_result:
                # 3. LEARN (Save to DB)
                await self._save_to_database(api_result)
                ip_data = api_result["geolocation"]
                
                # Standardize security flags from API result
                security_flags = api_result["security"]
            else:
                # Total failure (API down + DB empty)
                return self._construct_fallback_response(ip, user_country)
        else:
            # We found it in DB!
            logger.info(f"✅ Found IP {ip} in {source_type}")
            # Map DB security flags
            security_flags = self._extract_security_flags(ip_data, source_type)

        # 4. RULE ENGINE (Apply Logic)
        risk_score, risk_level, triggered_rules, recommendation = self._apply_rules(
            ip_data=ip_data,
            user_country=user_country,
            security=security_flags,
            source_type=source_type
        )

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "should_block": risk_level == RiskLevel.CRITICAL,
            "confidence": 0.99 if source_type else 0.90,
            "detected_country": ip_data.get("country_code", "XX"),
            "countries_match": user_country == ip_data.get("country_code"),
            "security": security_flags,
            "triggered_rules": triggered_rules,
            "recommendation": recommendation
        }

    async def _lookup_databases(self, ip: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Checks Tor -> VPN -> Clean collections.
        Returns: (data_dict, source_name)
        """
        # Step A: Check Tor (CRITICAL)
        tor_doc = await get_tor_collection().find_one({"ip": ip})
        if tor_doc:
            # Adapter: Convert Tor schema to standard schema
            return self._adapt_tor_schema(tor_doc), "tor_ips"

        # Step B: Check VPN (HIGH)
        vpn_doc = await get_vpn_collection().find_one({"ip": ip})
        if vpn_doc:
            return vpn_doc["geolocation"], "vpn_ips"

        # Step C: Check Clean (TRUST)
        clean_doc = await get_clean_collection().find_one({"ip": ip})
        if clean_doc:
            return clean_doc["geolocation"], "clean_ips"

        return None, None

    async def _save_to_database(self, api_result: Dict):
        """Saves new API data to the correct collection."""
        ip = api_result["ip"]
        is_risk = api_result["is_risk"]
        
        # Prepare the document (matching IPDocument schema)
        document = {
            "ip": ip,
            "type": "ipv4",
            "source": "vpnapi.io",
            "sources": ["vpnapi.io"],
            "first_seen": datetime.utcnow(),
            "last_seen": datetime.utcnow(),
            "confidence": 1,
            "is_active": True,
            "fetch_count": 1,
            "geolocation": api_result["geolocation"]
        }
        
        collection = get_vpn_collection() if is_risk else get_clean_collection()
        
        # Upsert: Update if exists, Insert if new
        await collection.update_one(
            {"ip": ip},
            {"$set": document},
            upsert=True
        )
        logger.info(f"💾 Saved {ip} to {'vpn_ips' if is_risk else 'clean_ips'}")

    def _apply_rules(self, ip_data: Dict, user_country: str, security: Dict, source_type: str):
        """
        The Rulebook. Returns (score, level, rules, recommendation).
        """
        rules = []
        score = 0
        ip_country = ip_data.get("country_code", "XX")
        
        # --- RULE 1: TOR (Critical) ---
        if security["is_tor"] or source_type == "tor_ips":
            score = 100
            rules.append(TriggeredRule(
                rule_name="Anonymizer Detected (Tor)",
                severity=RiskLevel.CRITICAL,
                description="Traffic from Tor network",
                score_contribution=100
            ))
            return score, RiskLevel.CRITICAL, rules, "BLOCK - Tor Network Detected"

        # --- RULE 2: SANCTIONS (Critical) ---
        if ip_country in HIGH_RISK_COUNTRIES or user_country in HIGH_RISK_COUNTRIES:
            score = 95
            rules.append(TriggeredRule(
                rule_name="Sanctioned Jurisdiction",
                severity=RiskLevel.CRITICAL,
                description=f"High-risk country involved: User={user_country}, IP={ip_country}",
                score_contribution=100
            ))
            return score, RiskLevel.CRITICAL, rules, "BLOCK - Sanctioned Jurisdiction"

        # --- RULE 3: VPN / PROXY (High) ---
        if security["is_vpn"] or security["is_proxy"] or source_type == "vpn_ips":
            # Geo-Masking Check (User in US + VPN in US)
            if user_country == ip_country:
                score = 85
                rules.append(TriggeredRule(
                    rule_name="Geo-Masking VPN",
                    severity=RiskLevel.HIGH,
                    description=f"VPN detected matching user country ({user_country}). Potential evasion.",
                    score_contribution=85
                ))
            else:
                score = 75
                rules.append(TriggeredRule(
                    rule_name="Commercial VPN",
                    severity=RiskLevel.HIGH,
                    description="Traffic from known VPN/Proxy",
                    score_contribution=75
                ))
        
        # --- RULE 4: GEOGRAPHIC MISMATCH ---
        if user_country != ip_country:
            # Check Neighbors (simplified logic for V4)
            # You can re-implement the 'are_neighbors' DB logic here if needed
            # For now, we use standard mismatch logic
            
            mismatch_score = 60
            # If we already flagged a VPN, we don't double count, but we add context
            if score < mismatch_score: 
                score = mismatch_score
            
            rules.append(TriggeredRule(
                rule_name="Location Mismatch",
                severity=RiskLevel.HIGH if score >= 60 else RiskLevel.MEDIUM,
                description=f"User ({user_country}) != IP ({ip_country})",
                score_contribution=mismatch_score
            ))

        # --- FINAL VERDICT ---
        if score == 0:
            return 0, RiskLevel.LOW, [], "Safe - Location Matches"
        
        level = RiskLevel.LOW
        if score >= 90: level = RiskLevel.CRITICAL
        elif score >= 60: level = RiskLevel.HIGH
        elif score >= 20: level = RiskLevel.MEDIUM
        
        rec = "Review Required"
        if level == RiskLevel.CRITICAL: rec = "BLOCK"
        elif level == RiskLevel.HIGH: rec = "Flag for Manual Review"
        elif level == RiskLevel.MEDIUM: rec = "Monitor"

        return score, level, rules, rec

    def _adapt_tor_schema(self, doc: Dict) -> Dict:
        """Adapts Tor DB schema to standard Geolocation schema."""
        geo = doc.get("geo", {})
        return {
            "country": geo.get("country"),
            "country_code": geo.get("country_code"),
            "city": geo.get("city"),
            "isp": "Tor Exit Node",
            "org": "Tor Project",
            "as_number": None
        }

    def _extract_security_flags(self, ip_data: Dict, source_type: str) -> Dict:
        """Determines flags based on source collection."""
        return {
            "is_vpn": source_type == "vpn_ips",
            "is_proxy": False, # Basic assumption for DB hits unless we store this detail
            "is_tor": source_type == "tor_ips",
            "is_relay": False
        }

    def _construct_fallback_response(self, ip, user_country):
        """Used when everything fails."""
        return {
            "risk_score": 50,
            "risk_level": RiskLevel.MEDIUM,
            "should_block": False,
            "confidence": 0,
            "detected_country": "XX",
            "countries_match": False,
            "security": {"is_vpn": False, "is_proxy": False, "is_tor": False},
            "triggered_rules": [],
            "recommendation": "Service Unavailable - Manual Check"
        }

# Global Instance
ip_intelligence = IPIntelligenceService()