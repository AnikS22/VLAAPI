"""Inference API router for VLA model inference."""

import logging
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_authenticated_user, get_db
from src.core.constants import InferenceStatus
from src.core.redis_client import get_redis
from src.middleware.authentication import APIKeyInfo
from src.middleware.rate_limiting import get_remaining_requests
from src.models.api_models import InferenceRequest, InferenceResponse
from src.models.api_models import (
    ActionResponse,
    ErrorResponse,
    PerformanceMetrics,
    SafetyResponse,
    UsageInfo,
)
from src.models.database import Customer, InferenceLog, SafetyIncident
from src.services.consent import get_consent_manager
from src.services.model_loader import model_manager
from src.services.safety_monitor import safety_monitor
from src.services.vla_inference import inference_service
from src.utils.image_processing import decode_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["inference"])


from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy import desc, and_


class InferenceHistoryResponse(BaseModel):
    logs: List[dict]
    total_count: int
    page: int
    limit: int
    total_pages: int


@router.get("/inference/history", response_model=InferenceHistoryResponse)
async def get_inference_history(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    robot_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    api_key: APIKeyInfo = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Get paginated inference history for the authenticated customer.

    Args:
        page: Page number (1-indexed)
        limit: Items per page
        status: Filter by status (success/error)
        robot_type: Filter by robot type
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)
        api_key: Authenticated API key
        session: Database session

    Returns:
        Paginated list of inference logs
    """
    offset = (page - 1) * limit

    # Build query filters
    filters = [InferenceLog.customer_id == api_key.customer_id]

    if status:
        filters.append(InferenceLog.status == status)
    if robot_type:
        filters.append(InferenceLog.robot_type == robot_type)
    if start_date:
        filters.append(InferenceLog.timestamp >= datetime.fromisoformat(start_date))
    if end_date:
        filters.append(InferenceLog.timestamp <= datetime.fromisoformat(end_date))

    # Count total
    from sqlalchemy import func
    count_query = select(func.count(InferenceLog.log_id)).where(and_(*filters))
    count_result = await session.execute(count_query)
    total_count = count_result.scalar() or 0

    # Get logs
    logs_query = select(InferenceLog).where(
        and_(*filters)
    ).order_by(desc(InferenceLog.timestamp)).offset(offset).limit(limit)

    logs_result = await session.execute(logs_query)
    logs = [
        {
            "log_id": str(log.log_id),
            "timestamp": log.timestamp.isoformat(),
            "instruction": log.instruction,
            "robot_type": log.robot_type,
            "environment_type": log.environment_type,
            "status": log.status,
            "latency_ms": log.latency_ms,
            "safety_score": log.safety_score,
            "action_vector": log.action_vector
        }
        for log in logs_result.scalars()
    ]

    return {
        "logs": logs,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit
    }


@router.post(
    "/inference",
    response_model=InferenceResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def infer_action(
    request: InferenceRequest,
    api_key: APIKeyInfo = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Perform VLA inference to predict robot action from image and instruction.

    This endpoint accepts an image and natural language instruction, runs VLA model
    inference, and returns a robot action with safety validation.

    **Privacy Compliance:**
    - Checks customer consent before storing images or embeddings
    - Respects data anonymization levels
    - Only stores data if consent is granted

    Args:
        request: Inference request with image, instruction, and optional configs
        api_key: Authenticated API key (injected)
        session: Database session (injected)
        redis: Redis client for consent caching (injected)

    Returns:
        InferenceResponse with action, safety evaluation, and performance metrics

    Raises:
        HTTPException: On validation error, model error, or safety rejection
    """
    request_id = uuid4()
    start_time = time.time()

    # Log request
    logger.info(
        f"Inference request {request_id} from customer {api_key.customer_id}"
    )

    try:
        # 1. Check customer consent for data storage
        consent_manager = get_consent_manager(redis)
        customer_id_str = str(api_key.customer_id)

        # Get consent preferences (cached for 10 minutes)
        can_store_images = await consent_manager.can_store_images(
            customer_id_str, session
        )
        can_store_embeddings = await consent_manager.can_store_embeddings(
            customer_id_str, session
        )

        logger.info(
            f"Customer {customer_id_str} consent: "
            f"images={can_store_images}, embeddings={can_store_embeddings}"
        )

        # 2. Validate model availability
        if not model_manager.is_model_loaded(request.model):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model {request.model} is not loaded or available",
            )

        # 3. Decode and validate image
        try:
            image = decode_image(request.image)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image: {e}",
            )

        # 4. Prepare robot configuration
        robot_type = request.robot_config.type if request.robot_config else "franka_panda"
        robot_config_dict = request.robot_config.model_dump() if request.robot_config else None

        # 5. Run VLA inference
        inference_start = time.time()

        inference_result = await inference_service.infer(
            model_id=request.model,
            image=image,
            instruction=request.instruction,
            robot_type=robot_type,
            robot_config=robot_config_dict,
            timeout=10.0,
        )

        if not inference_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Inference failed: {inference_result.error}",
            )

        inference_end = time.time()

        # 6. Safety evaluation
        safety_start = time.time()

        safety_config = request.safety or {}
        safety_result = safety_monitor.evaluate_action(
            action=inference_result.action,
            robot_type=robot_type,
            robot_config=robot_config_dict,
            current_pose=None,  # Would come from robot state in production
            context={
                "image": image,
                "instruction": request.instruction,
                "model": request.model,
            },
        )

        safety_end = time.time()

        # Check if action should be rejected
        if not safety_result["is_safe"]:
            # Log safety incident
            incident = SafetyIncident(
                customer_id=api_key.customer_id,
                severity="high",
                violation_type="multiple",
                violation_details=safety_result,
                action_taken="rejected",
                original_action=inference_result.action,
                safe_action=safety_result["safe_action"],
            )
            session.add(incident)

            # Use safe action instead or reject
            if safety_result["modifications_applied"]:
                final_action = safety_result["safe_action"]
                inference_status = InferenceStatus.SUCCESS
                logger.warning(f"Action modified for safety: {request_id}")
            else:
                # Reject action
                await session.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "safety_rejected",
                        "message": "Action rejected due to safety violations",
                        "violations": safety_result["flags"],
                    },
                )
        else:
            final_action = inference_result.action
            inference_status = InferenceStatus.SUCCESS

        # 7. Prepare response
        total_latency_ms = int((time.time() - start_time) * 1000)

        # Get remaining requests
        usage_info = await get_remaining_requests(api_key)

        response = InferenceResponse(
            request_id=request_id,
            timestamp=start_time,
            model=request.model,
            action=ActionResponse(
                type="end_effector_delta",
                dimensions=len(final_action),
                values=final_action,
            ),
            safety=SafetyResponse(
                overall_score=safety_result["overall_score"],
                checks_passed=safety_result["checks_passed"],
                flags=safety_result["flags"],
                classifier_confidence=safety_result["alignment"].get("score"),
                modifications_applied=safety_result["modifications_applied"],
            ),
            performance=PerformanceMetrics(
                total_latency_ms=total_latency_ms,
                queue_wait_ms=inference_result.queue_wait_ms,
                inference_ms=inference_result.inference_ms,
                safety_check_ms=int((safety_end - safety_start) * 1000),
                postprocess_ms=int((time.time() - safety_end) * 1000),
            ),
            usage=UsageInfo(**usage_info),
        )

        # 8. Log inference to database (respecting consent)
        # Note: We always log metadata for analytics, but only store
        # image_shape if consent allows (image data itself is never stored)
        log_entry = InferenceLog(
            customer_id=api_key.customer_id,
            key_id=api_key.key_id,
            request_id=request_id,
            model_name=request.model,
            instruction=request.instruction,
            # Only store image shape if consent allows any data storage
            image_shape=[image.height, image.width, 3] if can_store_images else None,
            action_vector=final_action,
            safety_score=safety_result["overall_score"],
            safety_flags=safety_result["flags"],
            inference_latency_ms=total_latency_ms,
            queue_wait_ms=inference_result.queue_wait_ms,
            gpu_compute_ms=inference_result.inference_ms,
            status=inference_status.value,
        )
        session.add(log_entry)

        # TODO: If can_store_embeddings is True, store image embeddings
        # in a separate service (vector database, S3, etc.)
        if can_store_embeddings:
            logger.debug(f"Customer {customer_id_str} consent allows embedding storage")
            # Future: Store embeddings for personalization/analytics

        # Update customer monthly usage
        result = await session.execute(
            select(Customer).where(Customer.customer_id == api_key.customer_id)
        )
        customer = result.scalar_one()
        customer.monthly_usage += 1

        await session.commit()

        logger.info(
            f"Inference {request_id} completed in {total_latency_ms}ms, "
            f"safety_score={safety_result['overall_score']:.2f}"
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        await session.rollback()
        raise

    except Exception as e:
        await session.rollback()
        logger.error(f"Inference {request_id} failed: {e}", exc_info=True)

        # Log error to database
        log_entry = InferenceLog(
            customer_id=api_key.customer_id,
            key_id=api_key.key_id,
            request_id=request_id,
            model_name=request.model,
            instruction=request.instruction,
            status=InferenceStatus.ERROR.value,
            error_message=str(e),
        )
        session.add(log_entry)
        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference failed: {e}",
        )
