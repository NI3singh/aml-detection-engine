"""
Alert Model

Represents alerts generated when transactions violate rules.

Alert Lifecycle:
1. NEW - Just created by rule engine
2. UNDER_REVIEW - Analyst is investigating
3. CLOSED - Confirmed suspicious, escalated to compliance
4. FALSE_POSITIVE - Determined to be legitimate

Why JSONB for Details:
- Each rule type may provide different contextual information
- Flexible schema for future rule types
- Can store supporting data used in the decision
"""

from sqlalchemy import Column, String, Text, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, TenantMixin
from app.utils.constants import AlertSeverity, AlertStatus


class Alert(Base, TenantMixin):
    """
    Alert model for suspicious transactions.
    
    Generated when a transaction triggers a rule.
    Analysts review alerts and mark them as legitimate or suspicious.
    """
    
    __tablename__ = "alerts"
    
    # ========================================================================
    # Foreign Keys
    # ========================================================================
    
    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Transaction that triggered this alert"
    )
    
    rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Rule that generated this alert"
    )
    
    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who reviewed this alert"
    )
    
    # ========================================================================
    # Alert Details
    # ========================================================================
    
    severity = Column(
        SQLEnum(AlertSeverity, name="alert_severity", create_type=True),
        nullable=False,
        index=True,
        comment="Alert severity level"
    )
    
    status = Column(
        SQLEnum(AlertStatus, name="alert_status", create_type=True),
        nullable=False,
        default=AlertStatus.NEW,
        index=True,
        comment="Current status of the alert"
    )
    
    details = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Rule-specific details about why alert was triggered"
    )
    
    # Example details for each rule type:
    #
    # LARGE_TRANSACTION:
    # {
    #     "threshold": 10000.00,
    #     "actual_amount": 15000.00,
    #     "currency": "USD",
    #     "exceeded_by": 5000.00
    # }
    #
    # HIGH_FREQUENCY:
    # {
    #     "time_window_minutes": 60,
    #     "max_transactions": 10,
    #     "actual_count": 15,
    #     "sender_id": "ACC001",
    #     "transaction_ids": ["TXN1", "TXN2", ...]
    # }
    #
    # RAPID_MOVEMENT:
    # {
    #     "chain": ["ACC001", "ACC002", "ACC003", "ACC004"],
    #     "time_span_minutes": 25,
    #     "total_amount": 50000.00
    # }
    #
    # HIGH_RISK_COUNTRY:
    # {
    #     "sender_country": "KP",
    #     "receiver_country": "US",
    #     "high_risk_party": "sender"
    # }
    
    # ========================================================================
    # Review Information
    # ========================================================================
    
    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When the alert was reviewed"
    )
    
    notes = Column(
        Text,
        nullable=True,
        comment="Analyst's notes about the alert"
    )
    
    # ========================================================================
    # Additional Context (for future ML features)
    # ========================================================================
    
    # risk_score = Column(
    #     DECIMAL(5, 2),
    #     nullable=True,
    #     comment="ML-generated risk score (0-100)"
    # )
    
    # confidence = Column(
    #     DECIMAL(5, 2),
    #     nullable=True,
    #     comment="Confidence in the alert (0-1)"
    # )
    
    # ========================================================================
    # Relationships
    # ========================================================================
    
    # Many alerts belong to one organization
    organization = relationship(
        "Organization",
        back_populates="alerts",
        lazy="selectin"
    )
    
    # Many alerts reference one transaction
    transaction = relationship(
        "Transaction",
        back_populates="alerts",
        lazy="selectin"
    )
    
    # Many alerts reference one rule
    rule = relationship(
        "Rule",
        back_populates="alerts",
        lazy="selectin"
    )
    
    # Many alerts can be reviewed by one user
    reviewed_by_user = relationship(
        "User",
        back_populates="reviewed_alerts",
        foreign_keys=[reviewed_by],
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return (
            f"<Alert(id={self.id}, "
            f"severity={self.severity.value}, "
            f"status={self.status.value})>"
        )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def is_reviewed(self) -> bool:
        """Check if alert has been reviewed."""
        return self.status in [AlertStatus.CLOSED, AlertStatus.FALSE_POSITIVE]
    
    def is_pending(self) -> bool:
        """Check if alert is pending review."""
        return self.status in [AlertStatus.NEW, AlertStatus.UNDER_REVIEW]
    
    def get_detail(self, key: str, default=None):
        """
        Get a detail value from the details JSON.
        
        Args:
            key: Detail key
            default: Default value if key not found
            
        Returns:
            Detail value or default
        """
        return self.details.get(key, default) if self.details else default