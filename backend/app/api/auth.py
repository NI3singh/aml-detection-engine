"""
Authentication API Endpoints

Handles:
- User registration (creates organization + first user)
- User login (returns JWT token)
- User logout (clears cookie)
- Get current user info
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    MessageResponse
)
from app.crud import user as crud_user
from app.core.security import create_access_token
from app.core.deps import get_current_active_user
from app.models.user import User
from app.utils.constants import UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# Register
# ============================================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user and organization.
    
    For MVP: First user to register creates the organization.
    """
    
    # Check if email already exists
    if await crud_user.email_exists(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create organization
    organization = await crud_user.create_organization(
        db=db,
        name=user_data.organization_name,
        contact_email=user_data.email
    )
    
    # Create user (first user is always admin)
    user = await crud_user.create_user(
        db=db,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        organization_id=organization.id,
        role=UserRole.ADMIN
    )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Set token in HTTP-only cookie (more secure than localStorage)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,  # Can't be accessed by JavaScript
        max_age=86400,  # 24 hours
        samesite="lax",  # CSRF protection
        secure=False  # Set to True in production with HTTPS
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


# ============================================================================
# Login
# ============================================================================

@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password.
    
    Returns JWT token in cookie and response body.
    """
    
    # Authenticate user
    user = await crud_user.authenticate_user(
        db=db,
        email=credentials.email,
        password=credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Set token in cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=86400,  # 24 hours
        samesite="lax",
        secure=False  # Set to True in production
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


# ============================================================================
# Logout
# ============================================================================

@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    """
    Logout by clearing the authentication cookie.
    """
    
    # Clear the cookie
    response.delete_cookie(key="access_token")
    
    return MessageResponse(
        message="Successfully logged out",
        success=True
    )


# ============================================================================
# Get Current User
# ============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user information.
    """
    return UserResponse.model_validate(current_user)