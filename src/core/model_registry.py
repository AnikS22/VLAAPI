"""VLA Model Registry - Central catalog of available models.

This module maintains metadata for all supported VLA models including:
- HuggingFace model IDs
- Hardware requirements (VRAM, compute)
- Expected performance (latency, throughput)
- Robot compatibility
- Cost and availability status
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class ModelStatus(str, Enum):
    """Model availability status."""
    PRODUCTION = "production"
    BETA = "beta"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


class ModelArchitecture(str, Enum):
    """VLA model architectures."""
    PRISMATIC = "prismatic"  # OpenVLA
    RT_1 = "rt-1"  # Google RT-1
    RT_2 = "rt-2"  # Google RT-2
    OCTO = "octo"  # Octo
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """Configuration for a VLA model."""

    # Identity
    model_id: str
    name: str
    version: str
    architecture: ModelArchitecture

    # HuggingFace
    hf_model_id: str
    hf_processor_id: Optional[str] = None  # If different from model

    # Hardware requirements
    size_gb: float
    min_vram_gb: float
    recommended_vram_gb: float
    requires_fp16: bool = True
    supports_bf16: bool = True
    supports_4bit: bool = False
    supports_8bit: bool = False

    # Performance expectations
    expected_latency_p50_ms: float
    expected_latency_p95_ms: float
    expected_throughput_rps: float  # Requests per second

    # Cost (per 1000 inferences)
    cost_per_1k: float

    # Capabilities
    supported_robots: List[str]
    max_image_size: tuple  # (height, width)
    action_dim: int  # Action dimensions (usually 7 for 6-DoF + gripper)

    # Training info
    training_datasets: List[str]
    accuracy_benchmark: Optional[float] = None  # If available

    # Availability
    status: ModelStatus = ModelStatus.PRODUCTION
    release_date: Optional[str] = None
    deprecation_date: Optional[str] = None


class ModelRegistry:
    """Central registry of all available VLA models."""

    # Model catalog
    MODELS: Dict[str, ModelConfig] = {

        # OpenVLA 7B (v1.0)
        "openvla-7b-v1": ModelConfig(
            model_id="openvla-7b-v1",
            name="OpenVLA 7B",
            version="1.0.0",
            architecture=ModelArchitecture.PRISMATIC,
            hf_model_id="openvla/openvla-7b-prismatic",
            size_gb=14.0,
            min_vram_gb=16.0,
            recommended_vram_gb=20.0,
            requires_fp16=False,
            supports_bf16=True,
            supports_4bit=True,
            supports_8bit=True,
            expected_latency_p50_ms=120.0,
            expected_latency_p95_ms=250.0,
            expected_throughput_rps=8.0,
            cost_per_1k=0.001,
            supported_robots=[
                "franka_panda",
                "franka_fr3",
                "universal_robots_ur5e",
                "kinova_gen3",
                "abb_yumi"
            ],
            max_image_size=(224, 224),
            action_dim=7,
            training_datasets=["bridge_v2", "fractal"],
            accuracy_benchmark=0.85,
            status=ModelStatus.PRODUCTION,
            release_date="2024-01-15"
        ),

        # OpenVLA 7B (v2.0 - improved)
        "openvla-7b-v2": ModelConfig(
            model_id="openvla-7b-v2",
            name="OpenVLA 7B v2",
            version="2.0.0",
            architecture=ModelArchitecture.PRISMATIC,
            hf_model_id="openvla/openvla-7b-v2",
            size_gb=14.0,
            min_vram_gb=16.0,
            recommended_vram_gb=20.0,
            supports_bf16=True,
            supports_4bit=True,
            supports_8bit=True,
            expected_latency_p50_ms=110.0,
            expected_latency_p95_ms=230.0,
            expected_throughput_rps=9.0,
            cost_per_1k=0.0012,
            supported_robots=[
                "franka_panda",
                "franka_fr3",
                "universal_robots_ur5e",
                "kinova_gen3",
                "abb_yumi",
                "kuka_iiwa7"
            ],
            max_image_size=(224, 224),
            action_dim=7,
            training_datasets=["bridge_v2", "fractal", "oxe"],
            accuracy_benchmark=0.88,
            status=ModelStatus.BETA,
            release_date="2024-09-01"
        ),

        # Google RT-1
        "rt-1": ModelConfig(
            model_id="rt-1",
            name="RT-1 (Robotics Transformer 1)",
            version="1.0.0",
            architecture=ModelArchitecture.RT_1,
            hf_model_id="google/rt-1-x",
            size_gb=8.5,
            min_vram_gb=12.0,
            recommended_vram_gb=16.0,
            supports_bf16=True,
            supports_4bit=True,
            expected_latency_p50_ms=90.0,
            expected_latency_p95_ms=180.0,
            expected_throughput_rps=11.0,
            cost_per_1k=0.0008,
            supported_robots=[
                "franka_panda",
                "universal_robots_ur5e",
                "kinova_gen3"
            ],
            max_image_size=(300, 300),
            action_dim=7,
            training_datasets=["rt-1"],
            accuracy_benchmark=0.82,
            status=ModelStatus.PRODUCTION,
            release_date="2023-06-15"
        ),

        # Google RT-2
        "rt-2-base": ModelConfig(
            model_id="rt-2-base",
            name="RT-2 Base",
            version="1.0.0",
            architecture=ModelArchitecture.RT_2,
            hf_model_id="google/rt-2-base",
            size_gb=18.0,
            min_vram_gb=24.0,
            recommended_vram_gb=32.0,
            supports_bf16=True,
            supports_4bit=True,
            expected_latency_p50_ms=150.0,
            expected_latency_p95_ms=300.0,
            expected_throughput_rps=6.0,
            cost_per_1k=0.0015,
            supported_robots=[
                "franka_panda",
                "franka_fr3",
                "universal_robots_ur5e",
                "kinova_gen3",
                "abb_yumi",
                "kuka_iiwa7"
            ],
            max_image_size=(320, 320),
            action_dim=7,
            training_datasets=["rt-1", "rt-2"],
            accuracy_benchmark=0.90,
            status=ModelStatus.PRODUCTION,
            release_date="2023-12-01"
        ),

        # Octo Base
        "octo-base": ModelConfig(
            model_id="octo-base",
            name="Octo Base",
            version="1.0.0",
            architecture=ModelArchitecture.OCTO,
            hf_model_id="octo-models/octo-base",
            size_gb=12.0,
            min_vram_gb=16.0,
            recommended_vram_gb=20.0,
            supports_bf16=True,
            supports_4bit=True,
            supports_8bit=True,
            expected_latency_p50_ms=100.0,
            expected_latency_p95_ms=200.0,
            expected_throughput_rps=10.0,
            cost_per_1k=0.0009,
            supported_robots=[
                "franka_panda",
                "universal_robots_ur5e",
                "kinova_gen3",
                "abb_yumi"
            ],
            max_image_size=(256, 256),
            action_dim=7,
            training_datasets=["oxe"],
            accuracy_benchmark=0.87,
            status=ModelStatus.PRODUCTION,
            release_date="2024-03-15"
        ),

        # Octo Small (faster, less accurate)
        "octo-small": ModelConfig(
            model_id="octo-small",
            name="Octo Small",
            version="1.0.0",
            architecture=ModelArchitecture.OCTO,
            hf_model_id="octo-models/octo-small",
            size_gb=5.0,
            min_vram_gb=8.0,
            recommended_vram_gb=12.0,
            supports_bf16=True,
            supports_4bit=True,
            supports_8bit=True,
            expected_latency_p50_ms=60.0,
            expected_latency_p95_ms=120.0,
            expected_throughput_rps=16.0,
            cost_per_1k=0.0005,
            supported_robots=[
                "franka_panda",
                "universal_robots_ur5e",
                "kinova_gen3"
            ],
            max_image_size=(256, 256),
            action_dim=7,
            training_datasets=["oxe"],
            accuracy_benchmark=0.81,
            status=ModelStatus.PRODUCTION,
            release_date="2024-03-15"
        ),
    }

    @classmethod
    def get_model(cls, model_id: str) -> ModelConfig:
        """Get model configuration by ID.

        Args:
            model_id: Model identifier

        Returns:
            ModelConfig for the model

        Raises:
            ValueError: If model not found
        """
        if model_id not in cls.MODELS:
            available = ", ".join(cls.MODELS.keys())
            raise ValueError(
                f"Model '{model_id}' not found in registry. "
                f"Available models: {available}"
            )
        return cls.MODELS[model_id]

    @classmethod
    def list_models(
        cls,
        status: Optional[ModelStatus] = None,
        architecture: Optional[ModelArchitecture] = None,
        robot_type: Optional[str] = None,
        max_vram_gb: Optional[float] = None
    ) -> List[ModelConfig]:
        """List models with optional filtering.

        Args:
            status: Filter by model status
            architecture: Filter by architecture
            robot_type: Filter by robot compatibility
            max_vram_gb: Filter by maximum VRAM requirement

        Returns:
            List of matching model configurations
        """
        models = list(cls.MODELS.values())

        if status:
            models = [m for m in models if m.status == status]

        if architecture:
            models = [m for m in models if m.architecture == architecture]

        if robot_type:
            models = [m for m in models if robot_type in m.supported_robots]

        if max_vram_gb:
            models = [m for m in models if m.min_vram_gb <= max_vram_gb]

        return models

    @classmethod
    def get_compatible_models(
        cls,
        robot_type: str,
        max_latency_ms: Optional[float] = None,
        max_vram_gb: Optional[float] = None,
        min_accuracy: Optional[float] = None
    ) -> List[ModelConfig]:
        """Get models compatible with robot and constraints.

        Args:
            robot_type: Robot type identifier
            max_latency_ms: Maximum acceptable latency (p95)
            max_vram_gb: Maximum available VRAM
            min_accuracy: Minimum accuracy requirement

        Returns:
            List of compatible models sorted by performance
        """
        models = cls.list_models(
            status=ModelStatus.PRODUCTION,
            robot_type=robot_type,
            max_vram_gb=max_vram_gb
        )

        # Filter by latency
        if max_latency_ms:
            models = [m for m in models if m.expected_latency_p95_ms <= max_latency_ms]

        # Filter by accuracy
        if min_accuracy:
            models = [
                m for m in models
                if m.accuracy_benchmark and m.accuracy_benchmark >= min_accuracy
            ]

        # Sort by accuracy descending, latency ascending
        models.sort(
            key=lambda m: (
                -(m.accuracy_benchmark or 0),
                m.expected_latency_p50_ms
            )
        )

        return models

    @classmethod
    def get_fastest_model(cls, robot_type: str) -> ModelConfig:
        """Get fastest model for robot type.

        Args:
            robot_type: Robot type identifier

        Returns:
            Fastest compatible model
        """
        models = cls.list_models(
            status=ModelStatus.PRODUCTION,
            robot_type=robot_type
        )

        if not models:
            raise ValueError(f"No models available for robot type: {robot_type}")

        return min(models, key=lambda m: m.expected_latency_p50_ms)

    @classmethod
    def get_cheapest_model(cls, robot_type: str) -> ModelConfig:
        """Get cheapest model for robot type.

        Args:
            robot_type: Robot type identifier

        Returns:
            Cheapest compatible model
        """
        models = cls.list_models(
            status=ModelStatus.PRODUCTION,
            robot_type=robot_type
        )

        if not models:
            raise ValueError(f"No models available for robot type: {robot_type}")

        return min(models, key=lambda m: m.cost_per_1k)

    @classmethod
    def get_most_accurate_model(cls, robot_type: str) -> ModelConfig:
        """Get most accurate model for robot type.

        Args:
            robot_type: Robot type identifier

        Returns:
            Most accurate compatible model
        """
        models = cls.list_models(
            status=ModelStatus.PRODUCTION,
            robot_type=robot_type
        )

        if not models:
            raise ValueError(f"No models available for robot type: {robot_type}")

        # Filter models with benchmark scores
        models_with_scores = [m for m in models if m.accuracy_benchmark]

        if not models_with_scores:
            # Return first model if no benchmarks available
            return models[0]

        return max(models_with_scores, key=lambda m: m.accuracy_benchmark)

    @classmethod
    def model_exists(cls, model_id: str) -> bool:
        """Check if model exists in registry.

        Args:
            model_id: Model identifier

        Returns:
            True if model exists, False otherwise
        """
        return model_id in cls.MODELS

    @classmethod
    def get_model_versions(cls, base_model: str) -> List[ModelConfig]:
        """Get all versions of a model.

        Args:
            base_model: Base model name (e.g., "openvla-7b")

        Returns:
            List of model versions sorted by release date
        """
        versions = [
            m for m in cls.MODELS.values()
            if m.model_id.startswith(base_model)
        ]

        # Sort by release date descending (newest first)
        versions.sort(
            key=lambda m: m.release_date or "0000-00-00",
            reverse=True
        )

        return versions
