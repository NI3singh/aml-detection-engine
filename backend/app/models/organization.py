"""
Organization Model

Represents a tenant/customer in the multi-tenant SaaS.
Each organization has its own users, transactions, rules, and alerts.

Data Isolation Strategy:
- All tenant-specific data includes organization_id foreign key
- Every query must filter by organization_id
- This is enforced at the repository layer

Why This Approach:
- Simpler than separate databases per tenant
- Cost-effective for MVP
- Easier backups and maintenance
- Can migrate to separate DBs later if needed
"""

from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class Organization(Base):
    """
    Organization/Tenant model.
    
    Each organization represents a separate customer/company
    using the AML monitoring system.
    """
    
    __tablename__ = "organizations"
    
    # Basic Information
    name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Organization name"
    )
    
    # Optional contact information
    contact_email = Column(
        String(255),
        nullable=True,
        comment="Primary contact email"
    )
    
    contact_phone = Column(
        String(50),
        nullable=True,
        comment="Primary contact phone"
    )
    
    # Status
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether organization is active"
    )
    
    # Settings (stored as JSON for flexibility)
    # settings = Column(
    #     JSONB,
    #     nullable=True,
    #     comment="Organization-specific settings"
    # )
    
    # Optional: Subscription/billing info (for future)
    # subscription_tier = Column(String(50), nullable=True)
    # subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    notes = Column(
        Text,
        nullable=True,
        comment="Internal notes about the organization"
    )
    
    # ========================================================================
    # Relationships
    # ========================================================================
    
    # One organization has many users
    users = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan",  # Delete users when org is deleted
        lazy="selectin"  # Eager loading for better performance
    )
    
    # One organization has many transactions
    transactions = relationship(
        "Transaction",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="noload"  # Don't load by default (too many records)
    )
    
    # One organization has many rules
    rules = relationship(
        "Rule",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # One organization has many alerts
    alerts = relationship(
        "Alert",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    
    # One organization has many file uploads
    file_uploads = relationship(
        "FileUpload",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    
    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name='{self.name}')>"