"""Models API router for listing and managing VLA models."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_authenticated_user
from src.core.model_registry import ModelRegistry, ModelStatus
from src.middleware.authentication import APIKeyInfo
from src.services.multi_model_manager import multi_model_manager
from src.services.model_router import ModelRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["models"])


# Response Models
class ModelInfoResponse(BaseModel):
    """Model information response."""
    model_id: str
    name: str
    version: str
    architecture: str
    status: str
    size_gb: float
    min_vram_gb: float
    expected_latency_p50_ms: float
    cost_per_1k: float
    supported_robots: List[str]
    accuracy_benchmark: Optional[float] = None
    is_loaded: bool


class ModelStatsResponse(BaseModel):
    """Model runtime statistics."""
    model_id: str
    inference_count: int
    avg_latency_ms: float
    vram_usage_gb: float
    gpu_device: int


@router.get("/models", response_model=List[ModelInfoResponse])
async def list_models(
    status: Optional[str] = None,
    robot_type: Optional[str] = None,
    max_vram_gb: Optional[float] = None,
    api_key: APIKeyInfo = Depends(get_authenticated_user)
):
    """List available VLA models with filtering.

    Query Parameters:
    - status: Filter by status (production, beta, deprecated)
    - robot_type: Filter by robot compatibility (e.g., franka_panda)
    - max_vram_gb: Maximum VRAM requirement

    Returns:
        List of available models with metadata and availability status
    """
    # Parse status
    status_enum = None
    if status:
        try:
            status_enum = ModelStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Valid values: production, beta, deprecated"
            )

    # Get models from registry
    models = ModelRegistry.list_models(
        status=status_enum,
        robot_type=robot_type,
        max_vram_gb=max_vram_gb
    )

    # Convert to response format
    return [
        ModelInfoResponse(
            model_id=m.model_id,
            name=m.name,
            version=m.version,
            architecture=m.architecture.value,
            status=m.status.value,
            size_gb=m.size_gb,
            min_vram_gb=m.min_vram_gb,
            expected_latency_p50_ms=m.expected_latency_p50_ms,
            cost_per_1k=m.cost_per_1k,
            supported_robots=m.supported_robots,
            accuracy_benchmark=m.accuracy_benchmark,
            is_loaded=multi_model_manager.is_model_loaded(m.model_id)
        )
        for m in models
    ]


@router.get("/models/{model_id}")
async def get_model_info(
    model_id: str,
    api_key: APIKeyInfo = Depends(get_authenticated_user)
):
    """Get detailed information about a specific model.

    Returns:
        Model configuration and runtime statistics (if loaded)
    """
    try:
        model = ModelRegistry.get_model(model_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )

    # Get runtime stats if model is loaded
    runtime_stats = None
    if multi_model_manager.is_model_loaded(model_id):
        try:
            stats = multi_model_manager.get_model_stats(model_id)
            runtime_stats = {
                "inference_count": stats.inference_count,
                "avg_latency_ms": stats.avg_latency_ms,
                "p95_latency_ms": stats.p95_latency_ms,
                "vram_usage_gb": stats.vram_usage_gb,
                "gpu_device": stats.gpu_device,
                "loaded_at": stats.loaded_at.isoformat(),
                "last_used": stats.last_used.isoformat()
            }
        except Exception as e:
            logger.warning(f"Failed to get stats for {model_id}: {e}")

    return {
        "model_id": model.model_id,
        "name": model.name,
        "version": model.version,
        "architecture": model.architecture.value,
        "status": model.status.value,
        "size_gb": model.size_gb,
        "hardware_requirements": {
            "min_vram_gb": model.min_vram_gb,
            "recommended_vram_gb": model.recommended_vram_gb,
            "supports_fp16": model.supports_fp16,
            "supports_bf16": model.supports_bf16,
            "supports_4bit": model.supports_4bit
        },
        "performance": {
            "expected_latency_p50_ms": model.expected_latency_p50_ms,
            "expected_latency_p95_ms": model.expected_latency_p95_ms,
            "expected_throughput_rps": model.expected_throughput_rps,
            "cost_per_1k": model.cost_per_1k
        },
        "capabilities": {
            "supported_robots": model.supported_robots,
            "action_dim": model.action_dim,
            "max_image_size": model.max_image_size
        },
        "training": {
            "datasets": model.training_datasets,
            "accuracy_benchmark": model.accuracy_benchmark
        },
        "is_loaded": multi_model_manager.is_model_loaded(model_id),
        "runtime_stats": runtime_stats
    }


@router.post("/models/{model_id}/load")
async def load_model(
    model_id: str,
    api_key: APIKeyInfo = Depends(get_authenticated_user)
):
    """Load a model into GPU memory.

    Requires Pro or Enterprise tier. Model will be lazily loaded
    on first inference request for Free tier users.

    Returns:
        Success message with GPU assignment
    """
    # Validate model exists
    try:
        model = ModelRegistry.get_model(model_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found in registry"
        )

    # Check if already loaded
    if multi_model_manager.is_model_loaded(model_id):
        stats = multi_model_manager.get_model_stats(model_id)
        return {
            "success": True,
            "already_loaded": True,
            "model_id": model_id,
            "gpu_device": stats.gpu_device,
            "message": f"Model {model_id} is already loaded on GPU {stats.gpu_device}"
        }

    # Load model
    try:
        logger.info(f"Loading model {model_id} for customer {api_key.customer_id}")
        await multi_model_manager.load_model(model_id)

        stats = multi_model_manager.get_model_stats(model_id)

        return {
            "success": True,
            "model_id": model_id,
            "gpu_device": stats.gpu_device,
            "message": f"Model {model_id} loaded successfully on GPU {stats.gpu_device}"
        }

    except Exception as e:
        logger.error(f"Failed to load model {model_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to load model: {str(e)}"
        )


@router.get("/models/{model_id}/stats", response_model=ModelStatsResponse)
async def get_model_stats(
    model_id: str,
    api_key: APIKeyInfo = Depends(get_authenticated_user)
):
    """Get runtime statistics for a loaded model.

    Returns:
        Model performance statistics

    Raises:
        404: Model not loaded
    """
    try:
        stats = multi_model_manager.get_model_stats(model_id)
        return ModelStatsResponse(
            model_id=stats.model_id,
            inference_count=stats.inference_count,
            avg_latency_ms=stats.avg_latency_ms,
            vram_usage_gb=stats.vram_usage_gb,
            gpu_device=stats.gpu_device
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not loaded or stats unavailable"
        )
