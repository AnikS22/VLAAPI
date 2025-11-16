"""Unit tests for Model Registry."""

import pytest

from src.core.model_registry import (
    ModelArchitecture,
    ModelConfig,
    ModelRegistry,
    ModelStatus,
)


class TestModelRegistry:
    """Test suite for ModelRegistry."""

    def test_get_model_by_id(self):
        """Test retrieving a model by ID."""
        model = ModelRegistry.get_model("openvla-7b-v1")

        assert model.model_id == "openvla-7b-v1"
        assert model.name == "OpenVLA 7B"
        assert model.version == "1.0.0"
        assert model.architecture == ModelArchitecture.PRISMATIC
        assert model.status == ModelStatus.PRODUCTION

    def test_get_nonexistent_model(self):
        """Test that retrieving non-existent model raises ValueError."""
        with pytest.raises(ValueError, match="not found in registry"):
            ModelRegistry.get_model("nonexistent-model")

    def test_list_all_models(self):
        """Test listing all models without filters."""
        models = ModelRegistry.list_models()

        assert len(models) >= 6  # At least 6 models configured
        model_ids = [m.model_id for m in models]
        assert "openvla-7b-v1" in model_ids
        assert "rt-1" in model_ids
        assert "octo-base" in model_ids

    def test_filter_by_status(self):
        """Test filtering models by status."""
        production_models = ModelRegistry.list_models(status=ModelStatus.PRODUCTION)

        assert len(production_models) > 0
        assert all(m.status == ModelStatus.PRODUCTION for m in production_models)

    def test_filter_by_robot_type(self):
        """Test filtering models by robot compatibility."""
        franka_models = ModelRegistry.list_models(robot_type="franka_panda")

        assert len(franka_models) > 0
        assert all("franka_panda" in m.supported_robots for m in franka_models)

    def test_filter_by_vram(self):
        """Test filtering models by VRAM requirement."""
        low_vram_models = ModelRegistry.list_models(max_vram_gb=12.0)

        assert len(low_vram_models) > 0
        assert all(m.min_vram_gb <= 12.0 for m in low_vram_models)

        # Octo-small should be included (8GB requirement)
        model_ids = [m.model_id for m in low_vram_models]
        assert "octo-small" in model_ids

        # RT-2 should be excluded (24GB requirement)
        assert "rt-2-base" not in model_ids

    def test_get_compatible_models(self):
        """Test getting models compatible with constraints."""
        models = ModelRegistry.get_compatible_models(
            robot_type="franka_panda",
            max_latency_ms=150,
            max_vram_gb=16.0,
            min_accuracy=0.80
        )

        assert len(models) > 0

        # Verify all constraints are met
        for model in models:
            assert "franka_panda" in model.supported_robots
            assert model.expected_latency_p95_ms <= 150
            assert model.min_vram_gb <= 16.0
            if model.accuracy_benchmark:
                assert model.accuracy_benchmark >= 0.80

    def test_get_fastest_model(self):
        """Test getting fastest model for robot type."""
        fastest = ModelRegistry.get_fastest_model("franka_panda")

        assert fastest is not None
        assert "franka_panda" in fastest.supported_robots

        # Should be octo-small (60ms latency)
        assert fastest.model_id == "octo-small"
        assert fastest.expected_latency_p50_ms == 60.0

    def test_get_cheapest_model(self):
        """Test getting cheapest model for robot type."""
        cheapest = ModelRegistry.get_cheapest_model("franka_panda")

        assert cheapest is not None
        assert "franka_panda" in cheapest.supported_robots

        # Should be octo-small ($0.0005 per 1k)
        assert cheapest.model_id == "octo-small"
        assert cheapest.cost_per_1k == 0.0005

    def test_get_most_accurate_model(self):
        """Test getting most accurate model for robot type."""
        most_accurate = ModelRegistry.get_most_accurate_model("franka_panda")

        assert most_accurate is not None
        assert "franka_panda" in most_accurate.supported_robots
        assert most_accurate.accuracy_benchmark is not None

        # RT-2 should be most accurate for franka_panda (0.90)
        assert most_accurate.model_id == "rt-2-base"
        assert most_accurate.accuracy_benchmark == 0.90

    def test_model_exists(self):
        """Test checking if model exists."""
        assert ModelRegistry.model_exists("openvla-7b-v1") is True
        assert ModelRegistry.model_exists("nonexistent") is False

    def test_get_model_versions(self):
        """Test getting all versions of a model."""
        versions = ModelRegistry.get_model_versions("openvla-7b")

        assert len(versions) == 2
        assert versions[0].model_id == "openvla-7b-v2"  # Newest first
        assert versions[1].model_id == "openvla-7b-v1"

    def test_model_metadata_completeness(self):
        """Test that all models have complete metadata."""
        models = ModelRegistry.list_models()

        for model in models:
            # Required fields
            assert model.model_id
            assert model.name
            assert model.version
            assert model.architecture
            assert model.hf_model_id

            # Hardware requirements
            assert model.size_gb > 0
            assert model.min_vram_gb > 0
            assert model.recommended_vram_gb >= model.min_vram_gb

            # Performance metrics
            assert model.expected_latency_p50_ms > 0
            assert model.expected_latency_p95_ms >= model.expected_latency_p50_ms
            assert model.expected_throughput_rps > 0
            assert model.cost_per_1k >= 0

            # Capabilities
            assert len(model.supported_robots) > 0
            assert model.action_dim > 0
            assert len(model.training_datasets) > 0

    def test_combined_filters(self):
        """Test applying multiple filters together."""
        models = ModelRegistry.list_models(
            status=ModelStatus.PRODUCTION,
            robot_type="franka_panda",
            max_vram_gb=20.0
        )

        assert len(models) > 0

        for model in models:
            assert model.status == ModelStatus.PRODUCTION
            assert "franka_panda" in model.supported_robots
            assert model.min_vram_gb <= 20.0

    def test_architecture_diversity(self):
        """Test that registry contains diverse architectures."""
        models = ModelRegistry.list_models()

        architectures = {m.architecture for m in models}

        # Should have at least 3 different architectures
        assert len(architectures) >= 3
        assert ModelArchitecture.PRISMATIC in architectures
        assert ModelArchitecture.RT_1 in architectures
        assert ModelArchitecture.OCTO in architectures

    def test_robot_compatibility_matrix(self):
        """Test robot compatibility across models."""
        # Franka Panda should be widely supported
        franka_models = ModelRegistry.list_models(robot_type="franka_panda")
        assert len(franka_models) >= 4

        # KUKA should be less common
        kuka_models = ModelRegistry.list_models(robot_type="kuka_iiwa7")
        assert len(kuka_models) >= 2

    def test_performance_tiers(self):
        """Test that models span different performance tiers."""
        models = ModelRegistry.list_models(status=ModelStatus.PRODUCTION)

        latencies = [m.expected_latency_p50_ms for m in models]

        # Should have fast (<100ms), medium (100-150ms), and slower models
        assert any(lat < 100 for lat in latencies)  # Fast
        assert any(100 <= lat <= 150 for lat in latencies)  # Medium
        assert any(lat > 150 for lat in latencies)  # Slower but more capable

    def test_cost_tiers(self):
        """Test that models span different cost tiers."""
        models = ModelRegistry.list_models(status=ModelStatus.PRODUCTION)

        costs = [m.cost_per_1k for m in models]

        # Should have cheap (<0.001), medium, and premium models
        assert any(cost < 0.001 for cost in costs)
        assert any(cost >= 0.001 for cost in costs)


