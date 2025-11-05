# VLA Inference API Platform

A production-ready Vision-Language-Action (VLA) inference API for robotics with integrated safety monitoring and alignment research capabilities.

## 🎯 Overview

This platform provides a managed REST API for VLA model inference, specifically designed for robotics applications. It includes:

- **Multi-Model Support**: OpenVLA-7B and π₀ models with switchable architecture
- **Safety Monitoring**: Rule-based validation + pluggable alignment research interface
- **Production Features**: Authentication, rate limiting, usage tracking, GPU queue management
- **Research-Friendly**: Designed to integrate your SafeVLA alignment measures

## 🏗️ Architecture

```
Client Request
    ↓
[Authentication & Rate Limiting]
    ↓
[VLA Model Inference (GPU Queue)]
    ↓
[Safety Monitoring (Rule-based + Your Alignment)]
    ↓
[Action Response + Safety Scores]
```

## 📋 Requirements

- **Python**: 3.10+
- **GPU**: NVIDIA A100 (40GB) or equivalent with CUDA 12.1+
- **Database**: PostgreSQL 14+
- **Cache**: Redis 7+
- **RAM**: 32GB minimum
- **Storage**: 100GB for models + 500GB for database

## 🚀 Quick Start

### 1. Installation

```bash
# Navigate to VLA API directory
cd /path/to/VLAAPI

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Critical Settings**:
```env
# Database
DATABASE_URL=postgresql+asyncpg://vlaapi:password@localhost:5432/vlaapi

# Redis
REDIS_URL=redis://localhost:6379/0

# GPU
GPU_DEVICE=0
MODEL_DTYPE=bfloat16

# Models (start with one)
ENABLED_MODELS=openvla-7b

# Safety (enable your alignment research)
SAFETY_CLASSIFIER_ENABLED=false  # Set to true when you add your alignment model
```

### 3. Database Setup

```bash
# Start PostgreSQL and Redis (using Docker)
docker-compose up -d postgres redis

# Initialize database schema
python scripts/setup_database.py

# Create your first API key
python scripts/create_api_key.py
```

### 4. Run the API

**Development (Mock Models)**:
```bash
# Use mock models for testing without GPU
docker-compose --profile dev up api-dev
```

**Production (Real Models on GPU)**:
```bash
# Requires NVIDIA GPU + nvidia-docker
docker-compose --profile prod up api-prod
```

**Local Development**:
```bash
# Run directly with Python
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Test the API

```bash
# Health check
curl http://localhost:8000/health

# List available models
curl http://localhost:8000/v1/models/list

# Inference (replace with your API key)
curl -X POST http://localhost:8000/v1/inference \
  -H "Authorization: Bearer vla_live_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openvla-7b",
    "image": "<base64_encoded_image>",
    "instruction": "pick up the red cube"
  }'
```

## 🔬 Integrating Your Alignment Research

Your SafeVLA alignment measures can be integrated into the safety monitoring system:

### 1. Create Your Alignment Check

```python
# src/services/custom_alignment.py
from src.services.safety_monitor import AlignmentCheck

class MyAlignmentCheck(AlignmentCheck):
    def __init__(self):
        super().__init__("MyCustomAlignment")
        # Load your trained model
        self.model = load_your_model()

    def check(self, action, context):
        """Your custom alignment logic."""
        # Extract features
        features = self.extract_features(action, context)

        # Run your classifier
        is_aligned, confidence = self.model.predict(features)

        explanation = f"Alignment score: {confidence:.2f}"

        return is_aligned, confidence, explanation
```

### 2. Register Your Check

```python
# In src/services/safety_monitor.py, add to __init__:
from src.services.custom_alignment import MyAlignmentCheck

class SafetyMonitor:
    def __init__(self):
        # ... existing code ...
        self.add_alignment_check(MyAlignmentCheck())
```

### 3. Enable in Configuration

```env
# .env
SAFETY_CLASSIFIER_ENABLED=true
SAFETY_CLASSIFIER_PATH=/path/to/your/model.pth
SAFETY_CLASSIFIER_THRESHOLD=0.85
```

## 📊 API Documentation

### Authentication

All requests require a Bearer token:
```http
Authorization: Bearer vla_live_abc123...
```

### Endpoints

#### POST /v1/inference
Perform VLA inference with safety validation.

**Request**:
```json
{
  "model": "openvla-7b",
  "image": "<base64_string>",
  "instruction": "pick up the red cube",
  "robot_config": {
    "type": "franka_panda",
    "workspace_bounds": [[-0.5, -0.5, 0.0], [0.5, 0.5, 0.8]],
    "velocity_limits": [0.5, 0.5, 0.5, 1.0, 1.0, 1.0, 1.0]
  },
  "safety": {
    "enable_classifier": true,
    "safety_threshold": 0.8
  }
}
```

