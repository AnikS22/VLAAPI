"""Authentication utilities for password hashing and JWT token management."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire})

    # Use JWT secret key or fallback to secret key
    secret_key = settings.jwt_secret_key or settings.secret_key

    encoded_jwt = jwt.encode(
        to_encode,
        secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload dict, or None if invalid
    """
    try:
        secret_key = settings.jwt_secret_key or settings.secret_key

        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        return payload
    except JWTError:
        return None


def generate_password_reset_token() -> str:
    """Generate a secure random token for password reset.

    Returns:
        Random URL-safe token string
    """
    return secrets.token_urlsafe(32)


def generate_email_verification_token() -> str:
    """Generate a secure random token for email verification.

    Returns:
        Random URL-safe token string
    """
    return secrets.token_urlsafe(32)
