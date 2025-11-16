"""Unit tests for Model Router."""

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from src.core.model_registry import ModelRegistry
from src.services.model_router import (
    ModelRouter,
    RoutingConstraints,
    RoutingDecision,
)
from src.services.multi_model_manager import MultiModelManager


class TestRoutingConstraints:
    """Test suite for RoutingConstraints dataclass."""

    def test_basic_constraints(self):
        """Test creating basic routing constraints."""
        constraints = RoutingConstraints(
            robot_type="franka_panda",
            max_latency_ms=100,
            optimize_latency=True
        )

        assert constraints.robot_type == "franka_panda"
        assert constraints.max_latency_ms == 100
        assert constraints.optimize_latency is True
        assert constraints.optimize_cost is False

    def test_constraints_defaults(self):
        """Test default values in constraints."""
        constraints = RoutingConstraints(robot_type="franka_panda")

        assert constraints.max_latency_ms is None
        assert constraints.min_accuracy is None
        assert constraints.optimize_latency is False
        assert constraints.optimize_cost is False


class TestModelRouter:
    """Test suite for ModelRouter."""

    @pytest.fixture
    def mock_model_manager(self):
        """Create mock model manager."""
        manager = Mock(spec=MultiModelManager)
        manager.is_model_loaded.return_value = False
        manager.get_gpu_info.return_value = {
            0: Mock(device_id=0, utilization=50.0)
        }
        return manager

    @pytest.fixture
    def router(self, mock_model_manager):
        """Create router with mock manager."""
        return ModelRouter(mock_model_manager)

    def test_router_initialization(self, mock_model_manager):
        """Test router initialization."""
        router = ModelRouter(mock_model_manager)

        assert router.model_manager == mock_model_manager
        assert router.registry == ModelRegistry

    def test_select_fastest_model(self, router):
        """Test selecting fastest model for real-time use."""
        constraints = RoutingConstraints(
            robot_type="franka_panda",
            max_latency_ms=100,
            optimize_latency=True
        )

        decision = router.select_model(constraints)

        assert decision.selected_model_id == "octo-small"  # Fastest model (60ms)
        assert decision.selection_reason == "optimized_for_latency"
        assert decision.confidence_score >= 0.8

    def test_select_cheapest_model(self, router):
        """Test selecting cheapest model."""
        constraints = RoutingConstraints(
            robot_type="franka_panda",
            optimize_cost=True
        )

        decision = router.select_model(constraints)

        assert decision.selected_model_id == "octo-small"  # Cheapest ($0.0005/1k)
        assert decision.selection_reason == "optimized_for_cost"
        assert decision.confidence_score >= 0.8

    def test_select_most_accurate_model(self, router):
        """Test selecting most accurate model."""
        constraints = RoutingConstraints(
            robot_type="franka_panda",
            optimize_accuracy=True,
            max_vram_gb=32.0  # Allow RT-2
        )

        decision = router.select_model(constraints)

        # Should select RT-2 (highest accuracy at 0.90)
        assert decision.selected_model_id == "rt-2-base"
        assert decision.selection_reason == "optimized_for_accuracy"
        assert decision.confidence_score >= 0.8

    def test_explicit_model_preference(self, router):
        """Test explicit model preference."""
        constraints = RoutingConstraints(
            robot_type="franka_panda",
            preferred_model_id="rt-1"
        )

        decision = router.select_model(constraints)

        assert decision.selected_model_id == "rt-1"
        assert decision.selection_reason == "explicit_customer_preference"
        assert decision.confidence_score == 1.0

    def test_customer_pinned_version(self, router):
        """Test customer pinned version preference."""
        constraints = RoutingConstraints(robot_type="franka_panda")

        customer_prefs = {
            "model_pins": {
                "franka_panda": "openvla-7b-v2"
            }
        }

        decision = router.select_model(constraints, customer_prefs)

        assert decision.selected_model_id == "openvla-7b-v2"
        assert decision.selection_reason == "customer_pinned_version"
        assert decision.confidence_score == 0.95

    def test_latency_constraint(self, router):
        """Test latency constraint filtering."""
        constraints = RoutingConstraints(
            robot_type="franka_panda",
            max_latency_ms=100  # Should exclude slower models
        )

        decision = router.select_model(constraints)

        # Get selected model config
        model = ModelRegistry.get_model(decision.selected_model_id)

        # Verify it meets latency constraint
        assert model.expected_latency_p95_ms <= 100

    def test_accuracy_constraint(self, router):
        """Test accuracy constraint filtering."""
        constraints = RoutingConstraints(
            robot_type="franka_panda",
            min_accuracy=0.85,
            max_vram_gb=32.0
        )

        decision = router.select_model(constraints)

        model = ModelRegistry.get_model(decision.selected_model_id)

        # Verify it meets accuracy constraint
        if model.accuracy_benchmark:
            assert model.accuracy_benchmark >= 0.85

    def test_vram_constraint(self, router):
        """Test VRAM constraint filtering."""
        constraints = RoutingConstraints(
            robot_type="franka_panda",
            max_vram_gb=12.0  # Should exclude larger models
        )

        decision = router.select_model(constraints)

        model = ModelRegistry.get_model(decision.selected_model_id)

        # Verify it meets VRAM constraint
        assert model.min_vram_gb <= 12.0

    def test_unsupported_robot_type(self, router):
        """Test that unsupported robot type raises error."""
        constraints = RoutingConstraints(
            robot_type="unsupported_robot_xyz"
        )

        with pytest.raises(ValueError, match="No models available"):
            router.select_model(constraints)

    def test_impossible_constraints(self, router):
        """Test that impossible constraints raise error."""
        constraints = RoutingConstraints(
            robot_type="franka_panda",
            max_latency_ms=10,  # Impossible: too fast
            min_accuracy=0.95,  # Impossible: too high
            max_vram_gb=4.0     # Impossible: too small
        )

        with pytest.raises(ValueError, match="No models available"):
            router.select_model(constraints)

    def test_balanced_selection(self, router):
        """Test balanced selection (no optimization specified)."""
        constraints = RoutingConstraints(robot_type="franka_panda")

        decision = router.select_model(constraints)

        assert decision.selected_model_id  # Should return some model
        assert decision.selection_reason == "balanced_selection"
        assert 0 < decision.confidence_score <= 1.0

    def test_alternatives_provided(self, router):
        """Test that alternatives are provided."""
        constraints = RoutingConstraints(
            robot_type="franka_panda",
            optimize_latency=True
        )

        decision = router.select_model(constraints)

        # Should provide alternatives
        assert isinstance(decision.alternatives, list)
        assert len(decision.alternatives) > 0

        # Selected model should not be in alternatives
        assert decision.selected_model_id not in decision.alternatives

    def test_gpu_load_preference(self, router, mock_model_manager):
        """Test that router prefers loaded models under high GPU load."""
        # Mock high GPU utilization
        mock_model_manager.get_gpu_info.return_value = {
            0: Mock(device_id=0, utilization=85.0)  # High utilization
        }

        # Mock octo-small as loaded, rt-1 as not loaded
        def is_loaded(model_id):
            return model_id == "octo-small"

        mock_model_manager.is_model_loaded.side_effect = is_loaded

        constraints = RoutingConstraints(
            robot_type="franka_panda",
            optimize_accuracy=True  # Would normally select more accurate model
        )

        decision = router.select_model(constraints)

        # Under high GPU load, should prefer loaded model
        # even if not optimizing for latency
        assert decision.selected_model_id == "octo-small"

    def test_excluded_models(self, router):
        """Test excluding specific models."""
        constraints = RoutingConstraints(
            robot_type="franka_panda",
            optimize_latency=True,
            excluded_models=["octo-small"]  # Exclude fastest model
        )

        decision = router.select_model(constraints)

        # Should select next fastest model
        assert decision.selected_model_id != "octo-small"
        assert decision.selected_model_id in ["rt-1", "octo-base", "openvla-7b-v2"]

    def test_invalid_preferred_model(self, router):
        """Test that invalid preferred model falls back to auto-select."""
        constraints = RoutingConstraints(
            robot_type="franka_panda",
            preferred_model_id="nonexistent-model"
        )

        # Should fall back to auto-selection instead of failing
        decision = router.select_model(constraints)

        assert decision.selected_model_id != "nonexistent-model"
        assert decision.selection_reason != "explicit_customer_preference"

    def test_get_routing_recommendation_realtime(self, router):
        """Test routing recommendation for real-time use case."""
        decision = router.get_routing_recommendation(
            robot_type="franka_panda",
            use_case="real-time"
        )

        # Should select fast model
        model = ModelRegistry.get_model(decision.selected_model_id)
        assert model.expected_latency_p95_ms <= 100

    def test_get_routing_recommendation_high_accuracy(self, router):
        """Test routing recommendation for high-accuracy use case."""
        decision = router.get_routing_recommendation(
            robot_type="franka_panda",
            use_case="high-accuracy"
        )

        # Should select accurate model
        model = ModelRegistry.get_model(decision.selected_model_id)
        assert model.accuracy_benchmark >= 0.85

    def test_get_routing_recommendation_cost(self, router):
        """Test routing recommendation for cost-sensitive use case."""
        decision = router.get_routing_recommendation(
            robot_type="franka_panda",
            use_case="cost-optimized batch processing"
        )

        # Should optimize for cost
        assert decision.selected_model_id == "octo-small"  # Cheapest


