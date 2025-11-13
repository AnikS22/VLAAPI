"""Admin customer management endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from pydantic import BaseModel
from datetime import datetime, timedelta
from uuid import UUID

from src.api.dependencies import get_db
from src.models.database import User, Customer, InferenceLog
from src.utils.admin_auth import get_current_admin_user

router = APIRouter(prefix="/admin/customers", tags=["admin"])


class UpdateCustomerTierRequest(BaseModel):
    tier: str


@router.get("")
async def get_all_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of all customers with their usage stats.
    """
    offset = (page - 1) * limit

    # Total count
    count_query = select(func.count(Customer.customer_id))
    count_result = await db.execute(count_query)
    total_count = count_result.scalar() or 0

    # Get customers with basic info
    customers_query = select(Customer).order_by(
        desc(Customer.created_at)
    ).offset(offset).limit(limit)

    customers_result = await db.execute(customers_query)
    customers = customers_result.scalars().all()

    # Get usage stats for each customer
    customer_list = []
    for customer in customers:
        # Get monthly usage count
        usage_query = select(func.count(InferenceLog.log_id)).where(
            InferenceLog.customer_id == customer.customer_id
        )
        usage_result = await db.execute(usage_query)
        total_usage = usage_result.scalar() or 0

        customer_list.append({
            "customer_id": str(customer.customer_id),
            "email": customer.email,
            "company_name": customer.company_name,
            "tier": customer.tier,
            "monthly_usage": customer.monthly_usage,
            "monthly_quota": customer.monthly_quota,
            "is_active": customer.is_active,
            "created_at": customer.created_at.isoformat(),
            "total_requests": total_usage
        })

    return {
        "customers": customer_list,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit
    }


@router.get("/{customer_id}")
async def get_customer_details(
    customer_id: UUID,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific customer.
    """
    # Get customer
    customer_query = select(Customer).where(Customer.customer_id == customer_id)
    customer_result = await db.execute(customer_query)
    customer = customer_result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Get usage statistics
    total_requests_query = select(func.count(InferenceLog.log_id)).where(
        InferenceLog.customer_id == customer_id
    )
    total_requests_result = await db.execute(total_requests_query)
    total_requests = total_requests_result.scalar() or 0

    # Success rate
    success_query = select(func.count(InferenceLog.log_id)).where(
        and_(
            InferenceLog.customer_id == customer_id,
            InferenceLog.status == "success"
        )
    )
    success_result = await db.execute(success_query)
    success_count = success_result.scalar() or 0
    success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0

    # Recent inferences
    recent_query = select(InferenceLog).where(
        InferenceLog.customer_id == customer_id
    ).order_by(desc(InferenceLog.timestamp)).limit(10)

    recent_result = await db.execute(recent_query)
    recent_inferences = [
        {
            "log_id": str(log.log_id),
            "timestamp": log.timestamp.isoformat(),
            "instruction": log.instruction,
            "status": log.status,
            "latency_ms": log.latency_ms,
            "safety_score": log.safety_score
        }
        for log in recent_result.scalars()
    ]

    return {
        "customer_id": str(customer.customer_id),
        "email": customer.email,
        "company_name": customer.company_name,
        "tier": customer.tier,
        "monthly_usage": customer.monthly_usage,
        "monthly_quota": customer.monthly_quota,
        "is_active": customer.is_active,
        "created_at": customer.created_at.isoformat(),
        "stripe_customer_id": customer.stripe_customer_id,
        "stripe_subscription_status": customer.stripe_subscription_status,
        "total_requests": total_requests,
        "success_rate": success_rate,
        "recent_inferences": recent_inferences
    }


@router.patch("/{customer_id}/tier")
async def update_customer_tier(
    customer_id: UUID,
    request: UpdateCustomerTierRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually update a customer's tier (admin override).
    """
    # Validate tier
    valid_tiers = ["free", "pro", "enterprise"]
    if request.tier not in valid_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}"
        )

    # Get customer
    customer_query = select(Customer).where(Customer.customer_id == customer_id)
    customer_result = await db.execute(customer_query)
    customer = customer_result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Update tier and quota
    customer.tier = request.tier

    # Update quota based on tier
    if request.tier == "free":
        customer.monthly_quota = 100
    elif request.tier == "pro":
        customer.monthly_quota = 50000
    elif request.tier == "enterprise":
        customer.monthly_quota = None  # Unlimited

    await db.commit()
    await db.refresh(customer)

    return {
        "customer_id": str(customer.customer_id),
        "email": customer.email,
        "tier": customer.tier,
        "monthly_quota": customer.monthly_quota,
        "updated_at": datetime.utcnow().isoformat()
    }
