#!/usr/bin/env python3
"""
Customer Management Script
--------------------------
Create and manage customer accounts and API keys.

Usage:
    python scripts/create_customer.py
"""

import asyncio
import hashlib
import secrets
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session_factory
from src.models.database import APIKey, Customer


def generate_api_key(prefix: str = "vla_live") -> tuple[str, str]:
    """Generate a secure API key.
    
    Args:
        prefix: API key prefix
        
    Returns:
        Tuple of (api_key, key_hash)
    """
    # Generate random 32-byte string
    random_part = secrets.token_urlsafe(32)
    api_key = f"{prefix}_{random_part}"
    
    # Create hash for storage (never store raw key)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    return api_key, key_hash


async def create_customer_interactive():
    """Create customer account interactively."""
    
    print("\n" + "="*60)
    print("🤖 VLA API - Customer Account Creation")
    print("="*60 + "\n")
    
    # Get customer information
    print("Enter customer information:")
    company_name = input("  Company name: ").strip()
    if not company_name:
        print("❌ Company name is required")
        return
    
    email = input("  Contact email: ").strip()
    if not email:
        print("❌ Email is required")
        return
    
    print("\nAvailable tiers:")
    print("  1. free     - 10 req/min, 1,000 req/day, 10,000/month")
    print("  2. pro      - 100 req/min, 10,000 req/day, 100,000/month")
    print("  3. enterprise - 1,000 req/min, 100,000 req/day, unlimited")
    
    tier_choice = input("\n  Select tier (1-3): ").strip()
    tier_map = {"1": "free", "2": "pro", "3": "enterprise"}
    tier = tier_map.get(tier_choice, "free")
    
    # Set rate limits based on tier
    rate_limits = {
        "free": {
            "rpm": 10,
            "rpd": 1000,
            "monthly": 10000
        },
        "pro": {
            "rpm": 100,
            "rpd": 10000,
            "monthly": 100000
        },
        "enterprise": {
            "rpm": 1000,
            "rpd": 100000,
            "monthly": None  # Unlimited
        }
    }
    
    limits = rate_limits[tier]
    
    print(f"\nCreating {tier} tier account for {company_name}...")
    
    # Generate API key
    api_key_str, key_hash = generate_api_key()
    
    # Create database session
    session_factory = await get_session_factory()
    async with session_factory() as session:
        try:
            # Create customer record
            customer = Customer(
                customer_id=uuid4(),
                company_name=company_name,
                email=email,
                tier=tier,
                is_active=True,
                monthly_quota=limits["monthly"],
                monthly_usage=0,
                created_at=datetime.utcnow()
            )
            session.add(customer)
            await session.flush()  # Get customer_id
            
            # Create API key record
            api_key = APIKey(
                key_id=uuid4(),
                customer_id=customer.customer_id,
                key_hash=key_hash,
                key_prefix=api_key_str[:16],  # Store first 16 chars for identification
                is_active=True,
                rate_limit_per_minute=limits["rpm"],
                rate_limit_per_day=limits["rpd"],
                created_at=datetime.utcnow()
            )
            session.add(api_key)
            
            # Commit transaction
            await session.commit()
            
            # Print success message
            print("\n" + "="*60)
            print("✅ Customer account created successfully!")
            print("="*60)
            print(f"\n📋 Customer Details:")
            print(f"   Customer ID: {customer.customer_id}")
            print(f"   Company: {company_name}")
            print(f"   Email: {email}")
            print(f"   Tier: {tier}")
            print(f"\n🔑 API Key (SAVE THIS - it won't be shown again!):")
            print(f"   {api_key_str}")
            print(f"\n📊 Rate Limits:")
            print(f"   Per Minute: {limits['rpm']} requests")
            print(f"   Per Day: {limits['rpd']} requests")
            if limits['monthly']:
                print(f"   Per Month: {limits['monthly']:,} requests")
            else:
                print(f"   Per Month: Unlimited")
            print(f"\n🌐 API Endpoint:")
            print(f"   https://api.yourdomain.com/v1/inference")
            print(f"\n📖 Documentation:")
            print(f"   https://docs.yourdomain.com/")
            print(f"\n💡 Example Usage:")
            print(f"""
   curl -X POST https://api.yourdomain.com/v1/inference \\
     -H "Authorization: Bearer {api_key_str}" \\
     -H "Content-Type: application/json" \\
     -d '{{
       "model": "openvla-7b",
       "image": "BASE64_IMAGE",
       "instruction": "pick up the object"
     }}'
""")
            print("="*60 + "\n")
            
            # Offer to send welcome email
            send_email = input("Send welcome email? (y/n): ").strip().lower()
            if send_email == 'y':
                print("✉️  Email functionality not implemented yet")
                print("   Manually send them:")
                print(f"   - API Key: {api_key_str}")
                print(f"   - Documentation: https://docs.yourdomain.com/")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error creating customer: {e}")
            raise


