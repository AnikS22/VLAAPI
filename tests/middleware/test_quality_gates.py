"""
Comprehensive tests for quality gates middleware.
Tests all validation rules and rejection criteria.
"""
import pytest
from fastapi import Request, HTTPException
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import json

from src.middleware.quality_gates import (
    QualityGatesMiddleware,
    validate_robot_type,
    validate_action_bounds,
    validate_safety_score,
    check_deduplication,
    validate_instruction_quality,
    validate_image_quality,
    record_rejection_metric
)
from src.models.inference import RobotType, InferenceRequest


@pytest.fixture
def quality_gates():
    """Create quality gates middleware instance."""
    app = Mock()
    return QualityGatesMiddleware(app)


@pytest.fixture
def valid_request():
    """Create valid inference request."""
    return InferenceRequest(
        robot_type=RobotType.GOOGLE_ROBOT,
        instruction="Pick up the red block",
        observation={
            "images": [{"data": "base64_image_data", "width": 224, "height": 224, "channels": 3}]
        }
    )


class TestRobotTypeValidation:
    """Tests for robot type validation."""

    def test_valid_robot_types(self, valid_request):
        """Test all valid robot types pass validation."""
        valid_types = [
            RobotType.GOOGLE_ROBOT,
            RobotType.WIDOWX,
            RobotType.BRIDGE_DATASET,
            RobotType.PANDA
        ]

        for robot_type in valid_types:
            request = valid_request.copy()
            request.robot_type = robot_type

            # Should not raise exception
            validate_robot_type(request)

    def test_unknown_robot_type_rejected(self, valid_request):
        """Test UNKNOWN robot type is rejected."""
        request = valid_request.copy()
        request.robot_type = RobotType.UNKNOWN

        with pytest.raises(HTTPException) as exc_info:
            validate_robot_type(request)

        assert exc_info.value.status_code == 422
        assert "robot_type" in str(exc_info.value.detail).lower()
        assert "unknown" in str(exc_info.value.detail).lower()

    def test_null_robot_type_rejected(self, valid_request):
        """Test null robot type is rejected."""
        request = valid_request.copy()
        request.robot_type = None

        with pytest.raises((HTTPException, ValueError)):
            validate_robot_type(request)


class TestActionBoundsValidation:
    """Tests for action vector bounds validation."""

    def test_valid_7dof_action(self, valid_request):
        """Test valid 7-DoF action passes validation."""
        request = valid_request.copy()
        request.action = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]

        validate_action_bounds(request)  # Should not raise

    def test_action_within_bounds(self, valid_request):
        """Test action values within [-1.1, 1.1] pass."""
        request = valid_request.copy()
        request.action = [-1.1, -0.5, 0.0, 0.5, 1.0, 1.1, 0.3]

        validate_action_bounds(request)  # Should not raise

    def test_action_exceeds_upper_bound(self, valid_request):
        """Test action value > 1.1 is rejected."""
        request = valid_request.copy()
        request.action = [0.1, 0.2, 1.2, 0.4, 0.5, 0.6, 0.7]

        with pytest.raises(HTTPException) as exc_info:
            validate_action_bounds(request)

        assert exc_info.value.status_code == 422
        assert "action" in str(exc_info.value.detail).lower()
        assert "1.1" in str(exc_info.value.detail)

    def test_action_exceeds_lower_bound(self, valid_request):
        """Test action value < -1.1 is rejected."""
        request = valid_request.copy()
        request.action = [0.1, -1.5, 0.3, 0.4, 0.5, 0.6, 0.7]

        with pytest.raises(HTTPException) as exc_info:
            validate_action_bounds(request)

        assert exc_info.value.status_code == 422

    def test_action_wrong_dimensions(self, valid_request):
        """Test action with wrong number of dimensions is rejected."""
        invalid_actions = [
            [0.1, 0.2],  # 2-DoF
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],  # 6-DoF
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],  # 8-DoF
            []  # Empty
        ]

        for invalid_action in invalid_actions:
            request = valid_request.copy()
            request.action = invalid_action

            with pytest.raises(HTTPException) as exc_info:
                validate_action_bounds(request)

            assert exc_info.value.status_code == 422
            assert "7" in str(exc_info.value.detail)

    def test_action_none_allowed(self, valid_request):
        """Test action can be None (for some requests)."""
        request = valid_request.copy()
        request.action = None

        # Should not raise if action is optional
        validate_action_bounds(request)


