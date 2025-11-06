"""Tests for feedback API endpoints."""

import pytest
from datetime import datetime
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient

from src.models.contracts.feedback import FeedbackType


class TestSuccessRating:
    """Tests for success rating feedback endpoint."""

    @pytest.mark.asyncio
    async def test_report_success_rating_valid(
        self, client: AsyncClient, auth_headers: dict, test_log_id: int
    ):
        """Test reporting valid success rating."""
        response = await client.post(
            "/v1/feedback/success",
            json={
                "log_id": test_log_id,
                "rating": 5,
                "notes": "Perfect execution, robot completed task successfully",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["feedback_type"] == FeedbackType.SUCCESS_RATING.value
        assert data["log_id"] == test_log_id
        assert "feedback_id" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_report_success_rating_without_notes(
        self, client: AsyncClient, auth_headers: dict, test_log_id: int
    ):
        """Test reporting success rating without optional notes."""
        response = await client.post(
            "/v1/feedback/success",
            json={"log_id": test_log_id, "rating": 3},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_report_success_rating_invalid_range(
        self, client: AsyncClient, auth_headers: dict, test_log_id: int
    ):
        """Test rating outside valid range (1-5)."""
        # Rating too high
        response = await client.post(
            "/v1/feedback/success",
            json={"log_id": test_log_id, "rating": 6},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Rating too low
        response = await client.post(
            "/v1/feedback/success",
            json={"log_id": test_log_id, "rating": 0},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_report_success_rating_nonexistent_log(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test reporting for non-existent log ID."""
        response = await client.post(
            "/v1/feedback/success",
            json={"log_id": 999999, "rating": 5},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_report_success_rating_unauthorized(
        self, client: AsyncClient, test_log_id: int
    ):
        """Test reporting without authentication."""
        response = await client.post(
            "/v1/feedback/success",
            json={"log_id": test_log_id, "rating": 5},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestSafetyRating:
    """Tests for safety rating feedback endpoint."""

    @pytest.mark.asyncio
    async def test_report_safety_rating_valid(
        self, client: AsyncClient, auth_headers: dict, test_log_id: int
    ):
        """Test reporting valid safety rating."""
        response = await client.post(
            "/v1/feedback/safety-rating",
            json={
                "log_id": test_log_id,
                "rating": 5,
                "notes": "Robot maintained safe distance from obstacles",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["feedback_type"] == FeedbackType.SAFETY_RATING.value

    @pytest.mark.asyncio
    async def test_report_safety_rating_low_score(
        self, client: AsyncClient, auth_headers: dict, test_log_id: int
    ):
        """Test reporting low safety rating."""
        response = await client.post(
            "/v1/feedback/safety-rating",
            json={
                "log_id": test_log_id,
                "rating": 2,
                "notes": "Robot moved too close to person",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED


class TestActionCorrection:
    """Tests for action correction feedback endpoint."""

    @pytest.mark.asyncio
    async def test_report_action_correction_valid(
        self, client: AsyncClient, auth_headers: dict, test_log_id: int
    ):
        """Test reporting valid action correction."""
        corrected_action = [0.05, 0.02, -0.01, 0.0, 0.0, 0.1, 1.0]

        response = await client.post(
            "/v1/feedback/action-correction",
            json={
                "log_id": test_log_id,
                "corrected_action": corrected_action,
                "notes": "Adjusted z-axis to avoid collision",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["feedback_type"] == FeedbackType.ACTION_CORRECTION.value
        assert "magnitude" in data["message"]

    @pytest.mark.asyncio
    async def test_report_action_correction_invalid_dimension(
        self, client: AsyncClient, auth_headers: dict, test_log_id: int
    ):
        """Test action correction with wrong dimensions."""
        # Too few dimensions
        response = await client.post(
            "/v1/feedback/action-correction",
            json={
                "log_id": test_log_id,
                "corrected_action": [0.1, 0.2, 0.3],
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Too many dimensions
        response = await client.post(
            "/v1/feedback/action-correction",
            json={
                "log_id": test_log_id,
                "corrected_action": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_report_action_correction_invalid_values(
        self, client: AsyncClient, auth_headers: dict, test_log_id: int
    ):
        """Test action correction with invalid values."""
        # NaN value
        response = await client.post(
            "/v1/feedback/action-correction",
            json={
                "log_id": test_log_id,
                "corrected_action": [0.1, 0.2, float("nan"), 0.4, 0.5, 0.6, 1.0],
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Invalid gripper value
        response = await client.post(
            "/v1/feedback/action-correction",
            json={
                "log_id": test_log_id,
                "corrected_action": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 2.0],
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestFailureReport:
    """Tests for failure report feedback endpoint."""

    @pytest.mark.asyncio
    async def test_report_failure_valid(
        self, client: AsyncClient, auth_headers: dict, test_log_id: int
    ):
        """Test reporting valid failure."""
        response = await client.post(
            "/v1/feedback/failure-report",
            json={
                "log_id": test_log_id,
                "failure_reason": "collision",
                "notes": "Robot collided with table edge during execution",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["feedback_type"] == FeedbackType.FAILURE_REPORT.value
        assert "collision" in data["message"]

    @pytest.mark.asyncio
    async def test_report_failure_empty_reason(
        self, client: AsyncClient, auth_headers: dict, test_log_id: int
    ):
        """Test reporting failure with empty reason."""
        response = await client.post(
            "/v1/feedback/failure-report",
            json={
                "log_id": test_log_id,
                "failure_reason": "",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_report_failure_common_reasons(
        self, client: AsyncClient, auth_headers: dict, test_log_id: int
    ):
        """Test reporting failures with common reasons."""
        common_reasons = [
            "collision",
            "gripper_malfunction",
            "wrong_object",
            "incomplete_task",
            "timeout",
        ]

        for reason in common_reasons:
            response = await client.post(
                "/v1/feedback/failure-report",
                json={
                    "log_id": test_log_id,
                    "failure_reason": reason,
                },
                headers=auth_headers,
            )
            assert response.status_code == status.HTTP_201_CREATED


class TestFeedbackStats:
    """Tests for feedback statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_feedback_stats_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting stats with no feedback."""
        response = await client.get(
            "/v1/feedback/stats",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_feedback_count"] >= 0
        assert data["feedback_rate"] >= 0.0
        assert "feedback_by_type" in data
        assert "period" in data

    @pytest.mark.asyncio
    async def test_get_feedback_stats_with_data(
        self, client: AsyncClient, auth_headers: dict, test_log_id: int
    ):
        """Test getting stats after submitting feedback."""
        # Submit various feedback types
        await client.post(
            "/v1/feedback/success",
            json={"log_id": test_log_id, "rating": 5},
            headers=auth_headers,
        )
        await client.post(
            "/v1/feedback/safety-rating",
            json={"log_id": test_log_id, "rating": 4},
            headers=auth_headers,
        )

        # Get stats
        response = await client.get(
            "/v1/feedback/stats",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_feedback_count"] >= 2
        assert "average_success_rating" in data
        assert "average_safety_rating" in data

    @pytest.mark.asyncio
    async def test_get_feedback_stats_unauthorized(self, client: AsyncClient):
        """Test getting stats without authentication."""
        response = await client.get("/v1/feedback/stats")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestFeedbackList:
    """Tests for feedback list endpoint."""

    @pytest.mark.asyncio
    async def test_list_feedback_default(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing feedback with default pagination."""
        response = await client.get(
            "/v1/feedback/list",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "feedback" in data
        assert "total_count" in data
        assert "page" in data
        assert "per_page" in data
        assert "has_next" in data

    @pytest.mark.asyncio
    async def test_list_feedback_pagination(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test feedback list pagination."""
        response = await client.get(
            "/v1/feedback/list?page=1&per_page=10",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 10

    @pytest.mark.asyncio
    async def test_list_feedback_filter_by_type(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test filtering feedback by type."""
        response = await client.get(
            f"/v1/feedback/list?feedback_type={FeedbackType.SUCCESS_RATING.value}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for feedback in data["feedback"]:
            assert feedback["feedback_type"] == FeedbackType.SUCCESS_RATING.value

    @pytest.mark.asyncio
    async def test_list_feedback_invalid_page(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing with invalid page number."""
        response = await client.get(
            "/v1/feedback/list?page=0",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# Fixtures for tests


@pytest.fixture
async def test_log_id(client: AsyncClient, auth_headers: dict) -> int:
    """Create a test inference log and return its ID."""
    # This would typically create a real inference log
    # For testing, we'll mock this or use a pre-existing log
    # In a real test environment, you'd create an actual log first
    return 1  # Replace with actual log creation logic


@pytest.fixture
def auth_headers() -> dict:
    """Create authentication headers for testing."""
    # This should use a test API key
    return {"Authorization": "Bearer vla_test_mock_api_key_for_testing"}