**Response**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-11-05T10:30:45.123Z",
  "model": "openvla-7b",
  "action": {
    "type": "end_effector_delta",
    "dimensions": 7,
    "values": [0.05, -0.02, 0.10, 0.0, 0.0, 0.1, 1.0],
    "units": ["m", "m", "m", "rad", "rad", "rad", "binary"]
  },
  "safety": {
    "overall_score": 0.95,
    "checks_passed": ["workspace", "velocity", "collision", "alignment"],
    "flags": {
      "workspace_violation": false,
      "velocity_violation": false,
      "collision_risk": false,
      "alignment_violation": false
    },
    "classifier_confidence": 0.97,
    "modifications_applied": false
  },
  "performance": {
    "total_latency_ms": 145,
    "queue_wait_ms": 12,
    "inference_ms": 98,
    "safety_check_ms": 8
  },
  "usage": {
    "requests_remaining_minute": 58,
    "requests_remaining_day": 945,
    "monthly_quota_remaining": 9850
  }
}
```

#### GET /v1/models/list
List available VLA models.

#### GET /health
System health check.

## 🐳 Deployment

### Docker Compose (Recommended)

**Development**:
```bash
docker-compose --profile dev up
```

**Production**:
```bash
docker-compose --profile prod up -d
```

### Manual Deployment

1. **Set up PostgreSQL**:
```bash
# Create database and user
createdb vlaapi
psql -c "CREATE USER vlaapi WITH PASSWORD 'your-secure-password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE vlaapi TO vlaapi;"
```

2. **Set up Redis**:
```bash
redis-server --port 6379
```

3. **Initialize Database**:
```bash
python scripts/setup_database.py
```

4. **Run with Gunicorn** (production):
```bash
gunicorn src.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

## 📈 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Prometheus Metrics
```bash
curl http://localhost:8000/metrics
```

### Logs
Structured JSON logs are written to stdout. Configure log aggregation (ELK, Datadog) in production.

## 🔐 Security

- **API Keys**: SHA-256 hashed, never stored in plaintext
- **Rate Limiting**: Token bucket algorithm per customer
- **Input Validation**: Pydantic models with strict validation
- **SQL Injection**: Parameterized queries via SQLAlchemy
- **CORS**: Configurable allowed origins

## 💰 Pricing Tiers

Configure in database per customer:

| Tier       | RPM   | RPD     | Monthly Quota |
|------------|-------|---------|---------------|
| Free       | 10    | 1,000   | 10,000        |
| Pro        | 100   | 10,000  | 100,000       |
| Enterprise | 1,000 | 100,000 | Unlimited     |

## 🧪 Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Coverage report
pytest --cov=src tests/
```

## 📚 Project Structure

```
VLAAPI/
├── src/
│   ├── api/              # FastAPI application
│   │   ├── main.py       # Main app with lifespan
│   │   └── routers/      # API endpoints
│   ├── core/             # Core utilities
│   │   ├── config.py     # Configuration management
│   │   ├── database.py   # Database connection
│   │   ├── redis_client.py
│   │   ├── security.py   # API key hashing
│   │   └── constants.py  # VLA/robot constants
│   ├── middleware/       # Request middleware
│   │   ├── authentication.py
│   │   ├── rate_limiting.py
│   │   └── logging.py
│   ├── models/           # Data models
│   │   ├── database.py   # SQLAlchemy ORM
│   │   └── api_models.py # Pydantic schemas
│   ├── services/         # Business logic
│   │   ├── model_loader.py      # VLA model loading
│   │   ├── vla_inference.py     # Inference service
│   │   ├── action_validator.py  # Rule-based safety
│   │   └── safety_monitor.py    # Pluggable safety
│   └── utils/            # Utilities
│       ├── image_processing.py
│       └── action_processing.py
├── scripts/              # CLI tools
│   ├── setup_database.py
│   └── create_api_key.py
├── docker/               # Docker configuration
├── config/               # Robot configurations
├── tests/                # Test suite
├── docs/                 # Documentation
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## 🤝 Contributing

This is a personal research project. For collaboration, please reach out directly.

## 📝 License

[Add your license]

## 🆘 Support

For issues or questions:
1. Check `/docs` for detailed documentation
2. Review API docs at `/docs` (when running locally)
3. Examine logs for error details

## 🎓 Research Citation

If you use this platform for research, please cite:
```bibtex
@software{vla_inference_api,
  title={VLA Inference API Platform with Safety Monitoring},
  author={Your Name},
  year={2025},
  url={https://github.com/yourusername/VLAAPI}
}
```

---

**Built with FastAPI, PyTorch, and PostgreSQL** | **Designed for robotics safety research**
