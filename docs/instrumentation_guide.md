# Instrumentation Guide for Prometheus Metrics

This guide shows exactly how to instrument existing code with the new Prometheus metrics.

## 1. Instrument VLA Inference Service

**File:** `/src/services/vla_inference.py`

### Add Imports
```python
# Add to existing imports at top of file
from src.monitoring.prometheus_metrics import (
    inference_queue_depth,
    inference_workers_active,
    record_inference_request,
    update_queue_metrics,
)
from src.monitoring.gpu_monitor import gpu_monitor
```

### Instrument `start()` Method
```python
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

    # ADD THIS: Update worker count metric
    inference_workers_active.set(len(self._workers))

    logger.info("Inference service started")
```

### Instrument `_process_request()` Method - Success Case
```python
# In the success return block (around line 210):
# Calculate total latency
total_latency_ms = int((time.time() - start_time) * 1000)

# ADD THIS: Record metrics
record_inference_request(
    model=request.model_id,
    robot_type=request.robot_type,
    status="success",
    duration_seconds=total_latency_ms / 1000.0,
    queue_wait_seconds=queue_wait_ms / 1000.0,
    gpu_compute_seconds=inference_ms / 1000.0,
    safety_score=1.0,  # Will be updated by safety check
)

return InferenceResult(
    request_id=request.request_id,
    action=action,
    latency_ms=total_latency_ms,
    queue_wait_ms=queue_wait_ms,
    inference_ms=inference_ms,
    success=True,
)
```

### Instrument `_process_request()` Method - Error Case
```python
# In the exception handler (around line 220):
except Exception as e:
    logger.error(f"Inference failed: {e}", exc_info=True)
    total_latency_ms = int((time.time() - start_time) * 1000)

    # ADD THIS: Record error metrics
    record_inference_request(
        model=request.model_id,
        robot_type=request.robot_type,
        status="error",
        duration_seconds=total_latency_ms / 1000.0,
        queue_wait_seconds=queue_wait_ms / 1000.0,
        gpu_compute_seconds=0.0,
        safety_score=0.0,
    )

    return InferenceResult(
        request_id=request.request_id,
        action=[],
        latency_ms=total_latency_ms,
        queue_wait_ms=queue_wait_ms,
        inference_ms=0,
        success=False,
        error=str(e),
    )
```

### Instrument `get_queue_depth()` Method
```python
def get_queue_depth(self) -> int:
    """Get current queue depth.

    Returns:
        Number of requests in queue
    """
    depth = self._queue.qsize()

    # ADD THIS: Update Prometheus metrics
    update_queue_metrics(depth, settings.inference_queue_max_size)

    return depth
```

### Add GPU Memory Tracking Context Manager
```python
# In _process_request(), wrap inference with GPU tracking:
# Run inference
inference_start = time.time()

# ADD THIS: Track GPU memory during inference
with gpu_monitor.track_inference_memory(request.model_id, device_id=0):
    with torch.no_grad():
        outputs = model(**inputs)

inference_ms = int((time.time() - inference_start) * 1000)
```

## 2. Instrument Rate Limiting Middleware

**File:** `/src/middleware/rate_limiting.py`

### Add Imports
```python
# Add to existing imports
from src.monitoring.prometheus_metrics import (
    rate_limit_hits_total,
    rate_limit_tokens_remaining,
    record_rate_limit_hit,
)
```

### Instrument `check_rate_limit()` Function
```python
async def check_rate_limit(
    api_key: APIKeyInfo = Depends(get_current_api_key),
) -> APIKeyInfo:
    """FastAPI dependency to check rate limits."""
    if not settings.rate_limit_enabled:
        return api_key

    # Check if monthly quota exceeded
    if api_key.is_quota_exceeded():
        # ADD THIS: Record rate limit hit
        record_rate_limit_hit(str(api_key.customer_id), "monthly")

        raise RateLimitExceeded(
            retry_after=86400,
            limits={
                "monthly_quota": api_key.monthly_quota,
                "monthly_usage": api_key.monthly_usage,
            },
        )

    # Check rate limits
    allowed, retry_after = await check_rate_limit_internal(
        str(api_key.customer_id),
        api_key.rate_limit_rpm,
        api_key.rate_limit_rpd,
    )

    if not allowed:
        # ADD THIS: Record rate limit hit
        record_rate_limit_hit(str(api_key.customer_id), "rpm_or_rpd")

        raise RateLimitExceeded(
            retry_after=retry_after,
            limits={
                "requests_per_minute": api_key.rate_limit_rpm,
                "requests_per_day": api_key.rate_limit_rpd,
            },
        )

    # ADD THIS: Update remaining tokens gauge
    remaining = await get_remaining_requests(api_key)
    rate_limit_tokens_remaining.labels(
        customer_id=str(api_key.customer_id),
        limit_type="rpm"
    ).set(remaining["requests_remaining_minute"])

    return api_key
```

