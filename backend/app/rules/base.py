"""
Base Rule Class

Defines the interface that all rule implementations must follow.

Why Abstract Base Class:
- Ensures all rules have consistent interface
- Makes it easy to add new rules
- Type-safe (IDE knows what methods to expect)
- Self-documenting code

Each rule must implement:
- evaluate(): Check if transaction violates the rule
- get_alert_details(): Return context for the alert
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.rule import Rule
from app.utils.constants import AlertSeverity


class BaseRule(ABC):
    """
    Abstract base class for all AML rules.
    
    Each rule type must inherit from this class and implement:
    - evaluate(): Main logic to check if rule is triggered
    - get_alert_details(): Context information for the alert
    """
    
    def __init__(
        self,
        db: AsyncSession,
        organization_id: str,
        rule_config: Rule
    ):
        """
        Initialize rule with database session and configuration.
        
        Args:
            db: Async database session
            organization_id: Organization ID for data isolation
            rule_config: Rule configuration from database
        """
        self.db = db
        self.organization_id = organization_id
        self.rule_config = rule_config
        self.parameters = rule_config.parameters or {}
    
    @abstractmethod
    async def evaluate(self, transaction: Transaction) -> bool:
        """
        Evaluate if transaction violates this rule.
        
        Args:
            transaction: Transaction to evaluate
            
        Returns:
            bool: True if rule is triggered (alert should be created)
        """
        pass
    
    @abstractmethod
    async def get_alert_details(self, transaction: Transaction) -> Dict[str, Any]:
        """
        Get detailed information about why the alert was triggered.
        
        This context helps analysts understand the alert.
        
        Args:
            transaction: Transaction that triggered the alert
            
        Returns:
            dict: Details to store in alert.details JSON field
        """
        pass
    
    @abstractmethod
    def get_severity(self, transaction: Transaction) -> AlertSeverity:
        """
        Determine the severity level of the alert.
        
        Args:
            transaction: Transaction that triggered the alert
            
        Returns:
            AlertSeverity: Severity level
        """
        pass
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """
        Get a parameter value from rule configuration.
        
        Args:
            key: Parameter key
            default: Default value if key not found
            
        Returns:
            Parameter value or default
        """
        return self.parameters.get(key, default)
    
    def __str__(self) -> str:
        """String representation of the rule."""
        return f"{self.__class__.__name__}(rule_id={self.rule_config.id})"
    
    def __repr__(self) -> str:
        """Detailed representation of the rule."""
        return (
            f"{self.__class__.__name__}("
            f"rule_id={self.rule_config.id}, "
            f"type={self.rule_config.rule_type.value}, "
            f"active={self.rule_config.is_active})"
        )