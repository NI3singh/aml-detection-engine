"""
Large Transaction Rule

Detects transactions that exceed a specified threshold amount.

Why This Rule:
- Large transactions are common money laundering indicator
- Helps identify structuring attempts (splitting large amounts)
- Required by most AML regulations

Logic:
- If transaction.amount > threshold → Alert
- Configurable threshold per organization
- Severity based on how much threshold is exceeded
"""

from typing import Dict, Any
from decimal import Decimal

from app.rules.base import BaseRule
from app.models.transaction import Transaction
from app.utils.constants import AlertSeverity


class LargeTransactionRule(BaseRule):
    """
    Rule to detect transactions exceeding a threshold amount.
    
    Parameters:
    - threshold_amount: Amount threshold (default: 10,000)
    - currency: Currency for threshold (default: USD)
    
    Severity Logic:
    - 1-2x threshold: HIGH
    - 2-5x threshold: HIGH
    - 5x+ threshold: CRITICAL
    """
    
    async def evaluate(self, transaction: Transaction) -> bool:
        """
        Check if transaction amount exceeds threshold.
        
        Args:
            transaction: Transaction to evaluate
            
        Returns:
            bool: True if amount exceeds threshold
        """
        threshold = Decimal(str(self.get_parameter('threshold_amount', 10000)))
        
        # Convert transaction amount to Decimal for precise comparison
        amount = Decimal(str(transaction.amount))
        
        return amount > threshold
    
    async def get_alert_details(self, transaction: Transaction) -> Dict[str, Any]:
        """
        Get details about why alert was triggered.
        
        Args:
            transaction: Transaction that triggered alert
            
        Returns:
            dict: Alert details
        """
        threshold = Decimal(str(self.get_parameter('threshold_amount', 10000)))
        amount = Decimal(str(transaction.amount))
        exceeded_by = amount - threshold
        exceeded_percentage = (exceeded_by / threshold) * 100
        
        return {
            "rule_name": "Large Transaction",
            "threshold_amount": float(threshold),
            "actual_amount": float(amount),
            "currency": transaction.currency.value,
            "exceeded_by": float(exceeded_by),
            "exceeded_percentage": float(exceeded_percentage),
            "sender_id": transaction.sender_id,
            "sender_name": transaction.sender_name,
            "receiver_id": transaction.receiver_id,
            "receiver_name": transaction.receiver_name,
            "transaction_type": transaction.transaction_type.value,
            "description": "Transaction amount significantly exceeds threshold"
        }
    
    def get_severity(self, transaction: Transaction) -> AlertSeverity:
        """
        Determine severity based on how much threshold was exceeded.
        
        Args:
            transaction: Transaction that triggered alert
            
        Returns:
            AlertSeverity: Calculated severity
        """
        threshold = Decimal(str(self.get_parameter('threshold_amount', 10000)))
        amount = Decimal(str(transaction.amount))
        
        # Calculate multiplier
        multiplier = amount / threshold
        
        if multiplier >= 5:
            return AlertSeverity.CRITICAL
        elif multiplier >= 2:
            return AlertSeverity.HIGH
        else:
            return AlertSeverity.HIGH