## 3. Instrument Inference Router

**File:** `/src/api/routers/inference.py`

### Add Imports
```python
# Add to existing imports
from src.monitoring.prometheus_metrics import (
    record_http_request,
    record_safety_check,
)
```

### Instrument `infer_action()` Endpoint
```python
@router.post("/v1/inference", response_model=InferenceResponse)
async def infer_action(
    request: InferenceRequest,
    api_key: APIKeyInfo = Depends(get_authenticated_user),
    session: AsyncSession = Depends(get_db),
):
    """Perform VLA inference to predict robot action."""
    request_id = uuid4()
    start_time = time.time()

    # ... existing code ...

    try:
        # ... inference logic ...

        # 5. Safety evaluation
        safety_start = time.time()

        safety_config = request.safety or {}
        safety_result = safety_monitor.evaluate_action(
            action=inference_result.action,
            robot_type=robot_type,
            robot_config=robot_config_dict,
            current_pose=None,
            context={
                "image": image,
                "instruction": request.instruction,
                "model": request.model,
            },
        )

        safety_end = time.time()

        # ADD THIS: Record safety check metrics
        record_safety_check(
            is_safe=safety_result["is_safe"],
            safety_score=safety_result["overall_score"],
            modifications_applied=safety_result["modifications_applied"],
            duration_seconds=(safety_end - safety_start),
            violations=safety_result.get("flags", []),
        )

        # ... rest of code ...

        # ADD THIS: Record HTTP request metrics at the end
        total_duration = time.time() - start_time
        record_http_request(
            method="POST",
            endpoint="/v1/inference",
            status_code=200,
            duration_seconds=total_duration,
        )

        return response

    except HTTPException as e:
        # ADD THIS: Record HTTP error
        total_duration = time.time() - start_time
        record_http_request(
            method="POST",
            endpoint="/v1/inference",
            status_code=e.status_code,
            duration_seconds=total_duration,
        )
        await session.rollback()
        raise

    except Exception as e:
        # ADD THIS: Record HTTP error
        total_duration = time.time() - start_time
        record_http_request(
            method="POST",
            endpoint="/v1/inference",
            status_code=500,
            duration_seconds=total_duration,
        )
        # ... existing error handling ...
```

## 4. Update Application Startup

**File:** `/src/main.py`

### Add Imports
```python
from src.monitoring.gpu_monitor import start_gpu_monitoring, stop_gpu_monitoring
from src.api.routers import monitoring
```

### Register Monitoring Router
```python
# Add to existing router registrations
app.include_router(monitoring.router)
```

### Add GPU Monitoring to Startup
```python
@app.on_event("startup")
async def startup_event():
    """Application startup event handler."""
    logger.info("Starting VLA API application")

    # Initialize database
    await db_manager.initialize()

    # Initialize Redis
    await redis_manager.initialize()

    # Load models
    await model_manager.load_models()

    # Start inference service
    await start_inference_service()

    # ADD THIS: Start GPU monitoring
    await start_gpu_monitoring()

    logger.info("Application startup complete")
```

### Add GPU Monitoring to Shutdown
```python
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event handler."""
    logger.info("Shutting down VLA API application")

    # Stop inference service
    await stop_inference_service()

    # ADD THIS: Stop GPU monitoring
    await stop_gpu_monitoring()

    # Close database
    await db_manager.close()

    # Close Redis
    await redis_manager.close()

    logger.info("Application shutdown complete")
```

## 5. Add Dependencies

**File:** `requirements.txt`

