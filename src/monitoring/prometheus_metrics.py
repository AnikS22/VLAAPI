"""Prometheus metrics registry for VLA API platform."""

from prometheus_client import Counter, Gauge, Histogram, Info, Summary

# ============================================================================
# REQUEST METRICS
# ============================================================================

# Total inference requests
inference_requests_total = Counter(
    "vla_inference_requests_total",
    "Total number of inference requests",
    ["model", "robot_type", "status"],
)

# Inference request duration
inference_duration_seconds = Histogram(
    "vla_inference_duration_seconds",
    "Inference request latency in seconds",
    ["model", "robot_type"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# Inference queue wait time
inference_queue_wait_seconds = Histogram(
    "vla_inference_queue_wait_seconds",
    "Time spent waiting in inference queue",
    ["model"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)

# GPU compute time
inference_gpu_compute_seconds = Histogram(
    "vla_inference_gpu_compute_seconds",
    "GPU compute time for inference",
    ["model"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
)

# ============================================================================
# QUEUE METRICS
# ============================================================================

# Current queue depth
inference_queue_depth = Gauge(
    "vla_inference_queue_depth",
    "Current number of requests in inference queue",
)

# Queue capacity
inference_queue_capacity = Gauge(
    "vla_inference_queue_capacity",
    "Maximum capacity of inference queue",
)

# Queue utilization percentage
inference_queue_utilization = Gauge(
    "vla_inference_queue_utilization",
    "Inference queue utilization percentage (0-100)",
)

# ============================================================================
# GPU METRICS
# ============================================================================

# GPU utilization percentage
gpu_utilization_percent = Gauge(
    "vla_gpu_utilization_percent",
    "GPU utilization percentage",
    ["device", "device_name"],
)

# GPU memory used
gpu_memory_used_bytes = Gauge(
    "vla_gpu_memory_used_bytes",
    "GPU memory used in bytes",
    ["device", "device_name"],
)

# GPU memory total
gpu_memory_total_bytes = Gauge(
    "vla_gpu_memory_total_bytes",
    "Total GPU memory in bytes",
    ["device", "device_name"],
)

# GPU memory utilization percentage
gpu_memory_utilization_percent = Gauge(
    "vla_gpu_memory_utilization_percent",
    "GPU memory utilization percentage",
    ["device", "device_name"],
)

# GPU temperature
gpu_temperature_celsius = Gauge(
    "vla_gpu_temperature_celsius",
    "GPU temperature in Celsius",
    ["device", "device_name"],
)

# GPU power usage
gpu_power_watts = Gauge(
    "vla_gpu_power_watts",
    "GPU power consumption in watts",
    ["device", "device_name"],
)

# GPU compute mode
gpu_compute_mode = Gauge(
    "vla_gpu_compute_mode",
    "GPU compute mode (0=default, 1=exclusive_thread, 2=prohibited, 3=exclusive_process)",
    ["device", "device_name"],
)

# Per-inference GPU memory delta
inference_gpu_memory_delta_bytes = Histogram(
    "vla_inference_gpu_memory_delta_bytes",
    "GPU memory change during inference",
    ["model", "device"],
    buckets=[
        1024 * 1024,  # 1 MB
        10 * 1024 * 1024,  # 10 MB
        50 * 1024 * 1024,  # 50 MB
        100 * 1024 * 1024,  # 100 MB
        500 * 1024 * 1024,  # 500 MB
        1024 * 1024 * 1024,  # 1 GB
        2 * 1024 * 1024 * 1024,  # 2 GB
    ],
)

# ============================================================================
# SAFETY METRICS
# ============================================================================

# Safety check results
safety_checks_total = Counter(
    "vla_safety_checks_total",
    "Total number of safety checks performed",
    ["result"],  # safe, unsafe, modified
)

# Safety rejections
safety_rejections_total = Counter(
    "vla_safety_rejections_total",
    "Total number of safety rejections",
    ["severity", "violation_type"],
)

# Safety modifications
safety_modifications_total = Counter(
    "vla_safety_modifications_total",
    "Total number of actions modified for safety",
    ["modification_type"],
)

# Safety score distribution
safety_score_distribution = Histogram(
    "vla_safety_score",
    "Distribution of safety scores",
    ["robot_type"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0],
)

# Safety check duration
safety_check_duration_seconds = Histogram(
    "vla_safety_check_duration_seconds",
    "Time spent performing safety checks",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

# ============================================================================
# DATA VALIDATION METRICS
# ============================================================================

# Validation failures
validation_failures_total = Counter(
    "vla_validation_failures_total",
    "Total number of validation failures",
    ["field", "reason"],
)

# Image processing errors
image_processing_errors_total = Counter(
    "vla_image_processing_errors_total",
    "Total number of image processing errors",
    ["error_type"],
)

# Image decoding duration
image_decode_duration_seconds = Histogram(
    "vla_image_decode_duration_seconds",
    "Time spent decoding images",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

# ============================================================================
# RATE LIMITING METRICS
# ============================================================================

# Rate limit hits
rate_limit_hits_total = Counter(
    "vla_rate_limit_hits_total",
    "Total number of rate limit hits",
    ["customer_id", "limit_type"],  # rpm, rpd, monthly
)

# Rate limit tokens remaining
rate_limit_tokens_remaining = Gauge(
    "vla_rate_limit_tokens_remaining",
    "Remaining rate limit tokens",
    ["customer_id", "limit_type"],
)

# Quota usage
quota_usage_percent = Gauge(
    "vla_quota_usage_percent",
    "Monthly quota usage percentage",
    ["customer_id"],
)

# ============================================================================
# DATABASE METRICS
# ============================================================================

# Database query duration
database_query_duration_seconds = Histogram(
    "vla_database_query_duration_seconds",
    "Database query execution time",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

# Database connection pool
database_pool_size = Gauge(
    "vla_database_pool_size",
    "Current size of database connection pool",
)

database_pool_available = Gauge(
    "vla_database_pool_available",
    "Available connections in database pool",
)

database_pool_used = Gauge(
    "vla_database_pool_used",
    "Used connections in database pool",
)

# ============================================================================
# REDIS METRICS
# ============================================================================

# Redis operations
redis_operations_total = Counter(
    "vla_redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],
)

# Redis operation duration
redis_operation_duration_seconds = Histogram(
    "vla_redis_operation_duration_seconds",
    "Redis operation duration",
    ["operation"],
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1],
)

# ============================================================================
# MODEL METRICS
# ============================================================================

# Model load time
model_load_duration_seconds = Histogram(
    "vla_model_load_duration_seconds",
    "Time to load model into memory",
    ["model"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

# Model memory usage
model_memory_bytes = Gauge(
    "vla_model_memory_bytes",
    "Memory used by loaded model",
    ["model"],
)

# Models loaded
models_loaded = Gauge(
    "vla_models_loaded",
    "Number of models currently loaded",
)

# Model info
model_info = Info(
    "vla_model",
    "Information about loaded models",
)

# ============================================================================
# WORKER METRICS
# ============================================================================

# Active workers
inference_workers_active = Gauge(
    "vla_inference_workers_active",
    "Number of active inference workers",
)

# Worker utilization
inference_worker_utilization_percent = Gauge(
    "vla_inference_worker_utilization_percent",
    "Average worker utilization percentage",
)

# Worker task processing time
worker_task_duration_seconds = Histogram(
    "vla_worker_task_duration_seconds",
    "Worker task processing time",
    ["worker_id"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# ============================================================================
# API METRICS
# ============================================================================

# HTTP requests
http_requests_total = Counter(
    "vla_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

# HTTP request duration
http_request_duration_seconds = Histogram(
    "vla_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Active connections
http_connections_active = Gauge(
    "vla_http_connections_active",
    "Number of active HTTP connections",
)

# ============================================================================
# ERROR METRICS
# ============================================================================

# Total errors
errors_total = Counter(
    "vla_errors_total",
    "Total number of errors",
    ["error_type", "component"],
)

# Exception counts
exceptions_total = Counter(
    "vla_exceptions_total",
    "Total number of exceptions",
    ["exception_class", "component"],
)

# ============================================================================
# BUSINESS METRICS
# ============================================================================

# Customer usage
customer_requests_total = Counter(
    "vla_customer_requests_total",
    "Total requests per customer",
    ["customer_id"],
)

# Revenue tracking (if applicable)
revenue_generated = Counter(
    "vla_revenue_generated",
    "Total revenue generated",
    ["customer_tier"],
)

# ============================================================================
# SYSTEM METRICS
# ============================================================================

# Application info
application_info = Info(
    "vla_application",
    "Application version and build information",
)

# Uptime
application_uptime_seconds = Gauge(
    "vla_application_uptime_seconds",
    "Application uptime in seconds",
)

# Health status
application_health = Gauge(
    "vla_application_health",
    "Application health status (1=healthy, 0=unhealthy)",
    ["component"],
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def record_inference_request(
    model: str,
    robot_type: str,
    status: str,
    duration_seconds: float,
    queue_wait_seconds: float,
    gpu_compute_seconds: float,
    safety_score: float,
):
    """Record metrics for an inference request.

    Args:
        model: Model identifier
        robot_type: Robot type
        status: Request status (success, error, rejected)
        duration_seconds: Total request duration
        queue_wait_seconds: Time spent in queue
        gpu_compute_seconds: GPU compute time
        safety_score: Safety evaluation score
    """
    inference_requests_total.labels(
        model=model, robot_type=robot_type, status=status
    ).inc()

    inference_duration_seconds.labels(model=model, robot_type=robot_type).observe(
        duration_seconds
    )

    inference_queue_wait_seconds.labels(model=model).observe(queue_wait_seconds)

    inference_gpu_compute_seconds.labels(model=model).observe(gpu_compute_seconds)

    safety_score_distribution.labels(robot_type=robot_type).observe(safety_score)


def update_queue_metrics(current_depth: int, max_size: int):
    """Update queue metrics.

    Args:
        current_depth: Current queue size
        max_size: Maximum queue capacity
    """
    inference_queue_depth.set(current_depth)
    inference_queue_capacity.set(max_size)

    utilization = (current_depth / max_size * 100) if max_size > 0 else 0
    inference_queue_utilization.set(utilization)


def record_safety_check(
    is_safe: bool,
    safety_score: float,
    modifications_applied: bool,
    duration_seconds: float,
    violations: list = None,
):
    """Record safety check metrics.

    Args:
        is_safe: Whether action is safe
        safety_score: Safety score
        modifications_applied: Whether modifications were applied
        duration_seconds: Safety check duration
        violations: List of safety violations
    """
    if is_safe:
        result = "safe"
    elif modifications_applied:
        result = "modified"
    else:
        result = "unsafe"

    safety_checks_total.labels(result=result).inc()
    safety_check_duration_seconds.observe(duration_seconds)

    if modifications_applied:
        safety_modifications_total.labels(modification_type="action_clipping").inc()

    if violations:
        for violation in violations:
            safety_rejections_total.labels(
                severity=violation.get("severity", "unknown"),
                violation_type=violation.get("type", "unknown"),
            ).inc()


def record_rate_limit_hit(customer_id: str, limit_type: str):
    """Record rate limit hit.

    Args:
        customer_id: Customer identifier
        limit_type: Type of limit hit (rpm, rpd, monthly)
    """
    rate_limit_hits_total.labels(
        customer_id=customer_id, limit_type=limit_type
    ).inc()


def update_gpu_metrics(
    device_id: int,
    device_name: str,
    utilization: float,
    memory_used: int,
    memory_total: int,
    temperature: float,
    power: float,
):
    """Update GPU metrics.

    Args:
        device_id: GPU device ID
        device_name: GPU device name
        utilization: GPU utilization percentage
        memory_used: GPU memory used in bytes
        memory_total: Total GPU memory in bytes
        temperature: GPU temperature in Celsius
        power: GPU power consumption in watts
    """
    device = str(device_id)

    gpu_utilization_percent.labels(device=device, device_name=device_name).set(
        utilization
    )

    gpu_memory_used_bytes.labels(device=device, device_name=device_name).set(
        memory_used
    )

    gpu_memory_total_bytes.labels(device=device, device_name=device_name).set(
        memory_total
    )

    memory_util = (memory_used / memory_total * 100) if memory_total > 0 else 0
    gpu_memory_utilization_percent.labels(device=device, device_name=device_name).set(
        memory_util
    )

    gpu_temperature_celsius.labels(device=device, device_name=device_name).set(
        temperature
    )

    gpu_power_watts.labels(device=device, device_name=device_name).set(power)


def record_http_request(
    method: str, endpoint: str, status_code: int, duration_seconds: float
):
    """Record HTTP request metrics.

    Args:
        method: HTTP method
        endpoint: API endpoint
        status_code: HTTP status code
        duration_seconds: Request duration
    """
    http_requests_total.labels(
        method=method, endpoint=endpoint, status_code=status_code
    ).inc()

    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
        duration_seconds
    )
