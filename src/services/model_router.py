"""Model Router - Intelligent model selection based on constraints.

This module implements routing logic to select the optimal VLA model for each
inference request based on:
- Robot compatibility
- Performance requirements (latency, accuracy)
- Cost optimization
- Customer preferences
- Current GPU load
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from uuid import UUID

from src.core.model_registry import ModelConfig, ModelRegistry, ModelStatus
from src.services.multi_model_manager import MultiModelManager

logger = logging.getLogger(__name__)


@dataclass
class RoutingConstraints:
    """Constraints for model selection."""

    # Required
    robot_type: str

    # Performance requirements
    max_latency_ms: Optional[float] = None
    min_accuracy: Optional[float] = None
    max_vram_gb: Optional[float] = None

    # Optimization goals
    optimize_latency: bool = False
    optimize_cost: bool = False
    optimize_accuracy: bool = False

    # Model preferences
    preferred_model_id: Optional[str] = None
    excluded_models: Optional[List[str]] = None
    min_model_version: Optional[str] = None


@dataclass
class RoutingDecision:
    """Result of routing decision."""

    selected_model_id: str
    model_config: ModelConfig
    selection_reason: str
    alternatives: List[str]
    confidence_score: float  # 0-1, how confident we are in this choice


class ModelRouter:
    """Routes inference requests to optimal VLA model.

    Selection strategy:
    1. Filter by compatibility (robot type, VRAM, status)
    2. Apply hard constraints (latency, accuracy)
    3. Rank by optimization goal
    4. Consider GPU load
    5. Return best match with alternatives
    """

    def __init__(self, model_manager: MultiModelManager):
        """Initialize router.

        Args:
            model_manager: Multi-model manager instance
        """
        self.model_manager = model_manager
        self.registry = ModelRegistry

    def select_model(
        self,
        constraints: RoutingConstraints,
        customer_preferences: Optional[Dict] = None
    ) -> RoutingDecision:
        """Select optimal model for inference request.

        Args:
            constraints: Routing constraints
            customer_preferences: Customer-specific preferences (model pins, etc.)

        Returns:
            RoutingDecision with selected model and reasoning

        Raises:
            ValueError: If no suitable model found
        """
        logger.debug(f"Routing request for robot_type={constraints.robot_type}")

        # Priority 1: Explicit model preference
        if constraints.preferred_model_id:
            if self._validate_model_choice(
                constraints.preferred_model_id,
                constraints
            ):
                model_config = self.registry.get_model(constraints.preferred_model_id)
                return RoutingDecision(
                    selected_model_id=constraints.preferred_model_id,
                    model_config=model_config,
                    selection_reason="explicit_customer_preference",
                    alternatives=self._get_alternatives(constraints),
                    confidence_score=1.0
                )
            else:
                logger.warning(
                    f"Preferred model {constraints.preferred_model_id} "
                    f"doesn't meet constraints, auto-selecting"
                )

        # Priority 2: Customer pinned version
        if customer_preferences and "model_pins" in customer_preferences:
            pinned_model = customer_preferences["model_pins"].get(constraints.robot_type)
            if pinned_model and self._validate_model_choice(pinned_model, constraints):
                model_config = self.registry.get_model(pinned_model)
                return RoutingDecision(
                    selected_model_id=pinned_model,
                    model_config=model_config,
                    selection_reason="customer_pinned_version",
                    alternatives=self._get_alternatives(constraints),
                    confidence_score=0.95
                )

        # Priority 3: Auto-select based on constraints
        return self._auto_select(constraints)

    def _auto_select(self, constraints: RoutingConstraints) -> RoutingDecision:
        """Auto-select model based on constraints.

        Args:
            constraints: Routing constraints

        Returns:
            RoutingDecision

        Raises:
            ValueError: If no suitable model found
        """
        # Get compatible models
        candidates = self.registry.get_compatible_models(
            robot_type=constraints.robot_type,
            max_latency_ms=constraints.max_latency_ms,
            max_vram_gb=constraints.max_vram_gb,
            min_accuracy=constraints.min_accuracy
        )

        if not candidates:
            raise ValueError(
                f"No models available for robot_type={constraints.robot_type} "
                f"with constraints: latency<={constraints.max_latency_ms}ms, "
                f"accuracy>={constraints.min_accuracy}, "
                f"vram<={constraints.max_vram_gb}GB"
            )

        # Filter excluded models
        if constraints.excluded_models:
            candidates = [
                m for m in candidates
                if m.model_id not in constraints.excluded_models
            ]

        # Rank by optimization goal
        if constraints.optimize_latency:
            # Prefer fastest models
            selected = min(candidates, key=lambda m: m.expected_latency_p50_ms)
            reason = "optimized_for_latency"
            confidence = 0.9

        elif constraints.optimize_cost:
            # Prefer cheapest models
            selected = min(candidates, key=lambda m: m.cost_per_1k)
            reason = "optimized_for_cost"
            confidence = 0.85

        elif constraints.optimize_accuracy:
            # Prefer most accurate models
            models_with_benchmarks = [m for m in candidates if m.accuracy_benchmark]
            if models_with_benchmarks:
                selected = max(
                    models_with_benchmarks,
                    key=lambda m: m.accuracy_benchmark
                )
                reason = "optimized_for_accuracy"
                confidence = 0.9
            else:
                # Fallback to first candidate
                selected = candidates[0]
                reason = "no_benchmark_available"
                confidence = 0.6

        else:
            # Default: Balance accuracy and latency
            selected = self._balanced_selection(candidates)
            reason = "balanced_selection"
            confidence = 0.8

        # Consider GPU load
        selected = self._adjust_for_gpu_load(selected, candidates)

        # Get alternatives
        alternatives = [
            m.model_id for m in candidates
            if m.model_id != selected.model_id
        ][:3]  # Top 3 alternatives

        logger.info(
            f"Selected {selected.model_id} for {constraints.robot_type} "
            f"(reason: {reason}, confidence: {confidence:.2f})"
        )

        return RoutingDecision(
            selected_model_id=selected.model_id,
            model_config=selected,
            selection_reason=reason,
            alternatives=alternatives,
            confidence_score=confidence
        )

    def _balanced_selection(self, candidates: List[ModelConfig]) -> ModelConfig:
        """Select model balancing accuracy and latency.

        Scoring formula:
        score = (accuracy * 100) - (latency_p50 / 10)

        Args:
            candidates: List of candidate models

        Returns:
            Best balanced model
        """
        def score(model: ModelConfig) -> float:
            accuracy = model.accuracy_benchmark or 0.5  # Default if unknown
            latency_penalty = model.expected_latency_p50_ms / 10.0
            return (accuracy * 100) - latency_penalty

        return max(candidates, key=score)

    def _adjust_for_gpu_load(
        self,
        selected: ModelConfig,
        candidates: List[ModelConfig]
    ) -> ModelConfig:
        """Adjust selection based on current GPU load.

        If selected model is not loaded and GPU is busy, prefer a loaded model.

        Args:
            selected: Currently selected model
            candidates: All candidate models

        Returns:
            Potentially adjusted model selection
        """
        # Check if selected model is already loaded
        if self.model_manager.is_model_loaded(selected.model_id):
            return selected

        # Get loaded models from candidates
        loaded_candidates = [
            m for m in candidates
            if self.model_manager.is_model_loaded(m.model_id)
        ]

        if not loaded_candidates:
            # No loaded models, stick with selection
            return selected

        # Check GPU utilization
        gpu_info = self.model_manager.get_gpu_info()
        avg_utilization = sum(g.utilization for g in gpu_info.values()) / len(gpu_info)

        if avg_utilization > 80.0:
            # High GPU load, prefer loaded model to avoid loading delay
            logger.info(
                f"High GPU utilization ({avg_utilization:.1f}%), "
                f"preferring loaded model over {selected.model_id}"
            )

            # Select best loaded model
            best_loaded = self._balanced_selection(loaded_candidates)
            return best_loaded

        return selected

    def _validate_model_choice(
        self,
        model_id: str,
        constraints: RoutingConstraints
    ) -> bool:
        """Validate if a model meets constraints.

        Args:
            model_id: Model to validate
            constraints: Constraints to check

        Returns:
            True if model is valid, False otherwise
        """
        try:
            model_config = self.registry.get_model(model_id)
        except ValueError:
            logger.warning(f"Model {model_id} not found in registry")
            return False

        # Check robot compatibility
        if constraints.robot_type not in model_config.supported_robots:
            logger.debug(
                f"Model {model_id} doesn't support robot {constraints.robot_type}"
            )
            return False

        # Check latency constraint
        if constraints.max_latency_ms:
            if model_config.expected_latency_p95_ms > constraints.max_latency_ms:
                logger.debug(
                    f"Model {model_id} latency {model_config.expected_latency_p95_ms}ms "
                    f"exceeds max {constraints.max_latency_ms}ms"
                )
                return False

        # Check accuracy constraint
        if constraints.min_accuracy and model_config.accuracy_benchmark:
            if model_config.accuracy_benchmark < constraints.min_accuracy:
                logger.debug(
                    f"Model {model_id} accuracy {model_config.accuracy_benchmark} "
                    f"below min {constraints.min_accuracy}"
                )
                return False

        # Check VRAM constraint
        if constraints.max_vram_gb:
            if model_config.min_vram_gb > constraints.max_vram_gb:
                logger.debug(
                    f"Model {model_id} requires {model_config.min_vram_gb}GB VRAM, "
                    f"max is {constraints.max_vram_gb}GB"
                )
                return False

        # Check excluded models
        if constraints.excluded_models and model_id in constraints.excluded_models:
            logger.debug(f"Model {model_id} is in excluded list")
            return False

        return True

    def _get_alternatives(
        self,
        constraints: RoutingConstraints,
        limit: int = 3
    ) -> List[str]:
        """Get alternative model suggestions.

        Args:
            constraints: Routing constraints
            limit: Maximum number of alternatives

        Returns:
            List of alternative model IDs
        """
        try:
            candidates = self.registry.get_compatible_models(
                robot_type=constraints.robot_type,
                max_latency_ms=constraints.max_latency_ms,
                max_vram_gb=constraints.max_vram_gb,
                min_accuracy=constraints.min_accuracy
            )
            return [m.model_id for m in candidates[:limit]]
        except Exception as e:
            logger.warning(f"Failed to get alternatives: {e}")
            return []

    def get_routing_recommendation(
        self,
        robot_type: str,
        use_case: str
    ) -> RoutingDecision:
        """Get routing recommendation for common use cases.

        Args:
            robot_type: Robot type
            use_case: Use case description (real-time, offline, high-accuracy, etc.)

        Returns:
            RoutingDecision
        """
        use_case_lower = use_case.lower()

        if "real-time" in use_case_lower or "streaming" in use_case_lower:
            # Real-time: prioritize latency
            constraints = RoutingConstraints(
                robot_type=robot_type,
                max_latency_ms=100.0,
                optimize_latency=True
            )
        elif "high-accuracy" in use_case_lower or "critical" in use_case_lower:
            # Critical applications: prioritize accuracy
            constraints = RoutingConstraints(
                robot_type=robot_type,
                optimize_accuracy=True,
                min_accuracy=0.85
            )
        elif "cost" in use_case_lower or "batch" in use_case_lower:
            # Cost-sensitive: optimize cost
            constraints = RoutingConstraints(
                robot_type=robot_type,
                optimize_cost=True
            )
        else:
            # Default: balanced
            constraints = RoutingConstraints(
                robot_type=robot_type
            )

        return self.select_model(constraints)


# Convenience function for quick routing
def route_inference_request(
    robot_type: str,
    model_manager: MultiModelManager,
    preferred_model: Optional[str] = None,
    max_latency_ms: Optional[float] = None,
    optimize_cost: bool = False,
    customer_preferences: Optional[Dict] = None
) -> str:
    """Quick routing for inference request.

    Args:
        robot_type: Robot type identifier
        model_manager: Multi-model manager instance
        preferred_model: Preferred model ID (optional)
        max_latency_ms: Maximum acceptable latency
        optimize_cost: Optimize for cost
        customer_preferences: Customer preferences

    Returns:
        Selected model ID
    """
    router = ModelRouter(model_manager)

    constraints = RoutingConstraints(
        robot_type=robot_type,
        preferred_model_id=preferred_model,
        max_latency_ms=max_latency_ms,
        optimize_cost=optimize_cost
    )

    decision = router.select_model(constraints, customer_preferences)

    return decision.selected_model_id