```txt
# Add these dependencies
prometheus-client>=0.19.0
nvidia-ml-py3>=7.352.0  # For GPU monitoring
```

Install:
```bash
pip install prometheus-client nvidia-ml-py3
```

## 6. Configure Application Settings

**File:** `/src/core/config.py`

Add configuration:
```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Metrics configuration
    metrics_enabled: bool = True
    metrics_port: int = 8000  # Same as API port
    gpu_monitoring_enabled: bool = True
    gpu_monitoring_interval: int = 5  # seconds
```

## Quick Integration Checklist

- [ ] Add imports to `vla_inference.py`
- [ ] Instrument `start()` method
- [ ] Instrument `_process_request()` success case
- [ ] Instrument `_process_request()` error case
- [ ] Instrument `get_queue_depth()`
- [ ] Add GPU memory tracking
- [ ] Add imports to `rate_limiting.py`
- [ ] Instrument `check_rate_limit()`
- [ ] Add imports to `inference.py`
- [ ] Instrument safety checks
- [ ] Instrument HTTP requests
- [ ] Update `main.py` with GPU monitoring
- [ ] Register monitoring router
- [ ] Add dependencies to `requirements.txt`
- [ ] Install new dependencies
- [ ] Test metrics endpoint: `curl http://localhost:8000/monitoring/metrics`
- [ ] Verify GPU stats: `curl -H "X-API-Key: test" http://localhost:8000/gpu/stats`
- [ ] Set up Prometheus scraping
- [ ] Create Grafana dashboards

## Testing the Instrumentation

### 1. Start the Application
```bash
uvicorn src.main:app --reload
```

### 2. Check Metrics Endpoint
```bash
curl http://localhost:8000/monitoring/metrics
```

Expected output should include:
```
# HELP vla_inference_requests_total Total number of inference requests
# TYPE vla_inference_requests_total counter
vla_inference_requests_total{model="openvla-7b",robot_type="franka_panda",status="success"} 42.0

# HELP vla_gpu_utilization_percent GPU utilization percentage
# TYPE vla_gpu_utilization_percent gauge
vla_gpu_utilization_percent{device="0",device_name="NVIDIA GeForce RTX 3090"} 65.0

# ... more metrics ...
```

### 3. Generate Load and Check Metrics
```bash
# Run inference requests
curl -X POST http://localhost:8000/v1/inference \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d @test_request.json

# Check metrics updated
curl http://localhost:8000/monitoring/metrics | grep vla_inference_requests_total
```

### 4. Check GPU Monitoring
```bash
curl -H "X-API-Key: your-key" http://localhost:8000/gpu/stats
```

Expected output:
```json
{
  "available": true,
  "device_count": 1,
  "devices": [
    {
      "device_id": 0,
      "name": "NVIDIA GeForce RTX 3090",
      "utilization_percent": 65.2,
      "memory": {
        "used_gb": 18.4,
        "total_gb": 24.0,
        "utilization_percent": 76.7
      },
      "temperature_celsius": 72,
      "power": {
        "usage_watts": 285.5,
        "limit_watts": 350.0,
        "utilization_percent": 81.6
      }
    }
  ]
}
```

## Common Issues and Fixes

### Issue: `ModuleNotFoundError: No module named 'pynvml'`
**Fix:** Install nvidia-ml-py3
```bash
pip install nvidia-ml-py3
```

### Issue: GPU monitoring not working
**Fix:** Check NVIDIA drivers installed
```bash
nvidia-smi
```

### Issue: Metrics endpoint returns empty
**Fix:** Ensure metrics are being recorded. Add debug logging:
```python
logger.info(f"Recording metric: {model}, {status}")
record_inference_request(...)
```

### Issue: Prometheus can't scrape metrics
**Fix:** Check Prometheus configuration:
```yaml
scrape_configs:
  - job_name: 'vla-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/monitoring/metrics'
```

## Next Steps

1. Set up Prometheus server
2. Configure Grafana dashboards
3. Define alerting rules
4. Monitor in production
5. Tune metric collection intervals
6. Add custom business metrics as needed

## Support

For issues or questions:
- Check logs for instrumentation errors
- Verify all imports are correct
- Test metrics endpoint manually
- Check Prometheus scrape targets
- Review Grafana data sources
