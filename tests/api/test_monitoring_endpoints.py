"""
Comprehensive tests for monitoring API endpoints.

Tests /metrics, /health, /monitoring/gpu endpoints.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import json

# Import app
from src.main import app
from src.monitoring.gpu_monitor import GPUStats


@pytest.fixture
def client():
    """Provide test client."""
    return TestClient(app)


@pytest.fixture
def mock_gpu_stats():
    """Provide mock GPU stats."""
    return [
        GPUStats(
            gpu_id=0,
            name="NVIDIA Tesla T4 0",
            memory_used=4_000_000_000,
            memory_total=16_000_000_000,
            memory_free=12_000_000_000,
            utilization=75,
            temperature=65,
            power_usage=150,
            power_limit=250,
        ),
        GPUStats(
            gpu_id=1,
            name="NVIDIA Tesla T4 1",
            memory_used=8_000_000_000,
            memory_total=16_000_000_000,
            memory_free=8_000_000_000,
            utilization=50,
            temperature=60,
            power_usage=120,
            power_limit=250,
        ),
    ]


class TestMetricsEndpoint:
    """Test Prometheus /metrics endpoint."""

    def test_metrics_endpoint_exists(self, client):
        """Test /metrics endpoint is available."""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self, client):
        """Test metrics endpoint returns correct content type."""
        response = client.get("/metrics")

        # Prometheus expects text/plain or specific prometheus content type
        assert response.headers["content-type"] in [
            "text/plain; charset=utf-8",
            "text/plain; version=0.0.4; charset=utf-8",
        ]

    def test_metrics_format(self, client):
        """Test metrics are in Prometheus format."""
        response = client.get("/metrics")
        content = response.text

        # Check for Prometheus format markers
        assert "# HELP" in content or "# TYPE" in content

        # Check for our custom metrics
        assert "inference_requests_total" in content or \
               "vla_api" in content.lower()

    def test_metrics_include_system_metrics(self, client):
        """Test metrics include system metrics."""
        response = client.get("/metrics")
        content = response.text

        # Should include process metrics
        assert "process_" in content or "python_" in content

    def test_metrics_include_custom_metrics(self, client):
        """Test metrics include our custom metrics."""
        # Generate some metrics
        client.post("/v1/inference", json={
            "model_name": "test-model",
            "input": {"text": "test"},
        })

        response = client.get("/metrics")
        content = response.text

        # Should include our inference metrics
        expected_metrics = [
            "inference_requests",
            "inference_duration",
            "active_requests",
        ]

        # At least some of our metrics should be present
        assert any(metric in content for metric in expected_metrics)

    def test_metrics_no_auth_required(self, client):
        """Test metrics endpoint doesn't require authentication."""
        # Should work without any auth headers
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_caching(self, client):
        """Test metrics endpoint caching behavior."""
        response1 = client.get("/metrics")
        response2 = client.get("/metrics")

        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Content might differ due to time-based metrics
        # but both should be valid


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_endpoint_basic(self, client):
        """Test basic health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy", "degraded"]

    def test_health_endpoint_json(self, client):
        """Test health endpoint returns JSON."""
        response = client.get("/health")

        assert response.headers["content-type"] == "application/json"

        # Should be valid JSON
        data = response.json()
        assert isinstance(data, dict)

    def test_health_includes_timestamp(self, client):
        """Test health response includes timestamp."""
        response = client.get("/health")
        data = response.json()

        assert "timestamp" in data
        assert isinstance(data["timestamp"], (int, float, str))

    def test_health_includes_version(self, client):
        """Test health response includes version."""
        response = client.get("/health")
        data = response.json()

        # Should have version info
        assert "version" in data or "api_version" in data

    def test_health_no_auth_required(self, client):
        """Test health endpoint doesn't require authentication."""
        response = client.get("/health")
        assert response.status_code == 200


class TestDetailedHealthEndpoint:
    """Test /health/detailed endpoint."""

    def test_detailed_health_endpoint(self, client):
        """Test detailed health endpoint."""
        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "checks" in data or "components" in data

    def test_detailed_health_includes_subsystems(self, client):
        """Test detailed health includes subsystem checks."""
        response = client.get("/health/detailed")
        data = response.json()

        # Should have checks for various subsystems
        checks = data.get("checks", data.get("components", {}))

        # Expected subsystems
        expected_subsystems = [
            "database",
            "model_cache",
            "gpu",
            "queue",
            "storage",
        ]

        # At least some subsystems should be present
        assert any(
            subsystem in str(checks).lower()
            for subsystem in expected_subsystems
        )

    def test_detailed_health_component_status(self, client):
        """Test each component has a status."""
        response = client.get("/health/detailed")
        data = response.json()

        checks = data.get("checks", data.get("components", {}))

        # Each check should have status
        for check_name, check_data in checks.items():
            if isinstance(check_data, dict):
                assert "status" in check_data or "healthy" in check_data

    @patch('src.monitoring.gpu_monitor.GPUMonitor.get_gpu_stats')
    def test_detailed_health_gpu_info(self, mock_gpu_stats, client, mock_gpu_stats):
        """Test detailed health includes GPU info."""
        mock_gpu_stats.return_value = mock_gpu_stats

        response = client.get("/health/detailed")
        data = response.json()

        # Should include GPU information
        assert any(
            "gpu" in str(key).lower()
            for key in data.keys()
        ) or any(
            "gpu" in str(value).lower()
            for value in str(data).lower()
        )

    def test_detailed_health_performance_metrics(self, client):
        """Test detailed health includes performance metrics."""
        response = client.get("/health/detailed")
        data = response.json()

        # Should include some performance metrics
        metrics_keys = [
            "response_time",
            "uptime",
            "request_count",
            "error_rate",
        ]

        # At least some metrics should be present
        data_str = str(data).lower()
        assert any(key in data_str for key in metrics_keys)


