"""
Security utilities for authentication and authorization.

Handles:
- Password hashing (bcrypt)
- JWT token creation and verification
- Security helpers

Why bcrypt:
- Industry standard for password hashing
- Automatically salted
- Slow by design (prevents brute force)
- Future-proof (can increase rounds as computers get faster)
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.core.config import settings

# Password hashing context
# Using bcrypt with recommended settings
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Higher = more secure but slower
)


# ============================================================================
# Password Hashing
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: Password entered by user
        hashed_password: Hashed password from database
        
    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password for storing in database.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


# ============================================================================
# JWT Token Management
# ============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in token (usually user_id, email)
        expires_delta: Token expiration time (default from settings)
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    
    # Create token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Decoded token payload, or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


# ============================================================================
# Helper Functions
# ============================================================================

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets minimum requirements.
    
    Requirements:
    - At least 8 characters
    - Contains at least one number
    - Contains at least one letter
    
    Args:
        password: Password to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters"
    
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number"
    
    if not any(char.isalpha() for char in password):
        return False, "Password must contain at least one letter"
    
    return True, ""


def create_email_verification_token(email: str) -> str:
    """
    Create a token for email verification.
    
    Args:
        email: User's email address
        
    Returns:
        str: Verification token
    """
    delta = timedelta(hours=24)  # Token valid for 24 hours
    return create_access_token(
        data={"sub": email, "type": "email_verification"},
        expires_delta=delta
    )


def verify_email_token(token: str) -> Optional[str]:
    """
    Verify email verification token and extract email.
    
    Args:
        token: Verification token
        
    Returns:
        str: Email address if valid, None otherwise
    """
    payload = decode_access_token(token)
    if payload and payload.get("type") == "email_verification":
        return payload.get("sub")
    return None