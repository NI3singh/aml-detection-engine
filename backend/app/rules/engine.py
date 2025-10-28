"""
Rule Engine

Orchestrates all rules and manages alert generation.

Responsibilities:
- Load and instantiate rules
- Evaluate transactions against all active rules
- Create alerts when rules are triggered
- Handle errors gracefully (one failing rule shouldn't break others)

Architecture:
- Plugin-based: Easy to add new rules
- Parallel evaluation (future): Can evaluate rules concurrently
- Comprehensive logging for debugging
"""

from typing import List, Dict, Type
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.rule import Rule
from app.models.alert import Alert
from app.utils.constants import RuleType
from app.crud.alert import create_alert

# Import all rule implementations
from app.rules.base import BaseRule
from app.rules.large_transaction import LargeTransactionRule
from app.rules.high_frequency import HighFrequencyRule
from app.rules.rapid_movement import RapidMovementRule
from app.rules.high_risk_country import HighRiskCountryRule


class RuleEngine:
    """
    Rule engine that evaluates transactions against configured rules.
    
    Usage:
        engine = RuleEngine(db, organization_id)
        alerts = await engine.evaluate_transaction(transaction, active_rules)
    """
    
    # Map rule types to their implementations
    RULE_REGISTRY: Dict[RuleType, Type[BaseRule]] = {
        RuleType.LARGE_TRANSACTION: LargeTransactionRule,
        RuleType.HIGH_FREQUENCY: HighFrequencyRule,
        RuleType.RAPID_MOVEMENT: RapidMovementRule,
        RuleType.HIGH_RISK_COUNTRY: HighRiskCountryRule,
    }
    
    def __init__(self, db: AsyncSession, organization_id: UUID):
        """
        Initialize rule engine.
        
        Args:
            db: Async database session
            organization_id: Organization ID for data isolation
        """
        self.db = db
        self.organization_id = organization_id
    
    def _instantiate_rule(self, rule_config: Rule) -> BaseRule:
        """
        Create rule instance from configuration.
        
        Args:
            rule_config: Rule configuration from database
            
        Returns:
            BaseRule: Instantiated rule
            
        Raises:
            ValueError: If rule type not found in registry
        """
        rule_class = self.RULE_REGISTRY.get(rule_config.rule_type)
        
        if not rule_class:
            raise ValueError(f"Unknown rule type: {rule_config.rule_type}")
        
        return rule_class(
            db=self.db,
            organization_id=str(self.organization_id),
            rule_config=rule_config
        )
    
    async def evaluate_transaction(
        self,
        transaction: Transaction,
        active_rules: List[Rule]
    ) -> List[Alert]:
        """
        Evaluate a transaction against all active rules.
        
        Args:
            transaction: Transaction to evaluate
            active_rules: List of active rule configurations
            
        Returns:
            List[Alert]: List of alerts created (if any)
        """
        alerts_created = []
        
        for rule_config in active_rules:
            try:
                # Skip if rule is not active
                if not rule_config.is_active:
                    continue
                
                # Instantiate rule
                rule = self._instantiate_rule(rule_config)
                
                # Evaluate rule
                triggered = await rule.evaluate(transaction)
                
                if triggered:
                    # Get alert details
                    details = await rule.get_alert_details(transaction)
                    
                    # Determine severity
                    # Some rules need async severity calculation
                    if hasattr(rule, 'get_severity_async'):
                        severity = await rule.get_severity_async(transaction)
                    else:
                        severity = rule.get_severity(transaction)
                    
                    # Create alert
                    alert = await create_alert(
                        db=self.db,
                        organization_id=self.organization_id,
                        transaction_id=transaction.id,
                        rule_id=rule_config.id,
                        severity=severity,
                        details=details
                    )
                    
                    alerts_created.append(alert)
            
            except Exception as e:
                # Log error but continue with other rules
                print(f"Error evaluating rule {rule_config.id}: {str(e)}")
                # In production, use proper logging
                # logger.error(f"Rule evaluation error", exc_info=True, extra={
                #     "rule_id": rule_config.id,
                #     "transaction_id": transaction.id,
                #     "error": str(e)
                # })
                continue
        
        return alerts_created
    
    async def evaluate_transactions_batch(
        self,
        transactions: List[Transaction],
        active_rules: List[Rule]
    ) -> Dict[str, int]:
        """
        Evaluate multiple transactions in batch.
        
        Useful for processing uploaded CSV files.
        
        Args:
            transactions: List of transactions to evaluate
            active_rules: List of active rule configurations
            
        Returns:
            dict: Statistics about alerts created
        """
        total_alerts = 0
        alerts_by_severity = {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0
        }
        alerts_by_rule = {}
        
        for transaction in transactions:
            alerts = await self.evaluate_transaction(transaction, active_rules)
            total_alerts += len(alerts)
            
            for alert in alerts:
                # Count by severity
                alerts_by_severity[alert.severity.value] += 1
                
                # Count by rule
                rule_name = alert.rule.name
                alerts_by_rule[rule_name] = alerts_by_rule.get(rule_name, 0) + 1
        
        return {
            "total_alerts": total_alerts,
            "alerts_by_severity": alerts_by_severity,
            "alerts_by_rule": alerts_by_rule
        }
    
    @classmethod
    def register_rule(cls, rule_type: RuleType, rule_class: Type[BaseRule]) -> None:
        """
        Register a new rule type.
        
        This allows adding custom rules without modifying the engine.
        
        Args:
            rule_type: Type identifier for the rule
            rule_class: Rule implementation class
            
        Example:
            RuleEngine.register_rule(RuleType.CUSTOM_RULE, CustomRule)
        """
        cls.RULE_REGISTRY[rule_type] = rule_class
    
    @classmethod
    def get_supported_rule_types(cls) -> List[RuleType]:
        """
        Get list of supported rule types.
        
        Returns:
            List[RuleType]: Supported rule types
        """
        return list(cls.RULE_REGISTRY.keys())