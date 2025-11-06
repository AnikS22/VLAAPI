"""
Comprehensive tests for feedback service.
Tests feedback creation, statistics, and analytics.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json

from src.services.feedback import (
    FeedbackService,
    create_feedback,
    get_feedback_stats,
    calculate_feedback_rate,
    compute_correction_magnitude,
    analyze_failure_reasons,
    update_instruction_analytics
)
from src.models.feedback import (
    FeedbackType,
    SuccessFeedback,
    SafetyRating,
    ActionCorrection,
    FailureReport
)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch('src.database.supabase.get_supabase_client') as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def feedback_service(mock_supabase):
    """Create feedback service instance."""
    return FeedbackService(mock_supabase)


class TestFeedbackCreation:
    """Tests for feedback creation."""

    def test_create_success_feedback(self, feedback_service, mock_supabase):
        """Test creating success feedback."""
        feedback = SuccessFeedback(
            inference_id="infer_123",
            rating=5,
            comment="Excellent performance"
        )

        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": "fb_123",
                "type": "success",
                "inference_id": "infer_123",
                "rating": 5,
                "comment": "Excellent performance",
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        result = feedback_service.create_feedback(feedback, customer_id="cust_123")

        assert result["id"] == "fb_123"
        assert result["type"] == "success"
        assert result["rating"] == 5
        mock_supabase.table.assert_called_with("feedback")

    def test_create_safety_rating(self, feedback_service, mock_supabase):
        """Test creating safety rating feedback."""
        feedback = SafetyRating(
            inference_id="infer_123",
            safety_rating=0.95,
            concerns=["None"],
            would_deploy=True
        )

        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": "fb_456",
                "type": "safety",
                "inference_id": "infer_123",
                "safety_rating": 0.95,
                "would_deploy": True,
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        result = feedback_service.create_feedback(feedback, customer_id="cust_123")

        assert result["type"] == "safety"
        assert result["safety_rating"] == 0.95
        assert result["would_deploy"] is True

    def test_create_action_correction(self, feedback_service, mock_supabase):
        """Test creating action correction feedback."""
        feedback = ActionCorrection(
            inference_id="infer_123",
            original_action=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
            corrected_action=[0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75],
            reason="Improved trajectory"
        )

        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": "fb_789",
                "type": "correction",
                "inference_id": "infer_123",
                "original_action": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
                "corrected_action": [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75],
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        result = feedback_service.create_feedback(feedback, customer_id="cust_123")

        assert result["type"] == "correction"
        assert len(result["original_action"]) == 7
        assert len(result["corrected_action"]) == 7

    def test_create_failure_report(self, feedback_service, mock_supabase):
        """Test creating failure report feedback."""
        feedback = FailureReport(
            inference_id="infer_123",
            failure_type="collision",
            description="Robot collided with obstacle",
            severity="high"
        )

        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": "fb_999",
                "type": "failure",
                "inference_id": "infer_123",
                "failure_type": "collision",
                "severity": "high",
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        result = feedback_service.create_feedback(feedback, customer_id="cust_123")

        assert result["type"] == "failure"
        assert result["failure_type"] == "collision"
        assert result["severity"] == "high"

    def test_create_feedback_with_metadata(self, feedback_service, mock_supabase):
        """Test creating feedback with additional metadata."""
        feedback = SuccessFeedback(
            inference_id="infer_123",
            rating=4,
            comment="Good",
            metadata={"environment": "production", "operator": "user_1"}
        )

        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": "fb_meta",
                "type": "success",
                "metadata": {"environment": "production", "operator": "user_1"},
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        result = feedback_service.create_feedback(feedback, customer_id="cust_123")

        assert "metadata" in result
        assert result["metadata"]["environment"] == "production"


class TestFeedbackStatistics:
    """Tests for feedback statistics."""

    def test_get_overall_stats(self, feedback_service, mock_supabase):
        """Test getting overall feedback statistics."""
        mock_supabase.rpc.return_value.execute.return_value.data = [
            {
                "total_feedback": 150,
                "avg_rating": 4.3,
                "avg_safety": 0.87,
                "total_corrections": 30,
                "total_failures": 8,
                "feedback_rate": 0.75
            }
        ]

        stats = feedback_service.get_feedback_stats(customer_id="cust_123")

        assert stats["total_feedback"] == 150
        assert stats["avg_rating"] == 4.3
        assert stats["avg_safety"] == 0.87
        assert stats["total_corrections"] == 30
        assert stats["total_failures"] == 8
        assert stats["feedback_rate"] == 0.75

    def test_get_stats_for_inference(self, feedback_service, mock_supabase):
        """Test getting statistics for specific inference."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {
                "type": "success",
                "rating": 5,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "type": "safety",
                "safety_rating": 0.9,
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        stats = feedback_service.get_feedback_stats(
            customer_id="cust_123",
            inference_id="infer_123"
        )

        assert "feedback_count" in stats
        assert "avg_rating" in stats

    def test_get_stats_for_time_range(self, feedback_service, mock_supabase):
        """Test getting statistics for specific time range."""
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value.data = [
            {"rating": 4, "type": "success"},
            {"rating": 5, "type": "success"}
        ]

        stats = feedback_service.get_feedback_stats(
            customer_id="cust_123",
            start_date=start_date,
            end_date=end_date
        )

        assert "total_feedback" in stats

    def test_calculate_feedback_rate(self, mock_supabase):
        """Test calculating feedback rate."""
        # 80 feedback items for 100 inferences = 80% rate
        feedback_count = 80
        inference_count = 100

        rate = calculate_feedback_rate(feedback_count, inference_count)

        assert rate == 0.8

    def test_calculate_feedback_rate_zero_inferences(self):
        """Test feedback rate with zero inferences."""
        rate = calculate_feedback_rate(0, 0)
        assert rate == 0.0

    def test_calculate_feedback_rate_more_feedback_than_inferences(self):
        """Test feedback rate when feedback > inferences (multi-feedback)."""
        # Multiple feedback items per inference
        rate = calculate_feedback_rate(150, 100)
        assert rate == 1.5


