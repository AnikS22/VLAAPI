"""Monitoring API router for health checks and metrics."""

import logging
from datetime import datetime

import torch
from fastapi import APIRouter, Depends
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from src.api.dependencies import get_db
from src.core.config import settings
from src.core.database import db_manager
from src.core.redis_client import redis_manager
from src.middleware.authentication import api_key_auth
from src.models.api_models import GPUInfo, HealthCheckResponse, ServiceHealth
from src.models.database import Customer
from src.monitoring.gpu_monitor import gpu_monitor
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


@router.get("/health/detailed", dependencies=[Depends(api_key_auth)])
async def detailed_health_check(session: AsyncSession = Depends(get_db)):
    """Detailed health check with comprehensive component status.

    Checks:
    - Database connectivity
    - Redis connectivity
    - GPU availability and utilization
    - Model loading status
    - Inference service status
    - Queue statistics

    Returns:
        Detailed health status for all components
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
    }

    # Check database
    try:
        result = await session.execute(select(Customer).limit(1))
        result.scalar_one_or_none()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection OK",
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database error: {str(e)}",
        }

    # Check Redis
    try:
        await redis_manager.redis.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection OK",
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis error: {str(e)}",
        }

    # Check GPU with enhanced monitoring
    if gpu_monitor.is_initialized():
        gpu_count = gpu_monitor.get_device_count()
        gpu_stats = gpu_monitor.get_all_gpu_stats()

        health_status["checks"]["gpu"] = {
            "status": "healthy",
            "message": f"{gpu_count} GPU(s) available",
            "devices": [
                {
                    "device_id": stats.device_id,
                    "name": stats.device_name,
                    "utilization": stats.utilization,
                    "memory_used_gb": round(stats.memory_used / (1024**3), 2),
                    "memory_total_gb": round(stats.memory_total / (1024**3), 2),
                    "temperature": stats.temperature,
                }
                for stats in gpu_stats.values()
            ],
        }
    else:
        health_status["checks"]["gpu"] = {
            "status": "unavailable",
            "message": "No GPU monitoring available",
        }

    # Check models
    loaded_models = model_manager.get_loaded_models()
    health_status["checks"]["models"] = {
        "status": "healthy" if loaded_models else "unhealthy",
        "message": f"{len(loaded_models)} model(s) loaded",
        "models": loaded_models,
    }

    # Check inference service
    if inference_service._running:
        queue_depth = inference_service.get_queue_depth()
        health_status["checks"]["inference_service"] = {
            "status": "healthy",
            "message": "Inference service running",
            "queue_depth": queue_depth,
            "workers": len(inference_service._workers),
        }
    else:
        health_status["status"] = "unhealthy"
        health_status["checks"]["inference_service"] = {
            "status": "unhealthy",
            "message": "Inference service not running",
        }

    return health_status


@router.get("/gpu/stats", dependencies=[Depends(api_key_auth)])
async def gpu_statistics():
    """Get current GPU statistics from GPU monitor.

    Returns:
        Current GPU utilization, memory, temperature, and power statistics
    """
    if not gpu_monitor.is_initialized():
        return {
            "available": False,
            "message": "GPU monitoring not available",
        }

    stats = gpu_monitor.get_all_gpu_stats()

    return {
        "available": True,
        "device_count": gpu_monitor.get_device_count(),
        "devices": [
            {
                "device_id": s.device_id,
                "name": s.device_name,
                "utilization_percent": s.utilization,
                "memory": {
                    "used_bytes": s.memory_used,
                    "total_bytes": s.memory_total,
                    "free_bytes": s.memory_free,
                    "used_gb": round(s.memory_used / (1024**3), 2),
                    "total_gb": round(s.memory_total / (1024**3), 2),
                    "utilization_percent": round(
                        (s.memory_used / s.memory_total * 100), 2
                    ),
                },
                "temperature_celsius": s.temperature,
                "power": {
                    "usage_watts": s.power_usage,
                    "limit_watts": s.power_limit,
                    "utilization_percent": round(
                        (s.power_usage / s.power_limit * 100), 2
                    ),
                },
            }
            for s in stats.values()
        ],
    }


@router.get("/queue/stats", dependencies=[Depends(api_key_auth)])
async def queue_statistics():
    """Get inference queue statistics.

    Returns:
        Current queue depth and capacity information
    """
    queue_depth = inference_service.get_queue_depth()
    queue_capacity = settings.inference_queue_max_size

    return {
        "current_depth": queue_depth,
        "capacity": queue_capacity,
        "utilization_percent": round((queue_depth / queue_capacity * 100), 2),
        "available_slots": queue_capacity - queue_depth,
        "workers": {
            "total": len(inference_service._workers),
            "max": settings.inference_max_workers,
        },
    }


@router.get("/models/stats", dependencies=[Depends(api_key_auth)])
async def model_statistics():
    """Get loaded model statistics.

    Returns:
        Information about loaded models and their status
    """
    loaded_models = model_manager.get_loaded_models()

    models_info = []
    for model_id in loaded_models:
        info = {
            "model_id": model_id,
            "loaded": True,
        }

        # Add GPU device info if available
        if hasattr(model_manager, "device"):
            info["device"] = str(model_manager.device)

        models_info.append(info)

    return {
        "total_loaded": len(loaded_models),
        "models": models_info,
    }
