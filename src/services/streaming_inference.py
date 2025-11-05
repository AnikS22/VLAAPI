"""Streaming VLA inference service for real-time robot control.

This service enables continuous inference from live video streams for
real-time robot control at 10-50Hz.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional
from uuid import UUID, uuid4

import numpy as np
from PIL import Image

from src.core.config import settings
from src.services.model_loader import model_manager
from src.services.safety_monitor import safety_monitor
from src.services.vla_inference import inference_service
from src.utils.action_processing import unnormalize_action

logger = logging.getLogger(__name__)


@dataclass
class StreamFrame:
    """Single frame in the streaming pipeline."""

    frame_id: int
    timestamp: float
    image: Image.Image
    instruction: str
    robot_state: Optional[Dict] = None


@dataclass
class StreamAction:
    """Action result from streaming inference."""

    frame_id: int
    timestamp: float
    action: List[float]
    safety_score: float
    latency_ms: int
    smoothed: bool = False


class ActionSmoother:
    """Smooth actions for continuous robot control."""

    def __init__(self, window_size: int = 3, alpha: float = 0.3):
        """Initialize action smoother.

        Args:
            window_size: Number of previous actions to consider
            alpha: Exponential smoothing factor (0 = no smoothing, 1 = no history)
        """
        self.window_size = window_size
        self.alpha = alpha
        self.history: Deque[List[float]] = deque(maxlen=window_size)

    def smooth(self, action: List[float]) -> List[float]:
        """Apply exponential moving average smoothing.

        Args:
            action: Raw action from model

        Returns:
            Smoothed action
        """
        if not self.history:
            # First action - no smoothing
            self.history.append(action)
            return action

        # Exponential moving average
        prev_action = self.history[-1]
        smoothed = [
            self.alpha * curr + (1 - self.alpha) * prev
            for curr, prev in zip(action, prev_action)
        ]

        self.history.append(smoothed)
        return smoothed

    def reset(self):
        """Reset smoother history."""
        self.history.clear()


class StreamingInferenceSession:
    """Manages a single streaming inference session."""

    def __init__(
        self,
        session_id: UUID,
        customer_id: UUID,
        model_id: str,
        robot_type: str = "franka_panda",
        target_fps: int = 10,
        enable_smoothing: bool = True,
        enable_safety: bool = True,
    ):
        """Initialize streaming session.

        Args:
            session_id: Unique session identifier
            customer_id: Customer UUID
            model_id: VLA model to use
            robot_type: Robot type
            target_fps: Target inference rate (Hz)
            enable_smoothing: Enable action smoothing
            enable_safety: Enable safety monitoring
        """
        self.session_id = session_id
        self.customer_id = customer_id
        self.model_id = model_id
        self.robot_type = robot_type
        self.target_fps = target_fps
        self.enable_smoothing = enable_smoothing
        self.enable_safety = enable_safety

        # Frame processing
        self.frame_queue: asyncio.Queue[StreamFrame] = asyncio.Queue(maxsize=30)
        self.action_queue: asyncio.Queue[StreamAction] = asyncio.Queue(maxsize=30)

        # Action smoothing
        self.smoother = ActionSmoother() if enable_smoothing else None

        # State
        self.is_running = False
        self.frame_counter = 0
        self.last_instruction = ""
        self.current_robot_state = None

        # Statistics
        self.total_frames = 0
        self.dropped_frames = 0
        self.avg_latency_ms = 0.0
        self.start_time = time.time()

        # Worker task
        self.worker_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start streaming inference worker."""
        if self.is_running:
            logger.warning(f"Session {self.session_id} already running")
            return

        self.is_running = True
        self.start_time = time.time()

        # Start worker
        self.worker_task = asyncio.create_task(self._inference_worker())

        logger.info(f"Streaming session {self.session_id} started (target: {self.target_fps} FPS)")

    async def stop(self):
        """Stop streaming inference worker."""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel worker
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        logger.info(
            f"Session {self.session_id} stopped - "
            f"Processed {self.total_frames} frames, "
            f"Dropped {self.dropped_frames} frames, "
            f"Avg latency: {self.avg_latency_ms:.1f}ms"
        )

    async def submit_frame(
        self,
        image: Image.Image,
        instruction: Optional[str] = None,
        robot_state: Optional[Dict] = None,
    ) -> int:
        """Submit a frame for inference.

        Args:
            image: Input image
            instruction: Optional instruction (uses last if not provided)
            robot_state: Optional robot state for safety checking

        Returns:
            Frame ID

        Raises:
            RuntimeError: If session not running or queue full
        """
        if not self.is_running:
            raise RuntimeError("Session not running")

        # Update instruction if provided
        if instruction:
            self.last_instruction = instruction

        # Update robot state
        if robot_state:
            self.current_robot_state = robot_state

        # Create frame
        frame = StreamFrame(
            frame_id=self.frame_counter,
            timestamp=time.time(),
            image=image,
            instruction=self.last_instruction,
            robot_state=robot_state,
        )

        self.frame_counter += 1

        # Try to add to queue
        try:
            self.frame_queue.put_nowait(frame)
            return frame.frame_id
        except asyncio.QueueFull:
            # Drop frame if queue full
            self.dropped_frames += 1
            logger.warning(
                f"Frame queue full - dropping frame {frame.frame_id} "
                f"(dropped: {self.dropped_frames}/{self.total_frames + 1})"
            )
            raise RuntimeError("Frame queue full - consider reducing FPS")

    async def get_action(self, timeout: float = 1.0) -> Optional[StreamAction]:
        """Get next action from inference.

        Args:
            timeout: Timeout in seconds

        Returns:
            StreamAction or None if timeout
        """
        try:
            action = await asyncio.wait_for(
                self.action_queue.get(),
                timeout=timeout,
            )
            return action
        except asyncio.TimeoutError:
            return None

    async def _inference_worker(self):
        """Background worker that processes frames."""
        logger.info(f"Inference worker started for session {self.session_id}")

        while self.is_running:
            try:
                # Get next frame with timeout
                try:
                    frame = await asyncio.wait_for(
                        self.frame_queue.get(),
                        timeout=0.1,
                    )
                except asyncio.TimeoutError:
                    continue

                self.total_frames += 1
                start_time = time.time()

                # Run inference
                result = await inference_service.infer(
                    model_id=self.model_id,
                    image=frame.image,
                    instruction=frame.instruction,
                    robot_type=self.robot_type,
                    timeout=5.0,
                )

                if not result.success:
                    logger.error(f"Inference failed: {result.error}")
                    continue

                action = result.action

                # Apply smoothing
                if self.smoother:
                    action = self.smoother.smooth(action)

                # Safety check
                safety_score = 1.0
                if self.enable_safety:
                    safety_result = safety_monitor.evaluate_action(
                        action=action,
                        robot_type=self.robot_type,
                        current_pose=frame.robot_state.get("pose") if frame.robot_state else None,
                        context={
                            "image": frame.image,
                            "instruction": frame.instruction,
                        },
                    )
                    safety_score = safety_result["overall_score"]

                    # Use safe action if modifications applied
                    if safety_result["modifications_applied"]:
                        action = safety_result["safe_action"]
                        logger.warning(f"Action modified for safety (frame {frame.frame_id})")

                # Calculate latency
                latency_ms = int((time.time() - start_time) * 1000)

                # Update average latency (exponential moving average)
                self.avg_latency_ms = 0.9 * self.avg_latency_ms + 0.1 * latency_ms

                # Create action result
                stream_action = StreamAction(
                    frame_id=frame.frame_id,
                    timestamp=time.time(),
                    action=action,
                    safety_score=safety_score,
                    latency_ms=latency_ms,
                    smoothed=self.smoother is not None,
                )

                # Add to output queue
                try:
                    self.action_queue.put_nowait(stream_action)
                except asyncio.QueueFull:
                    # Drop oldest action if queue full
                    try:
                        self.action_queue.get_nowait()
                        self.action_queue.put_nowait(stream_action)
                    except:
                        pass

                # Rate limiting to target FPS
                elapsed = time.time() - start_time
                target_interval = 1.0 / self.target_fps
                if elapsed < target_interval:
                    await asyncio.sleep(target_interval - elapsed)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)

        logger.info(f"Inference worker stopped for session {self.session_id}")

    def get_stats(self) -> Dict:
        """Get session statistics.

        Returns:
            Statistics dictionary
        """
        runtime = time.time() - self.start_time
        actual_fps = self.total_frames / runtime if runtime > 0 else 0.0
        drop_rate = self.dropped_frames / max(1, self.total_frames + self.dropped_frames)

        return {
            "session_id": str(self.session_id),
            "runtime_seconds": runtime,
            "total_frames": self.total_frames,
            "dropped_frames": self.dropped_frames,
            "drop_rate_percent": drop_rate * 100,
            "target_fps": self.target_fps,
            "actual_fps": actual_fps,
            "avg_latency_ms": self.avg_latency_ms,
            "frame_queue_size": self.frame_queue.qsize(),
            "action_queue_size": self.action_queue.qsize(),
        }


