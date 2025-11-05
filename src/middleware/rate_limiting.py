"""Rate limiting middleware using token bucket algorithm."""

import time
from typing import Tuple

from fastapi import Depends, HTTPException, status

from src.core.config import settings
from src.core.redis_client import redis_manager
from src.middleware.authentication import APIKeyInfo, get_current_api_key


class RateLimitExceeded(HTTPException):
    """Custom exception for rate limit exceeded."""

    def __init__(self, retry_after: int, limits: dict):
        """Initialize rate limit exception.

        Args:
            retry_after: Seconds until retry allowed
            limits: Current rate limits
        """
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Rate limit exceeded. Please try again later.",
                "retry_after_seconds": retry_after,
                "limits": limits,
            },
            headers={"Retry-After": str(retry_after)},
        )


async def refill_tokens(
    key_prefix: str,
    capacity: int,
    refill_rate: float,
) -> int:
    """Refill tokens based on elapsed time (token bucket algorithm).

    Args:
        key_prefix: Redis key prefix (e.g., 'rate_limit:customer_id')
        capacity: Maximum token capacity
        refill_rate: Tokens added per second

    Returns:
        Current token count after refill
    """
    tokens_key = f"{key_prefix}:tokens"
    refill_key = f"{key_prefix}:last_refill"

    now = time.time()

    # Get current state
    current_tokens = await redis_manager.get_rate_limit_tokens(tokens_key)
    last_refill = await redis_manager.get_last_refill_time(refill_key)

    # Initialize if not exists
    if current_tokens is None or last_refill is None:
        await redis_manager.set_rate_limit_tokens(tokens_key, capacity)
        await redis_manager.set_last_refill_time(refill_key, now)
        return capacity

    # Calculate tokens to add based on elapsed time
    elapsed = now - last_refill
    tokens_to_add = elapsed * refill_rate
    new_tokens = min(capacity, current_tokens + tokens_to_add)

    # Update state
    await redis_manager.set_rate_limit_tokens(tokens_key, int(new_tokens))
    await redis_manager.set_last_refill_time(refill_key, now)

    return int(new_tokens)


async def consume_token(key_prefix: str) -> bool:
    """Consume one token from the bucket.

    Args:
        key_prefix: Redis key prefix

    Returns:
        True if token consumed successfully, False if no tokens available
    """
    tokens_key = f"{key_prefix}:tokens"
    current_tokens = await redis_manager.get_rate_limit_tokens(tokens_key)

    if current_tokens is None or current_tokens < 1:
        return False

    # Decrement token count
    new_tokens = await redis_manager.decrement_rate_limit_tokens(tokens_key)

    # Check if decrement was successful and we still have tokens
    return new_tokens is not None and new_tokens >= 0


async def check_rate_limit_internal(
    customer_id: str,
    rate_limit_rpm: int,
    rate_limit_rpd: int,
) -> Tuple[bool, int]:
    """Check rate limit for customer.

    Args:
        customer_id: Customer UUID string
        rate_limit_rpm: Requests per minute limit
        rate_limit_rpd: Requests per day limit

    Returns:
        Tuple of (allowed, retry_after_seconds)
    """
    # Check per-minute rate limit
    rpm_key = f"rate_limit:{customer_id}:minute"
    rpm_capacity = rate_limit_rpm
    rpm_refill_rate = rate_limit_rpm / 60.0  # tokens per second

    # Refill tokens
    current_tokens_rpm = await refill_tokens(rpm_key, rpm_capacity, rpm_refill_rate)

    # Try to consume token
    if current_tokens_rpm < 1:
        # Calculate retry-after (time until 1 token available)
        retry_after = int(60.0 / rate_limit_rpm) + 1
        return False, retry_after

    # Check per-day rate limit
    rpd_key = f"rate_limit:{customer_id}:day"
    rpd_capacity = rate_limit_rpd
    rpd_refill_rate = rate_limit_rpd / 86400.0  # tokens per second (24 hours)

    current_tokens_rpd = await refill_tokens(rpd_key, rpd_capacity, rpd_refill_rate)

    if current_tokens_rpd < 1:
        # Calculate retry-after (time until 1 token available)
        retry_after = int(86400.0 / rate_limit_rpd) + 1
        return False, retry_after

    # Consume tokens from both buckets
    rpm_consumed = await consume_token(rpm_key)
    rpd_consumed = await consume_token(rpd_key)

    if not rpm_consumed or not rpd_consumed:
        # Race condition - tokens consumed by another request
        retry_after = 1  # Try again in 1 second
        return False, retry_after

    return True, 0


async def check_rate_limit(
    api_key: APIKeyInfo = Depends(get_current_api_key),
) -> APIKeyInfo:
    """FastAPI dependency to check rate limits.

    Args:
        api_key: API key information from authentication

    Returns:
        APIKeyInfo: API key info if rate limit not exceeded

    Raises:
        RateLimitExceeded: If rate limit exceeded
    """
    if not settings.rate_limit_enabled:
        return api_key

    # Check if monthly quota exceeded
    if api_key.is_quota_exceeded():
        raise RateLimitExceeded(
            retry_after=86400,  # Retry next day
            limits={
                "monthly_quota": api_key.monthly_quota,
                "monthly_usage": api_key.monthly_usage,
            },
        )

    # Check rate limits
    allowed, retry_after = await check_rate_limit_internal(
        str(api_key.customer_id),
        api_key.rate_limit_rpm,
        api_key.rate_limit_rpd,
    )

    if not allowed:
        raise RateLimitExceeded(
            retry_after=retry_after,
            limits={
                "requests_per_minute": api_key.rate_limit_rpm,
                "requests_per_day": api_key.rate_limit_rpd,
            },
        )

    return api_key


async def get_remaining_requests(api_key: APIKeyInfo) -> dict:
    """Get remaining requests for API key.

    Args:
        api_key: API key information

    Returns:
        Dictionary with remaining request counts
    """
    customer_id = str(api_key.customer_id)

    # Get remaining tokens for minute
    rpm_key = f"rate_limit:{customer_id}:minute:tokens"
    remaining_minute = await redis_manager.get_rate_limit_tokens(rpm_key)

    # Get remaining tokens for day
    rpd_key = f"rate_limit:{customer_id}:day:tokens"
    remaining_day = await redis_manager.get_rate_limit_tokens(rpd_key)

    # Calculate remaining monthly quota
    if api_key.monthly_quota is None:
        remaining_monthly = None  # Unlimited
    else:
        remaining_monthly = max(0, api_key.monthly_quota - api_key.monthly_usage)

    return {
        "requests_remaining_minute": remaining_minute or 0,
        "requests_remaining_day": remaining_day or 0,
        "monthly_quota_remaining": remaining_monthly,
    }
