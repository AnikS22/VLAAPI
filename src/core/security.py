"""Security utilities for API key management and authentication."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings

# Password hashing context (for future user accounts)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_api_key() -> Tuple[str, str, str]:
    """Generate a new API key with secure random bytes.

    Returns:
        Tuple of (full_key, key_prefix, key_hash)
            - full_key: Complete API key (show to user ONLY ONCE)
            - key_prefix: First 12 characters for display
            - key_hash: SHA-256 hash for storage

    Example:
        >>> full_key, prefix, hash_val = generate_api_key()
        >>> print(f"Your API key (save this!): {full_key}")
        >>> print(f"Key prefix for identification: {prefix}")
        # Store only prefix and hash in database
    """
    # Generate random key with specified length (default 32 bytes = 256 bits)
    random_suffix = secrets.token_urlsafe(settings.api_key_length)

    # Create full key with prefix
    full_key = f"{settings.api_key_prefix}_{random_suffix}"

    # Extract display prefix (e.g., "vla_live_xyz7")
    key_prefix = full_key[:12]

    # Compute hash for storage
    key_hash = hash_api_key(full_key)

    return full_key, key_prefix, key_hash


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256.

    Args:
        api_key: Raw API key string

    Returns:
        Hexadecimal hash string

    Note:
        This is a one-way hash. You cannot recover the original key.
    """
    if settings.api_key_hash_algorithm == "sha256":
        return hashlib.sha256(api_key.encode()).hexdigest()
    elif settings.api_key_hash_algorithm == "sha512":
        return hashlib.sha512(api_key.encode()).hexdigest()
    else:
        raise ValueError(
            f"Unsupported hash algorithm: {settings.api_key_hash_algorithm}"
        )


def verify_api_key_hash(api_key: str, stored_hash: str) -> bool:
    """Verify an API key against its stored hash.

    Args:
        api_key: Raw API key from request
        stored_hash: Hash stored in database

    Returns:
        True if key matches hash, False otherwise
    """
    computed_hash = hash_api_key(api_key)
    return secrets.compare_digest(computed_hash, stored_hash)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password

    Note:
        Used for future admin user accounts.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token for admin dashboard.

    Args:
        data: Data to encode in token
        expires_delta: Token expiry duration (optional)

    Returns:
        Encoded JWT token

    Example:
        ```python
        token = create_access_token(
            data={"sub": "admin@example.com"},
            expires_delta=timedelta(minutes=30)
        )
        ```
    """
    to_encode = data.copy()

    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire})

    # Get JWT secret key (fallback to app secret key)
    secret_key = settings.jwt_secret_key or settings.secret_key

    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify JWT access token.

    Args:
        token: JWT token string

    Returns:
        Token payload or None if invalid

    Example:
        ```python
        payload = decode_access_token(token)
        if payload:
            user_email = payload.get("sub")
        ```
    """
    try:
        secret_key = settings.jwt_secret_key or settings.secret_key
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None


def is_api_key_expired(expires_at: Optional[datetime]) -> bool:
    """Check if an API key is expired.

    Args:
        expires_at: Expiration datetime (None = never expires)

    Returns:
        True if expired, False otherwise
    """
    if expires_at is None:
        return False  # Never expires
    return datetime.utcnow() > expires_at


def validate_api_key_format(api_key: str) -> bool:
    """Validate API key format (basic structure check).

    Args:
        api_key: API key string

    Returns:
        True if format is valid, False otherwise

    Note:
        This only checks format, not authenticity.
        Expected format: "vla_live_" or "vla_test_" followed by 43+ chars
    """
    if not api_key:
        return False

    # Check prefix
    if not (api_key.startswith("vla_live_") or api_key.startswith("vla_test_")):
        return False

    # Check minimum length (prefix + random suffix)
    if len(api_key) < 20:  # Conservative minimum
        return False

    return True


def extract_bearer_token(authorization: str) -> Optional[str]:
    """Extract token from Authorization header.

    Args:
        authorization: Authorization header value (e.g., "Bearer vla_live_...")

    Returns:
        Extracted token or None if invalid format

    Example:
        >>> token = extract_bearer_token("Bearer vla_live_abc123")
        >>> print(token)
        "vla_live_abc123"
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def generate_request_id() -> str:
    """Generate a unique request ID for tracing.

    Returns:
        UUID-like request ID string

    Example:
        >>> request_id = generate_request_id()
        >>> print(request_id)
        "req_abc123def456..."
    """
    import uuid

    return f"req_{uuid.uuid4().hex[:16]}"


# For testing purposes
if __name__ == "__main__":
    # Generate and verify API key
    full_key, prefix, key_hash = generate_api_key()
    print(f"Generated API key: {full_key}")
    print(f"Key prefix: {prefix}")
    print(f"Key hash: {key_hash}")
    print(f"Verification: {verify_api_key_hash(full_key, key_hash)}")
