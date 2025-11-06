"""GPU monitoring service using NVIDIA Management Library (NVML)."""

import asyncio
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, List, Optional

import pynvml

from src.monitoring.prometheus_metrics import (
    inference_gpu_memory_delta_bytes,
    update_gpu_metrics,
)

logger = logging.getLogger(__name__)


@dataclass
class GPUStats:
    """GPU statistics snapshot."""

    device_id: int
    device_name: str
    utilization: float  # 0-100
    memory_used: int  # bytes
    memory_total: int  # bytes
    memory_free: int  # bytes
    temperature: float  # Celsius
    power_usage: float  # Watts
    power_limit: float  # Watts
    compute_mode: int


class GPUMonitor:
    """Monitor GPU statistics and update Prometheus metrics."""

    def __init__(self, poll_interval: int = 5):
        """Initialize GPU monitor.

        Args:
            poll_interval: Polling interval in seconds (default: 5)
        """
        self.poll_interval = poll_interval
        self._initialized = False
        self._device_count = 0
        self._device_handles: List = []
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False

    def initialize(self):
        """Initialize NVML and get device handles."""
        if self._initialized:
            return

        try:
            pynvml.nvmlInit()
            self._device_count = pynvml.nvmlDeviceGetCount()

            # Get handles for all devices
            self._device_handles = []
            for i in range(self._device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                self._device_handles.append(handle)

            self._initialized = True
            logger.info(f"GPU monitor initialized with {self._device_count} devices")

        except pynvml.NVMLError as e:
            logger.warning(f"Failed to initialize NVML: {e}")
            self._initialized = False

    def shutdown(self):
        """Shutdown NVML."""
        if self._initialized:
            try:
                pynvml.nvmlShutdown()
                self._initialized = False
                logger.info("GPU monitor shutdown")
            except pynvml.NVMLError as e:
                logger.error(f"Error during NVML shutdown: {e}")

    def get_gpu_stats(self, device_id: int = 0) -> Optional[GPUStats]:
        """Get current GPU statistics for a device.

        Args:
            device_id: GPU device ID

        Returns:
            GPUStats object or None if unavailable
        """
        if not self._initialized or device_id >= self._device_count:
            return None

        try:
            handle = self._device_handles[device_id]

            # Get device name
            device_name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(device_name, bytes):
                device_name = device_name.decode("utf-8")

            # Get utilization rates
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_util = utilization.gpu

            # Get memory info
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            memory_used = memory_info.used
            memory_total = memory_info.total
            memory_free = memory_info.free

            # Get temperature
            temperature = pynvml.nvmlDeviceGetTemperature(
                handle, pynvml.NVML_TEMPERATURE_GPU
            )

            # Get power usage
            power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW to W
            power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0

            # Get compute mode
            compute_mode = pynvml.nvmlDeviceGetComputeMode(handle)

            return GPUStats(
                device_id=device_id,
                device_name=device_name,
                utilization=gpu_util,
                memory_used=memory_used,
                memory_total=memory_total,
                memory_free=memory_free,
                temperature=temperature,
                power_usage=power_usage,
                power_limit=power_limit,
                compute_mode=compute_mode,
            )

        except pynvml.NVMLError as e:
            logger.error(f"Error getting GPU stats for device {device_id}: {e}")
            return None

    def get_all_gpu_stats(self) -> Dict[int, GPUStats]:
        """Get statistics for all GPU devices.

        Returns:
            Dictionary mapping device ID to GPUStats
        """
        stats = {}
        for device_id in range(self._device_count):
            device_stats = self.get_gpu_stats(device_id)
            if device_stats:
                stats[device_id] = device_stats
        return stats

    async def update_prometheus_metrics(self):
        """Update Prometheus metrics with current GPU stats."""
        stats = self.get_all_gpu_stats()

        for device_id, gpu_stats in stats.items():
            update_gpu_metrics(
                device_id=device_id,
                device_name=gpu_stats.device_name,
                utilization=gpu_stats.utilization,
                memory_used=gpu_stats.memory_used,
                memory_total=gpu_stats.memory_total,
                temperature=gpu_stats.temperature,
                power=gpu_stats.power_usage,
            )

    async def start_monitoring(self):
        """Start background monitoring loop."""
        if not self._initialized:
            logger.warning("GPU monitor not initialized, skipping monitoring")
            return

        if self._running:
            logger.warning("GPU monitoring already running")
            return

        self._running = True
        logger.info(
            f"Starting GPU monitoring (poll interval: {self.poll_interval}s)"
        )

        while self._running:
            try:
                await self.update_prometheus_metrics()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in GPU monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

        logger.info("GPU monitoring stopped")

    def stop_monitoring(self):
        """Stop background monitoring."""
        self._running = False
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()

    @contextmanager
    def track_inference_memory(self, model_id: str, device_id: int = 0):
        """Context manager to track GPU memory usage during inference.

        Args:
            model_id: Model identifier
            device_id: GPU device ID

        Example:
            with gpu_monitor.track_inference_memory("openvla-7b", 0):
                # Run inference
                outputs = model(**inputs)
        """
        # Get memory before inference
        stats_before = self.get_gpu_stats(device_id)
        memory_before = stats_before.memory_used if stats_before else 0

        try:
            yield
        finally:
            # Get memory after inference
            stats_after = self.get_gpu_stats(device_id)
            memory_after = stats_after.memory_used if stats_after else 0

            # Calculate delta
            memory_delta = memory_after - memory_before

            # Record to Prometheus
            if memory_delta > 0:
                inference_gpu_memory_delta_bytes.labels(
                    model=model_id, device=str(device_id)
                ).observe(memory_delta)

    def get_device_count(self) -> int:
        """Get number of available GPU devices.

        Returns:
            Number of GPU devices
        """
        return self._device_count

    def is_initialized(self) -> bool:
        """Check if GPU monitor is initialized.

        Returns:
            True if initialized
        """
        return self._initialized

    def get_device_info(self, device_id: int = 0) -> Optional[Dict]:
        """Get detailed device information.

        Args:
            device_id: GPU device ID

        Returns:
            Dictionary with device information
        """
        if not self._initialized or device_id >= self._device_count:
            return None

        try:
            handle = self._device_handles[device_id]

            device_name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(device_name, bytes):
                device_name = device_name.decode("utf-8")

            # Get additional info
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            driver_version = pynvml.nvmlSystemGetDriverVersion()
            if isinstance(driver_version, bytes):
                driver_version = driver_version.decode("utf-8")

            cuda_version = pynvml.nvmlSystemGetCudaDriverVersion()
            cuda_major = cuda_version // 1000
            cuda_minor = (cuda_version % 1000) // 10

            return {
                "device_id": device_id,
                "name": device_name,
                "driver_version": driver_version,
                "cuda_version": f"{cuda_major}.{cuda_minor}",
                "memory_total": memory_info.total,
                "memory_total_gb": memory_info.total / (1024**3),
            }

        except pynvml.NVMLError as e:
            logger.error(f"Error getting device info for {device_id}: {e}")
            return None


# Global GPU monitor instance
gpu_monitor = GPUMonitor(poll_interval=5)


async def start_gpu_monitoring():
    """Start GPU monitoring service during application startup."""
    gpu_monitor.initialize()

    if gpu_monitor.is_initialized():
        # Start monitoring loop
        task = asyncio.create_task(gpu_monitor.start_monitoring())
        gpu_monitor._monitoring_task = task
        logger.info("GPU monitoring service started")
    else:
        logger.warning("GPU monitoring not available")


async def stop_gpu_monitoring():
    """Stop GPU monitoring service during application shutdown."""
    gpu_monitor.stop_monitoring()

    if gpu_monitor._monitoring_task:
        try:
            await asyncio.wait_for(gpu_monitor._monitoring_task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("GPU monitoring task did not stop gracefully")

    gpu_monitor.shutdown()
    logger.info("GPU monitoring service stopped")
