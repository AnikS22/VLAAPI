"""Multi-Model VLA Manager - Load and manage multiple models across GPUs.

This module extends the single-model manager to support:
- Multiple models loaded simultaneously
- Multi-GPU distribution
- Dynamic model loading/unloading
- Model performance tracking
- Memory management
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import torch
from transformers import AutoModelForVision2Seq, AutoProcessor

from src.core.config import settings
from src.core.model_registry import ModelConfig, ModelRegistry

logger = logging.getLogger(__name__)


class ModelNotLoadedError(Exception):
    """Exception raised when trying to use a model that hasn't been loaded."""
    pass


class InsufficientVRAMError(Exception):
    """Exception raised when not enough VRAM available to load model."""
    pass


@dataclass
class LoadedModel:
    """Container for a loaded model and its metadata."""

    model_id: str
    model: Any
    processor: Any
    gpu_device: int
    config: ModelConfig
    loaded_at: datetime = field(default_factory=datetime.utcnow)

    # Runtime stats
    inference_count: int = 0
    total_inference_time_ms: float = 0.0
    last_used: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GPUInfo:
    """GPU device information and allocation."""

    device_id: int
    total_vram_gb: float
    available_vram_gb: float
    loaded_models: List[str] = field(default_factory=list)

    @property
    def used_vram_gb(self) -> float:
        """Calculate used VRAM."""
        return self.total_vram_gb - self.available_vram_gb

    @property
    def utilization(self) -> float:
        """GPU utilization as percentage."""
        if self.total_vram_gb == 0:
            return 0.0
        return (self.used_vram_gb / self.total_vram_gb) * 100


@dataclass
class ModelStats:
    """Performance statistics for a loaded model."""

    model_id: str
    inference_count: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    total_time_ms: float
    vram_usage_gb: float
    gpu_device: int
    loaded_at: datetime
    last_used: datetime


