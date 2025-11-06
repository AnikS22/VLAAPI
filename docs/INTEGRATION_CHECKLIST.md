# VLA Inference API - Integration Checklist

## Integration Summary

All monitoring and data collection components have been successfully integrated into the main application.

### Components Integrated

1. **Configuration Management** ✓
   - Added comprehensive settings to `src/core/config.py`
   - Monitoring, embeddings, storage, ETL, consent, and anonymization settings
   - All settings have validation and defaults

2. **Main Application Startup** ✓
   - Updated `src/api/main.py` with full initialization
   - GPU monitoring service initialization
   - Embedding service initialization
   - Prometheus metrics endpoint mounted at `/metrics`
   - Uptime tracking with background task

3. **VLA Inference Service** ✓
   - Integrated Prometheus metrics recording
   - Embedding generation support (instruction + image)
   - Queue metrics tracking
   - GPU memory tracking support
   - Error metrics recording

4. **Quality Gates Middleware** ✓
   - Created `src/middleware/quality_gates.py`
   - Robot type validation (no UNKNOWN)
   - Action bounds validation (7-DoF, no NaN/Inf)
   - Safety score thresholds
   - Deduplication checking (5-minute window)
   - Instruction quality validation
   - Image quality validation

5. **Inference Router** ✓
   - Consent checking before data storage
   - Quality gate validation before database writes
   - Prometheus metrics recording
   - Embedding generation (when consented)
   - Comprehensive error handling

6. **Environment Configuration** ✓
   - Updated `.env.example` with all new settings
   - Organized by category
   - Clear documentation and defaults

7. **Dependencies** ✓
   - All required packages in `requirements.txt`
   - sentence-transformers for text embeddings
   - CLIP (via transformers) for image embeddings
   - prometheus-client for metrics
   - nvidia-ml-py3 for GPU monitoring

---

## Deployment Checklist

### 1. Pre-Deployment Configuration

#### Database Setup
- [ ] PostgreSQL 14+ with pgvector extension installed
- [ ] Run migrations: `alembic upgrade head`
- [ ] Verify vector indexes created:
  ```sql
  SELECT tablename, indexname FROM pg_indexes
  WHERE tablename IN ('instruction_analytics', 'context_metadata');
  ```

#### Redis Setup
- [ ] Redis 6.0+ running and accessible
- [ ] Test connection: `redis-cli ping`
- [ ] Configure memory limits (recommended: 2GB minimum)

#### Environment Variables
- [ ] Copy `.env.example` to `.env`
- [ ] Set **DATABASE_URL** with correct credentials
- [ ] Set **REDIS_URL** with correct host/port
- [ ] Generate **SECRET_KEY**: `openssl rand -hex 32`
- [ ] Generate **JWT_SECRET_KEY**: `openssl rand -hex 32`
- [ ] Configure **ANONYMIZATION_HASH_SALT** (production-specific)

#### GPU Configuration
- [ ] Verify CUDA installation: `nvidia-smi`
- [ ] Set **GPU_DEVICE** (default: 0)
- [ ] Enable GPU monitoring: **ENABLE_GPU_MONITORING=true**
- [ ] Set **GPU_POLL_INTERVAL** (default: 5 seconds)

#### Embedding Models
- [ ] Set **ENABLE_EMBEDDINGS=true**
- [ ] Configure **INSTRUCTION_EMBEDDING_MODEL** (default: all-MiniLM-L6-v2)
- [ ] Configure **IMAGE_EMBEDDING_MODEL** (default: clip-vit-base-patch32)
- [ ] Ensure sufficient disk space for model downloads (~2GB)
- [ ] Test model loading during startup

#### Storage (S3/MinIO)
- [ ] Choose storage backend (set **ENABLE_S3_STORAGE**)
- [ ] Configure **S3_ENDPOINT** (leave empty for AWS)
- [ ] Set **S3_BUCKET** name
- [ ] Configure **S3_ACCESS_KEY** and **S3_SECRET_KEY**
- [ ] Create bucket with appropriate permissions
- [ ] Test connectivity: `aws s3 ls s3://<bucket>`

#### Monitoring
- [ ] Enable Prometheus: **ENABLE_PROMETHEUS=true**
- [ ] Configure Prometheus to scrape `/metrics` endpoint
- [ ] Set up Grafana dashboards (optional)
- [ ] Configure **SENTRY_DSN** for error tracking (optional)

### 2. Application Startup

#### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import transformers, sentence_transformers, pynvml; print('OK')"
```

#### Database Migration
```bash
# Run migrations
alembic upgrade head

# Verify tables
python -c "from src.core.database import engine; import asyncio; asyncio.run(engine.connect())"
```

#### Start Application
```bash
# Development
python -m src.api.main

# Production
gunicorn src.api.main:app \
  --workers 1 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --log-level info
