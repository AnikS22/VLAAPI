"""Feedback service for processing ground truth collection."""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.contracts.feedback import FeedbackType
from src.models.database import Feedback, InferenceLog


class FeedbackService:
    """Service for processing feedback and analytics."""

    def __init__(self, session: AsyncSession):
        """Initialize feedback service.

        Args:
            session: Async database session
        """
        self.session = session

    async def create_success_rating(
        self,
        log_id: int,
        customer_id: UUID,
        rating: int,
        notes: Optional[str] = None,
    ) -> Feedback:
        """Create success rating feedback.

        Args:
            log_id: Inference log ID
            customer_id: Customer UUID
            rating: Success rating (1-5)
            notes: Optional notes

        Returns:
            Created feedback record

        Raises:
            ValueError: If log not found or doesn't belong to customer
        """
        # Verify log exists and belongs to customer
        await self._verify_log_ownership(log_id, customer_id)

        # Create feedback record
        feedback = Feedback(
            log_id=log_id,
            customer_id=customer_id,
            feedback_type=FeedbackType.SUCCESS_RATING.value,
            rating=rating,
            notes=notes,
        )

        self.session.add(feedback)
        await self.session.commit()
        await self.session.refresh(feedback)

        # Asynchronously update analytics (don't await)
        # In production, this would be handled by a background task queue
        await self._update_success_analytics(customer_id)

        return feedback

    async def create_safety_rating(
        self,
        log_id: int,
        customer_id: UUID,
        rating: int,
        notes: Optional[str] = None,
    ) -> Feedback:
        """Create safety rating feedback.

        Args:
            log_id: Inference log ID
            customer_id: Customer UUID
            rating: Safety rating (1-5)
            notes: Optional notes

        Returns:
            Created feedback record

        Raises:
            ValueError: If log not found or doesn't belong to customer
        """
        # Verify log exists and belongs to customer
        await self._verify_log_ownership(log_id, customer_id)

        # Create feedback record
        feedback = Feedback(
            log_id=log_id,
            customer_id=customer_id,
            feedback_type=FeedbackType.SAFETY_RATING.value,
            rating=rating,
            notes=notes,
        )

        self.session.add(feedback)
        await self.session.commit()
        await self.session.refresh(feedback)

        # Asynchronously update analytics
        await self._update_safety_analytics(customer_id)

        return feedback

    async def create_action_correction(
        self,
        log_id: int,
        customer_id: UUID,
        corrected_action: List[float],
        notes: Optional[str] = None,
    ) -> Feedback:
        """Create action correction feedback.

        Args:
            log_id: Inference log ID
            customer_id: Customer UUID
            corrected_action: Corrected 7-DoF action vector
            notes: Optional notes

        Returns:
            Created feedback record

        Raises:
            ValueError: If log not found or doesn't belong to customer
        """
        # Verify log exists and belongs to customer
        log = await self._verify_log_ownership(log_id, customer_id)

        # Get original action from log
        original_action = log.action_vector
        if not original_action or len(original_action) != 7:
            raise ValueError("Original action not found or invalid in inference log")

        # Calculate correction delta and magnitude
        correction_delta = [
            corrected_action[i] - original_action[i] for i in range(7)
        ]
        correction_magnitude = math.sqrt(sum(d * d for d in correction_delta))

        # Create feedback record
        feedback = Feedback(
            log_id=log_id,
            customer_id=customer_id,
            feedback_type=FeedbackType.ACTION_CORRECTION.value,
            corrected_action=corrected_action,
            original_action=original_action,
            correction_delta=correction_delta,
            correction_magnitude=correction_magnitude,
            notes=notes,
        )

        self.session.add(feedback)
        await self.session.commit()
        await self.session.refresh(feedback)

        # Asynchronously update analytics
        await self._update_correction_analytics(customer_id)

        return feedback

    async def create_failure_report(
        self,
        log_id: int,
        customer_id: UUID,
        failure_reason: str,
        notes: Optional[str] = None,
    ) -> Feedback:
        """Create failure report feedback.

        Args:
            log_id: Inference log ID
            customer_id: Customer UUID
            failure_reason: Brief failure reason
            notes: Optional detailed notes

        Returns:
            Created feedback record

        Raises:
            ValueError: If log not found or doesn't belong to customer
        """
        # Verify log exists and belongs to customer
        await self._verify_log_ownership(log_id, customer_id)

        # Create feedback record
        feedback = Feedback(
            log_id=log_id,
            customer_id=customer_id,
            feedback_type=FeedbackType.FAILURE_REPORT.value,
            failure_reason=failure_reason,
            notes=notes,
        )

        self.session.add(feedback)
        await self.session.commit()
        await self.session.refresh(feedback)

        # Asynchronously update analytics
        await self._update_failure_analytics(customer_id)

        return feedback

    async def get_feedback_stats(
        self,
        customer_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict:
        """Get feedback statistics for customer.

        Args:
            customer_id: Customer UUID
            start_date: Start of period (default: 30 days ago)
            end_date: End of period (default: now)

        Returns:
            Dictionary with feedback statistics
        """
        # Default to last 30 days
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Get total feedback count
        total_feedback_result = await self.session.execute(
            select(func.count(Feedback.feedback_id))
            .where(Feedback.customer_id == customer_id)
            .where(Feedback.timestamp >= start_date)
            .where(Feedback.timestamp <= end_date)
        )
        total_feedback_count = total_feedback_result.scalar() or 0

        # Get total inference count
        total_inference_result = await self.session.execute(
            select(func.count(InferenceLog.log_id))
            .where(InferenceLog.customer_id == customer_id)
            .where(InferenceLog.timestamp >= start_date)
            .where(InferenceLog.timestamp <= end_date)
        )
        total_inference_count = total_inference_result.scalar() or 0

        # Calculate feedback rate
        feedback_rate = (
            total_feedback_count / total_inference_count
            if total_inference_count > 0
            else 0.0
        )

        # Get feedback by type
        feedback_by_type_result = await self.session.execute(
            select(
                Feedback.feedback_type,
                func.count(Feedback.feedback_id).label("count"),
            )
            .where(Feedback.customer_id == customer_id)
            .where(Feedback.timestamp >= start_date)
            .where(Feedback.timestamp <= end_date)
            .group_by(Feedback.feedback_type)
        )
        feedback_by_type = {
            row.feedback_type: row.count for row in feedback_by_type_result
        }

        # Get average success rating
        avg_success_result = await self.session.execute(
            select(func.avg(Feedback.rating))
            .where(Feedback.customer_id == customer_id)
            .where(Feedback.feedback_type == FeedbackType.SUCCESS_RATING.value)
            .where(Feedback.timestamp >= start_date)
            .where(Feedback.timestamp <= end_date)
        )
        avg_success_rating = avg_success_result.scalar()

        # Get average safety rating
        avg_safety_result = await self.session.execute(
            select(func.avg(Feedback.rating))
            .where(Feedback.customer_id == customer_id)
            .where(Feedback.feedback_type == FeedbackType.SAFETY_RATING.value)
            .where(Feedback.timestamp >= start_date)
            .where(Feedback.timestamp <= end_date)
        )
        avg_safety_rating = avg_safety_result.scalar()

        # Get correction statistics
        correction_stats_result = await self.session.execute(
            select(
                func.count(Feedback.feedback_id).label("count"),
                func.avg(Feedback.correction_magnitude).label("avg_magnitude"),
            )
            .where(Feedback.customer_id == customer_id)
            .where(Feedback.feedback_type == FeedbackType.ACTION_CORRECTION.value)
            .where(Feedback.timestamp >= start_date)
            .where(Feedback.timestamp <= end_date)
        )
        correction_stats = correction_stats_result.first()
        correction_count = correction_stats.count if correction_stats else 0
        avg_correction_magnitude = (
            correction_stats.avg_magnitude if correction_stats else None
        )

        # Get top failure reasons
        failure_reasons_result = await self.session.execute(
            select(
                Feedback.failure_reason,
                func.count(Feedback.feedback_id).label("count"),
            )
            .where(Feedback.customer_id == customer_id)
            .where(Feedback.feedback_type == FeedbackType.FAILURE_REPORT.value)
            .where(Feedback.timestamp >= start_date)
            .where(Feedback.timestamp <= end_date)
            .group_by(Feedback.failure_reason)
            .order_by(func.count(Feedback.feedback_id).desc())
            .limit(10)
        )
        top_failure_reasons = [
            {"reason": row.failure_reason, "count": row.count}
            for row in failure_reasons_result
        ]

        return {
            "customer_id": customer_id,
            "total_feedback_count": total_feedback_count,
            "total_inference_count": total_inference_count,
            "feedback_rate": feedback_rate,
            "feedback_by_type": feedback_by_type,
            "average_success_rating": (
                float(avg_success_rating) if avg_success_rating else None
            ),
            "average_safety_rating": (
                float(avg_safety_rating) if avg_safety_rating else None
            ),
            "correction_count": correction_count,
            "average_correction_magnitude": (
                float(avg_correction_magnitude) if avg_correction_magnitude else None
            ),
            "failure_count": feedback_by_type.get(FeedbackType.FAILURE_REPORT.value, 0),
            "top_failure_reasons": top_failure_reasons,
            "period": {"start": start_date, "end": end_date},
        }

    async def get_feedback_list(
        self,
        customer_id: UUID,
        page: int = 1,
        per_page: int = 50,
        feedback_type: Optional[FeedbackType] = None,
    ) -> Tuple[List[Feedback], int]:
        """Get paginated list of feedback for customer.

        Args:
            customer_id: Customer UUID
            page: Page number (1-indexed)
            per_page: Items per page
            feedback_type: Optional filter by feedback type

        Returns:
            Tuple of (feedback_list, total_count)
        """
        # Build query
        query = select(Feedback).where(Feedback.customer_id == customer_id)

        if feedback_type:
            query = query.where(Feedback.feedback_type == feedback_type.value)

        # Get total count
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total_count = count_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * per_page
        query = (
            query.order_by(Feedback.timestamp.desc())
            .limit(per_page)
            .offset(offset)
        )

        result = await self.session.execute(query)
        feedback_list = result.scalars().all()

        return feedback_list, total_count

    # Private helper methods

    async def _verify_log_ownership(self, log_id: int, customer_id: UUID) -> InferenceLog:
        """Verify inference log exists and belongs to customer.

        Args:
            log_id: Inference log ID
            customer_id: Customer UUID

        Returns:
            InferenceLog object

        Raises:
            ValueError: If log not found or doesn't belong to customer
        """
        result = await self.session.execute(
            select(InferenceLog)
            .where(InferenceLog.log_id == log_id)
            .where(InferenceLog.customer_id == customer_id)
        )
        log = result.scalar_one_or_none()

        if not log:
            raise ValueError(
                f"Inference log {log_id} not found or doesn't belong to customer"
            )

        return log

    async def _update_success_analytics(self, customer_id: UUID) -> None:
        """Update success rate analytics for customer.

        Args:
            customer_id: Customer UUID
        """
        # In production, this would trigger a background job to update
        # analytics tables or materialized views
        # For now, this is a placeholder
        pass

    async def _update_safety_analytics(self, customer_id: UUID) -> None:
        """Update safety analytics for customer.

        Args:
            customer_id: Customer UUID
        """
        # Placeholder for analytics update
        pass

    async def _update_correction_analytics(self, customer_id: UUID) -> None:
        """Update correction analytics for customer.

        Args:
            customer_id: Customer UUID
        """
        # Placeholder for analytics update
        pass

    async def _update_failure_analytics(self, customer_id: UUID) -> None:
        """Update failure analytics for customer.

        Args:
            customer_id: Customer UUID
        """
        # Placeholder for analytics update
        pass
