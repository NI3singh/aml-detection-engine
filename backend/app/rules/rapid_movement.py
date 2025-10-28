"""
Rapid Movement Rule

Detects money moving quickly through multiple accounts (layering).

Why This Rule:
- Detects "layering" phase of money laundering
- Identifies attempts to obscure money trail
- Catches mule account networks

Logic:
- Track transaction chains: A→B→C→D
- If chain exceeds max hops in time window → Alert
- Example: Money moves through 4+ accounts in 30 minutes

This is the most complex rule as it requires graph traversal.
"""

from typing import Dict, Any, List, Set
from datetime import timedelta
from decimal import Decimal

from app.rules.base import BaseRule
from app.models.transaction import Transaction
from app.utils.constants import AlertSeverity
from app.crud.transaction import get_recent_transactions_by_accounts


class RapidMovementRule(BaseRule):
    """
    Rule to detect rapid movement of money through multiple accounts.
    
    Parameters:
    - max_hops: Maximum allowed hops (default: 3)
    - time_window_minutes: Time window to check (default: 30)
    
    Severity Logic:
    - 3-4 hops: HIGH
    - 5+ hops: CRITICAL
    """
    
    async def evaluate(self, transaction: Transaction) -> bool:
        """
        Check if transaction is part of rapid movement chain.
        
        This traces money flow: A→B→C→D
        - Current transaction: C→D
        - We check if there was: A→B→C recently
        
        Args:
            transaction: Transaction to evaluate
            
        Returns:
            bool: True if part of suspicious chain
        """
        max_hops = self.get_parameter('max_hops', 3)
        time_window_minutes = self.get_parameter('time_window_minutes', 30)
        
        # Build transaction chain
        chain = await self._build_transaction_chain(
            transaction=transaction,
            max_hops=max_hops,
            time_window_minutes=time_window_minutes
        )
        
        # Alert if chain exceeds max hops
        return len(chain) > max_hops
    
    async def _build_transaction_chain(
        self,
        transaction: Transaction,
        max_hops: int,
        time_window_minutes: int
    ) -> List[Transaction]:
        """
        Build the chain of transactions leading to this one.
        
        Algorithm:
        1. Start with current transaction (C→D)
        2. Find transactions where receiver = our sender (B→C)
        3. Continue backwards until no more found or max depth
        
        Args:
            transaction: Current transaction
            max_hops: Maximum depth to search
            time_window_minutes: Time window
            
        Returns:
            List[Transaction]: Chain of transactions
        """
        chain = [transaction]
        current_sender = transaction.sender_id
        visited_accounts: Set[str] = {transaction.receiver_id, transaction.sender_id}
        
        # Reference time for the chain
        reference_time = transaction.timestamp
        time_from = reference_time - timedelta(minutes=time_window_minutes)
        
        # Build chain backwards
        for _ in range(max_hops):
            # Find transactions where receiver became our sender
            # This means: someone sent to current_sender
            recent_txns = await get_recent_transactions_by_accounts(
                db=self.db,
                account_ids=[current_sender],
                organization_id=self.organization_id,
                time_window_minutes=time_window_minutes,
                reference_time=reference_time
            )
            
            # Filter to transactions where current_sender is receiver
            feeding_txns = [
                txn for txn in recent_txns
                if txn.receiver_id == current_sender
                and txn.sender_id not in visited_accounts  # Avoid cycles
                and txn.timestamp < reference_time  # Must be before current
            ]
            
            if not feeding_txns:
                break  # Chain ends here
            
            # Take the most recent feeding transaction
            prev_txn = max(feeding_txns, key=lambda t: t.timestamp)
            chain.insert(0, prev_txn)  # Add to beginning of chain
            
            # Move backwards
            current_sender = prev_txn.sender_id
            visited_accounts.add(prev_txn.sender_id)
            reference_time = prev_txn.timestamp
        
        return chain
    
    async def get_alert_details(self, transaction: Transaction) -> Dict[str, Any]:
        """
        Get details about the rapid movement chain.
        
        Args:
            transaction: Transaction that triggered alert
            
        Returns:
            dict: Alert details
        """
        max_hops = self.get_parameter('max_hops', 3)
        time_window_minutes = self.get_parameter('time_window_minutes', 30)
        
        # Build chain
        chain = await self._build_transaction_chain(
            transaction=transaction,
            max_hops=max_hops * 2,  # Get full chain for details
            time_window_minutes=time_window_minutes
        )
        
        # Extract account flow
        account_chain = []
        for txn in chain:
            if not account_chain:
                account_chain.append(txn.sender_id)
            account_chain.append(txn.receiver_id)
        
        # Calculate time span and total amount
        if len(chain) > 1:
            time_span = (chain[-1].timestamp - chain[0].timestamp).total_seconds() / 60
            total_amount = sum(float(txn.amount) for txn in chain)
        else:
            time_span = 0
            total_amount = float(transaction.amount)
        
        return {
            "rule_name": "Rapid Money Movement",
            "max_hops": max_hops,
            "actual_hops": len(chain),
            "account_chain": account_chain,
            "chain_length": len(account_chain),
            "time_span_minutes": round(time_span, 2),
            "total_amount": total_amount,
            "currency": transaction.currency.value,
            "transaction_ids": [str(txn.id) for txn in chain],
            "description": f"Money moved through {len(chain)} transactions in {round(time_span, 1)} minutes"
        }
    
    def get_severity(self, transaction: Transaction) -> AlertSeverity:
        """
        Determine severity based on chain length.
        
        Returns HIGH by default, engine will calculate actual severity.
        
        Args:
            transaction: Transaction that triggered alert
            
        Returns:
            AlertSeverity: HIGH severity
        """
        return AlertSeverity.HIGH
    
    async def get_severity_async(self, transaction: Transaction) -> AlertSeverity:
        """
        Async version to properly calculate severity.
        
        Args:
            transaction: Transaction that triggered alert
            
        Returns:
            AlertSeverity: Calculated severity
        """
        max_hops = self.get_parameter('max_hops', 3)
        time_window_minutes = self.get_parameter('time_window_minutes', 30)
        
        chain = await self._build_transaction_chain(
            transaction=transaction,
            max_hops=max_hops * 2,
            time_window_minutes=time_window_minutes
        )
        
        chain_length = len(chain)
        
        if chain_length >= 5:
            return AlertSeverity.CRITICAL
        else:
            return AlertSeverity.HIGH