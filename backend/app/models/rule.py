"""
Rule Model

Stores rule configurations for each organization.
Each rule can be enabled/disabled and have custom parameters.

Why JSONB for Parameters:
- Flexible schema (each rule type has different parameters)
- PostgreSQL JSONB is indexed and queryable
- Easy to add new rule types without schema changes
- Can store complex nested configurations

Caching Strategy:
- Rules don't change frequently
- Cache in Redis for performance
- Invalidate cache when rule is updated
"""

from sqlalchemy import Column, String, Text, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, TenantMixin
from app.utils.constants import RuleType


class Rule(Base, TenantMixin):
    """
    Rule configuration model.
    
    Each organization can customize rule parameters.
    Rules can be enabled/disabled without deleting them.
    """
    
    __tablename__ = "rules"
    
    # ========================================================================
    # Rule Identity
    # ========================================================================
    
    name = Column(
        String(255),
        nullable=False,
        comment="Human-readable rule name"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Detailed description of what the rule detects"
    )
    
    rule_type = Column(
        SQLEnum(RuleType, name="rule_type", create_type=True),
        nullable=False,
        index=True,
        comment="Type of rule (determines which evaluator to use)"
    )
    
    # ========================================================================
    # Rule Configuration
    # ========================================================================
    
    parameters = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Rule-specific parameters as JSON"
    )
    
    # Example parameters for each rule type:
    #
    # LARGE_TRANSACTION:
    # {
    #     "threshold_amount": 10000.00,
    #     "currency": "USD"
    # }
    #
    # HIGH_FREQUENCY:
    # {
    #     "max_transactions": 10,
    #     "time_window_minutes": 60
    # }
    #
    # RAPID_MOVEMENT:
    # {
    #     "max_hops": 3,
    #     "time_window_minutes": 30
    # }
    #
    # HIGH_RISK_COUNTRY:
    # {
    #     "high_risk_countries": ["KP", "IR", "SY"]
    # }
    #
    # ROUND_AMOUNT:
    # {
    #     "round_threshold": 1000.00,
    #     "tolerance": 0.01
    # }
    #
    # VELOCITY_CHANGE:
    # {
    #     "multiplier": 3.0,
    #     "baseline_window_days": 30,
    #     "comparison_window_days": 7
    # }
    
    # ========================================================================
    # Status
    # ========================================================================
    
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this rule is currently active"
    )
    
    # ========================================================================
    # Metadata
    # ========================================================================
    
    # For future: track rule performance
    # total_evaluations = Column(Integer, default=0)
    # total_alerts_generated = Column(Integer, default=0)
    # false_positive_rate = Column(DECIMAL(5, 2), nullable=True)
    
    # ========================================================================
    # Relationships
    # ========================================================================
    
    # Many rules belong to one organization
    organization = relationship(
        "Organization",
        back_populates="rules",
        lazy="selectin"
    )
    
    # One rule can generate many alerts
    alerts = relationship(
        "Alert",
        back_populates="rule",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    
    def __repr__(self) -> str:
        return (
            f"<Rule(id={self.id}, "
            f"name='{self.name}', "
            f"type={self.rule_type.value}, "
            f"active={self.is_active})>"
        )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def get_parameter(self, key: str, default=None):
        """
        Get a parameter value from the parameters JSON.
        
        Args:
            key: Parameter key
            default: Default value if key not found
            
        Returns:
            Parameter value or default
        """
        return self.parameters.get(key, default) if self.parameters else default
    
    def set_parameter(self, key: str, value) -> None:
        """
        Set a parameter value in the parameters JSON.
        
        Args:
            key: Parameter key
            value: Parameter value
        """
        if self.parameters is None:
            self.parameters = {}
        self.parameters[key] = value
    
    def update_parameters(self, new_parameters: dict) -> None:
        """
        Update multiple parameters at once.
        
        Args:
            new_parameters: Dictionary of parameters to update
        """
        if self.parameters is None:
            self.parameters = {}
        self.parameters.update(new_parameters)