async def list_customers():
    """List all customers."""
    
    print("\n" + "="*60)
    print("📋 Customer List")
    print("="*60 + "\n")
    
    session_factory = await get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Customer)
            .order_by(Customer.created_at.desc())
        )
        customers = result.scalars().all()
        
        if not customers:
            print("No customers found.")
            return
        
        print(f"{'Company':<30} {'Tier':<12} {'Active':<8} {'Usage':<15} {'Created'}")
        print("-" * 90)
        
        for customer in customers:
            active = "✓" if customer.is_active else "✗"
            usage = f"{customer.monthly_usage:,}"
            if customer.monthly_quota:
                usage += f"/{customer.monthly_quota:,}"
            created = customer.created_at.strftime("%Y-%m-%d")
            
            print(f"{customer.company_name:<30} {customer.tier:<12} {active:<8} {usage:<15} {created}")


async def view_customer_details():
    """View detailed information for a customer."""
    
    print("\n" + "="*60)
    print("🔍 Customer Details")
    print("="*60 + "\n")
    
    search = input("Enter company name or customer ID: ").strip()
    
    session_factory = await get_session_factory()
    async with session_factory() as session:
        # Try to find by company name or customer ID
        try:
            # Try as UUID first
            from uuid import UUID
            customer_id = UUID(search)
            result = await session.execute(
                select(Customer).where(Customer.customer_id == customer_id)
            )
        except ValueError:
            # Search by company name
            result = await session.execute(
                select(Customer).where(Customer.company_name.ilike(f"%{search}%"))
            )
        
        customer = result.scalar_one_or_none()
        
        if not customer:
            print(f"❌ No customer found matching: {search}")
            return
        
        # Get API keys
        key_result = await session.execute(
            select(APIKey).where(APIKey.customer_id == customer.customer_id)
        )
        api_keys = key_result.scalars().all()
        
        # Display details
        print(f"\n📋 Company: {customer.company_name}")
        print(f"📧 Email: {customer.email}")
        print(f"🆔 Customer ID: {customer.customer_id}")
        print(f"🎯 Tier: {customer.tier}")
        print(f"✓ Active: {'Yes' if customer.is_active else 'No'}")
        print(f"📊 Usage: {customer.monthly_usage:,}")
        if customer.monthly_quota:
            print(f"💯 Quota: {customer.monthly_quota:,}")
            remaining = customer.monthly_quota - customer.monthly_usage
            print(f"🔢 Remaining: {remaining:,} ({remaining/customer.monthly_quota*100:.1f}%)")
        else:
            print(f"💯 Quota: Unlimited")
        print(f"📅 Created: {customer.created_at}")
        
        print(f"\n🔑 API Keys ({len(api_keys)}):")
        for i, key in enumerate(api_keys, 1):
            status = "Active" if key.is_active else "Inactive"
            print(f"   {i}. {key.key_prefix}... ({status})")
            print(f"      Created: {key.created_at}")
            print(f"      Limits: {key.rate_limit_per_minute} req/min, {key.rate_limit_per_day} req/day")


async def deactivate_customer():
    """Deactivate a customer account."""
    
    print("\n" + "="*60)
    print("🚫 Deactivate Customer")
    print("="*60 + "\n")
    
    search = input("Enter company name or customer ID: ").strip()
    
    session_factory = await get_session_factory()
    async with session_factory() as session:
        # Find customer
        try:
            from uuid import UUID
            customer_id = UUID(search)
            result = await session.execute(
                select(Customer).where(Customer.customer_id == customer_id)
            )
        except ValueError:
            result = await session.execute(
                select(Customer).where(Customer.company_name.ilike(f"%{search}%"))
            )
        
        customer = result.scalar_one_or_none()
        
        if not customer:
            print(f"❌ No customer found matching: {search}")
            return
        
        print(f"\nCustomer: {customer.company_name}")
        print(f"Email: {customer.email}")
        print(f"Tier: {customer.tier}")
        
        confirm = input("\nAre you sure you want to deactivate this account? (yes/no): ").strip().lower()
        
        if confirm == "yes":
            customer.is_active = False
            
            # Also deactivate all API keys
            await session.execute(
                "UPDATE api_keys SET is_active = false WHERE customer_id = :customer_id",
                {"customer_id": customer.customer_id}
            )
            
            await session.commit()
            print(f"\n✅ Customer '{customer.company_name}' has been deactivated")
        else:
            print("\n❌ Deactivation cancelled")


async def main():
    """Main menu."""
    
    while True:
        print("\n" + "="*60)
        print("🤖 VLA API - Customer Management")
        print("="*60)
        print("\nOptions:")
        print("  1. Create new customer")
        print("  2. List all customers")
        print("  3. View customer details")
        print("  4. Deactivate customer")
        print("  5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        try:
            if choice == "1":
                await create_customer_interactive()
            elif choice == "2":
                await list_customers()
            elif choice == "3":
                await view_customer_details()
            elif choice == "4":
                await deactivate_customer()
            elif choice == "5":
                print("\nGoodbye! 👋")
                break
            else:
                print("❌ Invalid choice. Please select 1-5.")
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

