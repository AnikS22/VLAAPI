"""Admin statistics endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime, timedelta
from typing import Optional

from src.api.dependencies import get_db
from src.models.database import User, Customer, InferenceLog, SafetyIncident
from src.utils.admin_auth import get_current_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def get_admin_stats(
    days: int = Query(30, ge=1, le=365),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive admin statistics.

    Returns system-wide metrics including:
    - Customer counts and tier distribution
    - Request statistics and success rates
    - Revenue metrics (MRR)
    - Safety incident summary
    - Top customers by usage
    """
    # Calculate time range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Total customers
    total_customers_query = select(func.count(Customer.customer_id))
    total_customers_result = await db.execute(total_customers_query)
    total_customers = total_customers_result.scalar() or 0

    # Active customers (have made at least one request)
    active_customers_query = select(func.count(func.distinct(Customer.customer_id))).select_from(
        Customer
    ).join(
        InferenceLog, Customer.customer_id == InferenceLog.customer_id
    ).where(
        InferenceLog.timestamp >= start_date
    )
    active_customers_result = await db.execute(active_customers_query)
    active_customers = active_customers_result.scalar() or 0

    # Tier distribution
    tier_query = select(
        Customer.tier,
        func.count(Customer.customer_id).label('count')
    ).group_by(Customer.tier)
    tier_result = await db.execute(tier_query)
    tier_distribution = {row.tier: row.count for row in tier_result}

    # Total requests in period
    total_requests_query = select(func.count(InferenceLog.log_id)).where(
        InferenceLog.timestamp >= start_date
    )
    total_requests_result = await db.execute(total_requests_query)
    total_requests = total_requests_result.scalar() or 0

    # Success rate
    success_query = select(func.count(InferenceLog.log_id)).where(
        and_(
            InferenceLog.timestamp >= start_date,
            InferenceLog.status == "success"
        )
    )
    success_result = await db.execute(success_query)
    success_count = success_result.scalar() or 0
    success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0

    # Average latency
    avg_latency_query = select(func.avg(InferenceLog.latency_ms)).where(
        InferenceLog.timestamp >= start_date
    )
    avg_latency_result = await db.execute(avg_latency_query)
    avg_latency_ms = avg_latency_result.scalar() or 0

    # Monthly Recurring Revenue (MRR)
    # Pro tier: $499/month, Enterprise: custom pricing (assume $2000 for calculation)
    paying_customers_query = select(
        Customer.tier,
        func.count(Customer.customer_id).label('count')
    ).where(
        Customer.tier.in_(["pro", "enterprise"])
    ).group_by(Customer.tier)
    paying_result = await db.execute(paying_customers_query)
    paying_customers = 0
    monthly_revenue = 0
    for row in paying_result:
        paying_customers += row.count
        if row.tier == "pro":
            monthly_revenue += row.count * 499
        elif row.tier == "enterprise":
            monthly_revenue += row.count * 2000

    # Safety incidents
    total_incidents_query = select(func.count(SafetyIncident.incident_id)).where(
        SafetyIncident.timestamp >= start_date
    )
    total_incidents_result = await db.execute(total_incidents_query)
    total_incidents = total_incidents_result.scalar() or 0

    critical_incidents_query = select(func.count(SafetyIncident.incident_id)).where(
        and_(
            SafetyIncident.timestamp >= start_date,
            SafetyIncident.severity == "critical"
        )
    )
    critical_incidents_result = await db.execute(critical_incidents_query)
    critical_incidents = critical_incidents_result.scalar() or 0

    # Top customers by usage
    top_customers_query = select(
        Customer.customer_id,
        Customer.email,
        Customer.company_name,
        Customer.tier,
        func.count(InferenceLog.log_id).label('request_count')
    ).select_from(
        Customer
    ).join(
        InferenceLog, Customer.customer_id == InferenceLog.customer_id
    ).where(
        InferenceLog.timestamp >= start_date
    ).group_by(
        Customer.customer_id,
        Customer.email,
        Customer.company_name,
        Customer.tier
    ).order_by(
        desc('request_count')
    ).limit(10)

    top_customers_result = await db.execute(top_customers_query)
    top_customers = [
        {
            "customer_id": row.customer_id,
            "email": row.email,
            "company_name": row.company_name,
            "tier": row.tier,
            "monthly_usage": row.request_count
        }
        for row in top_customers_result
    ]

    # Recent critical incidents
    recent_incidents_query = select(SafetyIncident).where(
        and_(
            SafetyIncident.timestamp >= start_date,
            SafetyIncident.severity.in_(["critical", "high"])
        )
    ).order_by(desc(SafetyIncident.timestamp)).limit(5)

    recent_incidents_result = await db.execute(recent_incidents_query)
    recent_incidents = [
        {
            "incident_id": incident.incident_id,
            "timestamp": incident.timestamp.isoformat(),
            "severity": incident.severity,
            "violation_type": incident.violation_type,
            "customer_id": str(incident.customer_id),
            "robot_type": incident.robot_type,
            "action_taken": incident.action_taken
        }
        for incident in recent_incidents_result.scalars()
    ]

    return {
        "total_customers": total_customers,
        "active_customers": active_customers,
        "tier_distribution": tier_distribution,
        "total_requests": total_requests,
        "success_rate": success_rate,
        "avg_latency_ms": float(avg_latency_ms) if avg_latency_ms else 0,
        "paying_customers": paying_customers,
        "monthly_revenue": monthly_revenue,
        "total_incidents": total_incidents,
        "critical_incidents": critical_incidents,
        "top_customers": top_customers,
        "recent_incidents": recent_incidents
    }