class TestCorrectionAnalysis:
    """Tests for action correction analysis."""

    def test_compute_correction_magnitude(self):
        """Test computing correction magnitude."""
        original = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
        corrected = [0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75]

        magnitude = compute_correction_magnitude(original, corrected)

        # Each dimension changed by 0.05
        expected = (7 * (0.05 ** 2)) ** 0.5
        assert abs(magnitude - expected) < 0.001

    def test_compute_correction_magnitude_zero(self):
        """Test correction magnitude when actions are identical."""
        action = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]

        magnitude = compute_correction_magnitude(action, action)

        assert magnitude == 0.0

    def test_compute_correction_magnitude_large(self):
        """Test correction magnitude with large changes."""
        original = [-1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0]
        corrected = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

        magnitude = compute_correction_magnitude(original, corrected)

        # Large magnitude expected
        assert magnitude > 5.0

    def test_get_correction_statistics(self, feedback_service, mock_supabase):
        """Test getting correction statistics."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {
                "original_action": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
                "corrected_action": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
            },
            {
                "original_action": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "corrected_action": [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
            }
        ]

        stats = feedback_service.get_correction_statistics(customer_id="cust_123")

        assert "avg_magnitude" in stats
        assert "total_corrections" in stats
        assert "max_magnitude" in stats


class TestFailureAnalysis:
    """Tests for failure report analysis."""

    def test_analyze_failure_reasons(self, feedback_service, mock_supabase):
        """Test analyzing failure reasons."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"failure_type": "collision", "severity": "high"},
            {"failure_type": "collision", "severity": "medium"},
            {"failure_type": "timeout", "severity": "low"},
            {"failure_type": "error", "severity": "high"}
        ]

        analysis = analyze_failure_reasons(customer_id="cust_123")

        assert "collision" in analysis["by_type"]
        assert analysis["by_type"]["collision"] == 2
        assert "high" in analysis["by_severity"]
        assert analysis["by_severity"]["high"] == 2

    def test_get_failure_statistics(self, feedback_service, mock_supabase):
        """Test getting failure statistics."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {
                "failure_type": "collision",
                "severity": "critical",
                "created_at": datetime.utcnow().isoformat()
            }
        ]

        stats = feedback_service.get_failure_statistics(customer_id="cust_123")

        assert "total_failures" in stats
        assert "by_type" in stats
        assert "by_severity" in stats

    def test_get_recent_failures(self, feedback_service, mock_supabase):
        """Test getting recent failures."""
        recent_time = datetime.utcnow() - timedelta(hours=1)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": "fb_fail_1",
                "failure_type": "error",
                "severity": "high",
                "created_at": recent_time.isoformat()
            }
        ]

        failures = feedback_service.get_recent_failures(
            customer_id="cust_123",
            limit=10
        )

        assert len(failures) > 0
        assert failures[0]["failure_type"] == "error"


class TestInstructionAnalytics:
    """Tests for instruction analytics updates."""

    def test_update_instruction_analytics_success(self, mock_supabase):
        """Test updating analytics after success feedback."""
        feedback = SuccessFeedback(
            inference_id="infer_123",
            rating=5
        )

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "instruction": "Pick up the red block"
        }

        update_instruction_analytics(
            inference_id="infer_123",
            feedback=feedback,
            supabase=mock_supabase
        )

        # Should update instruction_analytics table
        mock_supabase.table.assert_called_with("instruction_analytics")

    def test_update_instruction_analytics_failure(self, mock_supabase):
        """Test updating analytics after failure feedback."""
        feedback = FailureReport(
            inference_id="infer_123",
            failure_type="collision",
            severity="high"
        )

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "instruction": "Move forward quickly"
        }

        update_instruction_analytics(
            inference_id="infer_123",
            feedback=feedback,
            supabase=mock_supabase
        )

        # Should increment failure count
        mock_supabase.table.assert_called()

    def test_update_instruction_analytics_correction(self, mock_supabase):
        """Test updating analytics after correction feedback."""
        feedback = ActionCorrection(
            inference_id="infer_123",
            original_action=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
            corrected_action=[0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        )

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "instruction": "Grasp the object"
        }

        update_instruction_analytics(
            inference_id="infer_123",
            feedback=feedback,
            supabase=mock_supabase
        )

        # Should track correction magnitude
        mock_supabase.table.assert_called()


class TestServiceEdgeCases:
    """Tests for service edge cases."""

    def test_handle_database_errors(self, feedback_service, mock_supabase):
        """Test graceful handling of database errors."""
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
            "Database connection error"
        )

        feedback = SuccessFeedback(inference_id="infer_123", rating=5)

        with pytest.raises(Exception):
            feedback_service.create_feedback(feedback, customer_id="cust_123")

    def test_handle_missing_inference(self, feedback_service, mock_supabase):
        """Test handling feedback for non-existent inference."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

        feedback = SuccessFeedback(inference_id="nonexistent", rating=5)

        with pytest.raises(Exception):
            feedback_service.create_feedback(feedback, customer_id="cust_123")

    def test_concurrent_feedback_creation(self, feedback_service, mock_supabase):
        """Test handling concurrent feedback submissions."""
        import concurrent.futures

        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "fb_concurrent", "created_at": datetime.utcnow().isoformat()}
        ]

        def create_feedback():
            feedback = SuccessFeedback(inference_id="infer_123", rating=5)
            return feedback_service.create_feedback(feedback, customer_id="cust_123")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_feedback) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 10

    def test_feedback_list_pagination(self, feedback_service, mock_supabase):
        """Test paginating feedback list."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
            {"id": f"fb_{i}", "rating": 5} for i in range(20)
        ]

        page1 = feedback_service.list_feedback(
            customer_id="cust_123",
            page=1,
            limit=10
        )

        page2 = feedback_service.list_feedback(
            customer_id="cust_123",
            page=2,
            limit=10
        )

        assert len(page1["items"]) == 10
        assert len(page2["items"]) == 10
        assert page1["items"][0]["id"] != page2["items"][0]["id"]
