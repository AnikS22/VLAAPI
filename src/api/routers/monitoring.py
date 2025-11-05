"""Monitoring API router for health checks and metrics."""

import logging
from datetime import datetime

import torch
from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

from src.core.config import settings
from src.core.database import db_manager
from src.core.redis_client import redis_manager
from src.models.api_models import GPUInfo, HealthCheckResponse, ServiceHealth
from src.services.model_loader import model_manager
from src.services.vla_inference import inference_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["monitoring"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint for monitoring system status.

    Checks the health of all system components including API, database,
    Redis, GPU, and loaded models.

    Returns:
        HealthCheckResponse with detailed health status
    """
    # Check database
    try:
        db_healthy = await db_manager.health_check()
        db_status = "healthy" if db_healthy else "unhealthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    # Check Redis
    try:
        redis_healthy = await redis_manager.health_check()
        redis_status = "healthy" if redis_healthy else "unhealthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"

    # Check GPU
    gpu_info = None
    gpu_status = "healthy"

    if torch.cuda.is_available():
        try:
            device_id = settings.gpu_device
            device_name = torch.cuda.get_device_name(device_id)
            memory_allocated = torch.cuda.memory_allocated(device_id) / 1024**3
            memory_total = torch.cuda.get_device_properties(device_id).total_memory / 1024**3
            utilization = int((memory_allocated / memory_total) * 100)

            gpu_info = GPUInfo(
                device_name=device_name,
                memory_used_gb=round(memory_allocated, 2),
                memory_total_gb=round(memory_total, 2),
                utilization_percent=utilization,
            )

            if utilization > 95:
                gpu_status = "degraded"
        except Exception as e:
            logger.error(f"GPU health check failed: {e}")
            gpu_status = "unhealthy"
    else:
        gpu_status = "unavailable"

    # Get queue depth
    queue_depth = inference_service.get_queue_depth()

    # Get loaded models
    loaded_models = model_manager.get_loaded_models()

    # Overall status
    if db_status == "unhealthy" or redis_status == "unhealthy":
        overall_status = "unhealthy"
    elif gpu_status == "degraded" or gpu_status == "unavailable":
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        services={
            "api": ServiceHealth(status="healthy"),
            "database": ServiceHealth(status=db_status),
            "redis": ServiceHealth(status=redis_status),
            "gpu": ServiceHealth(status=gpu_status),
        },
        gpu_info=gpu_info,
        queue_depth=queue_depth,
        models_loaded=loaded_models,
    )


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint.

    Returns:
        Prometheus-formatted metrics
    """
    if not settings.metrics_enabled:
        return {"error": "Metrics disabled"}

    # Generate Prometheus metrics
    metrics_output = generate_latest(REGISTRY)

    return Response(content=metrics_output, media_type=CONTENT_TYPE_LATEST)


# Import Response for metrics endpoint
from starlette.responses import Response