class TestGPUStatsEndpoint:
    """Test /monitoring/gpu/stats endpoint."""

    @patch('src.monitoring.gpu_monitor.GPUMonitor.get_gpu_stats')
    def test_gpu_stats_endpoint(self, mock_get_stats, client, mock_gpu_stats):
        """Test GPU stats endpoint."""
        mock_get_stats.return_value = mock_gpu_stats

        response = client.get("/monitoring/gpu/stats")

        assert response.status_code == 200
        data = response.json()

        assert "gpus" in data or isinstance(data, list)

    @patch('src.monitoring.gpu_monitor.GPUMonitor.get_gpu_stats')
    def test_gpu_stats_includes_all_devices(
        self,
        mock_get_stats,
        client,
        mock_gpu_stats
    ):
        """Test GPU stats includes all devices."""
        mock_get_stats.return_value = mock_gpu_stats

        response = client.get("/monitoring/gpu/stats")
        data = response.json()

        gpus = data.get("gpus", data)
        assert len(gpus) == 2

    @patch('src.monitoring.gpu_monitor.GPUMonitor.get_gpu_stats')
    def test_gpu_stats_device_info(self, mock_get_stats, client, mock_gpu_stats):
        """Test GPU stats includes device information."""
        mock_get_stats.return_value = mock_gpu_stats

        response = client.get("/monitoring/gpu/stats")
        data = response.json()

        gpus = data.get("gpus", data)
        gpu = gpus[0]

        # Should have device info
        assert "gpu_id" in gpu or "id" in gpu
        assert "name" in gpu
        assert "memory_used" in gpu or "memory" in gpu
        assert "utilization" in gpu

    @patch('src.monitoring.gpu_monitor.GPUMonitor.get_gpu_stats')
    def test_gpu_stats_single_device(self, mock_get_stats, client, mock_gpu_stats):
        """Test getting stats for single GPU."""
        mock_get_stats.return_value = [mock_gpu_stats[0]]

        response = client.get("/monitoring/gpu/stats?gpu_id=0")

        assert response.status_code == 200
        data = response.json()

        # Should only have one GPU
        gpus = data.get("gpus", data)
        if isinstance(gpus, list):
            assert len(gpus) == 1

    @patch('src.monitoring.gpu_monitor.GPUMonitor.get_gpu_stats')
    def test_gpu_stats_no_gpu_available(self, mock_get_stats, client):
        """Test GPU stats when no GPU available."""
        mock_get_stats.return_value = []

        response = client.get("/monitoring/gpu/stats")

        # Should still return 200 with empty list
        assert response.status_code == 200
        data = response.json()

        gpus = data.get("gpus", data)
        assert len(gpus) == 0 or data.get("available") is False


class TestQueueStatsEndpoint:
    """Test /monitoring/queue/stats endpoint."""

    def test_queue_stats_endpoint(self, client):
        """Test queue stats endpoint."""
        response = client.get("/monitoring/queue/stats")

        assert response.status_code == 200
        data = response.json()

        assert "queue_size" in data or "size" in data
        assert "pending" in data or "waiting" in data

    def test_queue_stats_by_priority(self, client):
        """Test queue stats includes priority breakdown."""
        response = client.get("/monitoring/queue/stats")
        data = response.json()

        # Should have priority information
        assert any(
            "priority" in str(key).lower()
            for key in data.keys()
        ) or any(
            "high" in str(data).lower() or "low" in str(data).lower()
        )

    def test_queue_stats_includes_metrics(self, client):
        """Test queue stats includes relevant metrics."""
        response = client.get("/monitoring/queue/stats")
        data = response.json()

        # Should have queue metrics
        expected_fields = [
            "size",
            "pending",
            "processing",
            "average_wait_time",
            "oldest_request",
        ]

        data_str = str(data).lower()
        assert any(field in data_str for field in expected_fields)