class TestModelConfig:
    """Test suite for ModelConfig dataclass."""

    def test_model_config_creation(self):
        """Test creating a ModelConfig instance."""
        config = ModelConfig(
            model_id="test-model",
            name="Test Model",
            version="1.0.0",
            architecture=ModelArchitecture.CUSTOM,
            hf_model_id="test/model",
            size_gb=10.0,
            min_vram_gb=12.0,
            recommended_vram_gb=16.0,
            expected_latency_p50_ms=100.0,
            expected_latency_p95_ms=200.0,
            expected_throughput_rps=10.0,
            cost_per_1k=0.001,
            supported_robots=["franka_panda"],
            max_image_size=(224, 224),
            action_dim=7,
            training_datasets=["test_dataset"]
        )

        assert config.model_id == "test-model"
        assert config.architecture == ModelArchitecture.CUSTOM
        assert config.min_vram_gb == 12.0


class TestModelStatus:
    """Test suite for ModelStatus enum."""

    def test_status_values(self):
        """Test ModelStatus enum values."""
        assert ModelStatus.PRODUCTION.value == "production"
        assert ModelStatus.BETA.value == "beta"
        assert ModelStatus.DEPRECATED.value == "deprecated"
        assert ModelStatus.EXPERIMENTAL.value == "experimental"


class TestModelArchitecture:
    """Test suite for ModelArchitecture enum."""

    def test_architecture_values(self):
        """Test ModelArchitecture enum values."""
        assert ModelArchitecture.PRISMATIC.value == "prismatic"
        assert ModelArchitecture.RT_1.value == "rt-1"
        assert ModelArchitecture.RT_2.value == "rt-2"
        assert ModelArchitecture.OCTO.value == "octo"
        assert ModelArchitecture.CUSTOM.value == "custom"
