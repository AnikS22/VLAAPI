#!/usr/bin/env python3
"""Database initialization script for VLA Inference API Platform.

This script creates the database schema and optionally seeds initial data.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.config import settings
from src.models.database import Base


async def create_schema():
    """Create database schema."""
    print("Creating database schema...")

    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=True,
    )

    async with engine.begin() as conn:
        # Create schema
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS vlaapi"))

        # Create tables
        await conn.run_sync(Base.metadata.create_all)

        print("Schema created successfully")

    await engine.dispose()


async def seed_data():
    """Seed initial data (optional)."""
    print("Seeding initial data...")

    from src.core.security import generate_api_key
    from src.models.database import APIKey, Customer

    engine = create_async_engine(settings.database_url)

    async with engine.begin() as conn:
        from sqlalchemy.ext.asyncio import AsyncSession

        async_session = AsyncSession(bind=conn)

        # Create demo customer
        demo_customer = Customer(
            email="demo@example.com",
            company_name="Demo Company",
            tier="pro",
            rate_limit_rpm=100,
            monthly_quota=100000,
        )
        async_session.add(demo_customer)
        await async_session.flush()

        # Generate API key
        full_key, prefix, key_hash = generate_api_key()

        demo_api_key = APIKey(
            customer_id=demo_customer.customer_id,
            key_prefix=prefix,
            key_hash=key_hash,
            key_name="Demo API Key",
            scopes=["inference"],
        )
        async_session.add(demo_api_key)

        await async_session.commit()

        print(f"\nDemo customer created:")
        print(f"  Email: {demo_customer.email}")
        print(f"  Tier: {demo_customer.tier}")
        print(f"\nAPI Key (SAVE THIS - shown only once):")
        print(f"  {full_key}")
        print()

    await engine.dispose()


async def main():
    """Main function."""
    print("=" * 60)
    print("VLA Inference API Platform - Database Setup")
    print("=" * 60)
    print()

    # Create schema
    await create_schema()

    # Ask if user wants to seed data
    response = input("\nSeed demo data? (y/n): ").lower()
    if response == "y":
        await seed_data()

    print("\nDatabase setup complete!")


if __name__ == "__main__":
    asyncio.run(main())