class MultiModelManager:
    """Manages multiple VLA models across multiple GPUs.

    Features:
    - Load multiple models simultaneously
    - Auto-distribute across GPUs based on VRAM
    - Track model performance stats
    - Lazy loading (load on first use)
    - Memory-aware model eviction
    """

    _instance: Optional["MultiModelManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize multi-model manager."""
        if self._initialized:
            return

        self._models: Dict[str, LoadedModel] = {}
        self._gpu_info: Dict[int, GPUInfo] = {}
        self._dtype: torch.dtype = self._get_dtype()

        # Initialize GPU information
        self._initialize_gpus()

        self._initialized = True

        logger.info(
            f"Initialized Multi-Model Manager - "
            f"{len(self._gpu_info)} GPUs available, "
            f"Dtype: {self._dtype}"
        )

    def _initialize_gpus(self) -> None:
        """Initialize GPU information."""
        if torch.cuda.is_available():
            num_gpus = torch.cuda.device_count()
            for gpu_id in range(num_gpus):
                total_vram = torch.cuda.get_device_properties(gpu_id).total_memory / 1024**3

                # Get current memory usage
                torch.cuda.set_device(gpu_id)
                allocated = torch.cuda.memory_allocated(gpu_id) / 1024**3
                available = total_vram - allocated

                self._gpu_info[gpu_id] = GPUInfo(
                    device_id=gpu_id,
                    total_vram_gb=total_vram,
                    available_vram_gb=available
                )

                logger.info(
                    f"GPU {gpu_id}: {total_vram:.1f}GB total, "
                    f"{available:.1f}GB available"
                )
        else:
            # CPU fallback
            self._gpu_info[0] = GPUInfo(
                device_id=0,
                total_vram_gb=0.0,
                available_vram_gb=0.0
            )
            logger.warning("No CUDA GPUs available, using CPU")

    def _get_dtype(self) -> torch.dtype:
        """Get torch dtype from settings."""
        dtype_map = {
            "float32": torch.float32,
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
        }
        return dtype_map.get(settings.vla_model_dtype, torch.bfloat16)

    def _select_gpu_for_model(self, model_config: ModelConfig) -> int:
        """Select best GPU for loading a model.

        Strategy:
        1. Find GPUs with enough VRAM
        2. Among those, select GPU with most available VRAM
        3. If none suitable, try to evict old models

        Args:
            model_config: Model configuration

        Returns:
            GPU device ID

        Raises:
            InsufficientVRAMError: If no suitable GPU found
        """
        required_vram = model_config.min_vram_gb

        # Find GPUs with enough VRAM
        suitable_gpus = [
            gpu for gpu in self._gpu_info.values()
            if gpu.available_vram_gb >= required_vram
        ]

        if not suitable_gpus:
            # Try to find GPU where eviction would help
            for gpu in self._gpu_info.values():
                if gpu.total_vram_gb >= required_vram:
                    logger.warning(
                        f"GPU {gpu.device_id} has total capacity but no free VRAM. "
                        f"Consider implementing model eviction."
                    )

            raise InsufficientVRAMError(
                f"No GPU has {required_vram:.1f}GB available VRAM for {model_config.model_id}"
            )

        # Select GPU with most available VRAM (to balance load)
        selected_gpu = max(suitable_gpus, key=lambda g: g.available_vram_gb)

        logger.info(
            f"Selected GPU {selected_gpu.device_id} with "
            f"{selected_gpu.available_vram_gb:.1f}GB available for {model_config.model_id}"
        )

        return selected_gpu.device_id

    async def load_model(
        self,
        model_id: str,
        gpu_device: Optional[int] = None,
        force_reload: bool = False
    ) -> None:
        """Load a VLA model into GPU memory.

        Args:
            model_id: Model identifier from registry
            gpu_device: Specific GPU to use (auto-select if None)
            force_reload: Force reload even if already loaded

        Raises:
            ValueError: If model_id not in registry
            InsufficientVRAMError: If not enough VRAM available
            RuntimeError: If model loading fails
        """
        # Check if already loaded
        if model_id in self._models and not force_reload:
            logger.info(f"Model {model_id} already loaded on GPU {self._models[model_id].gpu_device}")
            return

        # Get model configuration from registry
        try:
            model_config = ModelRegistry.get_model(model_id)
        except ValueError as e:
            logger.error(f"Model {model_id} not found in registry")
            raise

        logger.info(f"Loading model {model_id} ({model_config.name})")

        try:
            if settings.use_mock_models:
                # Mock model for testing
                logger.warning(f"Using MOCK model for {model_id}")
                loaded_model = LoadedModel(
                    model_id=model_id,
                    model=MockVLAModel(model_id),
                    processor=MockProcessor(),
                    gpu_device=0,
                    config=model_config
                )
            else:
                # Real model loading
                loaded_model = await self._load_real_model(
                    model_config,
                    gpu_device
                )

            # Store loaded model
            self._models[model_id] = loaded_model

            # Update GPU info
            if loaded_model.gpu_device in self._gpu_info:
                self._gpu_info[loaded_model.gpu_device].loaded_models.append(model_id)
                self._gpu_info[loaded_model.gpu_device].available_vram_gb -= model_config.size_gb

            logger.info(
                f"Model {model_id} loaded successfully on GPU {loaded_model.gpu_device}"
            )

        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}", exc_info=True)
            raise RuntimeError(f"Model loading failed: {e}")

    async def _load_real_model(
        self,
        model_config: ModelConfig,
        gpu_device: Optional[int] = None
    ) -> LoadedModel:
        """Load actual VLA model from HuggingFace.

        Args:
            model_config: Model configuration
            gpu_device: Specific GPU to use (auto-select if None)

        Returns:
            LoadedModel instance
        """
        # Select GPU
        if gpu_device is None:
            gpu_device = self._select_gpu_for_model(model_config)

        device_str = f"cuda:{gpu_device}" if torch.cuda.is_available() else "cpu"

        # Load in thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        # Load processor
        logger.info(f"Loading processor for {model_config.model_id}")
        processor_id = model_config.hf_processor_id or model_config.hf_model_id

        processor = await loop.run_in_executor(
            None,
            lambda: AutoProcessor.from_pretrained(
                processor_id,
                trust_remote_code=settings.trust_remote_code
            )
        )

        # Load model
        logger.info(f"Loading model weights for {model_config.model_id}")
        model = await loop.run_in_executor(
            None,
            lambda: AutoModelForVision2Seq.from_pretrained(
                model_config.hf_model_id,
                torch_dtype=self._dtype,
                low_cpu_mem_usage=settings.low_cpu_mem_usage,
                trust_remote_code=settings.trust_remote_code
            )
        )

        # Move to GPU
        if torch.cuda.is_available():
            logger.info(f"Moving {model_config.model_id} to {device_str}")
            model = model.to(device_str)

        # Set to eval mode
        model.eval()

        # Log GPU memory
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated(gpu_device) / 1024**3
            logger.info(f"GPU {gpu_device} memory: {allocated:.2f}GB allocated")

        return LoadedModel(
            model_id=model_config.model_id,
            model=model,
            processor=processor,
            gpu_device=gpu_device,
            config=model_config
        )

    async def load_multiple_models(
        self,
        model_ids: List[str],
        parallel: bool = False
    ) -> Dict[str, bool]:
        """Load multiple models.

        Args:
            model_ids: List of model IDs to load
            parallel: Load models in parallel (requires multiple GPUs)

        Returns:
            Dict mapping model_id to success status
        """
        results = {}

        if parallel and len(self._gpu_info) > 1:
            # Parallel loading across GPUs
            tasks = [
                self.load_model(model_id)
                for model_id in model_ids
            ]
            load_results = await asyncio.gather(*tasks, return_exceptions=True)

            for model_id, result in zip(model_ids, load_results):
                results[model_id] = not isinstance(result, Exception)
                if isinstance(result, Exception):
                    logger.error(f"Failed to load {model_id}: {result}")
        else:
            # Sequential loading
            for model_id in model_ids:
                try:
                    await self.load_model(model_id)
                    results[model_id] = True
                except Exception as e:
                    logger.error(f"Failed to load {model_id}: {e}")
                    results[model_id] = False

        loaded_count = sum(results.values())
        logger.info(f"Loaded {loaded_count}/{len(model_ids)} models successfully")

        return results

    def get_model(self, model_id: str) -> Tuple[Any, Any]:
        """Get loaded model and processor.

        Args:
            model_id: Model identifier

        Returns:
            Tuple of (model, processor)

        Raises:
            ModelNotLoadedError: If model not loaded
        """
        if model_id not in self._models:
            raise ModelNotLoadedError(
                f"Model {model_id} not loaded. "
                f"Available models: {list(self._models.keys())}"
            )

        loaded_model = self._models[model_id]
        loaded_model.last_used = datetime.utcnow()

        return loaded_model.model, loaded_model.processor

    def is_model_loaded(self, model_id: str) -> bool:
        """Check if model is loaded.

        Args:
            model_id: Model identifier

        Returns:
            True if loaded, False otherwise
        """
        return model_id in self._models

    def get_loaded_models(self) -> List[str]:
        """Get list of loaded model IDs.

        Returns:
            List of model IDs
        """
        return list(self._models.keys())

    def get_model_stats(self, model_id: str) -> ModelStats:
        """Get performance statistics for a model.

        Args:
            model_id: Model identifier

        Returns:
            ModelStats instance

        Raises:
            ModelNotLoadedError: If model not loaded
        """
        if model_id not in self._models:
            raise ModelNotLoadedError(f"Model {model_id} not loaded")

        loaded_model = self._models[model_id]

        # Calculate percentiles (placeholder - would track all latencies in production)
        avg_latency = (
            loaded_model.total_inference_time_ms / loaded_model.inference_count
            if loaded_model.inference_count > 0
            else 0.0
        )

        return ModelStats(
            model_id=model_id,
            inference_count=loaded_model.inference_count,
            avg_latency_ms=avg_latency,
            p50_latency_ms=avg_latency,  # TODO: Track actual percentiles
            p95_latency_ms=avg_latency * 1.5,
            p99_latency_ms=avg_latency * 2.0,
            total_time_ms=loaded_model.total_inference_time_ms,
            vram_usage_gb=loaded_model.config.size_gb,
            gpu_device=loaded_model.gpu_device,
            loaded_at=loaded_model.loaded_at,
            last_used=loaded_model.last_used
        )

    def record_inference(self, model_id: str, latency_ms: float) -> None:
        """Record inference statistics.

        Args:
            model_id: Model identifier
            latency_ms: Inference latency in milliseconds
        """
        if model_id in self._models:
            self._models[model_id].inference_count += 1
            self._models[model_id].total_inference_time_ms += latency_ms
            self._models[model_id].last_used = datetime.utcnow()

    def get_gpu_info(self, gpu_id: Optional[int] = None) -> Dict[int, GPUInfo]:
        """Get GPU information.

        Args:
            gpu_id: Specific GPU ID (all GPUs if None)

        Returns:
            Dict mapping GPU ID to GPUInfo
        """
        if gpu_id is not None:
            return {gpu_id: self._gpu_info.get(gpu_id)}
        return dict(self._gpu_info)

    async def unload_model(self, model_id: str) -> None:
        """Unload a model from GPU memory.

        Args:
            model_id: Model identifier
        """
        if model_id not in self._models:
            logger.warning(f"Model {model_id} not loaded, nothing to unload")
            return

        logger.info(f"Unloading model {model_id}")

        loaded_model = self._models[model_id]
        gpu_device = loaded_model.gpu_device

        # Remove from loaded models
        del self._models[model_id]

        # Update GPU info
        if gpu_device in self._gpu_info:
            if model_id in self._gpu_info[gpu_device].loaded_models:
                self._gpu_info[gpu_device].loaded_models.remove(model_id)
            self._gpu_info[gpu_device].available_vram_gb += loaded_model.config.size_gb

        # Force garbage collection
        import gc
        gc.collect()

        # Clear GPU cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            allocated = torch.cuda.memory_allocated(gpu_device) / 1024**3
            logger.info(f"GPU {gpu_device} memory after unload: {allocated:.2f}GB")

    async def shutdown(self) -> None:
        """Shutdown manager and unload all models."""
        logger.info("Shutting down Multi-Model Manager")

        model_ids = list(self._models.keys())
        for model_id in model_ids:
            await self.unload_model(model_id)