class TestSafetyScoreValidation:
    """Tests for safety score threshold validation."""

    def test_high_safety_score_passes(self, valid_request):
        """Test safety score >= 0.7 passes."""
        request = valid_request.copy()

        for score in [0.7, 0.8, 0.9, 1.0]:
            request.safety_score = score
            validate_safety_score(request)  # Should not raise

    def test_low_safety_score_rejected(self, valid_request):
        """Test safety score < 0.7 is rejected."""
        request = valid_request.copy()

        for score in [0.0, 0.3, 0.5, 0.69]:
            request.safety_score = score

            with pytest.raises(HTTPException) as exc_info:
                validate_safety_score(request)

            assert exc_info.value.status_code == 422
            assert "safety" in str(exc_info.value.detail).lower()
            assert "0.7" in str(exc_info.value.detail)

    def test_safety_score_boundary(self, valid_request):
        """Test safety score exactly at 0.7 threshold."""
        request = valid_request.copy()
        request.safety_score = 0.7

        validate_safety_score(request)  # Should pass

        request.safety_score = 0.6999
        with pytest.raises(HTTPException):
            validate_safety_score(request)  # Should fail

    def test_safety_score_out_of_range(self, valid_request):
        """Test safety score outside [0, 1] range."""
        request = valid_request.copy()

        for invalid_score in [-0.1, 1.5, 2.0]:
            request.safety_score = invalid_score

            with pytest.raises(HTTPException):
                validate_safety_score(request)


