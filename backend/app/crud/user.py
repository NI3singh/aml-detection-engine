"""
User CRUD Operations

Handles all database operations for users.

Why separate CRUD layer:
- Keeps routes clean (routes handle HTTP, CRUD handles DB)
- Reusable functions across different routes
- Easier to test
- Single source of truth for DB operations
"""

from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.organization import Organization
from app.core.security import get_password_hash, verify_password
from app.utils.constants import UserRole


# ============================================================================
# Create Operations
# ============================================================================

async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    organization_id: UUID,
    role: UserRole = UserRole.ADMIN
) -> User:
    """
    Create a new user.
    
    Args:
        db: Database session
        email: User's email
        password: Plain password (will be hashed)
        full_name: User's full name
        organization_id: Organization ID
        role: User's role
        
    Returns:
        User: Created user
    """
    hashed_password = get_password_hash(password)
    
    user = User(
        email=email.lower(),
        hashed_password=hashed_password,
        full_name=full_name,
        organization_id=organization_id,
        role=role,
        is_active=True,
        is_email_verified=False  # For MVP, we'll skip email verification
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


async def create_organization(
    db: AsyncSession,
    name: str,
    contact_email: Optional[str] = None
) -> Organization:
    """
    Create a new organization.
    
    Args:
        db: Database session
        name: Organization name
        contact_email: Contact email
        
    Returns:
        Organization: Created organization
    """
    organization = Organization(
        name=name,
        contact_email=contact_email,
        is_active=True
    )
    
    db.add(organization)
    await db.commit()
    await db.refresh(organization)
    
    return organization


# ============================================================================
# Read Operations
# ============================================================================

async def get_user_by_id(
    db: AsyncSession,
    user_id: UUID
) -> Optional[User]:
    """
    Get user by ID.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        User or None
    """
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.organization))
    )
    return result.scalar_one_or_none()


async def get_user_by_email(
    db: AsyncSession,
    email: str
) -> Optional[User]:
    """
    Get user by email.
    
    Args:
        db: Database session
        email: User's email
        
    Returns:
        User or None
    """
    result = await db.execute(
        select(User)
        .where(User.email == email.lower())
        .options(selectinload(User.organization))
    )
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str
) -> Optional[User]:
    """
    Authenticate user with email and password.
    
    Args:
        db: Database session
        email: User's email
        password: Plain password
        
    Returns:
        User if authenticated, None otherwise
    """
    user = await get_user_by_email(db, email)
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    if not user.is_active:
        return None
    
    return user


# ============================================================================
# Update Operations
# ============================================================================

async def update_user(
    db: AsyncSession,
    user: User,
    **kwargs
) -> User:
    """
    Update user fields.
    
    Args:
        db: Database session
        user: User to update
        **kwargs: Fields to update
        
    Returns:
        User: Updated user
    """
    for key, value in kwargs.items():
        if value is not None:
            if key == "password":
                setattr(user, "hashed_password", get_password_hash(value))
            else:
                setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user


# ============================================================================
# Delete Operations
# ============================================================================

async def delete_user(
    db: AsyncSession,
    user: User
) -> bool:
    """
    Delete a user (soft delete by setting is_active=False).
    
    Args:
        db: Database session
        user: User to delete
        
    Returns:
        bool: True if successful
    """
    user.is_active = False
    await db.commit()
    return True


# ============================================================================
# Utility Functions
# ============================================================================

async def email_exists(
    db: AsyncSession,
    email: str
) -> bool:
    """
    Check if email already exists.
    
    Args:
        db: Database session
        email: Email to check
        
    Returns:
        bool: True if exists
    """
    result = await db.execute(
        select(User.id).where(User.email == email.lower())
    )
    return result.scalar_one_or_none() is not None