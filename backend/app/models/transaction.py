"""
Transaction Model

Core model representing financial transactions to be monitored.

Performance Considerations:
- Indexed on frequently queried fields (sender_id, receiver_id, timestamp)
- Composite indexes for common query patterns
- Will need partitioning for millions of records (future)

Data Integrity:
- Amount stored as NUMERIC for precision (no floating point errors)
- Timestamps with timezone support
- Foreign key to file_upload for traceability
"""

from decimal import Decimal
from sqlalchemy import (
    Column,
    String,
    DECIMAL,
    DateTime,
    ForeignKey,
    Index,
    Enum as SQLEnum,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TenantMixin
from app.utils.constants import TransactionType, Currency


class Transaction(Base, TenantMixin):
    """
    Transaction model for financial transactions.
    
    Each transaction represents a single financial movement
    that needs to be monitored for suspicious activity.
    """
    
    __tablename__ = "transactions"
    
    # ========================================================================
    # Foreign Keys
    # ========================================================================
    
    upload_id = Column(
        UUID(as_uuid=True),
        ForeignKey("file_uploads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="File upload this transaction came from"
    )
    
    # ========================================================================
    # Transaction Identification
    # ========================================================================
    
    transaction_id = Column(
        String(255),
        nullable=False,
        index=True,
        comment="External transaction ID from source system"
    )
    
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,  # Critical for time-based queries
        comment="When the transaction occurred"
    )
    
    # ========================================================================
    # Amount Information
    # ========================================================================
    
    amount = Column(
        DECIMAL(20, 2),  # Up to 999,999,999,999,999,999.99
        nullable=False,
        index=True,  # For threshold-based rules
        comment="Transaction amount"
    )
    
    currency = Column(
        SQLEnum(Currency, name="currency", create_type=True),
        nullable=False,
        default=Currency.USD,
        comment="Currency code (ISO 4217)"
    )
    
    # ========================================================================
    # Sender Information
    # ========================================================================
    
    sender_id = Column(
        String(255),
        nullable=False,
        index=True,  # Critical for sender-based queries
        comment="Sender's account ID"
    )
    
    sender_name = Column(
        String(255),
        nullable=False,
        comment="Sender's name"
    )
    
    sender_country = Column(
        String(2),  # ISO 3166-1 alpha-2
        nullable=False,
        index=True,  # For country-based rules
        comment="Sender's country code"
    )
    
    # ========================================================================
    # Receiver Information
    # ========================================================================
    
    receiver_id = Column(
        String(255),
        nullable=False,
        index=True,  # Critical for receiver-based queries
        comment="Receiver's account ID"
    )
    
    receiver_name = Column(
        String(255),
        nullable=False,
        comment="Receiver's name"
    )
    
    receiver_country = Column(
        String(2),  # ISO 3166-1 alpha-2
        nullable=False,
        index=True,  # For country-based rules
        comment="Receiver's country code"
    )
    
    # ========================================================================
    # Transaction Details
    # ========================================================================
    
    transaction_type = Column(
        SQLEnum(TransactionType, name="transaction_type", create_type=True),
        nullable=False,
        index=True,
        comment="Type of transaction"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Transaction description/memo"
    )
    
    reference_number = Column(
        String(255),
        nullable=True,
        comment="External reference number"
    )
    
    # ========================================================================
    # Relationships
    # ========================================================================
    
    # Many transactions belong to one organization
    organization = relationship(
        "Organization",
        back_populates="transactions",
        lazy="selectin"
    )
    
    # Many transactions come from one file upload
    file_upload = relationship(
        "FileUpload",
        back_populates="transactions",
        lazy="selectin"
    )
    
    # One transaction can generate many alerts
    alerts = relationship(
        "Alert",
        back_populates="transaction",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    
    # ========================================================================
    # Indexes
    # ========================================================================
    
    __table_args__ = (
        # Composite index for common query patterns
        Index(
            "ix_transactions_org_timestamp",
            "organization_id",
            "timestamp"
        ),
        Index(
            "ix_transactions_org_sender",
            "organization_id",
            "sender_id",
            "timestamp"
        ),
        Index(
            "ix_transactions_org_receiver",
            "organization_id",
            "receiver_id",
            "timestamp"
        ),
        Index(
            "ix_transactions_org_amount",
            "organization_id",
            "amount"
        ),
        # For high-frequency rule
        Index(
            "ix_transactions_sender_timestamp",
            "sender_id",
            "timestamp"
        ),
        # For rapid movement rule
        Index(
            "ix_transactions_sender_receiver_timestamp",
            "sender_id",
            "receiver_id",
            "timestamp"
        ),
    )
    
    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, "
            f"transaction_id='{self.transaction_id}', "
            f"amount={self.amount} {self.currency.value})>"
        )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def involves_high_risk_country(self, high_risk_countries: set[str]) -> bool:
        """
        Check if transaction involves a high-risk country.
        
        Args:
            high_risk_countries: Set of high-risk country codes
            
        Returns:
            bool: True if sender or receiver is in high-risk country
        """
        return (
            self.sender_country in high_risk_countries
            or self.receiver_country in high_risk_countries
        )
    
    def is_round_amount(self, threshold: float = 1000.0, tolerance: float = 0.01) -> bool:
        """
        Check if transaction amount is suspiciously round.
        
        Args:
            threshold: Minimum amount to consider
            tolerance: Tolerance percentage (0.01 = 1%)
            
        Returns:
            bool: True if amount is round
        """
        if float(self.amount) < threshold:
            return False
        
        # Check if amount is a round number (within tolerance)
        amount_float = float(self.amount)
        for round_value in [1000, 5000, 10000, 50000, 100000, 500000, 1000000]:
            if abs(amount_float - round_value) / round_value <= tolerance:
                return True
        
        return False