class StreamingInferenceManager:
    """Manages multiple streaming inference sessions."""

    def __init__(self):
        """Initialize streaming manager."""
        self.sessions: Dict[UUID, StreamingInferenceSession] = {}

    async def create_session(
        self,
        customer_id: UUID,
        model_id: str,
        robot_type: str = "franka_panda",
        target_fps: int = 10,
        enable_smoothing: bool = True,
        enable_safety: bool = True,
    ) -> StreamingInferenceSession:
        """Create a new streaming session.

        Args:
            customer_id: Customer UUID
            model_id: VLA model to use
            robot_type: Robot type
            target_fps: Target inference rate
            enable_smoothing: Enable action smoothing
            enable_safety: Enable safety monitoring

        Returns:
            StreamingInferenceSession
        """
        session_id = uuid4()

        session = StreamingInferenceSession(
            session_id=session_id,
            customer_id=customer_id,
            model_id=model_id,
            robot_type=robot_type,
            target_fps=target_fps,
            enable_smoothing=enable_smoothing,
            enable_safety=enable_safety,
        )

        await session.start()
        self.sessions[session_id] = session

        logger.info(f"Created streaming session {session_id} for customer {customer_id}")

        return session

    async def get_session(self, session_id: UUID) -> Optional[StreamingInferenceSession]:
        """Get session by ID.

        Args:
            session_id: Session UUID

        Returns:
            StreamingInferenceSession or None
        """
        return self.sessions.get(session_id)

    async def close_session(self, session_id: UUID):
        """Close a streaming session.

        Args:
            session_id: Session UUID
        """
        session = self.sessions.get(session_id)
        if session:
            await session.stop()
            del self.sessions[session_id]
            logger.info(f"Closed streaming session {session_id}")

    async def cleanup_inactive_sessions(self, max_idle_seconds: int = 300):
        """Clean up sessions that have been idle.

        Args:
            max_idle_seconds: Maximum idle time before cleanup
        """
        now = time.time()
        to_remove = []

        for session_id, session in self.sessions.items():
            idle_time = now - session.start_time
            if not session.is_running or (session.total_frames == 0 and idle_time > max_idle_seconds):
                to_remove.append(session_id)

        for session_id in to_remove:
            await self.close_session(session_id)


# Global streaming manager
streaming_manager = StreamingInferenceManager()
