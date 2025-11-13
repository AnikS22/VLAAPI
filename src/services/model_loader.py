"""VLA model loader with singleton pattern for efficient GPU memory management."""

import asyncio
import logging
from typing import Any, Dict, Optional

import torch
from transformers import AutoModelForVision2Seq, AutoProcessor

from src.core.config import settings
from src.core.constants import SUPPORTED_VLA_MODELS, get_model_config

logger = logging.getLogger(__name__)


class ModelNotLoadedError(Exception):
    """Exception raised when trying to use a model that hasn't been loaded."""

    pass


class VLAModelManager:
    """Manages VLA model loading and lifecycle (Singleton pattern)."""

    _instance: Optional["VLAModelManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize model manager (called only once)."""
        if self._initialized:
            return

        self._models: Dict[str, Any] = {}
        self._processors: Dict[str, Any] = {}
        self._device: str = f"cuda:{settings.gpu_device}"  if torch.cuda.is_available() else "cpu"
        self._dtype: torch.dtype = self._get_dtype()
        self._initialized = True

        logger.info(
            f"Initialized VLA Model Manager - Device: {self._device}, Dtype: {self._dtype}"
        )

    def _get_dtype(self) -> torch.dtype:
        """Get torch dtype from settings.

        Returns:
            torch.dtype: Data type for model weights
        """
        dtype_map = {
            "float32": torch.float32,
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
        }
        return dtype_map.get(settings.vla_model_dtype, torch.bfloat16)

    async def load_model(self, model_id: str) -> None:
        """Load a VLA model into GPU memory.

        Args:
            model_id: Model identifier (e.g., 'openvla-7b', 'pi0')

        Raises:
            ValueError: If model_id is not supported
            RuntimeError: If model loading fails
        """
        if model_id in self._models:
            logger.info(f"Model {model_id} already loaded")
            return

        # Get model configuration
        try:
            model_config = get_model_config(model_id)
        except ValueError as e:
            logger.error(f"Unsupported model: {model_id}")
            raise

        logger.info(f"Loading model: {model_id} ({model_config['name']})")

        try:
            if settings.use_mock_models:
                # Mock model for testing without GPU
                logger.warning(f"Using MOCK model for {model_id}")
                self._models[model_id] = MockVLAModel(model_id)
                self._processors[model_id] = MockProcessor()
            else:
                # Load actual model
                await self._load_openvla_model(model_id, model_config)

            logger.info(f"Model {model_id} loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}", exc_info=True)
            raise RuntimeError(f"Model loading failed: {e}")

    async def _load_openvla_model(self, model_id: str, model_config: Dict) -> None:
        """Load OpenVLA model from HuggingFace.

        Args:
            model_id: Model identifier
            model_config: Model configuration dictionary
        """
        hf_model_id = model_config["model_id"]

        # Load in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        # Load processor
        logger.info(f"Loading processor for {model_id}")
        processor = await loop.run_in_executor(
            None,
            lambda: AutoProcessor.from_pretrained(
                hf_model_id,
                trust_remote_code=settings.trust_remote_code,
            ),
        )
        self._processors[model_id] = processor

        # Load model
        logger.info(f"Loading model weights for {model_id}")
        model = await loop.run_in_executor(
            None,
            lambda: AutoModelForVision2Seq.from_pretrained(
                hf_model_id,
                torch_dtype=self._dtype,
                low_cpu_mem_usage=settings.low_cpu_mem_usage,
                trust_remote_code=settings.trust_remote_code,
            ),
        )

        # Move model to GPU
        if torch.cuda.is_available():
            logger.info(f"Moving model {model_id} to {self._device}")
            model = model.to(self._device)

        # Set to evaluation mode
        model.eval()

        self._models[model_id] = model

        # Log GPU memory usage
        if torch.cuda.is_available():
            memory_allocated = torch.cuda.memory_allocated(settings.gpu_device) / 1024**3
            logger.info(f"GPU memory allocated: {memory_allocated:.2f} GB")

    async def load_all_enabled_models(self) -> None:
        """Load all models specified in settings.enabled_models."""
        logger.info(f"Loading enabled models: {settings.enabled_models}")

        for model_id in settings.enabled_models:
            try:
                await self.load_model(model_id)
            except Exception as e:
                logger.error(f"Failed to load model {model_id}: {e}")
                if settings.is_production:
                    raise  # Fail fast in production

    def get_model(self, model_id: str) -> Any:
        """Get loaded model by ID.

        Args:
            model_id: Model identifier

        Returns:
            Loaded model instance

        Raises:
            ModelNotLoadedError: If model not loaded
        """
        if model_id not in self._models:
            raise ModelNotLoadedError(
                f"Model {model_id} not loaded. Available models: {list(self._models.keys())}"
            )
        return self._models[model_id]

    def get_processor(self, model_id: str) -> Any:
        """Get model processor by ID.

        Args:
            model_id: Model identifier

        Returns:
            Model processor instance

        Raises:
            ModelNotLoadedError: If processor not loaded
        """
        if model_id not in self._processors:
            raise ModelNotLoadedError(f"Processor for {model_id} not loaded")
        return self._processors[model_id]

    def is_model_loaded(self, model_id: str) -> bool:
        """Check if model is loaded.

        Args:
            model_id: Model identifier

        Returns:
            True if model is loaded, False otherwise
        """
        return model_id in self._models

    def get_loaded_models(self) -> list[str]:
        """Get list of loaded model IDs.

        Returns:
            List of loaded model IDs
        """
        return list(self._models.keys())

    @property
    def device(self) -> str:
        """Get device being used for models.

        Returns:
            Device string (e.g., 'cuda:0', 'cpu')
        """
        return self._device

    @property
    def dtype(self) -> torch.dtype:
        """Get data type being used for models.

        Returns:
            torch.dtype
        """
        return self._dtype

    async def unload_model(self, model_id: str) -> None:
        """Unload a model from GPU memory.

        Args:
            model_id: Model identifier
        """
        if model_id not in self._models:
            logger.warning(f"Model {model_id} not loaded, nothing to unload")
            return

        logger.info(f"Unloading model: {model_id}")

        # Remove model and processor
        del self._models[model_id]
        del self._processors[model_id]

        # Force garbage collection
        import gc

        gc.collect()

        # Clear GPU cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            memory_allocated = torch.cuda.memory_allocated(settings.gpu_device) / 1024**3
            logger.info(f"GPU memory after unload: {memory_allocated:.2f} GB")

    async def shutdown(self) -> None:
        """Shutdown model manager and free all resources."""
        logger.info("Shutting down model manager")

        # Unload all models
        for model_id in list(self._models.keys()):
            await self.unload_model(model_id)


class MockVLAModel:
    """Mock VLA model for testing without GPU."""

    def __init__(self, model_id: str):
        """Initialize mock model.

        Args:
            model_id: Model identifier
        """
        self.model_id = model_id

    def __call__(self, *args, **kwargs):
        """Mock inference call.

        Returns:
            Mock output with random action vector
        """
        import numpy as np

        class MockOutput:
            """Mock model output."""

            def __init__(self):
                # Generate random 7-DoF action
                self.action = np.random.randn(7) * 0.1  # Small random actions

        return MockOutput()

    def eval(self):
        """Mock eval mode."""
        pass

    def to(self, device):
        """Mock device transfer."""
        return self


class MockProcessor:
    """Mock processor for testing."""

    def __call__(self, *args, **kwargs):
        """Mock processing."""
        import numpy as np

        class MockInputs:
            """Mock processed inputs."""

            def __init__(self):
                # Create fake tensors
                self.pixel_values = torch.randn(1, 3, 224, 224)
                self.input_ids = torch.randint(0, 1000, (1, 10))

            def to(self, device):
                """Mock device transfer."""
                return self

        return MockInputs()


# Global singleton instance
model_manager = VLAModelManager()


async def init_models() -> None:
    """Initialize models during application startup."""
    logger.info("Initializing VLA models")
    await model_manager.load_all_enabled_models()


async def shutdown_models() -> None:
    """Shutdown models during application shutdown."""
    logger.info("Shutting down VLA models")
    await model_manager.shutdown()
