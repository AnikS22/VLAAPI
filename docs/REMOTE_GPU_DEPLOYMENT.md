# 🖥️ Remote GPU Server Deployment Guide

**Deploy VLA API to your Linux server with Titan X GPUs**

---

## 🎯 Your Setup

- **Hardware:** Remote Linux PC with dual Titan X GPUs
- **Goal:** Run real VLA inference with GPU acceleration
- **Network:** SSH access to remote server

---

## 📋 Prerequisites on Remote Server

### 1. Check Your Server

SSH into your server:
```bash
ssh user@your-server-ip
```

Check GPU:
```bash
nvidia-smi
```

You should see both Titan X GPUs:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.xx    Driver Version: 535.xx    CUDA Version: 12.2          |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA GeForce ...  Off  | 00000000:01:00.0 Off |                  N/A |
| 30%   42C    P0    60W / 250W |      0MiB / 12288MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
|   1  NVIDIA GeForce ...  Off  | 00000000:02:00.0 Off |                  N/A |
| 30%   41C    P0    58W / 250W |      0MiB / 12288MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

### 2. Install Required Software

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install NVIDIA Container Toolkit (for Docker GPU access)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version
nvidia-smi
```

### 3. Test Docker GPU Access

```bash
# Test that Docker can access GPU
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu20.04 nvidia-smi

# You should see your GPUs!
```

---

## 🚀 Deployment Steps

### Step 1: Copy Project to Server

**Option A: Using Git (Recommended)**
```bash
# On remote server
cd ~
git clone https://github.com/yourcompany/VLAAPI.git
cd VLAAPI
```

**Option B: Using rsync from your Mac**
```bash
# From your Mac
rsync -avz --exclude 'node_modules' --exclude 'venv' \
  /Users/aniksahai/Desktop/VLAAPI/ \
  user@your-server-ip:~/VLAAPI/
```

### Step 2: Create Remote Configuration

On your remote server, create `.env.remote`:

```bash
cat > .env.remote << 'EOF'
# VLA API Remote GPU Configuration

# ============================================================================
# APPLICATION
# ============================================================================
ENVIRONMENT=development
DEBUG=true
USE_MOCK_MODELS=false  # ← REAL MODELS with GPU!

# API
API_HOST=0.0.0.0
API_PORT=8000

# ============================================================================
# GPU CONFIGURATION
# ============================================================================
GPU_DEVICE=0  # Use first Titan X (or 1 for second GPU)
MODEL_DTYPE=float16  # Titan X works best with float16
LOW_CPU_MEM_USAGE=true
TRUST_REMOTE_CODE=true

# Models to load
ENABLED_MODELS=openvla-7b
DEFAULT_MODEL=openvla-7b

# ============================================================================
# DATABASE (PostgreSQL)
# ============================================================================
DATABASE_URL=postgresql+asyncpg://vlaapi:remote_password_456@localhost:5432/vlaapi
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=5

# ============================================================================
# REDIS (Cache)
# ============================================================================
REDIS_URL=redis://:remote_redis_456@localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# ============================================================================
# MONITORING
# ============================================================================
ENABLE_PROMETHEUS=true
ENABLE_GPU_MONITORING=true  # ← Monitor your Titan X!
GPU_POLL_INTERVAL=5

# ============================================================================
# INFERENCE SETTINGS
# ============================================================================
INFERENCE_QUEUE_MAX_SIZE=50
INFERENCE_MAX_WORKERS=2  # Start with 2 workers
INFERENCE_TIMEOUT_SECONDS=30

# ============================================================================
# SAFETY
# ============================================================================
SAFETY_ENABLE_WORKSPACE_CHECK=true
SAFETY_ENABLE_VELOCITY_CHECK=true
SAFETY_DEFAULT_THRESHOLD=0.8