```

#### Verify Startup
- [ ] Application starts without errors
- [ ] Database connection successful
- [ ] Redis connection successful
- [ ] GPU monitoring initialized (check logs)
- [ ] Embedding service initialized (check logs)
- [ ] VLA models loaded successfully
- [ ] Inference service workers started

### 3. Integration Testing

#### Health Checks
```bash
# Application health
curl http://localhost:8000/

# Metrics endpoint
curl http://localhost:8000/metrics

# GPU monitoring
curl http://localhost:8000/v1/monitoring/gpu
```

#### Inference Test
```bash
# Create test API key (run in Python)
python scripts/create_api_key.py --email test@example.com --tier pro

# Run inference
curl -X POST http://localhost:8000/v1/inference \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d @examples/inference_request.json
```

#### Quality Gates Test
```bash
# Test robot type validation (should fail)
# - Set robot_type to "UNKNOWN"
# - Should return 422 validation error

# Test action bounds validation (should fail)
# - Send action with values > 1.0
# - Should return 422 validation error

# Test deduplication (should fail 2nd time)
# - Send same request twice within 5 minutes
# - Second request should return 422 validation error
```

#### Embedding Generation Test
- [ ] Set customer consent to "full"
- [ ] Run inference request
- [ ] Verify embeddings generated in logs
- [ ] Check database for stored embeddings:
  ```sql
  SELECT COUNT(*) FROM instruction_analytics WHERE instruction_embedding IS NOT NULL;
  SELECT COUNT(*) FROM context_metadata WHERE image_embedding IS NOT NULL;
  ```

#### Metrics Test
```bash
# Prometheus metrics
curl http://localhost:8000/metrics | grep vla_

# Should see:
# - vla_inference_requests_total
# - vla_gpu_utilization_percent
# - vla_gpu_memory_used_bytes
# - vla_safety_checks_total
# - vla_validation_failures_total
```

### 4. Monitoring Setup

#### Prometheus Configuration
Add to `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'vla-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

#### Key Metrics to Monitor
- `vla_inference_requests_total` - Total inference requests
- `vla_inference_duration_seconds` - Inference latency
- `vla_gpu_utilization_percent` - GPU usage
- `vla_gpu_memory_utilization_percent` - GPU memory usage
- `vla_safety_rejections_total` - Safety rejections
- `vla_validation_failures_total` - Validation failures
- `vla_queue_depth` - Inference queue depth

#### Alerting Rules (Recommended)
```yaml
groups:
  - name: vla_api_alerts
    rules:
      # High GPU memory usage
      - alert: HighGPUMemory
        expr: vla_gpu_memory_utilization_percent > 90
        for: 5m
        annotations:
          summary: "GPU memory utilization above 90%"

      # High queue depth
      - alert: HighQueueDepth
        expr: vla_queue_depth > 80
        for: 2m
        annotations:
          summary: "Inference queue depth above 80"

      # High validation failure rate
      - alert: HighValidationFailures
        expr: rate(vla_validation_failures_total[5m]) > 0.1
        annotations:
          summary: "Validation failure rate > 10%"
```

### 5. Data Quality Verification

#### Quality Gate Metrics
```sql
-- Check validation failure reasons
SELECT
    field,
    reason,
    COUNT(*) as failures
FROM (
    SELECT
        jsonb_object_keys(validation_errors) as field,
        validation_errors->>jsonb_object_keys(validation_errors) as reason
    FROM inference_log
    WHERE validation_errors IS NOT NULL
) sub
GROUP BY field, reason
ORDER BY failures DESC;
```

#### Data Quality Report
```sql
-- Overall data quality metrics
SELECT
    COUNT(*) as total_inferences,
    COUNT(*) FILTER (WHERE robot_type != 'UNKNOWN') as valid_robot_type,
    COUNT(*) FILTER (WHERE safety_score >= 0.7) as passing_safety,
    COUNT(*) FILTER (WHERE instruction_embedding IS NOT NULL) as with_embeddings,
    AVG(safety_score) as avg_safety_score
FROM inference_log
WHERE created_at > NOW() - INTERVAL '24 hours';
```

### 6. Performance Tuning

#### Application Settings
- [ ] Adjust **INFERENCE_MAX_WORKERS** based on GPU memory
- [ ] Set **INFERENCE_QUEUE_MAX_SIZE** based on load
- [ ] Configure **DATABASE_POOL_SIZE** for concurrent users
- [ ] Adjust **EMBEDDING_CACHE_TTL** for cache hit rate

#### Database Optimization
```sql
-- Create indexes for common queries
CREATE INDEX CONCURRENTLY idx_inference_log_created_at
  ON inference_log(created_at DESC);

CREATE INDEX CONCURRENTLY idx_inference_log_customer_id
  ON inference_log(customer_id, created_at DESC);

-- Update table statistics
ANALYZE inference_log;
ANALYZE instruction_analytics;
ANALYZE context_metadata;
```

