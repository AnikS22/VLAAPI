"""Analytics endpoints for usage, safety, and performance metrics."""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routers.auth import get_current_user
from src.core.database import get_db_session
from src.models.database import (
    Customer,
    InferenceLog,
    InstructionAnalytics,
    RobotPerformanceMetrics,
    SafetyIncident,
    User,
)

router = APIRouter(prefix="/v1/analytics", tags=["Analytics"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class UsageDataPoint(BaseModel):
    """Time-series usage data point."""

    timestamp: str
    count: int
    success_count: int
    error_count: int
    avg_latency_ms: float | None


class UsageAnalyticsResponse(BaseModel):
    """Usage analytics over time."""

    total_requests: int
    success_rate: float
    avg_latency_ms: float
    data_points: list[UsageDataPoint]


class SafetyIncidentData(BaseModel):
    """Safety incident summary."""

    incident_id: int
    timestamp: str
    severity: str
    violation_type: str
    robot_type: str
    environment_type: str
    action_taken: str


class SafetyAnalyticsResponse(BaseModel):
    """Safety analytics with incidents."""

    total_incidents: int
    critical_incidents: int
    high_severity_incidents: int
    incidents_by_type: dict[str, int]
    recent_incidents: list[SafetyIncidentData]


class RobotProfileData(BaseModel):
    """Robot-specific performance profile."""

    robot_type: str
    total_inferences: int
    success_rate: float
    avg_latency_ms: float
    avg_safety_score: float
    common_instructions: list[str]


class RobotProfilesResponse(BaseModel):
    """Robot performance profiles."""

    profiles: list[RobotProfileData]


class TopInstruction(BaseModel):
    """Top instruction with usage stats."""

    instruction_text: str
    total_uses: int
    success_rate: float
    avg_latency_ms: float


class TopInstructionsResponse(BaseModel):
    """Most common instructions."""

    instructions: list[TopInstruction]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def get_customer_for_user(user: User, db: AsyncSession) -> Customer:
    """Get customer for authenticated user."""
    result = await db.execute(
        select(Customer).where(Customer.user_id == user.user_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found"
        )

    return customer


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/usage", response_model=UsageAnalyticsResponse)
async def get_usage_analytics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
) -> UsageAnalyticsResponse:
    """Get usage analytics over time.

    Args:
        current_user: Current authenticated user
        db: Database session
        days: Number of days to analyze

    Returns:
        UsageAnalyticsResponse with time-series data
    """
    customer = await get_customer_for_user(current_user, db)

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get aggregate stats
    result = await db.execute(
        select(
            func.count(InferenceLog.log_id).label("total"),
            func.count(InferenceLog.log_id).filter(InferenceLog.status == "success").label("success"),
            func.avg(InferenceLog.inference_latency_ms).label("avg_latency"),
        )
        .where(InferenceLog.customer_id == customer.customer_id)
        .where(InferenceLog.timestamp >= start_date)
    )
    stats = result.one()

    total_requests = stats.total or 0
    success_count = stats.success or 0
    success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0.0
    avg_latency = float(stats.avg_latency) if stats.avg_latency else 0.0

    # Get time-series data (group by day)
    result = await db.execute(
        select(
            func.date_trunc("day", InferenceLog.timestamp).label("day"),
            func.count(InferenceLog.log_id).label("count"),
            func.count(InferenceLog.log_id).filter(InferenceLog.status == "success").label("success"),
            func.count(InferenceLog.log_id).filter(InferenceLog.status != "success").label("error"),
            func.avg(InferenceLog.inference_latency_ms).label("avg_latency"),
        )
        .where(InferenceLog.customer_id == customer.customer_id)
        .where(InferenceLog.timestamp >= start_date)
        .group_by(func.date_trunc("day", InferenceLog.timestamp))
        .order_by(func.date_trunc("day", InferenceLog.timestamp))
    )

    data_points = [
        UsageDataPoint(
            timestamp=row.day.isoformat(),
            count=row.count,
            success_count=row.success,
            error_count=row.error,
            avg_latency_ms=float(row.avg_latency) if row.avg_latency else None,
        )
        for row in result.all()
    ]

    return UsageAnalyticsResponse(
        total_requests=total_requests,
        success_rate=success_rate,
        avg_latency_ms=avg_latency,
        data_points=data_points,
    )


@router.get("/safety", response_model=SafetyAnalyticsResponse)
async def get_safety_analytics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
) -> SafetyAnalyticsResponse:
    """Get safety incident analytics.

    Args:
        current_user: Current authenticated user
        db: Database session
        days: Number of days to analyze

    Returns:
        SafetyAnalyticsResponse with incident data
    """
    customer = await get_customer_for_user(current_user, db)

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get total incidents
    result = await db.execute(
        select(func.count(SafetyIncident.incident_id))
        .where(SafetyIncident.customer_id == customer.customer_id)
        .where(SafetyIncident.timestamp >= start_date)
    )
    total_incidents = result.scalar() or 0

    # Get critical incidents
    result = await db.execute(
        select(func.count(SafetyIncident.incident_id))
        .where(SafetyIncident.customer_id == customer.customer_id)
        .where(SafetyIncident.timestamp >= start_date)
        .where(SafetyIncident.severity == "critical")
    )
    critical_incidents = result.scalar() or 0

    # Get high severity incidents
    result = await db.execute(
        select(func.count(SafetyIncident.incident_id))
        .where(SafetyIncident.customer_id == customer.customer_id)
        .where(SafetyIncident.timestamp >= start_date)
        .where(SafetyIncident.severity == "high")
    )
    high_severity_incidents = result.scalar() or 0

    # Get incidents by type
    result = await db.execute(
        select(
            SafetyIncident.violation_type,
            func.count(SafetyIncident.incident_id).label("count"),
        )
        .where(SafetyIncident.customer_id == customer.customer_id)
        .where(SafetyIncident.timestamp >= start_date)
        .group_by(SafetyIncident.violation_type)
    )
    incidents_by_type = {row.violation_type: row.count for row in result.all()}

    # Get recent incidents (last 10)
    result = await db.execute(
        select(SafetyIncident)
        .where(SafetyIncident.customer_id == customer.customer_id)
        .where(SafetyIncident.timestamp >= start_date)
        .order_by(SafetyIncident.timestamp.desc())
        .limit(10)
    )
    recent_incidents_raw = result.scalars().all()

    recent_incidents = [
        SafetyIncidentData(
            incident_id=incident.incident_id,
            timestamp=incident.timestamp.isoformat(),
            severity=incident.severity,
            violation_type=incident.violation_type,
            robot_type=incident.robot_type,
            environment_type=incident.environment_type,
            action_taken=incident.action_taken,
        )
        for incident in recent_incidents_raw
    ]

    return SafetyAnalyticsResponse(
        total_incidents=total_incidents,
        critical_incidents=critical_incidents,
        high_severity_incidents=high_severity_incidents,
        incidents_by_type=incidents_by_type,
        recent_incidents=recent_incidents,
    )


@router.get("/robot-profiles", response_model=RobotProfilesResponse)
async def get_robot_profiles(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
) -> RobotProfilesResponse:
    """Get robot-specific performance profiles.

    Args:
        current_user: Current authenticated user
        db: Database session
        days: Number of days to analyze

    Returns:
        RobotProfilesResponse with per-robot analytics
    """
    customer = await get_customer_for_user(current_user, db)

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get performance metrics by robot type
    result = await db.execute(
        select(
            InferenceLog.robot_type,
            func.count(InferenceLog.log_id).label("total"),
            func.count(InferenceLog.log_id).filter(InferenceLog.status == "success").label("success"),
            func.avg(InferenceLog.inference_latency_ms).label("avg_latency"),
            func.avg(InferenceLog.safety_score).label("avg_safety"),
        )
        .where(InferenceLog.customer_id == customer.customer_id)
        .where(InferenceLog.timestamp >= start_date)
        .group_by(InferenceLog.robot_type)
    )

    profiles = []
    for row in result.all():
        # Get common instructions for this robot type
        inst_result = await db.execute(
            select(InferenceLog.instruction)
            .where(InferenceLog.customer_id == customer.customer_id)
            .where(InferenceLog.robot_type == row.robot_type)
            .where(InferenceLog.timestamp >= start_date)
            .limit(5)
        )
        common_instructions = [inst for (inst,) in inst_result.all()]

        success_rate = (row.success / row.total * 100) if row.total > 0 else 0.0

        profiles.append(
            RobotProfileData(
                robot_type=row.robot_type,
                total_inferences=row.total,
                success_rate=success_rate,
                avg_latency_ms=float(row.avg_latency) if row.avg_latency else 0.0,
                avg_safety_score=float(row.avg_safety) if row.avg_safety else 0.0,
                common_instructions=common_instructions[:3],  # Top 3
            )
        )

    return RobotProfilesResponse(profiles=profiles)


@router.get("/top-instructions", response_model=TopInstructionsResponse)
async def get_top_instructions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(default=10, ge=1, le=50, description="Number of top instructions"),
) -> TopInstructionsResponse:
    """Get most common instructions with usage stats.

    Args:
        current_user: Current authenticated user
        db: Database session
        limit: Number of top instructions to return

    Returns:
        TopInstructionsResponse with popular instructions
    """
    customer = await get_customer_for_user(current_user, db)

    # Get top instructions from instruction analytics
    result = await db.execute(
        select(InstructionAnalytics)
        .order_by(InstructionAnalytics.total_uses.desc())
        .limit(limit)
    )
    analytics = result.scalars().all()

    instructions = [
        TopInstruction(
            instruction_text=item.instruction_text,
            total_uses=item.total_uses,
            success_rate=item.success_rate * 100,  # Convert to percentage
            avg_latency_ms=item.avg_latency_ms,
        )
        for item in analytics
    ]

    return TopInstructionsResponse(instructions=instructions)
