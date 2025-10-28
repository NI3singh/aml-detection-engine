"""
Base Model with Common Fields

All database models inherit from this base to get:
- UUID primary key
- Created/updated timestamps
- Soft delete capability (future)

Why UUID:
- Globally unique (no conflicts in distributed systems)
- Non-sequential (security benefit)
- Can be generated client-side
- Standard for modern SaaS applications

Why Timestamps:
- Audit trail (when was record created/modified)
- Debugging (understand data lifecycle)
- Compliance requirements
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import func

from app.db.session import Base as SQLAlchemyBase


class Base(SQLAlchemyBase):
    """
    Base class for all database models.
    
    Provides common fields that every model should have:
    - id: UUID primary key
    - created_at: Timestamp when record was created
    - updated_at: Timestamp when record was last modified
    
    Using declared_attr allows each model to have its own table
    while sharing these common columns.
    """
    
    __abstract__ = True  # This is not a table itself
    
    # Primary key (UUID v4)
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        index=True,
        comment="Unique identifier for the record"
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),  # Set by database
        comment="Timestamp when record was created"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),  # Automatically update on modification
        comment="Timestamp when record was last updated"
    )
    
    # Soft delete support (optional, for future use)
    # deleted_at = Column(
    #     DateTime(timezone=True),
    #     nullable=True,
    #     comment="Timestamp when record was soft-deleted"
    # )
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Useful for:
        - API responses
        - Logging
        - Testing
        
        Returns:
            dict: Dictionary representation of the model
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class TenantMixin:
    """
    Mixin for multi-tenant models.
    
    All models that belong to an organization should include this mixin.
    This ensures data isolation between organizations.
    
    Usage:
        class Transaction(Base, TenantMixin):
            # Your model fields here
            pass
    """
    
    @declared_attr
    def organization_id(cls):
        """Foreign key to organizations table."""
        from sqlalchemy import Column, ForeignKey
        from sqlalchemy.dialects.postgresql import UUID
        
        return Column(
            UUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,  # Critical for query performance
            comment="Organization this record belongs to"
        )


__all__ = ["Base", "TenantMixin"]