"""VLA inference service with GPU queue management and batching."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import numpy as np
import torch
from PIL import Image

from src.core.config import settings
from src.core.constants import get_model_config
from src.services.model_loader import model_manager
from src.utils.action_processing import clip_action_to_limits, unnormalize_action
from src.utils.image_processing import preprocess_image

logger = logging.getLogger(__name__)


@dataclass
class InferenceRequest:
    """Internal inference request structure."""

    request_id: UUID
    model_id: str
    image: Image.Image
    instruction: str
    robot_type: str
    robot_config: Optional[Dict] = None
    timestamp: float = 0.0

    def __post_init__(self):
        """Set timestamp after initialization."""
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class InferenceResult:
    """Internal inference result structure."""

    request_id: UUID
    action: List[float]
    latency_ms: int
    queue_wait_ms: int
    inference_ms: int
    success: bool
    error: Optional[str] = None


class VLAInferenceService:
    """VLA inference service with async GPU queue management."""

    def __init__(self):
        """Initialize inference service."""
        self._queue: asyncio.Queue[InferenceRequest] = asyncio.Queue(
            maxsize=settings.inference_queue_max_size
        )
        self._results: Dict[UUID, InferenceResult] = {}
        self._workers: List[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        """Start inference workers."""
        if self._running:
            logger.warning("Inference service already running")
            return

        self._running = True
        logger.info(f"Starting {settings.inference_max_workers} inference workers")

        # Start worker tasks
        for i in range(settings.inference_max_workers):
            worker = asyncio.create_task(self._worker(worker_id=i))
            self._workers.append(worker)

        logger.info("Inference service started")

    async def stop(self) -> None:
        """Stop inference workers."""
        if not self._running:
            return

        logger.info("Stopping inference service")
        self._running = False

        # Cancel all workers
        for worker in self._workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()
        logger.info("Inference service stopped")

    async def _worker(self, worker_id: int) -> None:
        """Inference worker that processes requests from queue.

        Args:
            worker_id: Worker identifier
        """
        logger.info(f"Worker {worker_id} started")

        while self._running:
            try:
                # Wait for request with timeout
                try:
                    request = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                # Process request
                result = await self._process_request(request)

                # Store result
                self._results[request.request_id] = result

                # Mark task as done
                self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)

        logger.info(f"Worker {worker_id} stopped")

    async def _process_request(self, request: InferenceRequest) -> InferenceResult:
        """Process a single inference request.

        Args:
            request: Inference request

        Returns:
            Inference result
        """
        start_time = time.time()
        queue_wait_ms = int((start_time - request.timestamp) * 1000)

        try:
            # Get model and processor
            model = model_manager.get_model(request.model_id)
            processor = model_manager.get_processor(request.model_id)

            # Preprocess image
            model_config = get_model_config(request.model_id)
            image_size = model_config["image_size"]
            processed_image = preprocess_image(request.image, image_size)

            # Prepare input for model
            # Format instruction for OpenVLA
            if request.model_id == "openvla-7b":
                formatted_instruction = (
                    f"In: What action should the robot take to {request.instruction}?\nOut:"
                )
            else:
                formatted_instruction = request.instruction

            # Process inputs
            inputs = processor(
                text=formatted_instruction,
                images=processed_image,
                return_tensors="pt",
            )

            # Move to device
            if torch.cuda.is_available():
                inputs = inputs.to(model_manager.device)

            # Run inference
            inference_start = time.time()

            with torch.no_grad():
                outputs = model(**inputs)

            inference_ms = int((time.time() - inference_start) * 1000)

            # Extract action from outputs
            action = self._extract_action(outputs, request.model_id)

            # Un-normalize action
            if request.robot_config and "normalization_stats" in request.robot_config:
                action = unnormalize_action(
                    action,
                    custom_stats=request.robot_config["normalization_stats"],
                )
            else:
                action = unnormalize_action(action, robot_type=request.robot_type)

            # Clip to safe limits
            if request.robot_config and "velocity_limits" in request.robot_config:
                action = clip_action_to_limits(
                    action,
                    custom_limits={"velocity_limits": request.robot_config["velocity_limits"]},
                )
            else:
                action = clip_action_to_limits(action, robot_type=request.robot_type)

            # Calculate total latency
            total_latency_ms = int((time.time() - start_time) * 1000)

            return InferenceResult(
                request_id=request.request_id,
                action=action,
                latency_ms=total_latency_ms,
                queue_wait_ms=queue_wait_ms,
                inference_ms=inference_ms,
                success=True,
            )

        except Exception as e:
            logger.error(f"Inference failed: {e}", exc_info=True)
            total_latency_ms = int((time.time() - start_time) * 1000)

            return InferenceResult(
                request_id=request.request_id,
                action=[],
                latency_ms=total_latency_ms,
                queue_wait_ms=queue_wait_ms,
                inference_ms=0,
                success=False,
                error=str(e),
            )

    def _extract_action(self, outputs: Any, model_id: str) -> List[float]:
        """Extract action vector from model outputs.

        Args:
            outputs: Model outputs
            model_id: Model identifier

        Returns:
            Action vector (7-DoF)
        """
        if model_id == "openvla-7b":
            # OpenVLA outputs tokenized actions
            # Extract and decode tokens to action vector
            # For mock model, just return from output
            if hasattr(outputs, "action"):
                return outputs.action.tolist()

            # For real model, extract from logits
            logits = outputs.logits
            # Get predicted tokens (argmax)
            predicted_tokens = torch.argmax(logits, dim=-1)

            # Convert tokens to action (simplified - real implementation
            # would use proper de-tokenization)
            action = predicted_tokens[0, :7].float().cpu().numpy() / 128.0 - 1.0
            return action.tolist()

        else:
            # For other models, extract action directly
            if hasattr(outputs, "action"):
                return outputs.action.tolist()

            raise ValueError(f"Cannot extract action from model {model_id}")

    async def infer(
        self,
        model_id: str,
        image: Image.Image,
        instruction: str,
        robot_type: str = "franka_panda",
        robot_config: Optional[Dict] = None,
        timeout: float = 10.0,
    ) -> InferenceResult:
        """Submit inference request and wait for result.

        Args:
            model_id: Model identifier
            image: Input image
            instruction: Natural language instruction
            robot_type: Robot type
            robot_config: Optional robot configuration
            timeout: Timeout in seconds

        Returns:
            Inference result

        Raises:
            TimeoutError: If inference times out
            RuntimeError: If queue is full
        """
        # Create request
        request = InferenceRequest(
            request_id=uuid4(),
            model_id=model_id,
            image=image,
            instruction=instruction,
            robot_type=robot_type,
            robot_config=robot_config,
        )

        # Add to queue
        try:
            self._queue.put_nowait(request)
        except asyncio.QueueFull:
            raise RuntimeError("Inference queue is full. Please try again later.")

        # Wait for result with timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            if request.request_id in self._results:
                result = self._results.pop(request.request_id)
                return result

            await asyncio.sleep(0.01)  # Poll every 10ms

        raise TimeoutError(f"Inference timeout after {timeout}s")

    def get_queue_depth(self) -> int:
        """Get current queue depth.

        Returns:
            Number of requests in queue
        """
        return self._queue.qsize()


# Global inference service instance
inference_service = VLAInferenceService()


async def start_inference_service() -> None:
    """Start inference service during application startup."""
    await inference_service.start()


async def stop_inference_service() -> None:
    """Stop inference service during application shutdown."""
    await inference_service.stop()