# ============================================================================
# SECURITY
# ============================================================================
SECRET_KEY=remote-development-secret-change-in-production
API_KEY_PREFIX=vla_remote
EOF
```

### Step 3: Create Docker Compose for Remote GPU

Create `docker-compose.remote.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15
    container_name: vlaapi-postgres-remote
    environment:
      POSTGRES_DB: vlaapi
      POSTGRES_USER: vlaapi
      POSTGRES_PASSWORD: remote_password_456
    ports:
      - "5432:5432"
    volumes:
      - postgres-data-remote:/var/lib/postgresql/data
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: vlaapi-redis-remote
    command: redis-server --requirepass remote_redis_456
    ports:
      - "6379:6379"
    volumes:
      - redis-data-remote:/data
    restart: unless-stopped

  # VLA API Server with GPU
  api:
    build:
      context: .
      dockerfile: Dockerfile.gpu
    container_name: vlaapi-api-remote
    ports:
      - "8000:8000"
    env_file:
      - .env.remote
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']  # Use first GPU
              capabilities: [gpu]
    depends_on:
      - postgres
      - redis
    volumes:
      - ./src:/app/src:ro
      - ./config:/app/config:ro
      - model-cache:/root/.cache  # Cache downloaded models
    restart: unless-stopped
    shm_size: '8gb'  # Shared memory for GPU

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: vlaapi-prometheus-remote
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus-remote.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data-remote:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    restart: unless-stopped

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: vlaapi-grafana-remote
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin123
    volumes:
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana/datasources-remote.yml:/etc/grafana/provisioning/datasources/datasources.yml:ro
      - grafana-data-remote:/var/lib/grafana
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  postgres-data-remote:
  redis-data-remote:
  prometheus-data-remote:
  grafana-data-remote:
  model-cache:
```

### Step 4: Create GPU Dockerfile

Create `Dockerfile.gpu`:

```dockerfile
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

LABEL description="VLA Inference API - GPU Enabled"
LABEL version="remote-gpu"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src ./src
COPY config ./config

# Create directories
RUN mkdir -p /app/logs /root/.cache

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run with GPU support
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 5: Create Monitoring Configs

Create `monitoring/prometheus/prometheus-remote.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'vla-api-remote'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
```

Create `monitoring/grafana/datasources-remote.yml`:

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

### Step 6: Deploy!

```bash
# On remote server
cd ~/VLAAPI

# Start all services
docker-compose -f docker-compose.remote.yml up -d --build

# This will:
# 1. Build Docker image with GPU support
# 2. Download VLA model (~16GB - first time only)
# 3. Start PostgreSQL, Redis, API, monitoring
# Takes 10-15 minutes first time
```

### Step 7: Initialize Database

```bash
# Wait for services to start
sleep 60

# Initialize database
docker exec vlaapi-api-remote python -c "
import asyncio
import sys
sys.path.insert(0, '/app')
from src.models.database import Base
from sqlalchemy.ext.asyncio import create_async_engine

async def init():
    engine = create_async_engine('postgresql+asyncpg://vlaapi:remote_password_456@postgres:5432/vlaapi')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init())
"

# Install pgvector extension
docker exec vlaapi-postgres-remote psql -U vlaapi -d vlaapi -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Step 8: Create Test Customer

```bash
docker exec vlaapi-api-remote python << 'PYTHON_EOF'
import asyncio
import sys
sys.path.insert(0, '/app')
from uuid import uuid4
from datetime import datetime
import hashlib
import secrets
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models.database import Customer, APIKey

async def create_test_customer():
    # Generate API key
    random_part = secrets.token_urlsafe(32)
    api_key = f"vla_remote_{random_part}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    engine = create_async_engine('postgresql+asyncpg://vlaapi:remote_password_456@postgres:5432/vlaapi')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        async with session.begin():
            customer = Customer(
                customer_id=uuid4(),
                company_name="Test Customer (Remote GPU)",
                email="test@remote.com",
                tier="pro",
                is_active=True,
                monthly_quota=100000,
                monthly_usage=0,
                created_at=datetime.utcnow()
            )
            session.add(customer)
            await session.flush()
            
            api_key_obj = APIKey(
                key_id=uuid4(),
                customer_id=customer.customer_id,
                key_hash=key_hash,
                key_prefix=api_key[:20],
                is_active=True,
                rate_limit_per_minute=100,
                rate_limit_per_day=10000,
                created_at=datetime.utcnow()
            )
            session.add(api_key_obj)
    
    print(f"API_KEY={api_key}")

