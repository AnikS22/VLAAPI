"""
Comprehensive tests for feedback API endpoints.
Tests all feedback types, validation, authentication, and error handling.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json

from src.main import app
from src.models.feedback import (
    FeedbackType,
    SuccessFeedback,
    SafetyRating,
    ActionCorrection,
    FailureReport
)
from src.models.inference import RobotType


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """Valid API key for testing."""
    return "test_api_key_12345"


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch('src.database.supabase.get_supabase_client') as mock:
        mock_client = Mock()
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "test_feedback_id", "created_at": datetime.utcnow().isoformat()}
        ]
        mock_client.table.return_value.select.return_value.execute.return_value.data = []
        mock_client.rpc.return_value.execute.return_value.data = [
            {
                "total_feedback": 100,
                "avg_rating": 4.2,
                "avg_safety": 0.85,
                "total_corrections": 25,
                "total_failures": 5
            }
        ]
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_auth(valid_api_key):
    """Mock authentication."""
    with patch('src.middleware.auth.verify_api_key') as mock:
        mock.return_value = {
            "customer_id": "test_customer_123",
            "api_key": valid_api_key
        }
        yield mock


class TestSuccessFeedback:
    """Tests for POST /v1/feedback/success endpoint."""

    def test_success_feedback_valid(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test creating success feedback with valid data."""
        payload = {
            "inference_id": "infer_123",
            "rating": 5,
            "comment": "Excellent performance!"
        }

        response = client.post(
            "/v1/feedback/success",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["feedback_id"] == "test_feedback_id"
        assert data["type"] == "success"
        assert "created_at" in data

    def test_success_feedback_rating_validation(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test rating must be 1-5."""
        for invalid_rating in [0, 6, -1, 10]:
            payload = {
                "inference_id": "infer_123",
                "rating": invalid_rating
            }

            response = client.post(
                "/v1/feedback/success",
                json=payload,
                headers={"X-API-Key": valid_api_key}
            )

            assert response.status_code == 422
            assert "rating" in response.json()["detail"][0]["loc"]

    def test_success_feedback_valid_ratings(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test all valid ratings 1-5."""
        for valid_rating in [1, 2, 3, 4, 5]:
            payload = {
                "inference_id": f"infer_{valid_rating}",
                "rating": valid_rating
            }

            response = client.post(
                "/v1/feedback/success",
                json=payload,
                headers={"X-API-Key": valid_api_key}
            )

            assert response.status_code == 201

    def test_success_feedback_missing_inference_id(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test inference_id is required."""
        payload = {"rating": 5}

        response = client.post(
            "/v1/feedback/success",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 422
        assert "inference_id" in str(response.json())


class TestSafetyRating:
    """Tests for POST /v1/feedback/safety-rating endpoint."""

    def test_safety_rating_valid(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test creating safety rating with valid data."""
        payload = {
            "inference_id": "infer_123",
            "safety_rating": 0.95,
            "concerns": ["None"],
            "would_deploy": True
        }

        response = client.post(
            "/v1/feedback/safety-rating",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "safety"

    def test_safety_rating_bounds(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test safety rating must be 0.0-1.0."""
        for invalid_rating in [-0.1, 1.1, 2.0, -1.0]:
            payload = {
                "inference_id": "infer_123",
                "safety_rating": invalid_rating,
                "would_deploy": True
            }

            response = client.post(
                "/v1/feedback/safety-rating",
                json=payload,
                headers={"X-API-Key": valid_api_key}
            )

            assert response.status_code == 422

    def test_safety_rating_concerns_list(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test concerns can be list of strings."""
        payload = {
            "inference_id": "infer_123",
            "safety_rating": 0.6,
            "concerns": ["Gripper collision risk", "Speed too high"],
            "would_deploy": False
        }

        response = client.post(
            "/v1/feedback/safety-rating",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 201


class TestActionCorrection:
    """Tests for POST /v1/feedback/action-correction endpoint."""

    def test_action_correction_valid(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test creating action correction with valid 7-DoF vector."""
        payload = {
            "inference_id": "infer_123",
            "original_action": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
            "corrected_action": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75],
            "reason": "Adjusted for better trajectory"
        }

        response = client.post(
            "/v1/feedback/action-correction",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "correction"

    def test_action_correction_7dof_validation(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test action vectors must be exactly 7 dimensions."""
        invalid_vectors = [
            [0.1, 0.2],  # Too few
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],  # 6 DoF
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],  # Too many
            []  # Empty
        ]

        for invalid_vector in invalid_vectors:
            payload = {
                "inference_id": "infer_123",
                "original_action": invalid_vector,
                "corrected_action": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
            }

            response = client.post(
                "/v1/feedback/action-correction",
                json=payload,
                headers={"X-API-Key": valid_api_key}
            )

            assert response.status_code == 422

    def test_action_correction_bounds_validation(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test action values must be in [-1.1, 1.1] range."""
        payload = {
            "inference_id": "infer_123",
            "original_action": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
            "corrected_action": [1.2, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]  # 1.2 out of bounds
        }

        response = client.post(
            "/v1/feedback/action-correction",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 422

    def test_action_correction_reason_optional(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test reason field is optional."""
        payload = {
            "inference_id": "infer_123",
            "original_action": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
            "corrected_action": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75]
        }

        response = client.post(
            "/v1/feedback/action-correction",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 201


class TestFailureReport:
    """Tests for POST /v1/feedback/failure-report endpoint."""

    def test_failure_report_valid(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test creating failure report with valid data."""
        payload = {
            "inference_id": "infer_123",
            "failure_type": "collision",
            "description": "Robot collided with obstacle",
            "severity": "high"
        }

        response = client.post(
            "/v1/feedback/failure-report",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "failure"

    def test_failure_report_severity_levels(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test all valid severity levels."""
        for severity in ["low", "medium", "high", "critical"]:
            payload = {
                "inference_id": f"infer_{severity}",
                "failure_type": "error",
                "description": "Test failure",
                "severity": severity
            }

            response = client.post(
                "/v1/feedback/failure-report",
                json=payload,
                headers={"X-API-Key": valid_api_key}
            )

            assert response.status_code == 201

    def test_failure_report_invalid_severity(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test invalid severity is rejected."""
        payload = {
            "inference_id": "infer_123",
            "failure_type": "error",
            "description": "Test failure",
            "severity": "extreme"  # Invalid
        }

        response = client.post(
            "/v1/feedback/failure-report",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 422


class TestFeedbackStats:
    """Tests for GET /v1/feedback/stats endpoint."""

    def test_feedback_stats_all(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test getting all feedback statistics."""
        response = client.get(
            "/v1/feedback/stats",
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_feedback" in data
        assert "avg_rating" in data
        assert "avg_safety" in data
        assert "total_corrections" in data
        assert "total_failures" in data

    def test_feedback_stats_with_inference_id(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test getting stats for specific inference."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"rating": 4, "safety_rating": 0.8}
        ]

        response = client.get(
            "/v1/feedback/stats?inference_id=infer_123",
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200

    def test_feedback_stats_time_range(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test getting stats for time range."""
        start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        end_date = datetime.utcnow().isoformat()

        response = client.get(
            f"/v1/feedback/stats?start_date={start_date}&end_date={end_date}",
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200


class TestFeedbackList:
    """Tests for GET /v1/feedback/list endpoint."""

    def test_feedback_list_default_pagination(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test listing feedback with default pagination."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": "fb_1",
                "type": "success",
                "inference_id": "infer_1",
                "rating": 5,
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        response = client.get(
            "/v1/feedback/list",
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "page" in data
        assert "limit" in data
        assert "total" in data

    def test_feedback_list_custom_pagination(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test listing feedback with custom pagination."""
        response = client.get(
            "/v1/feedback/list?page=2&limit=50",
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["limit"] == 50

    def test_feedback_list_type_filter(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test filtering feedback by type."""
        for feedback_type in ["success", "safety", "correction", "failure"]:
            response = client.get(
                f"/v1/feedback/list?type={feedback_type}",
                headers={"X-API-Key": valid_api_key}
            )

            assert response.status_code == 200

    def test_feedback_list_inference_filter(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test filtering feedback by inference ID."""
        response = client.get(
            "/v1/feedback/list?inference_id=infer_123",
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 200


class TestAuthentication:
    """Tests for authentication and authorization."""

    def test_missing_api_key(self, client, mock_supabase):
        """Test request without API key is rejected."""
        payload = {
            "inference_id": "infer_123",
            "rating": 5
        }

        response = client.post("/v1/feedback/success", json=payload)

        assert response.status_code == 401
        assert "API key" in response.json()["detail"]

    def test_invalid_api_key(self, client, mock_supabase):
        """Test request with invalid API key is rejected."""
        with patch('src.middleware.auth.verify_api_key') as mock_auth:
            mock_auth.side_effect = Exception("Invalid API key")

            payload = {
                "inference_id": "infer_123",
                "rating": 5
            }

            response = client.post(
                "/v1/feedback/success",
                json=payload,
                headers={"X-API-Key": "invalid_key"}
            )

            assert response.status_code == 401

    def test_customer_ownership_validation(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test feedback can only be added to customer's own inferences."""
        # Mock inference belonging to different customer
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "customer_id": "different_customer"
        }

        payload = {
            "inference_id": "infer_123",
            "rating": 5
        }

        response = client.post(
            "/v1/feedback/success",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        # Should be forbidden since inference belongs to different customer
        assert response.status_code in [403, 404]


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_inference_not_found(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test feedback for non-existent inference."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

        payload = {
            "inference_id": "nonexistent_123",
            "rating": 5
        }

        response = client.post(
            "/v1/feedback/success",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 404

    def test_duplicate_feedback_prevention(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test duplicate feedback within time window is rejected."""
        # Mock existing recent feedback
        recent_time = datetime.utcnow() - timedelta(minutes=2)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
            {"id": "existing_fb", "created_at": recent_time.isoformat()}
        ]

        payload = {
            "inference_id": "infer_123",
            "rating": 5
        }

        response = client.post(
            "/v1/feedback/success",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 400
        assert "duplicate" in response.json()["detail"].lower()

    def test_database_error_handling(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test graceful handling of database errors."""
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")

        payload = {
            "inference_id": "infer_123",
            "rating": 5
        }

        response = client.post(
            "/v1/feedback/success",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        assert response.status_code == 500

    def test_malformed_json(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test handling of malformed JSON."""
        response = client.post(
            "/v1/feedback/success",
            data="{'invalid': json}",  # Malformed JSON
            headers={
                "X-API-Key": valid_api_key,
                "Content-Type": "application/json"
            }
        )

        assert response.status_code == 422

    def test_response_time(self, client, mock_auth, mock_supabase, valid_api_key):
        """Test API response times are reasonable."""
        import time

        payload = {
            "inference_id": "infer_123",
            "rating": 5
        }

        start = time.time()
        response = client.post(
            "/v1/feedback/success",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        elapsed = time.time() - start

        assert response.status_code == 201
        assert elapsed < 1.0  # Should respond within 1 second
