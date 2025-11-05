#!/usr/bin/env python3
"""CLI tool for generating API keys for customers."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.core.config import settings
from src.core.security import generate_api_key
from src.models.database import APIKey, Customer


async def create_customer(email: str, tier: str = "free") -> Customer:
    """Create a new customer.

    Args:
        email: Customer email
        tier: Subscription tier

    Returns:
        Customer instance
    """
    engine = create_async_engine(settings.database_url)

    async with engine.begin() as conn:
        async_session = AsyncSession(bind=conn)

        # Check if customer exists
        result = await async_session.execute(
            select(Customer).where(Customer.email == email)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Customer {email} already exists")
            return existing

        # Create new customer
        customer = Customer(
            email=email,
            tier=tier,
        )
        async_session.add(customer)
        await async_session.commit()

        print(f"Customer created: {email} (tier: {tier})")
        return customer

    await engine.dispose()


async def create_key_for_customer(customer_id: str, key_name: str = None):
    """Create API key for existing customer.

    Args:
        customer_id: Customer UUID
        key_name: Optional key name
    """
    engine = create_async_engine(settings.database_url)

    async with engine.begin() as conn:
        async_session = AsyncSession(bind=conn)

        # Generate key
        full_key, prefix, key_hash = generate_api_key()

        # Create API key
        api_key = APIKey(
            customer_id=customer_id,
            key_prefix=prefix,
            key_hash=key_hash,
            key_name=key_name,
            scopes=["inference"],
        )
        async_session.add(api_key)
        await async_session.commit()

        print(f"\nAPI Key created successfully!")
        print(f"  Key Name: {key_name or '(unnamed)'}")
        print(f"  Key Prefix: {prefix}")
        print(f"\n  Full API Key (SAVE THIS - shown only once):")
        print(f"  {full_key}")
        print()

    await engine.dispose()


async def main():
    """Main CLI function."""
    print("=" * 60)
    print("VLA Inference API - API Key Generator")
    print("=" * 60)
    print()

    # Get customer email
    email = input("Customer email: ").strip()

    if not email:
        print("Error: Email required")
        return

    # Get tier
    tier = input("Subscription tier (free/pro/enterprise) [free]: ").strip() or "free"

    if tier not in ["free", "pro", "enterprise"]:
        print(f"Error: Invalid tier '{tier}'")
        return

    # Create or get customer
    customer = await create_customer(email, tier)

    # Get key name
    key_name = input("API key name (optional): ").strip() or None

    # Create API key
    await create_key_for_customer(str(customer.customer_id), key_name)


if __name__ == "__main__":
    asyncio.run(main())
