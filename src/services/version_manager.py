"""Version Manager - A/B testing and traffic splitting for model versions.

This module enables:
- Gradual rollout of new model versions (canary deployments)
- A/B testing between model versions
- Customer cohort assignment for consistent routing
- Version performance comparison
- Traffic splitting and migration
"""

import hashlib
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.model_registry import ModelConfig, ModelRegistry

logger = logging.getLogger(__name__)


@dataclass
class ModelDeployment:
    """Model version deployment configuration."""

    deployment_id: str
    model_id: str
    version: str
    traffic_weight: float  # 0.0 to 1.0
    status: str  # 'active', 'canary', 'deprecated', 'disabled'
    created_at: datetime
    updated_at: datetime

    # Performance metrics (populated from inference logs)
    total_inferences: int = 0
    avg_latency_ms: float = 0.0
    success_rate: float = 0.0
    avg_safety_score: float = 0.0


@dataclass
class ABTestCohort:
    """Customer cohort assignment for A/B testing."""

    customer_id: UUID
    model_id: str
    assigned_version: str
    assigned_at: datetime
    cohort_name: str  # 'control', 'treatment_a', 'treatment_b', etc.


@dataclass
class VersionMetrics:
    """Performance metrics for a model version."""

    version: str
    inference_count: int
    avg_latency_ms: float
    p95_latency_ms: float
    success_rate: float
    avg_safety_score: float
    error_rate: float

    # Comparison to baseline (if available)
    latency_delta_pct: Optional[float] = None
    success_rate_delta_pct: Optional[float] = None
    safety_score_delta_pct: Optional[float] = None


@dataclass
class RolloutPlan:
    """Gradual rollout plan for a new model version."""

    model_id: str
    new_version: str
    stages: List[Dict]  # [{"traffic": 0.1, "duration_hours": 24}, ...]
    rollback_threshold: Dict  # {"error_rate": 0.05, "latency_increase_pct": 50}
    current_stage: int = 0
    started_at: Optional[datetime] = None


