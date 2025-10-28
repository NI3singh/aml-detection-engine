"""
High-Frequency Transaction Rule

Detects accounts sending many transactions in a short time period.

Why This Rule:
- Structuring/smurfing detection (splitting large amounts into many small transactions)
- Identifies compromised accounts being used for money laundering
- Detects automated fraud schemes

Logic:
- Count transactions from same sender in time window
- If count > threshold → Alert
- Configurable time window and threshold
"""

from typing import Dict, Any
from datetime import timedelta

from app.rules.base import BaseRule
from app.models.transaction import Transaction
from app.utils.constants import AlertSeverity
from app.crud.transaction import get_transactions_by_sender


class HighFrequencyRule(BaseRule):
    """
    Rule to detect high-frequency transactions from same sender.
    
    Parameters:
    - max_transactions: Maximum allowed transactions (default: 10)
    - time_window_minutes: Time window to check (default: 60)
    
    Severity Logic:
    - 10-20 transactions: MEDIUM
    - 20-50 transactions: HIGH
    - 50+ transactions: CRITICAL
    """
    
    async def evaluate(self, transaction: Transaction) -> bool:
        """
        Check if sender has too many recent transactions.
        
        Args:
            transaction: Transaction to evaluate
            
        Returns:
            bool: True if frequency exceeds threshold
        """
        max_transactions = self.get_parameter('max_transactions', 10)
        time_window_minutes = self.get_parameter('time_window_minutes', 60)
        
        # Calculate time range
        time_to = transaction.timestamp
        time_from = time_to - timedelta(minutes=time_window_minutes)
        
        # Get recent transactions from same sender
        recent_transactions = await get_transactions_by_sender(
            db=self.db,
            sender_id=transaction.sender_id,
            organization_id=self.organization_id,
            time_from=time_from,
            time_to=time_to
        )
        
        # Check if count exceeds threshold
        transaction_count = len(recent_transactions)
        
        return transaction_count > max_transactions
    
    async def get_alert_details(self, transaction: Transaction) -> Dict[str, Any]:
        """
        Get details about the high-frequency activity.
        
        Args:
            transaction: Transaction that triggered alert
            
        Returns:
            dict: Alert details
        """
        max_transactions = self.get_parameter('max_transactions', 10)
        time_window_minutes = self.get_parameter('time_window_minutes', 60)
        
        # Get recent transactions
        time_to = transaction.timestamp
        time_from = time_to - timedelta(minutes=time_window_minutes)
        
        recent_transactions = await get_transactions_by_sender(
            db=self.db,
            sender_id=transaction.sender_id,
            organization_id=self.organization_id,
            time_from=time_from,
            time_to=time_to
        )
        
        transaction_count = len(recent_transactions)
        
        # Calculate total amount transacted
        total_amount = sum(float(txn.amount) for txn in recent_transactions)
        
        # Get transaction IDs
        transaction_ids = [str(txn.id) for txn in recent_transactions[:20]]  # First 20
        
        return {
            "rule_name": "High-Frequency Transactions",
            "threshold_count": max_transactions,
            "actual_count": transaction_count,
            "exceeded_by": transaction_count - max_transactions,
            "time_window_minutes": time_window_minutes,
            "sender_id": transaction.sender_id,
            "sender_name": transaction.sender_name,
            "total_amount_in_window": total_amount,
            "currency": transaction.currency.value,
            "sample_transaction_ids": transaction_ids,
            "description": f"Account sent {transaction_count} transactions in {time_window_minutes} minutes"
        }
    
    def get_severity(self, transaction: Transaction) -> AlertSeverity:
        """
        Determine severity based on transaction frequency.
        
        Note: We can't make this async in the base class design,
        so we'll return MEDIUM by default and let the engine override if needed.
        
        Args:
            transaction: Transaction that triggered alert
            
        Returns:
            AlertSeverity: MEDIUM severity
        """
        # Default to MEDIUM
        # The engine will calculate actual severity based on count
        return AlertSeverity.MEDIUM
    
    async def get_severity_async(self, transaction: Transaction) -> AlertSeverity:
        """
        Async version to properly calculate severity.
        
        Args:
            transaction: Transaction that triggered alert
            
        Returns:
            AlertSeverity: Calculated severity
        """
        max_transactions = self.get_parameter('max_transactions', 10)
        time_window_minutes = self.get_parameter('time_window_minutes', 60)
        
        time_to = transaction.timestamp
        time_from = time_to - timedelta(minutes=time_window_minutes)
        
        recent_transactions = await get_transactions_by_sender(
            db=self.db,
            sender_id=transaction.sender_id,
            organization_id=self.organization_id,
            time_from=time_from,
            time_to=time_to
        )
        
        transaction_count = len(recent_transactions)
        
        if transaction_count >= 50:
            return AlertSeverity.CRITICAL
        elif transaction_count >= 20:
            return AlertSeverity.HIGH
        else:
            return AlertSeverity.MEDIUM