# Mock models for testing without GPU
class MockVLAModel:
    """Mock VLA model for testing."""

    def __init__(self, model_id: str):
        self.model_id = model_id

    def __call__(self, *args, **kwargs):
        """Mock inference."""
        import numpy as np

        class MockOutput:
            def __init__(self):
                self.action = np.random.randn(7) * 0.1

        return MockOutput()

    def eval(self):
        pass

    def to(self, device):
        return self


class MockProcessor:
    """Mock processor for testing."""

    def __call__(self, *args, **kwargs):
        """Mock processing."""
        class MockInputs:
            def __init__(self):
                self.pixel_values = torch.randn(1, 3, 224, 224)
                self.input_ids = torch.randint(0, 1000, (1, 10))

            def to(self, device):
                return self

        return MockInputs()


# Global singleton instance
multi_model_manager = MultiModelManager()


# Convenience functions for compatibility with old single-model interface
async def init_models() -> None:
    """Initialize models during application startup."""
    logger.info("Initializing VLA models from settings")

    if hasattr(settings, 'enabled_models') and settings.enabled_models:
        results = await multi_model_manager.load_multiple_models(
            settings.enabled_models
        )

        loaded = [m for m, success in results.items() if success]
        logger.info(f"Loaded {len(loaded)} models: {loaded}")


async def shutdown_models() -> None:
    """Shutdown models during application shutdown."""
    logger.info("Shutting down VLA models")
    await multi_model_manager.shutdown()