class TestRoutingDecision:
    """Test suite for RoutingDecision dataclass."""

    def test_routing_decision_creation(self):
        """Test creating a routing decision."""
        model = ModelRegistry.get_model("rt-1")

        decision = RoutingDecision(
            selected_model_id="rt-1",
            model_config=model,
            selection_reason="test_reason",
            alternatives=["openvla-7b-v1", "octo-base"],
            confidence_score=0.9
        )

        assert decision.selected_model_id == "rt-1"
        assert decision.model_config.model_id == "rt-1"
        assert decision.selection_reason == "test_reason"
        assert len(decision.alternatives) == 2
        assert decision.confidence_score == 0.9


class TestRouterEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def mock_model_manager(self):
        """Create mock model manager."""
        manager = Mock(spec=MultiModelManager)
        manager.is_model_loaded.return_value = False
        manager.get_gpu_info.return_value = {0: Mock(utilization=50.0)}
        return manager

    @pytest.fixture
    def router(self, mock_model_manager):
        """Create router."""
        return ModelRouter(mock_model_manager)

    def test_all_models_excluded(self, router):
        """Test when all compatible models are excluded."""
        # Get all franka_panda compatible models
        all_models = [
            m.model_id for m in
            ModelRegistry.list_models(robot_type="franka_panda")
        ]

        constraints = RoutingConstraints(
            robot_type="franka_panda",
            excluded_models=all_models  # Exclude everything
        )

        with pytest.raises(ValueError):
            router.select_model(constraints)

    def test_very_tight_constraints(self, router):
        """Test very tight but achievable constraints."""
        constraints = RoutingConstraints(
            robot_type="franka_panda",
            max_latency_ms=70,  # Very tight
            max_vram_gb=10.0,   # Very tight
            min_accuracy=0.80
        )

        decision = router.select_model(constraints)

        # Should find octo-small (60ms, 8GB, 0.81 accuracy)
        assert decision.selected_model_id == "octo-small"