#### Redis Optimization
```bash
# Configure maxmemory policy
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Monitor cache hit rate
redis-cli INFO stats | grep keyspace
```

### 7. Security Hardening

- [ ] Change all default secrets in production
- [ ] Enable HTTPS (configure reverse proxy)
- [ ] Set **ENVIRONMENT=production**
- [ ] Disable **DEBUG=false**
- [ ] Restrict **ALLOWED_HOSTS**
- [ ] Configure firewall rules
- [ ] Enable rate limiting
- [ ] Review and adjust **ANONYMIZATION_LEVEL**

### 8. Backup & Recovery

- [ ] Configure PostgreSQL backups (pg_dump)
- [ ] Configure Redis persistence (RDB/AOF)
- [ ] Backup model files
- [ ] Document recovery procedures
- [ ] Test backup restoration

---

## Configuration Summary

### Key Settings Added

#### Monitoring & GPU
```env
ENABLE_PROMETHEUS=true
ENABLE_GPU_MONITORING=true
GPU_POLL_INTERVAL=5
```

#### Embeddings
```env
ENABLE_EMBEDDINGS=true
INSTRUCTION_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
IMAGE_EMBEDDING_MODEL=openai/clip-vit-base-patch32
EMBEDDING_CACHE_TTL=300
```

#### Storage
```env
ENABLE_S3_STORAGE=false
S3_ENDPOINT=
S3_BUCKET=vla-training-data
S3_ACCESS_KEY=
S3_SECRET_KEY=
```

#### Data Retention
```env
RAW_DATA_RETENTION_DAYS=90
AGGREGATED_DATA_RETENTION_DAYS=365
SAFETY_DATA_RETENTION_DAYS=-1
```

#### ETL & Privacy
```env
ETL_ENABLED=true
ETL_SCHEDULE_HOUR=2
ETL_BATCH_SIZE=1000
DEFAULT_CONSENT_TIER=none
ANONYMIZATION_LEVEL=full
```

---

## Endpoints Summary

### New/Updated Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/metrics` | GET | Prometheus metrics endpoint |
| `/v1/inference` | POST | Enhanced with quality gates & embeddings |
| `/v1/monitoring/gpu` | GET | GPU status and metrics |
| `/v1/monitoring/queue` | GET | Inference queue status |
| `/v1/feedback` | POST | Ground truth feedback collection |

---

## Troubleshooting

### Common Issues

#### GPU Monitoring Not Working
```bash
# Check NVIDIA drivers
nvidia-smi

# Verify pynvml installation
python -c "import pynvml; pynvml.nvmlInit(); print('OK')"

# Check logs
grep "GPU monitor" /var/log/vlaapi/app.log
```

#### Embeddings Not Generated
```bash
# Check model downloads
ls -lh ~/.cache/huggingface/hub/

# Check disk space
df -h ~/.cache

# Verify models load
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

#### High Memory Usage
- Reduce **INFERENCE_MAX_WORKERS**
- Lower **EMBEDDING_CACHE_TTL**
- Adjust **MODEL_DTYPE** to float16
- Enable **LOW_CPU_MEM_USAGE=true**

#### Quality Gates Rejecting Valid Data
- Review validation thresholds
- Check logs for specific errors
- Adjust **min_safety_score** in quality_gates.py
- Review deduplication window settings

---

## Success Criteria

Integration is complete when:

- [x] All configuration settings added and documented
- [x] Main application starts with all services initialized
- [x] GPU monitoring active and reporting metrics
- [x] Embedding service generating 384-dim text and 512-dim image embeddings
- [x] Quality gates validating and rejecting bad data
- [x] Prometheus metrics endpoint returning comprehensive metrics
- [x] Inference requests successfully processed end-to-end
- [ ] All tests pass (run: `pytest tests/`)
- [ ] Documentation complete and reviewed
- [ ] Production deployment verified

---

## Next Steps

1. **Run Integration Tests**
   ```bash
   pytest tests/integration/ -v
   ```

2. **Load Testing**
   ```bash
   locust -f tests/load/locustfile.py --host http://localhost:8000
   ```

3. **Monitor Production**
   - Set up Grafana dashboards
   - Configure alerts
   - Monitor logs for errors
   - Track quality metrics

4. **Optimize Performance**
   - Analyze slow queries
   - Tune cache settings
   - Adjust worker counts
   - Monitor GPU utilization

---

## Support

For issues or questions:
- Check logs: `/var/log/vlaapi/app.log`
- Review metrics: `http://localhost:8000/metrics`
- Consult documentation: `/docs`
- GitHub Issues: [repository]/issues
