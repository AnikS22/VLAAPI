"""Admin safety incident management endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import Optional
from datetime import datetime, timedelta

from src.api.dependencies import get_db
from src.models.database import User, SafetyIncident
from src.utils.admin_auth import get_current_admin_user

router = APIRouter(prefix="/admin/safety", tags=["admin"])


@router.get("/incidents")
async def get_all_safety_incidents(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    severity: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of all safety incidents with optional severity filter.
    """
    offset = (page - 1) * limit
    start_date = datetime.utcnow() - timedelta(days=days)

    # Build base query
    base_conditions = [SafetyIncident.timestamp >= start_date]
    if severity:
        base_conditions.append(SafetyIncident.severity == severity)

    # Total count
    count_query = select(func.count(SafetyIncident.incident_id)).where(
        and_(*base_conditions)
    )
    count_result = await db.execute(count_query)
    total_count = count_result.scalar() or 0

    # Count by severity
    critical_query = select(func.count(SafetyIncident.incident_id)).where(
        and_(
            SafetyIncident.timestamp >= start_date,
            SafetyIncident.severity == "critical"
        )
    )
    critical_result = await db.execute(critical_query)
    critical_count = critical_result.scalar() or 0

    high_query = select(func.count(SafetyIncident.incident_id)).where(
        and_(
            SafetyIncident.timestamp >= start_date,
            SafetyIncident.severity == "high"
        )
    )
    high_result = await db.execute(high_query)
    high_count = high_result.scalar() or 0

    # Get incidents
    incidents_query = select(SafetyIncident).where(
        and_(*base_conditions)
    ).order_by(
        desc(SafetyIncident.timestamp)
    ).offset(offset).limit(limit)

    incidents_result = await db.execute(incidents_query)
    incidents = [
        {
            "incident_id": incident.incident_id,
            "timestamp": incident.timestamp.isoformat(),
            "severity": incident.severity,
            "violation_type": incident.violation_type,
            "robot_type": incident.robot_type,
            "environment_type": incident.environment_type,
            "customer_id": str(incident.customer_id),
            "log_id": str(incident.log_id) if incident.log_id else None,
            "action_taken": incident.action_taken,
            "details": incident.details or {}
        }
        for incident in incidents_result.scalars()
    ]

    # Get incident patterns (most common types)
    patterns_query = select(
        SafetyIncident.violation_type,
        func.count(SafetyIncident.incident_id).label('count')
    ).where(
        SafetyIncident.timestamp >= start_date
    ).group_by(
        SafetyIncident.violation_type
    ).order_by(
        desc('count')
    ).limit(5)

    patterns_result = await db.execute(patterns_query)
    incident_patterns = [
        {
            "type": row.violation_type,
            "count": row.count,
            "trend": 0  # Could calculate trend vs previous period
        }
        for row in patterns_result
    ]

    return {
        "incidents": incidents,
        "total_count": total_count,
        "critical_count": critical_count,
        "high_count": high_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit,
        "incident_patterns": incident_patterns
    }