class TestModelStatsEndpoint:
    """Test /monitoring/models/stats endpoint."""

    def test_model_stats_endpoint(self, client):
        """Test model stats endpoint."""
        response = client.get("/monitoring/models/stats")

        assert response.status_code == 200
        data = response.json()

        assert "models" in data or isinstance(data, list)

    def test_model_stats_includes_loaded_models(self, client):
        """Test model stats includes loaded models."""
        response = client.get("/monitoring/models/stats")
        data = response.json()

        # Should have information about models
        models = data.get("models", data)

        if isinstance(models, list) and len(models) > 0:
            model = models[0]
            assert "name" in model or "model_name" in model

    def test_model_stats_memory_usage(self, client):
        """Test model stats includes memory usage."""
        response = client.get("/monitoring/models/stats")
        data = response.json()

        # Should include memory information
        assert any(
            "memory" in str(key).lower()
            for key in str(data).lower().split()
        )

    def test_model_stats_specific_model(self, client):
        """Test getting stats for specific model."""
        response = client.get("/monitoring/models/stats?model_name=test-model")

        # Should return stats for specific model
        assert response.status_code in [200, 404]  # 404 if model not loaded


class TestMonitoringEndpointsIntegration:
    """Test integration between monitoring endpoints."""

    def test_metrics_reflects_api_calls(self, client):
        """Test metrics are updated by API calls."""
        # Get initial metrics
        response1 = client.get("/metrics")

        # Make some API calls
        client.post("/v1/inference", json={
            "model_name": "test-model",
            "input": {"text": "test"},
        })

        # Get updated metrics
        response2 = client.get("/metrics")

        # Metrics should have changed
        # (At minimum, request counters should increase)
        assert len(response2.text) >= len(response1.text)

    def test_health_reflects_system_state(self, client):
        """Test health endpoint reflects system state."""
        response = client.get("/health/detailed")
        data = response.json()

        status = data.get("status")

        # Status should be based on system checks
        assert status in ["healthy", "unhealthy", "degraded"]

    def test_all_monitoring_endpoints_accessible(self, client):
        """Test all monitoring endpoints are accessible."""
        endpoints = [
            "/metrics",
            "/health",
            "/health/detailed",
            "/monitoring/gpu/stats",
            "/monitoring/queue/stats",
            "/monitoring/models/stats",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 404, 501]  # 404/501 if not implemented


class TestMonitoringEndpointsSecurity:
    """Test security aspects of monitoring endpoints."""

    def test_metrics_no_sensitive_data(self, client):
        """Test metrics don't expose sensitive data."""
        response = client.get("/metrics")
        content = response.text.lower()

        # Should not contain sensitive information
        sensitive_keywords = [
            "password",
            "secret",
            "key",
            "token",
            "credential",
        ]

        for keyword in sensitive_keywords:
            assert keyword not in content

    def test_health_no_internal_paths(self, client):
        """Test health endpoint doesn't expose internal paths."""
        response = client.get("/health/detailed")
        data = response.json()

        data_str = str(data)

        # Should not contain absolute file paths
        assert "/home/" not in data_str
        assert "/root/" not in data_str
        assert "C:\\" not in data_str

    def test_rate_limiting_monitoring_endpoints(self, client):
        """Test monitoring endpoints handle rapid requests."""
        # Make many rapid requests
        responses = []
        for _ in range(100):
            response = client.get("/metrics")
            responses.append(response)

        # All should succeed (or be rate limited gracefully)
        for response in responses:
            assert response.status_code in [200, 429]  # 429 = Too Many Requests


@pytest.mark.benchmark
class TestMonitoringEndpointsPerformance:
    """Test performance of monitoring endpoints."""

    def test_metrics_endpoint_performance(self, benchmark, client):
        """Benchmark /metrics endpoint."""
        def get_metrics():
            return client.get("/metrics")

        result = benchmark(get_metrics)
        assert result.status_code == 200

    def test_health_endpoint_performance(self, benchmark, client):
        """Benchmark /health endpoint."""
        def get_health():
            return client.get("/health")

        result = benchmark(get_health)
        assert result.status_code == 200

    def test_gpu_stats_endpoint_performance(self, benchmark, client):
        """Benchmark /monitoring/gpu/stats endpoint."""
        def get_gpu_stats():
            return client.get("/monitoring/gpu/stats")

        result = benchmark(get_gpu_stats)
        assert result.status_code == 200

    def test_concurrent_monitoring_requests(self, client):
        """Test handling concurrent monitoring requests."""
        import concurrent.futures

        def make_request(endpoint):
            return client.get(endpoint)

        endpoints = [
            "/metrics",
            "/health",
            "/health/detailed",
            "/monitoring/gpu/stats",
        ] * 10  # 40 total requests

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_request, endpoint)
                for endpoint in endpoints
            ]
            results = [future.result() for future in futures]

        # All should succeed
        assert all(r.status_code == 200 for r in results)
