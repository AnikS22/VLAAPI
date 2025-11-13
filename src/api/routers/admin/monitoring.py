"""Admin system monitoring endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timedelta
import psutil
import os

from src.api.dependencies import get_db
from src.models.database import User, InferenceLog
from src.utils.admin_auth import get_current_admin_user

router = APIRouter(prefix="/admin/monitoring", tags=["admin"])


@router.get("/health")
async def get_system_health(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive system health metrics.
    """
    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        database_status = "disconnected"

    # Check Redis (if configured)
    redis_status = "connected"  # Would check actual Redis connection

    # API metrics (last 5 minutes)
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)

    # Requests per minute
    recent_count_query = select(func.count(InferenceLog.log_id)).where(
        InferenceLog.timestamp >= five_min_ago
    )
    recent_count_result = await db.execute(recent_count_query)
    recent_count = recent_count_result.scalar() or 0
    requests_per_minute = recent_count / 5

    # Average response time (last hour)
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    avg_response_query = select(func.avg(InferenceLog.latency_ms)).where(
        InferenceLog.timestamp >= one_hour_ago
    )
    avg_response_result = await db.execute(avg_response_query)
    avg_response_time = avg_response_result.scalar() or 0

    # Error rate (last hour)
    total_query = select(func.count(InferenceLog.log_id)).where(
        InferenceLog.timestamp >= one_hour_ago
    )
    total_result = await db.execute(total_query)
    total_count = total_result.scalar() or 0

    error_query = select(func.count(InferenceLog.log_id)).where(
        InferenceLog.timestamp >= one_hour_ago,
        InferenceLog.status == "error"
    )
    error_result = await db.execute(error_query)
    error_count = error_result.scalar() or 0
    error_rate = (error_count / total_count * 100) if total_count > 0 else 0

    # System resources
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Queue metrics (simulated - would use actual queue)
    queue_depth = 0
    processing_count = 0
    avg_wait_time = 0
    throughput = requests_per_minute

    # Active connections (simulated)
    active_connections = 10

    # Uptime
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_days = int(uptime_seconds / 86400)
            uptime_hours = int((uptime_seconds % 86400) / 3600)
            uptime = f"{uptime_days}d {uptime_hours}h"
    except:
        uptime = "Unknown"

    # Recent errors (last 24 hours)
    day_ago = datetime.utcnow() - timedelta(hours=24)
    recent_errors_query = select(InferenceLog).where(
        InferenceLog.timestamp >= day_ago,
        InferenceLog.status == "error"
    ).order_by(InferenceLog.timestamp.desc()).limit(10)

    recent_errors_result = await db.execute(recent_errors_query)
    recent_errors = [
        {
            "timestamp": log.timestamp.isoformat(),
            "message": f"Inference failed: {log.robot_type}",
            "endpoint": "/v1/inference",
            "status_code": 500
        }
        for log in recent_errors_result.scalars()
    ]

    return {
        "status": "healthy" if database_status == "connected" else "degraded",
        "database_status": database_status,
        "redis_status": redis_status,
        "queue_status": "operational",
        "requests_per_minute": requests_per_minute,
        "avg_response_time": float(avg_response_time) if avg_response_time else 0,
        "error_rate": error_rate,
        "active_connections": active_connections,
        "cpu_usage": cpu_usage,
        "memory_usage": memory.percent,
        "disk_usage": disk.percent,
        "queue_depth": queue_depth,
        "processing_count": processing_count,
        "avg_wait_time": avg_wait_time,
        "throughput": throughput,
        "uptime": uptime,
        "recent_errors": recent_errors
    }


@router.get("/gpu")
async def get_gpu_metrics(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get GPU utilization metrics.

    Note: This is a simulated response. In production, you would use
    nvidia-smi or pynvml to get actual GPU metrics.
    """
    # Simulated GPU metrics
    # In production, use: nvidia-smi or pynvml library
    gpus = [
        {
            "name": "NVIDIA A100",
            "utilization": 75,
            "memory_used": 32,
            "memory_total": 40,
            "temperature": 72,
            "power_draw": 250,
            "power_limit": 400
        }
    ]

    return {
        "gpus": gpus,
        "timestamp": datetime.utcnow().isoformat()
    }