asyncio.run(create_test_customer())
PYTHON_EOF

# Save the API key that gets printed!
```

---

## 🧪 Testing Your GPU Deployment

### Test 1: Check Services

```bash
# Check all containers are running
docker ps

# Expected:
# vlaapi-api-remote       (healthy)
# vlaapi-postgres-remote  (Up)
# vlaapi-redis-remote     (Up)
# vlaapi-prometheus-remote (Up)
# vlaapi-grafana-remote   (Up)
```

### Test 2: Check GPU Access

```bash
# Check API can see GPU
docker exec vlaapi-api-remote nvidia-smi

# Check logs for model loading
docker logs vlaapi-api-remote | grep -i "loading model"
docker logs vlaapi-api-remote | grep -i "gpu"
```

### Test 3: Make API Call from Your Mac

From your local Mac:

```bash
# Replace with your server IP and API key
export SERVER_IP="your-server-ip"
export API_KEY="vla_remote_YOUR_KEY_HERE"

# Test health
curl http://$SERVER_IP:8000/health

# Test real GPU inference!
curl -X POST http://$SERVER_IP:8000/v1/inference \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openvla-7b",
    "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "instruction": "pick up the red cube",
    "robot_config": {"type": "franka_panda"}
  }'

# Should return real GPU-computed action!
```

### Test 4: View Dashboards

Open in your browser (replace with your server IP):

- **Grafana:** http://your-server-ip:3000
- **Prometheus:** http://your-server-ip:9090
- **API Docs:** http://your-server-ip:8000/docs

---

## 📊 Monitor GPU Usage

### Real-Time GPU Monitoring

```bash
# Watch GPU usage
watch -n 1 nvidia-smi

# View GPU metrics in API
curl http://your-server-ip:8000/monitoring/gpu/stats | jq
```

### Check Performance

```bash
# View logs with GPU timing
docker logs -f vlaapi-api-remote | grep "inference_ms"

# You should see real GPU inference times:
# inference_ms: 120-150ms (with GPU)
# vs 500-1000ms+ (without GPU)
```

---

## 🔧 Configuration Options

### Use Second GPU

Edit `.env.remote`:
```bash
GPU_DEVICE=1  # Use second Titan X
```

Restart:
```bash
docker-compose -f docker-compose.remote.yml restart api
```

### Use Both GPUs (Advanced)

Run two API instances:

```bash
# First instance on GPU 0
docker-compose -f docker-compose.remote.yml up -d

# Second instance on GPU 1 (different port)
# Edit docker-compose.remote-gpu1.yml to use GPU 1 and port 8001
docker-compose -f docker-compose.remote-gpu1.yml up -d

# Load balance between them with nginx
```

---

## 🐛 Troubleshooting

### GPU Not Detected

```bash
# Check NVIDIA driver
nvidia-smi

# Check Docker can access GPU
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu20.04 nvidia-smi

# Check container GPU access
docker exec vlaapi-api-remote nvidia-smi
```

### Out of Memory

Titan X has 12GB VRAM. If you get OOM:

Edit `.env.remote`:
```bash
MODEL_DTYPE=float16  # Use half precision
LOW_CPU_MEM_USAGE=true
INFERENCE_BATCH_SIZE=1  # Process one at a time
```

### Model Download Slow

First model download is ~16GB. To speed up:

```bash
# Pre-download models
docker exec vlaapi-api-remote python -c "
from transformers import AutoModel, AutoProcessor
model = AutoModel.from_pretrained('openvla/openvla-7b')
processor = AutoProcessor.from_pretrained('openvla/openvla-7b')
"
```

### Can't Access from Mac

```bash
# Check firewall on server
sudo ufw status
sudo ufw allow 8000/tcp
sudo ufw allow 3000/tcp
sudo ufw allow 9090/tcp

