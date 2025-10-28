"""
Dependency injection helpers for FastAPI routes.

These functions are used with FastAPI's Depends() to:
- Get database session
- Get current user from JWT token
- Verify user permissions
- Handle authentication

Why Dependency Injection:
- Cleaner code (separation of concerns)
- Easy to test (can mock dependencies)
- Automatic error handling
- Reusable across routes
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.organization import Organization
from app.core.security import decode_access_token
from app.utils.constants import UserRole

# Security scheme for Swagger docs
security = HTTPBearer()


# ============================================================================
# Authentication Dependencies
# ============================================================================

async def get_current_user(
    access_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token in cookie.
    
    For MVP: Token stored in HTTP-only cookie (more secure than localStorage)
    
    Args:
        access_token: JWT token from cookie
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If token invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not access_token:
        raise credentials_exception
    
    # Decode token
    payload = decode_access_token(access_token)
    if payload is None:
        raise credentials_exception
    
    # Get user ID from token
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensure user is active.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        User: Active user
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


# ============================================================================
# Authorization Dependencies (Role-Based)
# ============================================================================

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Ensure current user is an admin.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Admin user
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )
    return current_user


async def get_current_analyst_or_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Ensure current user is analyst or admin.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Analyst or admin user
        
    Raises:
        HTTPException: If user is viewer
    """
    if current_user.role == UserRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Analyst or Admin access required."
        )
    return current_user


# ============================================================================
# Organization Dependencies
# ============================================================================

async def get_current_organization(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Organization:
    """
    Get the organization of the current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Organization: User's organization
        
    Raises:
        HTTPException: If organization not found
    """
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    organization = result.scalar_one_or_none()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return organization


# ============================================================================
# Optional Authentication (for public + private routes)
# ============================================================================

async def get_current_user_optional(
    access_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.
    
    Useful for routes that work both authenticated and unauthenticated.
    
    Args:
        access_token: JWT token from cookie
        db: Database session
        
    Returns:
        User or None: Current user if authenticated
    """
    if not access_token:
        return None
    
    try:
        return await get_current_user(access_token, db)
    except HTTPException:
        return None