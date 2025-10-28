"""
User Pydantic Schemas

Defines data validation for:
- User registration
- User login
- User responses (what API returns)

Why Pydantic:
- Automatic validation
- Type checking
- Serialization/deserialization
- Auto-generated API docs
- Clear error messages
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.utils.constants import UserRole


# ============================================================================
# Request Schemas (Input)
# ============================================================================

class UserRegister(BaseModel):
    """Schema for user registration."""
    
    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["admin@example.com"]
    )
    
    password: str = Field(
        ...,
        min_length=8,
        description="User's password (min 8 characters)",
        examples=["SecurePass123"]
    )
    
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="User's full name",
        examples=["John Doe"]
    )
    
    organization_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Organization/company name",
        examples=["Acme Corporation"]
    )
    
    @field_validator('email')
    @classmethod
    def email_must_be_lowercase(cls, v: str) -> str:
        """Ensure email is lowercase."""
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    
    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["admin@example.com"]
    )
    
    password: str = Field(
        ...,
        description="User's password",
        examples=["SecurePass123"]
    )
    
    @field_validator('email')
    @classmethod
    def email_must_be_lowercase(cls, v: str) -> str:
        """Ensure email is lowercase."""
        return v.lower()


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    
    full_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=255,
        description="User's full name"
    )
    
    password: Optional[str] = Field(
        None,
        min_length=8,
        description="New password"
    )
    
    is_active: Optional[bool] = Field(
        None,
        description="Whether user is active"
    )


# ============================================================================
# Response Schemas (Output)
# ============================================================================

class UserResponse(BaseModel):
    """Schema for user data in API responses."""
    
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_email_verified: bool
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True  # Allow ORM model conversion
    }


class UserWithOrganization(UserResponse):
    """Schema for user with organization details."""
    
    organization_name: Optional[str] = None


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    
    access_token: str = Field(
        ...,
        description="JWT access token"
    )
    
    token_type: str = Field(
        default="bearer",
        description="Token type"
    )
    
    user: UserResponse = Field(
        ...,
        description="Authenticated user details"
    )


class MessageResponse(BaseModel):
    """Generic message response."""
    
    message: str = Field(
        ...,
        description="Response message",
        examples=["Operation successful"]
    )
    
    success: bool = Field(
        default=True,
        description="Whether operation was successful"
    )


# ============================================================================
# Internal Schemas
# ============================================================================

class UserInDB(UserResponse):
    """User schema with hashed password (internal use only)."""
    
    hashed_password: str
    
    model_config = {
        "from_attributes": True
    }