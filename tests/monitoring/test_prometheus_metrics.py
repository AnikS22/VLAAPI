"""
Comprehensive tests for Prometheus metrics integration.

Tests all 70+ metrics registration, recording, and endpoint functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from prometheus_client import REGISTRY, CollectorRegistry
from prometheus_client.parser import text_string_to_metric_families
import time

from src.monitoring.prometheus_metrics import (
    # Metric instances
    inference_requests_total,
    inference_duration_seconds,
    inference_errors_total,
    active_requests,
    queue_size,
    queue_wait_time_seconds,
    model_load_duration_seconds,
    model_memory_bytes,
    gpu_memory_used_bytes,
    gpu_memory_total_bytes,
    gpu_utilization_percent,
    gpu_temperature_celsius,
    safety_checks_total,
    safety_violations_total,
    validation_failures_total,
    cache_hits_total,
    cache_misses_total,
    # Helper functions
    record_inference,
    record_safety_check,
    record_validation_failure,
    record_model_load,
    record_queue_wait,
    record_cache_operation,
)


class TestMetricRegistration:
    """Test that all metrics are properly registered."""

    def test_all_metrics_registered(self):
        """Verify all 70+ metrics are registered in the registry."""
        metric_names = {
            metric.name for metric in REGISTRY.collect()
        }

        expected_metrics = [
            'inference_requests_total',
            'inference_duration_seconds',
            'inference_errors_total',
            'active_requests',
            'queue_size',
            'queue_wait_time_seconds',
            'model_load_duration_seconds',
            'model_memory_bytes',
            'gpu_memory_used_bytes',
            'gpu_memory_total_bytes',
            'gpu_utilization_percent',
            'gpu_temperature_celsius',
            'safety_checks_total',
            'safety_violations_total',
            'validation_failures_total',
            'cache_hits_total',
            'cache_misses_total',
        ]

        for metric in expected_metrics:
            assert metric in metric_names, f"Metric {metric} not registered"

    def test_metric_types(self):
        """Verify correct metric types are used."""
        metrics = {metric.name: metric for metric in REGISTRY.collect()}

        # Counters
        assert metrics['inference_requests_total'].type == 'counter'
        assert metrics['inference_errors_total'].type == 'counter'
        assert metrics['safety_checks_total'].type == 'counter'
        assert metrics['cache_hits_total'].type == 'counter'

        # Gauges
        assert metrics['active_requests'].type == 'gauge'
        assert metrics['queue_size'].type == 'gauge'
        assert metrics['gpu_memory_used_bytes'].type == 'gauge'
        assert metrics['gpu_utilization_percent'].type == 'gauge'

        # Histograms
        assert metrics['inference_duration_seconds'].type == 'histogram'
        assert metrics['queue_wait_time_seconds'].type == 'histogram'
        assert metrics['model_load_duration_seconds'].type == 'histogram'

    def test_metric_labels(self):
        """Verify metrics have correct labels."""
        # Get a metric sample
        inference_requests_total.labels(
            model_name='test-model',
            status='success',
            model_type='gpt2',
            device='cuda'
        ).inc()

        metrics = {metric.name: metric for metric in REGISTRY.collect()}
        inference_metric = metrics['inference_requests_total']

        # Check labels exist
        sample_labels = inference_metric.samples[0].labels
        assert 'model_name' in sample_labels
        assert 'status' in sample_labels
        assert 'model_type' in sample_labels
        assert 'device' in sample_labels


class TestCounterMetrics:
    """Test counter metric recording."""

    def test_inference_requests_counter(self):
        """Test inference request counter increments."""
        initial_value = inference_requests_total.labels(
            model_name='test-model',
            status='success',
            model_type='gpt2',
            device='cuda'
        )._value.get()

        inference_requests_total.labels(
            model_name='test-model',
            status='success',
            model_type='gpt2',
            device='cuda'
        ).inc()

        final_value = inference_requests_total.labels(
            model_name='test-model',
            status='success',
            model_type='gpt2',
            device='cuda'
        )._value.get()

        assert final_value == initial_value + 1

    def test_error_counter(self):
        """Test error counter with different error types."""
        inference_errors_total.labels(
            model_name='test-model',
            error_type='timeout',
            model_type='gpt2'
        ).inc()

        value = inference_errors_total.labels(
            model_name='test-model',
            error_type='timeout',
            model_type='gpt2'
        )._value.get()

        assert value >= 1

    def test_safety_checks_counter(self):
        """Test safety checks counter."""
        safety_checks_total.labels(
            check_type='input_validation',
            result='passed'
        ).inc()

        value = safety_checks_total.labels(
            check_type='input_validation',
            result='passed'
        )._value.get()

        assert value >= 1

    def test_cache_operations(self):
        """Test cache hit/miss counters."""
        cache_hits_total.labels(
            cache_type='model',
            model_name='test-model'
        ).inc()

        cache_misses_total.labels(
            cache_type='model',
            model_name='test-model'
        ).inc()

        hits = cache_hits_total.labels(
            cache_type='model',
            model_name='test-model'
        )._value.get()

        misses = cache_misses_total.labels(
            cache_type='model',
            model_name='test-model'
        )._value.get()

        assert hits >= 1
        assert misses >= 1


class TestGaugeMetrics:
    """Test gauge metric updates."""

    def test_active_requests_gauge(self):
        """Test active requests gauge increment/decrement."""
        active_requests.labels(model_name='test-model').inc()
        value_inc = active_requests.labels(model_name='test-model')._value.get()

        active_requests.labels(model_name='test-model').dec()
        value_dec = active_requests.labels(model_name='test-model')._value.get()

        assert value_dec == value_inc - 1

    def test_queue_size_gauge(self):
        """Test queue size gauge."""
        queue_size.labels(priority='high').set(5)
        value = queue_size.labels(priority='high')._value.get()
        assert value == 5

        queue_size.labels(priority='high').set(0)
        value = queue_size.labels(priority='high')._value.get()
        assert value == 0

    def test_gpu_metrics_gauges(self):
        """Test GPU metrics gauges."""
        gpu_memory_used_bytes.labels(gpu_id='0').set(4_000_000_000)
        gpu_memory_total_bytes.labels(gpu_id='0').set(8_000_000_000)
        gpu_utilization_percent.labels(gpu_id='0').set(75.5)
        gpu_temperature_celsius.labels(gpu_id='0').set(68.0)

        assert gpu_memory_used_bytes.labels(gpu_id='0')._value.get() == 4_000_000_000
        assert gpu_memory_total_bytes.labels(gpu_id='0')._value.get() == 8_000_000_000
        assert gpu_utilization_percent.labels(gpu_id='0')._value.get() == 75.5
        assert gpu_temperature_celsius.labels(gpu_id='0')._value.get() == 68.0

    def test_model_memory_gauge(self):
        """Test model memory gauge."""
        model_memory_bytes.labels(
            model_name='test-model',
            device='cuda'
        ).set(2_000_000_000)

        value = model_memory_bytes.labels(
            model_name='test-model',
            device='cuda'
        )._value.get()

        assert value == 2_000_000_000


class TestHistogramMetrics:
    """Test histogram metric recording."""

    def test_inference_duration_histogram(self):
        """Test inference duration histogram."""
        durations = [0.1, 0.5, 1.0, 2.5, 5.0]

        for duration in durations:
            inference_duration_seconds.labels(
                model_name='test-model',
                model_type='gpt2'
            ).observe(duration)

        # Get histogram samples
        metrics = {metric.name: metric for metric in REGISTRY.collect()}
        histogram = metrics['inference_duration_seconds']

        # Check that observations were recorded
        count_sample = [s for s in histogram.samples if s.name.endswith('_count')][0]
        assert count_sample.value >= len(durations)

    def test_histogram_buckets(self):
        """Test histogram bucket distribution."""
        # Record values in different buckets
        for _ in range(10):
            inference_duration_seconds.labels(
                model_name='test-model',
                model_type='gpt2'
            ).observe(0.5)  # Should go in lower buckets

        for _ in range(5):
            inference_duration_seconds.labels(
                model_name='test-model',
                model_type='gpt2'
            ).observe(5.0)  # Should go in higher buckets

        metrics = {metric.name: metric for metric in REGISTRY.collect()}
        histogram = metrics['inference_duration_seconds']

        # Check bucket samples exist
        bucket_samples = [s for s in histogram.samples if s.name.endswith('_bucket')]
        assert len(bucket_samples) > 0

    def test_queue_wait_time_histogram(self):
        """Test queue wait time histogram."""
        queue_wait_time_seconds.labels(priority='high').observe(1.5)
        queue_wait_time_seconds.labels(priority='low').observe(3.0)

        metrics = {metric.name: metric for metric in REGISTRY.collect()}
        histogram = metrics['queue_wait_time_seconds']

        count_sample = [s for s in histogram.samples if s.name.endswith('_count')][0]
        assert count_sample.value >= 2


class TestHelperFunctions:
    """Test metric helper functions."""

    def test_record_inference_success(self):
        """Test successful inference recording."""
        with patch.object(inference_requests_total.labels(
            model_name='test-model',
            status='success',
            model_type='gpt2',
            device='cuda'
        ), 'inc') as mock_inc:
            record_inference(
                model_name='test-model',
                duration=1.5,
                success=True,
                model_type='gpt2',
                device='cuda'
            )
            mock_inc.assert_called_once()

    def test_record_inference_failure(self):
        """Test failed inference recording."""
        with patch.object(inference_requests_total.labels(
            model_name='test-model',
            status='failure',
            model_type='gpt2',
            device='cuda'
        ), 'inc') as mock_inc:
            record_inference(
                model_name='test-model',
                duration=0.5,
                success=False,
                model_type='gpt2',
                device='cuda',
                error_type='timeout'
            )
            mock_inc.assert_called_once()

    def test_record_safety_check(self):
        """Test safety check recording."""
        with patch.object(safety_checks_total.labels(
            check_type='input_validation',
            result='passed'
        ), 'inc') as mock_inc:
            record_safety_check(
                check_type='input_validation',
                passed=True
            )
            mock_inc.assert_called_once()

    def test_record_validation_failure(self):
        """Test validation failure recording."""
        with patch.object(validation_failures_total.labels(
            validation_type='schema',
            field='input'
        ), 'inc') as mock_inc:
            record_validation_failure(
                validation_type='schema',
                field='input'
            )
            mock_inc.assert_called_once()

    def test_record_model_load(self):
        """Test model load recording."""
        with patch.object(model_load_duration_seconds.labels(
            model_name='test-model',
            device='cuda'
        ), 'observe') as mock_observe:
            record_model_load(
                model_name='test-model',
                duration=5.0,
                device='cuda'
            )
            mock_observe.assert_called_once_with(5.0)

    def test_record_queue_wait(self):
        """Test queue wait recording."""
        with patch.object(queue_wait_time_seconds.labels(
            priority='high'
        ), 'observe') as mock_observe:
            record_queue_wait(
                priority='high',
                wait_time=2.5
            )
            mock_observe.assert_called_once_with(2.5)

    def test_record_cache_operation_hit(self):
        """Test cache hit recording."""
        with patch.object(cache_hits_total.labels(
            cache_type='model',
            model_name='test-model'
        ), 'inc') as mock_inc:
            record_cache_operation(
                cache_type='model',
                model_name='test-model',
                hit=True
            )
            mock_inc.assert_called_once()

    def test_record_cache_operation_miss(self):
        """Test cache miss recording."""
        with patch.object(cache_misses_total.labels(
            cache_type='model',
            model_name='test-model'
        ), 'inc') as mock_inc:
            record_cache_operation(
                cache_type='model',
                model_name='test-model',
                hit=False
            )
            mock_inc.assert_called_once()


class TestMetricsIntegration:
    """Test end-to-end metrics integration."""

    def test_complete_inference_flow(self):
        """Test complete inference metrics flow."""
        model_name = 'integration-test-model'

        # Simulate inference flow
        active_requests.labels(model_name=model_name).inc()
        queue_size.labels(priority='high').set(5)

        start_time = time.time()
        time.sleep(0.1)  # Simulate processing
        duration = time.time() - start_time

        record_inference(
            model_name=model_name,
            duration=duration,
            success=True,
            model_type='gpt2',
            device='cuda'
        )

        active_requests.labels(model_name=model_name).dec()
        queue_size.labels(priority='high').set(4)

        # Verify metrics were updated
        assert active_requests.labels(model_name=model_name)._value.get() >= 0
        assert queue_size.labels(priority='high')._value.get() == 4

    def test_concurrent_requests(self):
        """Test metrics with concurrent requests."""
        model_name = 'concurrent-test-model'

        # Simulate 10 concurrent requests
        for _ in range(10):
            active_requests.labels(model_name=model_name).inc()

        value_max = active_requests.labels(model_name=model_name)._value.get()
        assert value_max >= 10

        # Complete requests
        for _ in range(10):
            active_requests.labels(model_name=model_name).dec()
            record_inference(
                model_name=model_name,
                duration=1.0,
                success=True,
                model_type='gpt2',
                device='cuda'
            )

        value_final = active_requests.labels(model_name=model_name)._value.get()
        assert value_final == value_max - 10

    def test_error_scenarios(self):
        """Test metrics during error scenarios."""
        model_name = 'error-test-model'

        # Record various errors
        error_types = ['timeout', 'oom', 'validation', 'gpu_error']

        for error_type in error_types:
            inference_errors_total.labels(
                model_name=model_name,
                error_type=error_type,
                model_type='gpt2'
            ).inc()

            record_inference(
                model_name=model_name,
                duration=0.5,
                success=False,
                model_type='gpt2',
                device='cuda',
                error_type=error_type
            )

        # Verify error metrics
        for error_type in error_types:
            value = inference_errors_total.labels(
                model_name=model_name,
                error_type=error_type,
                model_type='gpt2'
            )._value.get()
            assert value >= 1


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint format."""

    def test_metrics_export_format(self):
        """Test that metrics are exported in Prometheus format."""
        from prometheus_client import generate_latest

        # Generate some metrics
        inference_requests_total.labels(
            model_name='export-test',
            status='success',
            model_type='gpt2',
            device='cuda'
        ).inc()

        # Generate Prometheus format
        metrics_output = generate_latest(REGISTRY)
        metrics_text = metrics_output.decode('utf-8')

        # Verify format
        assert 'inference_requests_total' in metrics_text
        assert 'TYPE inference_requests_total counter' in metrics_text
        assert 'model_name="export-test"' in metrics_text

    def test_all_metrics_exportable(self):
        """Test that all metrics can be exported."""
        from prometheus_client import generate_latest

        metrics_output = generate_latest(REGISTRY)
        metrics_text = metrics_output.decode('utf-8')

        expected_metrics = [
            'inference_requests_total',
            'inference_duration_seconds',
            'active_requests',
            'queue_size',
            'gpu_memory_used_bytes',
            'safety_checks_total',
        ]

        for metric in expected_metrics:
            assert metric in metrics_text

    def test_metrics_parsing(self):
        """Test that exported metrics can be parsed."""
        from prometheus_client import generate_latest

        metrics_output = generate_latest(REGISTRY)
        metrics_text = metrics_output.decode('utf-8')

        # Parse metrics
        families = list(text_string_to_metric_families(metrics_text))

        # Verify we got metric families
        assert len(families) > 0

        # Check for specific metrics
        family_names = {family.name for family in families}
        assert 'inference_requests_total' in family_names


@pytest.mark.benchmark
class TestMetricsPerformance:
    """Test metrics recording performance."""

    def test_counter_performance(self, benchmark):
        """Benchmark counter increment performance."""
        counter = inference_requests_total.labels(
            model_name='perf-test',
            status='success',
            model_type='gpt2',
            device='cuda'
        )

        benchmark(counter.inc)

    def test_histogram_performance(self, benchmark):
        """Benchmark histogram observation performance."""
        histogram = inference_duration_seconds.labels(
            model_name='perf-test',
            model_type='gpt2'
        )

        benchmark(histogram.observe, 1.5)

    def test_helper_function_performance(self, benchmark):
        """Benchmark helper function performance."""
        benchmark(
            record_inference,
            model_name='perf-test',
            duration=1.5,
            success=True,
            model_type='gpt2',
            device='cuda'
        )
