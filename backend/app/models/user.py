"""
User Model

Represents users who can access the system.
Each user belongs to one organization and has a specific role.

Security Considerations:
- Passwords are NEVER stored in plain text
- Use bcrypt for password hashing
- Email is unique across the entire system
- Role-based access control (RBAC)

Why Store Organization ID:
- Multi-tenant isolation
- Users can only see data from their organization
- Simplifies authorization checks
"""

from sqlalchemy import Column, String, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.utils.constants import UserRole


class User(Base):
    """
    User model for authentication and authorization.
    
    Each user:
    - Belongs to exactly one organization
    - Has a specific role (admin, analyst, viewer)
    - Can upload files and review alerts (based on role)
    """
    
    __tablename__ = "users"
    
    # ========================================================================
    # Foreign Keys
    # ========================================================================
    
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Organization this user belongs to"
    )
    
    # ========================================================================
    # Basic Information
    # ========================================================================
    
    email = Column(
        String(255),
        nullable=False,
        unique=True,  # Email must be unique across entire system
        index=True,
        comment="User's email address (used for login)"
    )
    
    hashed_password = Column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password"
    )
    
    full_name = Column(
        String(255),
        nullable=False,
        comment="User's full name"
    )
    
    # ========================================================================
    # Role & Permissions
    # ========================================================================
    
    role = Column(
        SQLEnum(UserRole, name="user_role", create_type=True),
        nullable=False,
        default=UserRole.ANALYST,
        index=True,
        comment="User's role within the organization"
    )
    
    # ========================================================================
    # Status
    # ========================================================================
    
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether user account is active"
    )
    
    is_email_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether user's email has been verified"
    )
    
    # ========================================================================
    # Optional Fields
    # ========================================================================
    
    # For future features
    # last_login_at = Column(
    #     DateTime(timezone=True),
    #     nullable=True,
    #     comment="Last login timestamp"
    # )
    
    # profile_picture_url = Column(
    #     String(500),
    #     nullable=True,
    #     comment="URL to profile picture"
    # )
    
    # ========================================================================
    # Relationships
    # ========================================================================
    
    # Many users belong to one organization
    organization = relationship(
        "Organization",
        back_populates="users",
        lazy="selectin"  # Always load organization with user
    )
    
    # One user can upload many files
    file_uploads = relationship(
        "FileUpload",
        back_populates="uploaded_by_user",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    
    # One user can review many alerts
    reviewed_alerts = relationship(
        "Alert",
        back_populates="reviewed_by_user",
        foreign_keys="Alert.reviewed_by",
        lazy="noload"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role={self.role.value})>"
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def has_permission(self, required_role: UserRole) -> bool:
        """
        Check if user has required permission level.
        
        Permission hierarchy: admin > analyst > viewer
        
        Args:
            required_role: Minimum role required
            
        Returns:
            bool: True if user has sufficient permissions
        """
        role_hierarchy = {
            UserRole.VIEWER: 1,
            UserRole.ANALYST: 2,
            UserRole.ADMIN: 3,
        }
        
        return role_hierarchy[self.role] >= role_hierarchy[required_role]
    
    def can_review_alerts(self) -> bool:
        """Check if user can review alerts."""
        return self.role in [UserRole.ANALYST, UserRole.ADMIN]
    
    def can_manage_rules(self) -> bool:
        """Check if user can create/modify rules."""
        return self.role == UserRole.ADMIN
    
    def can_manage_users(self) -> bool:
        """Check if user can create/modify other users."""
        return self.role == UserRole.ADMIN