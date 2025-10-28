"""
Audit Log Model

Tracks all important actions for compliance and security.

Why Audit Logs:
- Regulatory compliance (required for financial systems)
- Security monitoring (detect unauthorized access)
- Debugging (understand what happened)
- User accountability (who did what and when)

What to Log:
- User login/logout
- Alert reviews and status changes
- Rule modifications
- File uploads
- Configuration changes

Note: This is included for future use. 
MVP will focus on core features, but the model is ready.
"""

from sqlalchemy import Column, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship

from app.models.base import Base, TenantMixin


class AuditLog(Base, TenantMixin):
    """
    Audit log for tracking all important system actions.
    
    Provides an immutable record of who did what and when.
    Critical for compliance and security.
    """
    
    __tablename__ = "audit_logs"
    
    # ========================================================================
    # Foreign Keys
    # ========================================================================
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who performed the action"
    )
    
    # ========================================================================
    # Action Details
    # ========================================================================
    
    action = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Type of action performed"
    )
    
    # Common action types:
    # - user.login
    # - user.logout
    # - user.created
    # - user.updated
    # - alert.reviewed
    # - alert.status_changed
    # - rule.created
    # - rule.updated
    # - rule.deleted
    # - file.uploaded
    # - transaction.imported
    
    resource_type = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Type of resource affected (e.g., 'alert', 'rule')"
    )
    
    resource_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="ID of the affected resource"
    )
    
    # ========================================================================
    # Context Information
    # ========================================================================
    
    details = Column(
        JSONB,
        nullable=True,
        comment="Additional context about the action"
    )
    
    # Example details:
    # {
    #     "old_value": "new",
    #     "new_value": "under_review",
    #     "ip_address": "192.168.1.1",
    #     "user_agent": "Mozilla/5.0...",
    #     "reason": "Suspicious pattern detected"
    # }
    
    ip_address = Column(
        INET,
        nullable=True,
        comment="IP address of the user"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        comment="Browser user agent string"
    )
    
    # ========================================================================
    # Status
    # ========================================================================
    
    success = Column(
        String(10),
        nullable=False,
        default="success",
        comment="Whether the action succeeded or failed"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if action failed"
    )
    
    # ========================================================================
    # Relationships
    # ========================================================================
    
    organization = relationship(
        "Organization",
        lazy="selectin"
    )
    
    user = relationship(
        "User",
        lazy="selectin"
    )
    
    # ========================================================================
    # Indexes
    # ========================================================================
    
    __table_args__ = (
        Index(
            "ix_audit_logs_org_action_created",
            "organization_id",
            "action",
            "created_at"
        ),
        Index(
            "ix_audit_logs_org_user_created",
            "organization_id",
            "user_id",
            "created_at"
        ),
        Index(
            "ix_audit_logs_resource",
            "resource_type",
            "resource_id"
        ),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, "
            f"action='{self.action}', "
            f"user_id={self.user_id})>"
        )