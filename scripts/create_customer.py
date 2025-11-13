#!/usr/bin/env python3
"""Script to manually create customers and API keys.

Usage:
    python scripts/create_customer.py --email user@example.com --tier pro
    python scripts/create_customer.py --list
    python scripts/create_customer.py --create-api-key <customer_id>
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_engine, init_db
from src.core.security import generate_api_key, hash_api_key
from src.models.database import APIKey, Customer


async def create_customer(
    email: str,
    tier: str = "free",
    name: str = None,
    company: str = None,
) -> Customer:
    """Create a new customer account.
    
    Args:
        email: Customer email address
        tier: Subscription tier (free, starter, pro, enterprise)
        name: Optional customer name
        company: Optional company name
        
    Returns:
        Created Customer object
    """
    async with AsyncSession(async_engine) as session:
        # Check if customer already exists
        result = await session.execute(
            select(Customer).where(Customer.email == email)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"❌ Customer with email {email} already exists!")
            print(f"   Customer ID: {existing.customer_id}")
            return existing
        
        # Define tier settings
        tier_settings = {
            "free": {
                "rate_limit_rpm": 10,
                "rate_limit_rpd": 1000,
                "monthly_quota": 1000,
            },
            "starter": {
                "rate_limit_rpm": 60,
                "rate_limit_rpd": 50000,
                "monthly_quota": 50000,
            },
            "pro": {
                "rate_limit_rpm": 300,
                "rate_limit_rpd": 500000,
                "monthly_quota": 500000,
            },
            "enterprise": {
                "rate_limit_rpm": 1000,
                "rate_limit_rpd": None,
                "monthly_quota": None,  # Unlimited
            },
        }
        
        if tier not in tier_settings:
            raise ValueError(f"Invalid tier: {tier}. Choose from: {list(tier_settings.keys())}")
        
        settings = tier_settings[tier]
        
        # Create customer
        customer = Customer(
            customer_id=uuid4(),
            email=email,
            name=name,
            company_name=company,
            tier=tier,
            is_active=True,
            rate_limit_rpm=settings["rate_limit_rpm"],
            rate_limit_rpd=settings["rate_limit_rpd"],
            monthly_quota=settings["monthly_quota"],
            monthly_usage=0,
            created_at=datetime.utcnow(),
        )
        
        session.add(customer)
        await session.commit()
        await session.refresh(customer)
        
        print(f"✅ Customer created successfully!")
        print(f"   Customer ID: {customer.customer_id}")
        print(f"   Email: {customer.email}")
        print(f"   Tier: {customer.tier}")
        print(f"   Rate Limit: {customer.rate_limit_rpm} req/min, {customer.rate_limit_rpd or 'unlimited'} req/day")
        print(f"   Monthly Quota: {customer.monthly_quota or 'unlimited'} requests")
        print()
        print(f"⚠️  Don't forget to create an API key for this customer!")
        print(f"   Run: python scripts/create_customer.py --create-api-key {customer.customer_id}")
        
        return customer


async def create_api_key(
    customer_id: str,
    name: str = "Default API Key",
    expires_days: int = None,
    scopes: list[str] = None,
) -> APIKey:
    """Create an API key for a customer.
    
    Args:
        customer_id: Customer UUID
        name: Descriptive name for the API key
        expires_days: Optional expiration in days (None = never expires)
        scopes: API key scopes (default: ["inference"])
        
    Returns:
        Created APIKey object with raw key
    """
    async with AsyncSession(async_engine) as session:
        # Verify customer exists
        result = await session.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            print(f"❌ Customer {customer_id} not found!")
            return None
        
        # Generate API key
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        
        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        # Create API key
        api_key = APIKey(
            key_id=uuid4(),
            customer_id=customer.customer_id,
            key_hash=key_hash,
            name=name,
            scopes=scopes or ["inference"],
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
        )
        
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        
        print(f"✅ API key created successfully!")
        print(f"   Key ID: {api_key.key_id}")
        print(f"   Customer: {customer.email} ({customer.tier})")
        print(f"   Name: {api_key.name}")
        print(f"   Scopes: {', '.join(api_key.scopes)}")
        print(f"   Expires: {api_key.expires_at or 'Never'}")
        print()
        print(f"🔑 API Key (show this to the customer ONCE):")
        print(f"   {raw_key}")
        print()
        print(f"⚠️  Save this key! It cannot be retrieved again.")
        
        return api_key


async def list_customers():
    """List all customers with their API keys."""
    async with AsyncSession(async_engine) as session:
        result = await session.execute(
            select(Customer).order_by(Customer.created_at.desc())
        )
        customers = result.scalars().all()
        
        if not customers:
            print("No customers found.")
            return
        
        print(f"📋 Total Customers: {len(customers)}\n")
        
        for customer in customers:
            status = "✅" if customer.is_active else "❌"
            print(f"{status} {customer.email}")
            print(f"   ID: {customer.customer_id}")
            print(f"   Name: {customer.name or 'N/A'}")
            print(f"   Company: {customer.company_name or 'N/A'}")
            print(f"   Tier: {customer.tier}")
            print(f"   Usage: {customer.monthly_usage}/{customer.monthly_quota or '∞'} requests this month")
            print(f"   Created: {customer.created_at.strftime('%Y-%m-%d %H:%M')}")
            
            # Get API keys for this customer
            keys_result = await session.execute(
                select(APIKey).where(APIKey.customer_id == customer.customer_id)
            )
            api_keys = keys_result.scalars().all()
            
            if api_keys:
                print(f"   API Keys: {len(api_keys)}")
                for key in api_keys:
                    key_status = "🟢" if key.is_active else "🔴"
                    expires = key.expires_at.strftime('%Y-%m-%d') if key.expires_at else "Never"
                    last_used = key.last_used_at.strftime('%Y-%m-%d') if key.last_used_at else "Never"
                    print(f"      {key_status} {key.name} (ID: {key.key_id})")
                    print(f"         Expires: {expires} | Last used: {last_used}")
            else:
                print(f"   API Keys: None ⚠️")
            
            print()


async def revoke_api_key(key_id: str):
    """Revoke an API key.
    
    Args:
        key_id: API key UUID
    """
    async with AsyncSession(async_engine) as session:
        result = await session.execute(
            select(APIKey).where(APIKey.key_id == key_id)
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            print(f"❌ API key {key_id} not found!")
            return
        
        api_key.is_active = False
        await session.commit()
        
        print(f"✅ API key revoked: {api_key.name}")
        print(f"   Key ID: {api_key.key_id}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Manage VLA API customers and API keys")
    
    # Commands
    parser.add_argument("--list", action="store_true", help="List all customers")
    parser.add_argument("--email", type=str, help="Customer email address")
    parser.add_argument("--tier", type=str, default="free", 
                       choices=["free", "starter", "pro", "enterprise"],
                       help="Subscription tier (default: free)")
    parser.add_argument("--name", type=str, help="Customer name")
    parser.add_argument("--company", type=str, help="Company name")
    parser.add_argument("--create-api-key", type=str, metavar="CUSTOMER_ID",
                       help="Create API key for customer")
    parser.add_argument("--key-name", type=str, default="Default API Key",
                       help="API key name")
    parser.add_argument("--expires-days", type=int,
                       help="API key expiration in days (default: never)")
    parser.add_argument("--revoke-key", type=str, metavar="KEY_ID",
                       help="Revoke an API key")
    
    args = parser.parse_args()
    
    # Initialize database
    await init_db()
    
    # Execute command
    if args.list:
        await list_customers()
    elif args.email:
        await create_customer(
            email=args.email,
            tier=args.tier,
            name=args.name,
            company=args.company,
        )
    elif args.create_api_key:
        await create_api_key(
            customer_id=args.create_api_key,
            name=args.key_name,
            expires_days=args.expires_days,
        )
    elif args.revoke_key:
        await revoke_api_key(args.revoke_key)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())