# Or for development, temporarily disable
sudo ufw disable
```

---

## 📈 Performance Expectations

### Titan X GPU Performance

| Metric | Expected Value |
|--------|---------------|
| **First inference** | 10-15 seconds (model loading) |
| **Subsequent inferences** | 120-180ms |
| **GPU utilization** | 60-80% during inference |
| **GPU memory** | ~8-10GB (OpenVLA-7B) |
| **Throughput** | ~6-8 requests/second |

### Comparison: GPU vs CPU

| Operation | GPU (Titan X) | CPU Only |
|-----------|---------------|----------|
| Inference | 120-150ms | 1000-2000ms |
| Throughput | 6-8 req/s | 0.5-1 req/s |
| Quality | ✅ Same | ✅ Same |

---

## 🔐 Security Notes

**This setup is for testing!** For production:

1. **Change passwords** in `.env.remote`
2. **Add firewall rules** (only allow your IP)
3. **Add SSL/TLS** (use nginx reverse proxy)
4. **Secure SSH** (disable password auth, use keys)
5. **Update regularly** (`docker-compose pull`)

---

## 📊 View Results

### From Your Mac

Create `test_remote_gpu.py` on your Mac:

```python
#!/usr/bin/env python3
"""Test remote GPU deployment."""

import requests
import time

SERVER_IP = "your-server-ip"
API_KEY = "vla_remote_YOUR_KEY_HERE"
API_URL = f"http://{SERVER_IP}:8000"

# Test multiple inferences
print("Testing GPU inference speed...")
latencies = []

for i in range(10):
    start = time.time()
    
    response = requests.post(
        f"{API_URL}/v1/inference",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "openvla-7b",
            "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "instruction": f"test inference {i}"
        }
    )
    
    elapsed = (time.time() - start) * 1000
    latencies.append(elapsed)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Request {i+1}: {result['performance']['inference_ms']}ms (GPU time)")
    else:
        print(f"✗ Request {i+1} failed")

print(f"\nAverage latency: {sum(latencies)/len(latencies):.1f}ms")
print(f"Min: {min(latencies):.1f}ms, Max: {max(latencies):.1f}ms")
```

Run it:
```bash
python test_remote_gpu.py
```

---

## ✅ Success Checklist

- [ ] NVIDIA drivers installed
- [ ] Docker with GPU support working
- [ ] Services running (`docker ps`)
- [ ] Can access API from Mac
- [ ] GPU detected in container
- [ ] Real inference working (not mock)
- [ ] GPU metrics showing in dashboard
- [ ] Latency < 200ms for inference

**All ✅ → Your GPU deployment is working!** 🎉

---

## 🚀 Next Steps

### Scale Up

1. **Load balancer** - Add nginx to distribute load
2. **Multiple workers** - Run 2-3 API containers
3. **Both GPUs** - Use both Titan X GPUs
4. **Production setup** - Follow DEPLOYMENT_AND_OPERATIONS.md

### Monitor

- Watch Grafana dashboards
- Monitor GPU temperature (`nvidia-smi`)
- Check inference latency
- Review error rates

### Optimize

- Tune `INFERENCE_MAX_WORKERS`
- Adjust batch sizes
- Enable model quantization
- Add caching layers

---

## 📚 Related Docs

- **Local testing:** `LOCAL_DEPLOYMENT_QUICKSTART.md`
- **Production:** `docs/DEPLOYMENT_AND_OPERATIONS.md`
- **Architecture:** `docs/QUICK_ARCHITECTURE_GUIDE.md`

---

**You now have real GPU inference running on your remote server!** 🚀🎮

