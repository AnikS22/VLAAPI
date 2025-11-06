# 🤖 VLA Inference API

**Vision-Language-Action inference API for robotics with GPU acceleration**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)

Enterprise-grade API for robot action prediction from images and natural language instructions.

---

## 🎯 What Does This Do?

Send an **image** + **instruction** → Get back a **7-DoF robot action**

```python
# You send:
{
  "image": "base64_encoded_camera_image",
  "instruction": "pick up the red cube"
}

# You receive:
{
  "action": [0.15, -0.08, 0.22, 0.01, 0.05, -0.03, 1.0]
  #          ↓     ↓     ↓     ↓     ↓     ↓     ↓
  #         X     Y     Z    Roll  Pitch  Yaw  Gripper
}
```

---

## ✨ Features

- 🎮 **GPU Accelerated** - NVIDIA GPU support (CUDA 12+)
- 🤖 **30+ Robot Types** - Franka, UR, KUKA, ABB, Kinova, and more
- ⚡ **Real-Time Streaming** - WebSocket support for 10-50Hz control
- 🛡️ **Safety Monitoring** - Multi-layer safety validation
- 📊 **Production Ready** - Prometheus metrics, Grafana dashboards
- 🔐 **Privacy Compliant** - GDPR/CCPA with tiered consent
- 🔑 **API Key Auth** - Tier-based rate limiting
- 📈 **Analytics** - Vector embeddings and semantic search

---

## 🚀 Quick Start

### Option 1: Local Testing (No GPU Needed)

Test everything on your Mac with mock models:

```bash
# Deploy locally
./scripts/local_deploy.sh

# Test API
python test_local_api.py

# View dashboards
open http://localhost:3000  # Grafana
open http://localhost:8000/docs  # API docs
```

**Read:** [LOCAL_DEPLOYMENT_QUICKSTART.md](LOCAL_DEPLOYMENT_QUICKSTART.md)

### Option 2: Remote GPU Server

Deploy to Linux server with NVIDIA GPUs:

```bash
# Copy to remote server
rsync -avz ./ user@server:~/VLAAPI/

# SSH and deploy
ssh user@server
cd ~/VLAAPI
./scripts/remote_gpu_deploy.sh
```

**Read:** [REMOTE_GPU_QUICKSTART.md](REMOTE_GPU_QUICKSTART.md)

### Option 3: FAU Computer

Deploy to university computer from home:

**Read:** [docs/REMOTE_ACCESS_SETUP.md](docs/REMOTE_ACCESS_SETUP.md)

---

## 📚 Documentation

**Getting Started:**
- [START_HERE.md](START_HERE.md) - Absolute beginner start
- [docs/BEGINNERS_API_GUIDE.md](docs/BEGINNERS_API_GUIDE.md) - Complete API tutorial
- [GETTING-STARTED.md](GETTING-STARTED.md) - Quick setup

**Deployment:**
- [LOCAL_DEPLOYMENT_QUICKSTART.md](LOCAL_DEPLOYMENT_QUICKSTART.md) - Local testing
- [REMOTE_GPU_QUICKSTART.md](REMOTE_GPU_QUICKSTART.md) - GPU server deployment
- [docs/DEPLOYMENT_AND_OPERATIONS.md](docs/DEPLOYMENT_AND_OPERATIONS.md) - Production guide

**Architecture:**
- [docs/QUICK_ARCHITECTURE_GUIDE.md](docs/QUICK_ARCHITECTURE_GUIDE.md) - System overview
- [docs/COMPLETE_SYSTEM_REPORT.md](docs/COMPLETE_SYSTEM_REPORT.md) - Full documentation

**API Reference:**
- Interactive docs: `http://localhost:8000/docs`
- [docs/data-contracts.md](docs/data-contracts.md) - Data schemas

---

## 🖥️ System Requirements

### Development (Local Testing)
- **OS:** macOS, Linux, or Windows with Docker
- **RAM:** 8GB+
- **Disk:** 10GB+
- **Docker:** Required

### Production (GPU Inference)
- **OS:** Linux (Ubuntu 20.04+ recommended)
- **GPU:** NVIDIA GPU with 12GB+ VRAM (Titan X, RTX 3090, A100, etc.)
- **RAM:** 32GB+
- **Disk:** 100GB+ (for models)
- **CUDA:** 12.1+

---

## 🧪 Testing

```bash
# Local mock deployment (5 minutes)
./scripts/local_deploy.sh
python test_local_api.py

# Remote GPU deployment (15 minutes)
ssh server
./scripts/remote_gpu_deploy.sh

# Run test suite
pytest tests/
```

---

## 📊 Performance

| Metric | Local (Mock) | Remote (GPU) |
|--------|-------------|--------------|
| **Inference Time** | ~50ms (fake) | ~125ms (real) |
| **Throughput** | N/A | 6-8 req/s |
| **GPU Memory** | None | ~8-10GB |
| **Accuracy** | N/A | Real AI model |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           API Layer (FastAPI)           │
│  Authentication | Rate Limiting | CORS  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│        Services Layer                   │
│  VLA Inference | Safety | Embeddings    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Data Layer                      │
│  PostgreSQL | Redis | S3 | Prometheus   │
└─────────────────────────────────────────┘
```

---

## 🔧 Configuration

Key environment variables in `.env`:

```bash
# Models
USE_MOCK_MODELS=true  # false for GPU
ENABLED_MODELS=openvla-7b

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/vlaapi

# Redis
REDIS_URL=redis://localhost:6379/0

# Monitoring
ENABLE_PROMETHEUS=true
ENABLE_GPU_MONITORING=true
```

---

## 🛠️ Tech Stack

- **API:** FastAPI 0.115.0, Python 3.10+
- **Database:** PostgreSQL 15+ with pgvector
- **Cache:** Redis 7.0+
- **AI Models:** OpenVLA-7B, PyTorch 2.5+
- **Embeddings:** sentence-transformers, CLIP
- **Monitoring:** Prometheus, Grafana
- **Storage:** S3/MinIO (optional)

---

## 📁 Project Structure

```
VLAAPI/
├── src/
│   ├── api/            # FastAPI endpoints
│   ├── services/       # Business logic (inference, safety, embeddings)
│   ├── models/         # Database models
│   ├── middleware/     # Auth, rate limiting, quality gates
│   └── monitoring/     # Prometheus metrics, GPU monitoring
├── docs/               # Complete documentation
├── scripts/            # Deployment and management scripts
├── monitoring/         # Grafana dashboards, Prometheus configs
├── examples/           # Example clients and usage
└── tests/              # Test suite
```

---

## 🤝 Contributing

This is a research project. Feel free to:
- Report issues
- Submit pull requests
- Fork for your own research

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

## 🔗 Quick Links

- **Repository:** https://github.com/AnikS22/VLAAPI
- **Documentation:** [docs/](docs/)
- **Getting Started:** [START_HERE.md](START_HERE.md)

---

**Ready to start?** Read [START_HERE.md](START_HERE.md) or run `./scripts/local_deploy.sh`! 🚀

