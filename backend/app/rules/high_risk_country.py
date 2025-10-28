"""
High-Risk Country Rule

Detects transactions involving sanctioned or high-risk countries.

Why This Rule:
- Regulatory requirement (OFAC, EU sanctions, etc.)
- Prevents violations of international sanctions
- Identifies potential terrorist financing

Logic:
- Check if sender OR receiver country is in high-risk list
- Configurable list per organization
- Always CRITICAL severity (sanctions violations are serious)
"""

from typing import Dict, Any, List

from app.rules.base import BaseRule
from app.models.transaction import Transaction
from app.utils.constants import AlertSeverity, HIGH_RISK_COUNTRIES


class HighRiskCountryRule(BaseRule):
    """
    Rule to detect transactions involving high-risk countries.
    
    Parameters:
    - high_risk_countries: List of country codes (default: from constants)
    
    Severity Logic:
    - Always CRITICAL (sanctions compliance is mandatory)
    """
    
    async def evaluate(self, transaction: Transaction) -> bool:
        """
        Check if transaction involves high-risk country.
        
        Args:
            transaction: Transaction to evaluate
            
        Returns:
            bool: True if sender or receiver is in high-risk country
        """
        # Get high-risk countries list
        high_risk_countries = set(
            self.get_parameter('high_risk_countries', list(HIGH_RISK_COUNTRIES))
        )
        
        # Check both sender and receiver countries
        sender_high_risk = transaction.sender_country.upper() in high_risk_countries
        receiver_high_risk = transaction.receiver_country.upper() in high_risk_countries
        
        return sender_high_risk or receiver_high_risk
    
    async def get_alert_details(self, transaction: Transaction) -> Dict[str, Any]:
        """
        Get details about the high-risk country involvement.
        
        Args:
            transaction: Transaction that triggered alert
            
        Returns:
            dict: Alert details
        """
        high_risk_countries = set(
            self.get_parameter('high_risk_countries', list(HIGH_RISK_COUNTRIES))
        )
        
        sender_high_risk = transaction.sender_country.upper() in high_risk_countries
        receiver_high_risk = transaction.receiver_country.upper() in high_risk_countries
        
        # Determine which party is high-risk
        high_risk_parties = []
        if sender_high_risk:
            high_risk_parties.append("sender")
        if receiver_high_risk:
            high_risk_parties.append("receiver")
        
        return {
            "rule_name": "High-Risk Country",
            "sender_country": transaction.sender_country,
            "receiver_country": transaction.receiver_country,
            "sender_high_risk": sender_high_risk,
            "receiver_high_risk": receiver_high_risk,
            "high_risk_party": ", ".join(high_risk_parties),
            "amount": float(transaction.amount),
            "currency": transaction.currency.value,
            "sender_id": transaction.sender_id,
            "sender_name": transaction.sender_name,
            "receiver_id": transaction.receiver_id,
            "receiver_name": transaction.receiver_name,
            "transaction_type": transaction.transaction_type.value,
            "description": f"Transaction involves high-risk jurisdiction: {', '.join(high_risk_parties)}"
        }
    
    def get_severity(self, transaction: Transaction) -> AlertSeverity:
        """
        Always return CRITICAL for sanctions compliance.
        
        Args:
            transaction: Transaction that triggered alert
            
        Returns:
            AlertSeverity: CRITICAL
        """
        return AlertSeverity.CRITICAL