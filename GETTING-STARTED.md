# 🚀 VLA Inference API - Quick Start Guide

This guide will get your VLA inference API running in **under 10 minutes**.

## ✅ Prerequisites Checklist

- [ ] Python 3.10+ installed
- [ ] Docker and Docker Compose installed
- [ ] NVIDIA GPU with CUDA 12.1+ (for production)
- [ ] 16GB RAM minimum (32GB recommended)

## 📦 Step 1: Initial Setup (2 minutes)

```bash
# 1. Create Python virtual environment
python3.10 -m venv venv
source venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Copy environment configuration
cp .env.example .env

# 4. Edit .env - set these minimal values:
nano .env
# Change: USE_MOCK_MODELS=true (for testing without GPU)
```

## 🗄️ Step 2: Start Infrastructure (3 minutes)

```bash
# Start PostgreSQL and Redis using Docker
docker-compose up -d postgres redis

# Wait for services to be healthy (30 seconds)
docker-compose ps

# Initialize database schema
python scripts/setup_database.py
# Answer 'y' to seed demo data - this creates a test API key
```

**Save the API key shown!** You'll need it for testing.

## 🧪 Step 3: Test with Mock Models (1 minute)

```bash
# Start API with mock models (no GPU required)
USE_MOCK_MODELS=true python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

In another terminal:
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test inference (replace YOUR_API_KEY)
curl -X POST http://localhost:8000/v1/inference \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openvla-7b",
    "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "instruction": "pick up the red cube"
  }'
```

## 🎯 Step 4: Production Setup (Optional)

### For GPU Inference:

1. **Edit `.env`**:
```env
USE_MOCK_MODELS=false
ENABLED_MODELS=openvla-7b
GPU_DEVICE=0
MODEL_DTYPE=bfloat16
```

2. **Start with Docker**:
```bash
docker-compose --profile prod up
```

3. **First inference will download models** (~16GB for OpenVLA-7B)

## 🔬 Step 5: Add Your Alignment Research

### Create Your Custom Alignment Check:

```bash
# 1. Create your alignment module
touch src/services/custom_alignment.py
```

```python
# src/services/custom_alignment.py
from src.services.safety_monitor import AlignmentCheck

class MyAlignmentCheck(AlignmentCheck):
    def __init__(self):
        super().__init__("MyAlignment")
        # TODO: Load your trained model here
        # self.model = torch.load("path/to/your/model.pth")

    def check(self, action, context):
        # TODO: Implement your alignment logic
        # Example: Check if action violates your safety constraints

        is_safe = True  # Your logic here
        confidence = 0.9  # Your confidence score
        explanation = "Action passes alignment check"

        return is_safe, confidence, explanation
```

### Register Your Check:

```python
# Edit src/services/safety_monitor.py
from src.services.custom_alignment import MyAlignmentCheck

class SafetyMonitor:
    def __init__(self):
        # ... existing code ...

        # Add your alignment check
        self.add_alignment_check(MyAlignmentCheck())
```

### Enable in Configuration:

```env
# .env
SAFETY_CLASSIFIER_ENABLED=true
SAFETY_CLASSIFIER_PATH=/path/to/your/model.pth
SAFETY_CLASSIFIER_THRESHOLD=0.85
```

## 📊 Step 6: Monitor Your API

### View Logs:
```bash
# API logs (stdout)
docker logs -f vlaapi-prod

# Database logs
docker logs -f vlaapi-postgres

# Redis logs
docker logs -f vlaapi-redis
```

### Check Health:
```bash
curl http://localhost:8000/health | jq
```

### View Usage Stats:
```bash
# Query database for usage
docker exec -it vlaapi-postgres psql -U vlaapi -d vlaapi -c \
  "SELECT COUNT(*), status FROM vlaapi.inference_logs GROUP BY status;"
```

## 🎓 Next Steps

### 1. Generate More API Keys:
```bash
python scripts/create_api_key.py
```

### 2. Configure Your Robot:
```yaml
# config/robot_configs/my_robot.yaml
name: "My Robot"
dof: 7
workspace_bounds:
  - [-0.6, -0.6, 0.0]
  - [0.6, 0.6, 0.8]
velocity_limits: [0.5, 0.5, 0.5, 1.0, 1.0, 1.0, 1.0]
```

### 3. Integrate with Your Robot:
```python
# Example: Python client
import requests
import base64

# Read image
with open("robot_camera.jpg", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode()

# Call API
response = requests.post(
    "http://localhost:8000/v1/inference",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "model": "openvla-7b",
        "image": image_base64,
        "instruction": "pick up the red cube",
        "robot_config": {"type": "my_robot"}
    }
)

action = response.json()["action"]["values"]
print(f"Robot action: {action}")
```

### 4. Add More Models:
```env
# .env
ENABLED_MODELS=openvla-7b,pi0
```

## 🐛 Troubleshooting

### Issue: "Model not loaded"
**Solution**: Check GPU availability
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

### Issue: "Database connection failed"
**Solution**: Ensure PostgreSQL is running
```bash
docker-compose ps postgres
docker-compose up -d postgres
```

### Issue: "Rate limit exceeded"
**Solution**: Check your tier limits in database
```bash
python scripts/create_api_key.py  # Create new key with higher limits
```

### Issue: "Action rejected by safety"
**Solution**: Review safety logs
```bash
docker exec -it vlaapi-postgres psql -U vlaapi -d vlaapi -c \
  "SELECT * FROM vlaapi.safety_incidents ORDER BY timestamp DESC LIMIT 5;"
```

## 📚 Full Documentation

- **Complete API Reference**: `docs/VLA-API-README.md`
- **API Documentation (Interactive)**: http://localhost:8000/docs
- **Database Schema**: `src/models/database.py`
- **Safety System**: `src/services/safety_monitor.py`

## 🎉 You're Ready!

You now have a fully functional VLA inference API with:
- ✅ Authentication & Rate Limiting
- ✅ GPU-accelerated VLA inference
- ✅ Rule-based safety monitoring
- ✅ Pluggable alignment research interface
- ✅ Complete logging and usage tracking

**Start building and researching!** 🤖🔬
