"""Feedback API router for ground truth collection."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.middleware.authentication import APIKeyInfo, get_current_api_key
from src.models.contracts.feedback import (
    ActionCorrectionRequest,
    FailureReportRequest,
    FeedbackDetailResponse,
    FeedbackListResponse,
    FeedbackResponse,
    FeedbackStatsResponse,
    FeedbackType,
    SafetyRatingRequest,
    SuccessRatingRequest,
)
from src.services.feedback import FeedbackService

router = APIRouter(prefix="/v1/feedback", tags=["feedback"])


@router.post(
    "/success",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report inference success rating",
    description="Submit a success/failure rating (1-5 stars) for an inference result. "
    "Used to collect ground truth about model performance.",
)
async def report_success(
    request: SuccessRatingRequest,
    session: AsyncSession = Depends(get_db),
    api_key: APIKeyInfo = Depends(get_current_api_key),
) -> FeedbackResponse:
    """Report inference success/failure rating.

    Args:
        request: Success rating request with log_id, rating (1-5), and optional notes
        session: Database session
        api_key: Authenticated API key info

    Returns:
        Feedback response with confirmation

    Raises:
        HTTPException: If log_id not found or doesn't belong to customer
    """
    service = FeedbackService(session)

    try:
        feedback = await service.create_success_rating(
            log_id=request.log_id,
            customer_id=api_key.customer_id,
            rating=request.rating,
            notes=request.notes,
        )

        return FeedbackResponse(
            feedback_id=feedback.feedback_id,
            log_id=feedback.log_id,
            feedback_type=FeedbackType.SUCCESS_RATING,
            customer_id=feedback.customer_id,
            timestamp=feedback.timestamp,
            message=f"Success rating {request.rating}/5 recorded successfully",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record success rating: {str(e)}",
        )


@router.post(
    "/safety-rating",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report safety rating from human observer",
    description="Submit a safety rating (1-5 stars) from human observation of robot execution. "
    "Used to train and improve safety models.",
)
async def report_safety_rating(
    request: SafetyRatingRequest,
    session: AsyncSession = Depends(get_db),
    api_key: APIKeyInfo = Depends(get_current_api_key),
) -> FeedbackResponse:
    """Report safety rating from human observer.

    Args:
        request: Safety rating request with log_id, rating (1-5), and optional notes
        session: Database session
        api_key: Authenticated API key info

    Returns:
        Feedback response with confirmation

    Raises:
        HTTPException: If log_id not found or doesn't belong to customer
    """
    service = FeedbackService(session)

    try:
        feedback = await service.create_safety_rating(
            log_id=request.log_id,
            customer_id=api_key.customer_id,
            rating=request.rating,
            notes=request.notes,
        )

        return FeedbackResponse(
            feedback_id=feedback.feedback_id,
            log_id=feedback.log_id,
            feedback_type=FeedbackType.SAFETY_RATING,
            customer_id=feedback.customer_id,
            timestamp=feedback.timestamp,
            message=f"Safety rating {request.rating}/5 recorded successfully",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record safety rating: {str(e)}",
        )


@router.post(
    "/action-correction",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report corrected action vector from human",
    description="Submit a corrected 7-DoF action vector when the model's prediction was incorrect. "
    "This data is used for supervised learning and model improvement.",
)
async def report_action_correction(
    request: ActionCorrectionRequest,
    session: AsyncSession = Depends(get_db),
    api_key: APIKeyInfo = Depends(get_current_api_key),
) -> FeedbackResponse:
    """Report corrected action vector from human.

    Args:
        request: Action correction request with log_id, corrected_action, and optional notes
        session: Database session
        api_key: Authenticated API key info

    Returns:
        Feedback response with confirmation

    Raises:
        HTTPException: If log_id not found, doesn't belong to customer, or action invalid
    """
    service = FeedbackService(session)

    try:
        feedback = await service.create_action_correction(
            log_id=request.log_id,
            customer_id=api_key.customer_id,
            corrected_action=request.corrected_action,
            notes=request.notes,
        )

        return FeedbackResponse(
            feedback_id=feedback.feedback_id,
            log_id=feedback.log_id,
            feedback_type=FeedbackType.ACTION_CORRECTION,
            customer_id=feedback.customer_id,
            timestamp=feedback.timestamp,
            message=(
                f"Action correction recorded (magnitude: {feedback.correction_magnitude:.4f})"
            ),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record action correction: {str(e)}",
        )


@router.post(
    "/failure-report",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report why inference failed in real robot execution",
    description="Submit a failure report explaining why the inference result failed when executed on real robot. "
    "Helps identify systematic failure patterns.",
)
async def report_failure(
    request: FailureReportRequest,
    session: AsyncSession = Depends(get_db),
    api_key: APIKeyInfo = Depends(get_current_api_key),
) -> FeedbackResponse:
    """Report why inference failed in real robot execution.

    Args:
        request: Failure report request with log_id, failure_reason, and optional notes
        session: Database session
        api_key: Authenticated API key info

    Returns:
        Feedback response with confirmation

    Raises:
        HTTPException: If log_id not found or doesn't belong to customer
    """
    service = FeedbackService(session)

    try:
        feedback = await service.create_failure_report(
            log_id=request.log_id,
            customer_id=api_key.customer_id,
            failure_reason=request.failure_reason,
            notes=request.notes,
        )

        return FeedbackResponse(
            feedback_id=feedback.feedback_id,
            log_id=feedback.log_id,
            feedback_type=FeedbackType.FAILURE_REPORT,
            customer_id=feedback.customer_id,
            timestamp=feedback.timestamp,
            message=f"Failure report recorded: {request.failure_reason}",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record failure report: {str(e)}",
        )


@router.get(
    "/stats",
    response_model=FeedbackStatsResponse,
    summary="Get feedback statistics for customer",
    description="Retrieve comprehensive feedback statistics including rates, averages, "
    "and breakdowns by type. Defaults to last 30 days.",
)
async def get_feedback_stats(
    session: AsyncSession = Depends(get_db),
    api_key: APIKeyInfo = Depends(get_current_api_key),
) -> FeedbackStatsResponse:
    """Get feedback statistics for customer.

    Args:
        session: Database session
        api_key: Authenticated API key info

    Returns:
        Comprehensive feedback statistics

    Raises:
        HTTPException: If stats retrieval fails
    """
    service = FeedbackService(session)

    try:
        stats = await service.get_feedback_stats(customer_id=api_key.customer_id)

        return FeedbackStatsResponse(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve feedback stats: {str(e)}",
        )


@router.get(
    "/list",
    response_model=FeedbackListResponse,
    summary="List feedback submissions",
    description="Get paginated list of feedback submissions with optional filtering by type.",
)
async def list_feedback(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    feedback_type: Optional[FeedbackType] = Query(
        None,
        description="Filter by feedback type",
    ),
    session: AsyncSession = Depends(get_db),
    api_key: APIKeyInfo = Depends(get_current_api_key),
) -> FeedbackListResponse:
    """List feedback submissions for customer.

    Args:
        page: Page number (1-indexed)
        per_page: Items per page
        feedback_type: Optional filter by feedback type
        session: Database session
        api_key: Authenticated API key info

    Returns:
        Paginated list of feedback

    Raises:
        HTTPException: If list retrieval fails
    """
    service = FeedbackService(session)

    try:
        feedback_list, total_count = await service.get_feedback_list(
            customer_id=api_key.customer_id,
            page=page,
            per_page=per_page,
            feedback_type=feedback_type,
        )

        # Convert to response models
        feedback_details = []
        for feedback in feedback_list:
            detail = FeedbackDetailResponse(
                feedback_id=feedback.feedback_id,
                log_id=feedback.log_id,
                feedback_type=FeedbackType(feedback.feedback_type),
                customer_id=feedback.customer_id,
                timestamp=feedback.timestamp,
                rating=feedback.rating,
                corrected_action=feedback.corrected_action,
                original_action=feedback.original_action,
                correction_delta=feedback.correction_delta,
                correction_magnitude=feedback.correction_magnitude,
                failure_reason=feedback.failure_reason,
                notes=feedback.notes,
            )
            feedback_details.append(detail)

        has_next = (page * per_page) < total_count

        return FeedbackListResponse(
            feedback=feedback_details,
            total_count=total_count,
            page=page,
            per_page=per_page,
            has_next=has_next,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list feedback: {str(e)}",
        )
