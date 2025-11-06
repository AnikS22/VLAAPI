"""
Comprehensive tests for GPU monitoring functionality.

Tests GPU stats collection, memory tracking, and Prometheus integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from contextlib import contextmanager
import time

from src.monitoring.gpu_monitor import (
    GPUMonitor,
    GPUStats,
)


class MockNVMLDevice:
    """Mock NVML device for testing."""

    def __init__(self, index=0):
        self.index = index
        self.name = f"NVIDIA Tesla T4 {index}"
        self.memory_used = 4_000_000_000  # 4GB
        self.memory_total = 16_000_000_000  # 16GB
        self.utilization = 75
        self.temperature = 65
        self.power_usage = 150_000  # 150W in milliwatts
        self.power_limit = 250_000  # 250W in milliwatts


class MockNVML:
    """Mock NVML library for testing."""

    def __init__(self, device_count=2):
        self.device_count = device_count
        self.devices = [MockNVMLDevice(i) for i in range(device_count)]
        self.initialized = False

    def nvmlInit(self):
        self.initialized = True

    def nvmlShutdown(self):
        self.initialized = False

    def nvmlDeviceGetCount(self):
        if not self.initialized:
            raise Exception("NVML not initialized")
        return self.device_count

    def nvmlDeviceGetHandleByIndex(self, index):
        if not self.initialized:
            raise Exception("NVML not initialized")
        if index >= self.device_count:
            raise Exception(f"Invalid device index: {index}")
        return self.devices[index]

    def nvmlDeviceGetName(self, handle):
        return handle.name.encode('utf-8')

    def nvmlDeviceGetMemoryInfo(self, handle):
        class MemInfo:
            used = handle.memory_used
            total = handle.memory_total
            free = handle.memory_total - handle.memory_used
        return MemInfo()

    def nvmlDeviceGetUtilizationRates(self, handle):
        class UtilRates:
            gpu = handle.utilization
            memory = int(handle.memory_used / handle.memory_total * 100)
        return UtilRates()

    def nvmlDeviceGetTemperature(self, handle, sensor_id):
        return handle.temperature

    def nvmlDeviceGetPowerUsage(self, handle):
        return handle.power_usage

    def nvmlDeviceGetEnforcedPowerLimit(self, handle):
        return handle.power_limit


@pytest.fixture
def mock_nvml():
    """Provide mock NVML library."""
    return MockNVML(device_count=2)


@pytest.fixture
def gpu_monitor(mock_nvml):
    """Provide GPU monitor with mocked NVML."""
    with patch('src.monitoring.gpu_monitor.pynvml', mock_nvml):
        monitor = GPUMonitor(polling_interval=0.1)
        yield monitor
        monitor.stop()


class TestGPUMonitorInitialization:
    """Test GPU monitor initialization."""

    def test_init_with_gpu_available(self, mock_nvml):
        """Test initialization when GPU is available."""
        with patch('src.monitoring.gpu_monitor.pynvml', mock_nvml):
            monitor = GPUMonitor()

            assert monitor.available is True
            assert monitor.device_count == 2
            assert len(monitor.device_handles) == 2

            monitor.stop()

    def test_init_without_gpu(self):
        """Test initialization when GPU is not available."""
        mock_nvml_no_gpu = MockNVML(device_count=0)

        with patch('src.monitoring.gpu_monitor.pynvml', mock_nvml_no_gpu):
            monitor = GPUMonitor()

            assert monitor.available is True  # Still initializes
            assert monitor.device_count == 0

            monitor.stop()

    def test_init_nvml_import_error(self):
        """Test initialization when NVML cannot be imported."""
        with patch('src.monitoring.gpu_monitor.pynvml', None):
            monitor = GPUMonitor()

            assert monitor.available is False
            assert monitor.device_count == 0

            monitor.stop()

    def test_custom_polling_interval(self, mock_nvml):
        """Test custom polling interval."""
        with patch('src.monitoring.gpu_monitor.pynvml', mock_nvml):
            monitor = GPUMonitor(polling_interval=5.0)

            assert monitor.polling_interval == 5.0

            monitor.stop()

    def test_auto_start(self, mock_nvml):
        """Test automatic monitoring start."""
        with patch('src.monitoring.gpu_monitor.pynvml', mock_nvml):
            monitor = GPUMonitor(auto_start=True)

            # Give it time to start
            time.sleep(0.2)

            assert monitor._monitoring_thread is not None
            assert monitor._monitoring_thread.is_alive()

            monitor.stop()


class TestGPUStatsCollection:
    """Test GPU statistics collection."""

    def test_get_gpu_stats_single_device(self, gpu_monitor, mock_nvml):
        """Test getting stats for single GPU."""
        stats = gpu_monitor.get_gpu_stats(gpu_id=0)

        assert stats is not None
        assert stats.gpu_id == 0
        assert stats.name == "NVIDIA Tesla T4 0"
        assert stats.memory_used == 4_000_000_000
        assert stats.memory_total == 16_000_000_000
        assert stats.memory_free == 12_000_000_000
        assert stats.utilization == 75
        assert stats.temperature == 65

    def test_get_gpu_stats_all_devices(self, gpu_monitor):
        """Test getting stats for all GPUs."""
        all_stats = gpu_monitor.get_gpu_stats()

        assert len(all_stats) == 2
        assert all_stats[0].gpu_id == 0
        assert all_stats[1].gpu_id == 1

    def test_get_gpu_stats_invalid_device(self, gpu_monitor):
        """Test getting stats for invalid device ID."""
        stats = gpu_monitor.get_gpu_stats(gpu_id=99)

        assert stats is None

    def test_gpu_stats_memory_percentage(self, gpu_monitor):
        """Test memory percentage calculation."""
        stats = gpu_monitor.get_gpu_stats(gpu_id=0)

        expected_pct = (4_000_000_000 / 16_000_000_000) * 100
        assert stats.memory_percent == pytest.approx(expected_pct, rel=0.01)

    def test_gpu_stats_power_metrics(self, gpu_monitor):
        """Test power usage metrics."""
        stats = gpu_monitor.get_gpu_stats(gpu_id=0)

        assert stats.power_usage == 150  # Watts
        assert stats.power_limit == 250  # Watts

    def test_gpu_stats_with_error(self, gpu_monitor, mock_nvml):
        """Test graceful handling of NVML errors."""
        # Make NVML raise an error
        def raise_error(*args, **kwargs):
            raise Exception("NVML Error")

        mock_nvml.nvmlDeviceGetMemoryInfo = raise_error

        stats = gpu_monitor.get_gpu_stats(gpu_id=0)

        # Should return None on error
        assert stats is None


class TestPerInferenceMemoryTracking:
    """Test per-inference GPU memory tracking."""

    def test_context_manager_basic(self, gpu_monitor, mock_nvml):
        """Test basic context manager usage."""
        inference_id = "test-inference-1"

        with gpu_monitor.track_inference_memory(inference_id, gpu_id=0):
            # Simulate inference
            time.sleep(0.1)

        # Check memory was tracked
        memory_info = gpu_monitor.get_inference_memory_usage(inference_id)

        assert memory_info is not None
        assert 'start_memory' in memory_info
        assert 'end_memory' in memory_info
        assert 'peak_memory' in memory_info
        assert 'memory_delta' in memory_info

    def test_context_manager_memory_delta(self, gpu_monitor, mock_nvml):
        """Test memory delta calculation."""
        inference_id = "test-inference-2"

        # Simulate memory increase during inference
        device = mock_nvml.devices[0]
        initial_memory = device.memory_used

        with gpu_monitor.track_inference_memory(inference_id, gpu_id=0):
            # Simulate memory allocation
            device.memory_used += 1_000_000_000  # Add 1GB
            time.sleep(0.1)

        memory_info = gpu_monitor.get_inference_memory_usage(inference_id)

        # Should have tracked the increase
        assert memory_info['memory_delta'] > 0

        # Reset memory
        device.memory_used = initial_memory

    def test_context_manager_multiple_inferences(self, gpu_monitor):
        """Test tracking multiple concurrent inferences."""
        inference_ids = [f"inference-{i}" for i in range(5)]

        # Track multiple inferences
        for inference_id in inference_ids:
            with gpu_monitor.track_inference_memory(inference_id, gpu_id=0):
                time.sleep(0.05)

        # All should be tracked
        for inference_id in inference_ids:
            memory_info = gpu_monitor.get_inference_memory_usage(inference_id)
            assert memory_info is not None

    def test_context_manager_with_exception(self, gpu_monitor):
        """Test context manager handles exceptions gracefully."""
        inference_id = "test-inference-error"

        try:
            with gpu_monitor.track_inference_memory(inference_id, gpu_id=0):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should still have memory info
        memory_info = gpu_monitor.get_inference_memory_usage(inference_id)
        assert memory_info is not None

    def test_peak_memory_tracking(self, gpu_monitor, mock_nvml):
        """Test peak memory tracking during inference."""
        inference_id = "test-inference-peak"
        device = mock_nvml.devices[0]
        initial_memory = device.memory_used

        with gpu_monitor.track_inference_memory(inference_id, gpu_id=0):
            # Simulate memory spikes
            device.memory_used += 2_000_000_000  # Spike to +2GB
            time.sleep(0.05)
            device.memory_used -= 1_000_000_000  # Drop to +1GB
            time.sleep(0.05)

        memory_info = gpu_monitor.get_inference_memory_usage(inference_id)

        # Peak should reflect the spike
        assert memory_info['peak_memory'] >= initial_memory + 2_000_000_000

        # Reset
        device.memory_used = initial_memory


class TestPrometheusIntegration:
    """Test Prometheus metrics integration."""

    @patch('src.monitoring.gpu_monitor.gpu_memory_used_bytes')
    @patch('src.monitoring.gpu_monitor.gpu_memory_total_bytes')
    @patch('src.monitoring.gpu_monitor.gpu_utilization_percent')
    @patch('src.monitoring.gpu_monitor.gpu_temperature_celsius')
    def test_update_prometheus_metrics(
        self,
        mock_temp,
        mock_util,
        mock_total,
        mock_used,
        gpu_monitor
    ):
        """Test Prometheus metrics are updated."""
        gpu_monitor.start()

        # Give monitoring thread time to run
        time.sleep(0.3)

        # Verify metrics were updated
        assert mock_used.labels.called
        assert mock_total.labels.called
        assert mock_util.labels.called
        assert mock_temp.labels.called

        gpu_monitor.stop()

    @patch('src.monitoring.gpu_monitor.gpu_memory_used_bytes')
    def test_metrics_updated_per_gpu(self, mock_metric, gpu_monitor):
        """Test metrics updated for each GPU."""
        gpu_monitor.start()
        time.sleep(0.3)

        # Should be called once per GPU
        assert mock_metric.labels.call_count >= 2

        # Check labels
        calls = mock_metric.labels.call_args_list
        gpu_ids = {call[1]['gpu_id'] for call in calls}
        assert '0' in gpu_ids
        assert '1' in gpu_ids

        gpu_monitor.stop()

    def test_metrics_polling_interval(self, mock_nvml):
        """Test metrics update at correct interval."""
        with patch('src.monitoring.gpu_monitor.pynvml', mock_nvml):
            with patch('src.monitoring.gpu_monitor.gpu_memory_used_bytes') as mock_metric:
                monitor = GPUMonitor(polling_interval=0.2)
                monitor.start()

                # Count updates over time
                time.sleep(0.5)
                initial_count = mock_metric.labels.call_count

                time.sleep(0.5)
                final_count = mock_metric.labels.call_count

                # Should have multiple updates
                assert final_count > initial_count

                monitor.stop()


class TestGracefulDegradation:
    """Test graceful degradation when GPU unavailable."""

    def test_no_gpu_operations(self):
        """Test operations when no GPU available."""
        with patch('src.monitoring.gpu_monitor.pynvml', None):
            monitor = GPUMonitor()

            # Should not crash
            stats = monitor.get_gpu_stats()
            assert stats == []

            # Context manager should work
            with monitor.track_inference_memory("test-id", gpu_id=0):
                pass

            # Should return None
            memory_info = monitor.get_inference_memory_usage("test-id")
            assert memory_info is None

            monitor.stop()

    def test_nvml_error_handling(self, mock_nvml):
        """Test handling of NVML errors."""
        with patch('src.monitoring.gpu_monitor.pynvml', mock_nvml):
            monitor = GPUMonitor()

            # Make NVML raise errors
            def raise_error(*args, **kwargs):
                raise Exception("NVML Error")

            mock_nvml.nvmlDeviceGetMemoryInfo = raise_error

            # Should not crash
            stats = monitor.get_gpu_stats(gpu_id=0)
            assert stats is None

            monitor.stop()

    def test_monitoring_thread_resilience(self, gpu_monitor, mock_nvml):
        """Test monitoring thread handles errors gracefully."""
        gpu_monitor.start()

        # Inject error
        def raise_error(*args, **kwargs):
            raise Exception("Temporary error")

        original_func = mock_nvml.nvmlDeviceGetMemoryInfo
        mock_nvml.nvmlDeviceGetMemoryInfo = raise_error

        # Wait for a few polling cycles
        time.sleep(0.5)

        # Restore function
        mock_nvml.nvmlDeviceGetMemoryInfo = original_func

        # Thread should still be running
        assert gpu_monitor._monitoring_thread.is_alive()

        gpu_monitor.stop()


class TestMemoryLeaks:
    """Test for memory leaks in GPU monitoring."""

    def test_inference_tracking_cleanup(self, gpu_monitor):
        """Test that inference tracking data is cleaned up."""
        # Track many inferences
        for i in range(1000):
            inference_id = f"inference-{i}"
            with gpu_monitor.track_inference_memory(inference_id, gpu_id=0):
                pass

        # Memory should be bounded
        # (In real implementation, old entries should be cleaned up)
        inference_count = len(gpu_monitor._inference_memory_tracking)
        assert inference_count < 1000  # Should have cleanup

    def test_monitoring_thread_cleanup(self, gpu_monitor):
        """Test monitoring thread is properly cleaned up."""
        gpu_monitor.start()
        time.sleep(0.2)

        thread = gpu_monitor._monitoring_thread
        assert thread.is_alive()

        gpu_monitor.stop()
        time.sleep(0.2)

        assert not thread.is_alive()


@pytest.mark.benchmark
class TestGPUMonitorPerformance:
    """Test GPU monitor performance."""

    def test_stats_collection_performance(self, benchmark, gpu_monitor):
        """Benchmark GPU stats collection."""
        benchmark(gpu_monitor.get_gpu_stats, gpu_id=0)

    def test_context_manager_overhead(self, benchmark, gpu_monitor):
        """Benchmark context manager overhead."""
        def track_memory():
            with gpu_monitor.track_inference_memory("perf-test", gpu_id=0):
                pass

        benchmark(track_memory)

    def test_concurrent_tracking_performance(self, gpu_monitor):
        """Test performance with many concurrent inferences."""
        import concurrent.futures

        def track_inference(i):
            with gpu_monitor.track_inference_memory(f"concurrent-{i}", gpu_id=0):
                time.sleep(0.01)

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(track_inference, i) for i in range(100)]
            concurrent.futures.wait(futures)

        duration = time.time() - start_time

        # Should complete reasonably fast
        assert duration < 5.0  # 100 inferences in under 5 seconds


class TestGPUStatsDataclass:
    """Test GPUStats dataclass."""

    def test_gpu_stats_creation(self):
        """Test creating GPUStats instance."""
        stats = GPUStats(
            gpu_id=0,
            name="NVIDIA Tesla T4",
            memory_used=4_000_000_000,
            memory_total=16_000_000_000,
            memory_free=12_000_000_000,
            utilization=75,
            temperature=65,
            power_usage=150,
            power_limit=250,
        )

        assert stats.gpu_id == 0
        assert stats.memory_percent == 25.0

    def test_gpu_stats_serialization(self):
        """Test GPUStats can be serialized."""
        stats = GPUStats(
            gpu_id=0,
            name="NVIDIA Tesla T4",
            memory_used=4_000_000_000,
            memory_total=16_000_000_000,
            memory_free=12_000_000_000,
            utilization=75,
            temperature=65,
            power_usage=150,
            power_limit=250,
        )

        # Should be able to convert to dict
        stats_dict = stats.__dict__
        assert 'gpu_id' in stats_dict
        assert 'name' in stats_dict
        assert 'memory_used' in stats_dict