class VersionManager:
    """Manages model version deployments and A/B testing.

    Features:
    - Traffic splitting between versions
    - Consistent customer cohort assignment
    - Gradual rollout with automatic rollback
    - Version performance comparison
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize version manager.

        Args:
            db_session: Database session for persistence
        """
        self.db = db_session
        self._deployments_cache: Dict[str, List[ModelDeployment]] = {}
        self._cohorts_cache: Dict[tuple, str] = {}  # (customer_id, model_id) -> version

    async def create_deployment(
        self,
        model_id: str,
        version: str,
        traffic_weight: float = 0.0,
        status: str = "canary"
    ) -> str:
        """Create a new model version deployment.

        Args:
            model_id: Base model identifier
            version: Version string
            traffic_weight: Initial traffic percentage (0.0-1.0)
            status: Deployment status

        Returns:
            Deployment ID
        """
        # Validate model exists
        try:
            model_config = ModelRegistry.get_model(f"{model_id}-{version}")
        except ValueError:
            # If exact version not in registry, validate base model exists
            base_models = ModelRegistry.get_model_versions(model_id)
            if not base_models:
                raise ValueError(f"Model {model_id} not found in registry")

        deployment_id = f"{model_id}-{version}-{int(datetime.utcnow().timestamp())}"

        # Create deployment record (would insert to DB in production)
        deployment = ModelDeployment(
            deployment_id=deployment_id,
            model_id=model_id,
            version=version,
            traffic_weight=traffic_weight,
            status=status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Cache deployment
        if model_id not in self._deployments_cache:
            self._deployments_cache[model_id] = []
        self._deployments_cache[model_id].append(deployment)

        logger.info(
            f"Created deployment {deployment_id} with {traffic_weight*100}% traffic"
        )

        return deployment_id

    async def update_traffic_split(
        self,
        model_id: str,
        version_weights: Dict[str, float]
    ) -> None:
        """Update traffic distribution across versions.

        Args:
            model_id: Base model identifier
            version_weights: Dict mapping version to weight (must sum to 1.0)

        Raises:
            ValueError: If weights don't sum to 1.0
        """
        # Validate weights sum to 1.0
        total_weight = sum(version_weights.values())
        if not (0.99 <= total_weight <= 1.01):  # Allow small floating point error
            raise ValueError(
                f"Traffic weights must sum to 1.0, got {total_weight}. "
                f"Weights: {version_weights}"
            )

        # Update deployments
        if model_id in self._deployments_cache:
            for deployment in self._deployments_cache[model_id]:
                if deployment.version in version_weights:
                    deployment.traffic_weight = version_weights[deployment.version]
                    deployment.updated_at = datetime.utcnow()
                    logger.info(
                        f"Updated {deployment.deployment_id} traffic to "
                        f"{deployment.traffic_weight*100:.1f}%"
                    )

        # Clear cohort cache to force re-assignment
        self._cohorts_cache.clear()

    async def route_by_version(
        self,
        model_id: str,
        customer_id: UUID,
        use_cohorts: bool = True
    ) -> str:
        """Route customer to a model version.

        Args:
            model_id: Base model identifier
            customer_id: Customer UUID
            use_cohorts: Use consistent cohort assignment (default: True)

        Returns:
            Full model ID (base-version)

        Raises:
            ValueError: If no active deployments
        """
        # Get active deployments
        deployments = await self._get_active_deployments(model_id)

        if not deployments:
            raise ValueError(f"No active deployments for model {model_id}")

        # Check cohort cache first
        cache_key = (customer_id, model_id)
        if use_cohorts and cache_key in self._cohorts_cache:
            version = self._cohorts_cache[cache_key]
            logger.debug(f"Customer {customer_id} assigned to {version} (cached)")
            return f"{model_id}-{version}"

        # Assign version based on traffic weights
        version = self._weighted_random_selection(deployments, customer_id, use_cohorts)

        # Cache assignment if using cohorts
        if use_cohorts:
            self._cohorts_cache[cache_key] = version

        logger.debug(f"Customer {customer_id} assigned to {model_id}-{version}")

        return f"{model_id}-{version}"

    def _weighted_random_selection(
        self,
        deployments: List[ModelDeployment],
        customer_id: UUID,
        use_cohorts: bool
    ) -> str:
        """Select version using weighted random selection.

        Args:
            deployments: List of active deployments
            customer_id: Customer UUID
            use_cohorts: Use deterministic selection for consistent cohorts

        Returns:
            Selected version
        """
        if use_cohorts:
            # Deterministic selection based on customer ID hash
            # This ensures same customer always gets same version (unless weights change)
            hash_value = int(
                hashlib.md5(str(customer_id).encode()).hexdigest()[:8],
                16
            )
            rand_value = (hash_value % 10000) / 10000.0  # 0.0 to 1.0
        else:
            # Pure random selection
            rand_value = random.random()

        # Weighted selection
        cumulative = 0.0
        for deployment in deployments:
            cumulative += deployment.traffic_weight
            if rand_value < cumulative:
                return deployment.version

        # Fallback to last deployment (shouldn't happen if weights sum to 1.0)
        return deployments[-1].version

    async def _get_active_deployments(
        self,
        model_id: str
    ) -> List[ModelDeployment]:
        """Get active deployments for a model.

        Args:
            model_id: Base model identifier

        Returns:
            List of active deployments sorted by traffic weight
        """
        # Check cache first
        if model_id in self._deployments_cache:
            active = [
                d for d in self._deployments_cache[model_id]
                if d.status in ['active', 'canary'] and d.traffic_weight > 0
            ]
            active.sort(key=lambda d: d.traffic_weight, reverse=True)
            return active

        # In production, would query database here
        # For now, return empty list
        return []

    async def compare_versions(
        self,
        model_id: str,
        baseline_version: str,
        candidate_version: str,
        time_window_hours: int = 24
    ) -> Dict[str, VersionMetrics]:
        """Compare performance metrics between two versions.

        Args:
            model_id: Base model identifier
            baseline_version: Baseline version (e.g., current production)
            candidate_version: Candidate version (e.g., new version being tested)
            time_window_hours: Time window for metrics collection

        Returns:
            Dict mapping version to metrics
        """
        # In production, would query inference logs from DB
        # For now, return mock data

        logger.info(
            f"Comparing {model_id} versions: "
            f"{baseline_version} (baseline) vs {candidate_version} (candidate)"
        )

        # Mock metrics
        baseline_metrics = VersionMetrics(
            version=baseline_version,
            inference_count=10000,
            avg_latency_ms=120.0,
            p95_latency_ms=250.0,
            success_rate=0.985,
            avg_safety_score=0.92,
            error_rate=0.015
        )

        candidate_metrics = VersionMetrics(
            version=candidate_version,
            inference_count=1000,  # 10% traffic
            avg_latency_ms=110.0,  # 8% faster
            p95_latency_ms=230.0,
            success_rate=0.988,  # 0.3% better
            avg_safety_score=0.94,  # 2% better
            error_rate=0.012,
            # Comparison to baseline
            latency_delta_pct=-8.3,
            success_rate_delta_pct=0.3,
            safety_score_delta_pct=2.2
        )

        return {
            baseline_version: baseline_metrics,
            candidate_version: candidate_metrics
        }

    async def create_rollout_plan(
        self,
        model_id: str,
        current_version: str,
        new_version: str,
        strategy: str = "conservative"
    ) -> RolloutPlan:
        """Create a gradual rollout plan for a new version.

        Args:
            model_id: Base model identifier
            current_version: Current production version
            new_version: New version to roll out
            strategy: Rollout strategy ('conservative', 'moderate', 'aggressive')

        Returns:
            RolloutPlan
        """
        # Define rollout strategies
        strategies = {
            "conservative": [
                {"traffic": 0.01, "duration_hours": 24},   # 1% for 1 day
                {"traffic": 0.05, "duration_hours": 24},   # 5% for 1 day
                {"traffic": 0.10, "duration_hours": 24},   # 10% for 1 day
                {"traffic": 0.25, "duration_hours": 48},   # 25% for 2 days
                {"traffic": 0.50, "duration_hours": 48},   # 50% for 2 days
                {"traffic": 1.00, "duration_hours": 0}     # 100% (complete)
            ],
            "moderate": [
                {"traffic": 0.05, "duration_hours": 12},
                {"traffic": 0.20, "duration_hours": 24},
                {"traffic": 0.50, "duration_hours": 24},
                {"traffic": 1.00, "duration_hours": 0}
            ],
            "aggressive": [
                {"traffic": 0.10, "duration_hours": 6},
                {"traffic": 0.50, "duration_hours": 12},
                {"traffic": 1.00, "duration_hours": 0}
            ]
        }

        stages = strategies.get(strategy, strategies["conservative"])

        # Define rollback thresholds
        rollback_threshold = {
            "error_rate": 0.05,           # 5% error rate triggers rollback
            "latency_increase_pct": 50,   # 50% latency increase
            "safety_score_decrease": 0.05 # 5% safety score decrease
        }

        plan = RolloutPlan(
            model_id=model_id,
            new_version=new_version,
            stages=stages,
            rollback_threshold=rollback_threshold
        )

        logger.info(
            f"Created {strategy} rollout plan for {model_id} "
            f"{current_version} -> {new_version} ({len(stages)} stages)"
        )

        return plan

    async def execute_rollout_stage(
        self,
        plan: RolloutPlan,
        check_health: bool = True
    ) -> Dict:
        """Execute next stage of rollout plan.

        Args:
            plan: Rollout plan
            check_health: Check version health before proceeding

        Returns:
            Status dict with stage info and metrics
        """
        if plan.current_stage >= len(plan.stages):
            return {
                "status": "completed",
                "message": "Rollout completed successfully"
            }

        current_stage = plan.stages[plan.current_stage]
        new_traffic = current_stage["traffic"]

        logger.info(
            f"Executing rollout stage {plan.current_stage + 1}/{len(plan.stages)}: "
            f"{new_traffic * 100}% traffic to {plan.new_version}"
        )

        # Health check if enabled
        if check_health and plan.current_stage > 0:
            health_ok = await self._check_version_health(plan)
            if not health_ok:
                logger.warning(
                    f"Health check failed for {plan.new_version}, "
                    f"aborting rollout"
                )
                return {
                    "status": "rollback",
                    "message": "Health check failed, rolling back",
                    "stage": plan.current_stage
                }

        # Update traffic split
        await self.update_traffic_split(
            plan.model_id,
            {
                plan.new_version: new_traffic,
                # Assuming two-version split for simplicity
                # Would need to handle multi-version scenarios in production
            }
        )

        # Update plan state
        if plan.started_at is None:
            plan.started_at = datetime.utcnow()
        plan.current_stage += 1

        return {
            "status": "success",
            "stage": plan.current_stage,
            "total_stages": len(plan.stages),
            "current_traffic": new_traffic,
            "next_stage_at": (
                datetime.utcnow() + timedelta(hours=current_stage["duration_hours"])
                if current_stage["duration_hours"] > 0
                else None
            )
        }

    async def _check_version_health(self, plan: RolloutPlan) -> bool:
        """Check if new version is healthy based on metrics.

        Args:
            plan: Rollout plan with health thresholds

        Returns:
            True if healthy, False if should rollback
        """
        # Get current metrics (would query from DB in production)
        # For now, simulate healthy metrics
        error_rate = 0.01  # 1% (below 5% threshold)
        latency_increase = 10  # 10% (below 50% threshold)
        safety_score_delta = 0.02  # +2% (above -5% threshold)

        thresholds = plan.rollback_threshold

        if error_rate > thresholds["error_rate"]:
            logger.warning(
                f"Error rate {error_rate*100}% exceeds threshold "
                f"{thresholds['error_rate']*100}%"
            )
            return False

        if latency_increase > thresholds["latency_increase_pct"]:
            logger.warning(
                f"Latency increase {latency_increase}% exceeds threshold "
                f"{thresholds['latency_increase_pct']}%"
            )
            return False

        if safety_score_delta < -thresholds["safety_score_decrease"]:
            logger.warning(
                f"Safety score decreased by {abs(safety_score_delta)*100}% "
                f"exceeds threshold {thresholds['safety_score_decrease']*100}%"
            )
            return False

        return True

    async def rollback_deployment(
        self,
        model_id: str,
        from_version: str,
        to_version: str
    ) -> None:
        """Rollback from one version to another.

        Args:
            model_id: Base model identifier
            from_version: Version to roll back from
            to_version: Version to roll back to
        """
        logger.warning(
            f"Rolling back {model_id} from {from_version} to {to_version}"
        )

        # Set new version to 0% traffic, old version to 100%
        await self.update_traffic_split(
            model_id,
            {
                from_version: 0.0,
                to_version: 1.0
            }
        )

        # Mark deployment as disabled
        if model_id in self._deployments_cache:
            for deployment in self._deployments_cache[model_id]:
                if deployment.version == from_version:
                    deployment.status = "disabled"
                    deployment.updated_at = datetime.utcnow()

    def get_customer_cohort(
        self,
        customer_id: UUID,
        model_id: str
    ) -> Optional[str]:
        """Get customer's assigned cohort for A/B test.

        Args:
            customer_id: Customer UUID
            model_id: Base model identifier

        Returns:
            Cohort name or None if not assigned
        """
        cache_key = (customer_id, model_id)
        if cache_key in self._cohorts_cache:
            version = self._cohorts_cache[cache_key]
            return f"cohort_{version}"
        return None

    async def get_deployment_stats(
        self,
        model_id: str
    ) -> List[Dict]:
        """Get deployment statistics for all versions.

        Args:
            model_id: Base model identifier

        Returns:
            List of deployment stats
        """
        deployments = self._deployments_cache.get(model_id, [])

        stats = []
        for deployment in deployments:
            stats.append({
                "deployment_id": deployment.deployment_id,
                "version": deployment.version,
                "traffic_weight": deployment.traffic_weight,
                "status": deployment.status,
                "total_inferences": deployment.total_inferences,
                "avg_latency_ms": deployment.avg_latency_ms,
                "success_rate": deployment.success_rate,
                "avg_safety_score": deployment.avg_safety_score,
                "created_at": deployment.created_at.isoformat(),
                "updated_at": deployment.updated_at.isoformat()
            })

        return stats
