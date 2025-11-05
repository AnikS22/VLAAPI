"""Models API router for listing available VLA models."""

from fastapi import APIRouter

from src.core.constants import SUPPORTED_VLA_MODELS
from src.models.api_models import ModelInfo, ModelListResponse
from src.services.model_loader import model_manager

router = APIRouter(prefix="/v1", tags=["models"])


@router.get("/models/list", response_model=ModelListResponse)
async def list_models():
    """List all available VLA models.

    Returns information about supported models, including their specifications,
    availability status, and performance characteristics.

    Returns:
        ModelListResponse with list of model information
    """
    models_info = []

    for model_id, model_config in SUPPORTED_VLA_MODELS.items():
        # Check if model is currently loaded
        is_available = model_manager.is_model_loaded(model_id)

        model_info = ModelInfo(
            id=model_id,
            name=model_config["name"],
            description=model_config["description"],
            version="1.0",  # Could be dynamic from model metadata
            action_space={
                "dimensions": model_config["action_space_dim"],
                "type": model_config["action_space_type"],
            },
            input_requirements={
                "image_size": model_config["image_size"],
                "image_format": "RGB",
            },
            available=is_available,
            avg_latency_ms=model_config["avg_latency_ms"],
        )

        models_info.append(model_info)

    return ModelListResponse(models=models_info)
