"""Authentication middleware for API key validation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.redis_client import redis_manager
from src.core.security import extract_bearer_token, hash_api_key, validate_api_key_format
from src.models.database import APIKey, Customer

# HTTP Bearer token security scheme
security = HTTPBearer(
    scheme_name="Bearer Token",
    description="API key authentication. Use 'Bearer vla_live_...' in Authorization header",
)


class APIKeyInfo:
    """Container for authenticated API key information."""

    def __init__(
        self,
        key_id: UUID,
        customer_id: UUID,
        customer_tier: str,
        scopes: list[str],
        rate_limit_rpm: int,
        rate_limit_rpd: int,
        monthly_quota: Optional[int],
        monthly_usage: int,
    ):
        """Initialize API key info.

        Args:
            key_id: API key UUID
            customer_id: Customer UUID
            customer_tier: Customer subscription tier
            scopes: API key scopes
            rate_limit_rpm: Requests per minute limit
            rate_limit_rpd: Requests per day limit
            monthly_quota: Monthly quota (None = unlimited)
            monthly_usage: Current month usage count
        """
        self.key_id = key_id
        self.customer_id = customer_id
        self.customer_tier = customer_tier
        self.scopes = scopes
        self.rate_limit_rpm = rate_limit_rpm
        self.rate_limit_rpd = rate_limit_rpd
        self.monthly_quota = monthly_quota
        self.monthly_usage = monthly_usage

    def has_scope(self, scope: str) -> bool:
        """Check if API key has a specific scope.

        Args:
            scope: Scope to check (e.g., 'inference', 'admin')

        Returns:
            True if key has scope, False otherwise
        """
        return scope in self.scopes

    def is_quota_exceeded(self) -> bool:
        """Check if monthly quota is exceeded.

        Returns:
            True if quota exceeded, False otherwise
        """
        if self.monthly_quota is None:
            return False  # Unlimited
        return self.monthly_usage >= self.monthly_quota


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
    session: AsyncSession = Depends(get_db_session),
) -> APIKeyInfo:
    """Verify API key and return key information.

    Args:
        credentials: HTTP Bearer credentials
        session: Database session

    Returns:
        APIKeyInfo: Authenticated API key information

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = credentials.credentials

    # Validate API key format
    if not validate_api_key_format(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Compute hash for lookup
    key_hash = hash_api_key(api_key)

    # Try to get from Redis cache first
    cached_key_data = await redis_manager.get_cached_api_key(key_hash)

    if cached_key_data:
        # Use cached data
        return APIKeyInfo(
            key_id=UUID(cached_key_data["key_id"]),
            customer_id=UUID(cached_key_data["customer_id"]),
            customer_tier=cached_key_data["customer_tier"],
            scopes=cached_key_data["scopes"],
            rate_limit_rpm=cached_key_data["rate_limit_rpm"],
            rate_limit_rpd=cached_key_data["rate_limit_rpd"],
            monthly_quota=cached_key_data.get("monthly_quota"),
            monthly_usage=cached_key_data["monthly_usage"],
        )

    # Cache miss - query database
    result = await session.execute(
        select(APIKey, Customer)
        .join(Customer, APIKey.customer_id == Customer.customer_id)
        .where(APIKey.key_hash == key_hash)
        .where(APIKey.is_active == True)
        .where(Customer.is_active == True)
    )

    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key_obj: APIKey = row[0]
    customer: Customer = row[1]

    # Check if API key is expired
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last_used_at timestamp (async, don't await)
    api_key_obj.last_used_at = datetime.utcnow()
    await session.commit()

    # Determine rate limits (per-key override or customer default)
    rate_limit_rpm = (
        api_key_obj.rate_limit_override_rpm
        if api_key_obj.rate_limit_override_rpm
        else customer.rate_limit_rpm
    )

    # Prepare key info
    key_info = APIKeyInfo(
        key_id=api_key_obj.key_id,
        customer_id=customer.customer_id,
        customer_tier=customer.tier,
        scopes=api_key_obj.scopes or ["inference"],
        rate_limit_rpm=rate_limit_rpm,
        rate_limit_rpd=customer.rate_limit_rpd,
        monthly_quota=customer.monthly_quota,
        monthly_usage=customer.monthly_usage,
    )

    # Cache key data for 5 minutes
    await redis_manager.cache_api_key(
        key_hash,
        {
            "key_id": str(api_key_obj.key_id),
            "customer_id": str(customer.customer_id),
            "customer_tier": customer.tier,
            "scopes": api_key_obj.scopes or ["inference"],
            "rate_limit_rpm": rate_limit_rpm,
            "rate_limit_rpd": customer.rate_limit_rpd,
            "monthly_quota": customer.monthly_quota,
            "monthly_usage": customer.monthly_usage,
        },
        ttl=300,  # 5 minutes
    )

    return key_info


async def get_current_api_key(
    api_key_info: APIKeyInfo = Depends(verify_api_key),
) -> APIKeyInfo:
    """FastAPI dependency to get current authenticated API key.

    Args:
        api_key_info: Verified API key info

    Returns:
        APIKeyInfo: API key information

    Example:
        ```python
        @app.get("/protected")
        async def protected_endpoint(
            api_key: APIKeyInfo = Depends(get_current_api_key)
        ):
            return {"customer_id": api_key.customer_id}
        ```
    """
    return api_key_info


def require_scope(scope: str):
    """Create a dependency that requires a specific API key scope.

    Args:
        scope: Required scope (e.g., 'admin', 'inference')

    Returns:
        Dependency function that verifies scope

    Example:
        ```python
        @app.delete("/admin/customers/{customer_id}")
        async def delete_customer(
            customer_id: UUID,
            api_key: APIKeyInfo = Depends(require_scope("admin"))
        ):
            # Only accessible with 'admin' scope
            ...
        ```
    """

    async def verify_scope(api_key: APIKeyInfo = Depends(get_current_api_key)) -> APIKeyInfo:
        if not api_key.has_scope(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key does not have required scope: {scope}",
            )
        return api_key

    return verify_scope