class TestDeduplication:
    """Tests for request deduplication."""

    @pytest.fixture
    def mock_cache(self):
        """Mock cache for deduplication."""
        with patch('src.middleware.quality_gates.dedup_cache', {}) as cache:
            yield cache

    def test_first_request_allowed(self, valid_request, mock_cache):
        """Test first request with hash passes."""
        check_deduplication(valid_request)  # Should not raise

    def test_duplicate_within_window_rejected(self, valid_request, mock_cache):
        """Test duplicate request within 5-minute window is rejected."""
        # First request
        check_deduplication(valid_request)

        # Duplicate request immediately after
        with pytest.raises(HTTPException) as exc_info:
            check_deduplication(valid_request)

        assert exc_info.value.status_code == 422
        assert "duplicate" in str(exc_info.value.detail).lower()

    def test_duplicate_after_window_allowed(self, valid_request, mock_cache):
        """Test duplicate request after 5-minute window is allowed."""
        # First request
        check_deduplication(valid_request)

        # Mock time passage
        with patch('src.middleware.quality_gates.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.utcnow() + timedelta(minutes=6)

            # Should be allowed after window expires
            check_deduplication(valid_request)

    def test_different_requests_allowed(self, valid_request, mock_cache):
        """Test different requests are allowed concurrently."""
        request1 = valid_request.copy()
        request1.instruction = "Pick up red block"

        request2 = valid_request.copy()
        request2.instruction = "Pick up blue block"

        check_deduplication(request1)
        check_deduplication(request2)  # Should not raise


class TestInstructionQuality:
    """Tests for instruction quality validation."""

    def test_valid_instruction(self, valid_request):
        """Test valid instruction passes."""
        valid_instructions = [
            "Pick up the red block",
            "Move the arm to the left",
            "Grasp the object carefully",
            "Place the item on the table"
        ]

        for instruction in valid_instructions:
            request = valid_request.copy()
            request.instruction = instruction
            validate_instruction_quality(request)  # Should not raise

    def test_too_short_instruction_rejected(self, valid_request):
        """Test instruction with < 3 words is rejected."""
        short_instructions = [
            "Pick up",
            "Move",
            "Go",
            "Stop"
        ]

        for instruction in short_instructions:
            request = valid_request.copy()
            request.instruction = instruction

            with pytest.raises(HTTPException) as exc_info:
                validate_instruction_quality(request)

            assert exc_info.value.status_code == 422
            assert "instruction" in str(exc_info.value.detail).lower()
            assert "3 words" in str(exc_info.value.detail).lower()

    def test_too_long_instruction_rejected(self, valid_request):
        """Test instruction with > 500 characters is rejected."""
        request = valid_request.copy()
        request.instruction = "Pick up the block " * 50  # > 500 chars

        with pytest.raises(HTTPException) as exc_info:
            validate_instruction_quality(request)

        assert exc_info.value.status_code == 422
        assert "500" in str(exc_info.value.detail)

    def test_empty_instruction_rejected(self, valid_request):
        """Test empty instruction is rejected."""
        request = valid_request.copy()
        request.instruction = ""

        with pytest.raises(HTTPException):
            validate_instruction_quality(request)

    def test_whitespace_only_instruction_rejected(self, valid_request):
        """Test whitespace-only instruction is rejected."""
        request = valid_request.copy()
        request.instruction = "   \n\t  "

        with pytest.raises(HTTPException):
            validate_instruction_quality(request)

    def test_instruction_boundary_cases(self, valid_request):
        """Test instruction at boundaries."""
        # Exactly 3 words - should pass
        request = valid_request.copy()
        request.instruction = "Pick up block"
        validate_instruction_quality(request)

        # Exactly 500 characters - should pass
        request.instruction = "a" * 497 + " b c"  # 500 chars, 3+ words
        validate_instruction_quality(request)


class TestImageQuality:
    """Tests for image quality validation."""

    def test_valid_image(self, valid_request):
        """Test valid image passes validation."""
        request = valid_request.copy()
        request.observation = {
            "images": [
                {"data": "base64_data", "width": 224, "height": 224, "channels": 3}
            ]
        }

        validate_image_quality(request)  # Should not raise

    def test_image_minimum_dimensions(self, valid_request):
        """Test image must be at least 64x64."""
        # Valid minimum size
        request = valid_request.copy()
        request.observation = {
            "images": [{"data": "data", "width": 64, "height": 64, "channels": 3}]
        }
        validate_image_quality(request)

        # Too small
        request.observation = {
            "images": [{"data": "data", "width": 32, "height": 32, "channels": 3}]
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_image_quality(request)

        assert exc_info.value.status_code == 422
        assert "64" in str(exc_info.value.detail)

    def test_invalid_channels(self, valid_request):
        """Test image must have valid channel count (1, 3, or 4)."""
        valid_channels = [1, 3, 4]
        invalid_channels = [0, 2, 5]

        for channels in valid_channels:
            request = valid_request.copy()
            request.observation = {
                "images": [{"data": "data", "width": 224, "height": 224, "channels": channels}]
            }
            validate_image_quality(request)  # Should not raise

        for channels in invalid_channels:
            request = valid_request.copy()
            request.observation = {
                "images": [{"data": "data", "width": 224, "height": 224, "channels": channels}]
            }
            with pytest.raises(HTTPException) as exc_info:
                validate_image_quality(request)

            assert exc_info.value.status_code == 422

    def test_missing_image_data(self, valid_request):
        """Test missing image data is rejected."""
        request = valid_request.copy()
        request.observation = {"images": []}

        with pytest.raises(HTTPException) as exc_info:
            validate_image_quality(request)

        assert exc_info.value.status_code == 422

    def test_multiple_images(self, valid_request):
        """Test multiple images are validated."""
        request = valid_request.copy()
        request.observation = {
            "images": [
                {"data": "data1", "width": 224, "height": 224, "channels": 3},
                {"data": "data2", "width": 224, "height": 224, "channels": 3}
            ]
        }

        validate_image_quality(request)  # Should not raise


class TestRejectionMetrics:
    """Tests for rejection metrics recording."""

    @pytest.fixture
    def mock_prometheus(self):
        """Mock Prometheus metrics."""
        with patch('src.middleware.quality_gates.rejection_counter') as counter:
            yield counter

    def test_record_rejection_metric(self, mock_prometheus):
        """Test rejection metrics are recorded."""
        record_rejection_metric("robot_type", "UNKNOWN robot type")

        mock_prometheus.labels.assert_called_once_with(
            reason="robot_type",
            detail="UNKNOWN robot type"
        )
        mock_prometheus.labels.return_value.inc.assert_called_once()

    def test_different_rejection_reasons(self, mock_prometheus):
        """Test different rejection reasons are tracked."""
        reasons = [
            ("action_bounds", "Value exceeds 1.1"),
            ("safety_score", "Below 0.7 threshold"),
            ("duplicate", "Request seen within 5 minutes"),
            ("instruction", "Less than 3 words"),
            ("image_quality", "Dimensions below 64x64")
        ]

        for reason, detail in reasons:
            record_rejection_metric(reason, detail)


class TestMiddlewareIntegration:
    """Tests for middleware integration."""

    @pytest.mark.asyncio
    async def test_middleware_dispatch(self, quality_gates, valid_request):
        """Test middleware processes requests correctly."""
        mock_call_next = AsyncMock(return_value=Mock(status_code=200))

        request = Mock()
        request.method = "POST"
        request.url.path = "/v1/inference"

        with patch.object(quality_gates, 'validate_request', return_value=None):
            response = await quality_gates.dispatch(request, mock_call_next)

        assert response.status_code == 200
        mock_call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_validation_failure(self, quality_gates):
        """Test middleware handles validation failures."""
        mock_call_next = AsyncMock()

        request = Mock()
        request.method = "POST"
        request.url.path = "/v1/inference"

        with patch.object(
            quality_gates,
            'validate_request',
            side_effect=HTTPException(status_code=422, detail="Validation failed")
        ):
            with pytest.raises(HTTPException) as exc_info:
                await quality_gates.dispatch(request, mock_call_next)

        assert exc_info.value.status_code == 422
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_performance(self, quality_gates, valid_request):
        """Test middleware has minimal performance impact."""
        import time

        mock_call_next = AsyncMock(return_value=Mock(status_code=200))
        request = Mock()
        request.method = "POST"
        request.url.path = "/v1/inference"

        with patch.object(quality_gates, 'validate_request', return_value=None):
            start = time.time()
            await quality_gates.dispatch(request, mock_call_next)
            elapsed = time.time() - start

        # Middleware should add < 10ms overhead
        assert elapsed < 0.01


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_concurrent_validation(self, valid_request):
        """Test validation handles concurrent requests."""
        import concurrent.futures

        def validate():
            try:
                validate_robot_type(valid_request)
                validate_action_bounds(valid_request)
                validate_instruction_quality(valid_request)
                return True
            except Exception:
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(validate) for _ in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(results)

    def test_malformed_request_data(self):
        """Test handling of malformed request data."""
        malformed_requests = [
            {"robot_type": "invalid"},
            {"instruction": 123},  # Wrong type
            {"observation": "not a dict"},
            {},  # Empty
        ]

        for malformed in malformed_requests:
            # Should raise validation error
            with pytest.raises(Exception):
                InferenceRequest(**malformed)

    def test_unicode_in_instruction(self, valid_request):
        """Test handling of unicode characters in instruction."""
        request = valid_request.copy()
        request.instruction = "Pick up the 红色 block carefully"

        validate_instruction_quality(request)  # Should handle unicode

    def test_special_characters_in_instruction(self, valid_request):
        """Test handling of special characters."""
        request = valid_request.copy()
        request.instruction = "Pick up the block! @#$%"

        validate_instruction_quality(request)  # Should allow special chars
