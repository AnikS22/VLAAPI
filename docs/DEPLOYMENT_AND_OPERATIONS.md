# 🏗️ Deployment & Operations Guide

**Complete guide to deploying VLA API to production and managing customers**

---

## 📊 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Server Setup](#server-setup)
3. [Customer Onboarding](#customer-onboarding)
4. [Viewing Analytics](#viewing-analytics)
5. [Dashboard Access](#dashboard-access)
6. [Scaling & Load Balancing](#scaling--load-balancing)

---

## 🏛️ Architecture Overview

### The Complete System

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR BUSINESS                             │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              YOUR PRODUCTION SERVERS                        │ │
│  │                                                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │ │
│  │  │  API Server  │  │  API Server  │  │   API Server    │  │ │
│  │  │  (GPU)       │  │  (GPU)       │  │   (GPU)         │  │ │
│  │  │  Port 8000   │  │  Port 8000   │  │   Port 8000     │  │ │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘  │ │
│  │         │                  │                    │           │ │
│  │         └──────────────────┴────────────────────┘           │ │
│  │                            │                                 │ │
│  │                   ┌────────▼────────┐                       │ │
│  │                   │  Load Balancer  │                       │ │
│  │                   │  (nginx/HAProxy)│                       │ │
│  │                   │  https://api.   │                       │ │
│  │                   │  yourdomain.com │                       │ │
│  │                   └────────┬────────┘                       │ │
│  └────────────────────────────┼──────────────────────────────┘ │
│                                │                                 │
│  ┌────────────────────────────▼──────────────────────────────┐ │
│  │              SHARED INFRASTRUCTURE                         │ │
│  │                                                             │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐ │ │
│  │  │ PostgreSQL   │  │    Redis     │  │  S3/MinIO       │ │ │
│  │  │ (Database)   │  │   (Cache)    │  │  (Storage)      │ │ │
│  │  └──────────────┘  └──────────────┘  └─────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              MONITORING & ANALYTICS                      │  │
│  │                                                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │  │
│  │  │ Prometheus   │  │   Grafana    │  │ Admin Panel   │ │  │
│  │  │ (Metrics)    │  │ (Dashboards) │  │ (Management)  │ │  │
│  │  │ Port 9090    │  │  Port 3000   │  │  Port 3001    │ │  │
│  │  └──────────────┘  └──────────────┘  └───────────────┘ │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ API Calls
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      CUSTOMER SIDE                               │
│                                                                   │
│  Customer 1 (Warehouse Robotics Co.)                             │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  Their Robot Controller                              │        │
│  │  → Calls: https://api.yourdomain.com/v1/inference  │        │
│  │  → With: API Key vla_live_abc123...                 │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                   │
│  Customer 2 (Manufacturing Automation Inc.)                      │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  Their Robot Fleet (10 robots)                      │        │
│  │  → Calls: https://api.yourdomain.com/v1/inference  │        │
│  │  → With: API Key vla_live_xyz789...                 │        │
│  └─────────────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🖥️ Server Setup

### What You Need

**Minimum Production Setup:**

| Server Type | Purpose | Specs | Quantity |
|------------|---------|-------|----------|
| **API Server** | Run VLA models | 1x NVIDIA GPU (A100/A10), 32GB RAM, 8 CPU | 3+ |
| **Database Server** | PostgreSQL | 16GB RAM, 4 CPU, 500GB SSD | 1 |
| **Cache Server** | Redis | 8GB RAM, 2 CPU | 1 |
| **Load Balancer** | nginx/HAProxy | 4GB RAM, 2 CPU | 1 |
| **Monitoring Server** | Prometheus + Grafana | 8GB RAM, 4 CPU | 1 |
| **Storage** | S3 or MinIO | 1TB+ storage | 1 |

---

## 📦 Installation on Servers

### Server 1: API Servers (GPU Machines)

**What to install on each GPU server:**

```bash
# SSH into your GPU server
ssh user@api-server-1.yourdomain.com

# 1. Install NVIDIA drivers and CUDA
sudo apt update
sudo apt install nvidia-driver-535 nvidia-cuda-toolkit

# 2. Install Docker and nvidia-container-toolkit
sudo apt install docker.io
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update
sudo apt install nvidia-container-toolkit
sudo systemctl restart docker

# 3. Clone your repository
git clone https://github.com/yourcompany/VLAAPI.git
cd VLAAPI

# 4. Create production .env file
cat > .env << EOF
ENVIRONMENT=production
DEBUG=false
USE_MOCK_MODELS=false

# This server's config
API_HOST=0.0.0.0
API_PORT=8000
GPU_DEVICE=0

# Shared database (Database Server IP)
DATABASE_URL=postgresql+asyncpg://vlaapi:SECURE_PASSWORD@10.0.1.10:5432/vlaapi

# Shared Redis (Cache Server IP)
REDIS_URL=redis://10.0.1.11:6379/0

# S3 Storage (Storage Server)
S3_ENDPOINT=https://s3.yourdomain.com
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key

# Models
ENABLED_MODELS=openvla-7b
MODEL_DTYPE=bfloat16

# Monitoring
ENABLE_PROMETHEUS=true
ENABLE_GPU_MONITORING=true
EOF

# 5. Build and start Docker container
docker-compose --profile prod up -d

# 6. Verify it's running
docker ps
curl http://localhost:8000/health
```

**Repeat for api-server-2, api-server-3, etc.**

---

### Server 2: Database Server (PostgreSQL)

```bash
# SSH into database server
ssh user@db-server.yourdomain.com

# 1. Install PostgreSQL
sudo apt update
sudo apt install postgresql-15 postgresql-contrib

# 2. Install pgvector extension
sudo apt install postgresql-15-pgvector

# 3. Configure PostgreSQL
sudo -u postgres psql << EOF
-- Create database and user
CREATE DATABASE vlaapi;
CREATE USER vlaapi WITH ENCRYPTED PASSWORD 'SECURE_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE vlaapi TO vlaapi;

-- Enable extensions
\c vlaapi
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
EOF

# 4. Configure remote access
sudo nano /etc/postgresql/15/main/postgresql.conf
# Change: listen_addresses = '*'

sudo nano /etc/postgresql/15/main/pg_hba.conf
# Add: host    all    vlaapi    10.0.1.0/24    md5

sudo systemctl restart postgresql

# 5. Initialize schema from API server
# (Run this from one of the API servers)
cd VLAAPI
python -c "from src.models.database import init_db; init_db()"
```

---

### Server 3: Cache Server (Redis)

```bash
# SSH into cache server
ssh user@cache-server.yourdomain.com

# 1. Install Redis
sudo apt update
sudo apt install redis-server

# 2. Configure for production
sudo nano /etc/redis/redis.conf
# Change these settings:
# bind 0.0.0.0
# maxmemory 4gb
# maxmemory-policy allkeys-lru
# requirepass SECURE_REDIS_PASSWORD

# 3. Restart Redis
sudo systemctl restart redis
sudo systemctl enable redis

# 4. Test
redis-cli -h localhost -a SECURE_REDIS_PASSWORD ping
```

---

### Server 4: Load Balancer (nginx)

```bash
# SSH into load balancer
ssh user@lb-server.yourdomain.com

# 1. Install nginx
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx

# 2. Configure load balancing
sudo nano /etc/nginx/sites-available/vla-api

# Add this configuration:
upstream vla_api_backend {
    least_conn;  # Use least connections algorithm
    
    server 10.0.1.20:8000 max_fails=3 fail_timeout=30s;  # API Server 1
    server 10.0.1.21:8000 max_fails=3 fail_timeout=30s;  # API Server 2
    server 10.0.1.22:8000 max_fails=3 fail_timeout=30s;  # API Server 3
}

server {
    listen 80;
    server_name api.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL certificates (will be added by certbot)
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
    limit_req zone=api_limit burst=200 nodelay;

    # Proxy to backend
    location / {
        proxy_pass http://vla_api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Health check
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
    }

    # WebSocket support for streaming
    location /v1/stream {
        proxy_pass http://vla_api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Metrics endpoint (internal only)
    location /metrics {
        allow 10.0.1.0/24;  # Your internal network
        deny all;
        proxy_pass http://vla_api_backend;
    }
}

# 3. Enable site and get SSL certificate
sudo ln -s /etc/nginx/sites-available/vla-api /etc/nginx/sites-enabled/
sudo certbot --nginx -d api.yourdomain.com
sudo systemctl restart nginx
```

---

### Server 5: Monitoring Server (Prometheus + Grafana)

```bash
# SSH into monitoring server
ssh user@monitoring-server.yourdomain.com

# 1. Create docker-compose.yml for monitoring
cat > docker-compose.yml << EOF
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=90d'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=SECURE_PASSWORD
      - GF_SERVER_ROOT_URL=https://monitoring.yourdomain.com
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana-dashboards:/etc/grafana/provisioning/dashboards

volumes:
  prometheus-data:
  grafana-data:
EOF

# 2. Configure Prometheus to scrape all API servers
cat > prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'vla-api'
    static_configs:
      - targets:
        - '10.0.1.20:8000'  # API Server 1
        - '10.0.1.21:8000'  # API Server 2
        - '10.0.1.22:8000'  # API Server 3
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'node-exporter'
    static_configs:
      - targets:
        - '10.0.1.20:9100'
        - '10.0.1.21:9100'
        - '10.0.1.22:9100'

  - job_name: 'postgres'
    static_configs:
      - targets: ['10.0.1.10:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['10.0.1.11:9121']
EOF

# 3. Copy Grafana dashboards from repo
mkdir -p grafana-dashboards
cp /path/to/VLAAPI/monitoring/grafana/dashboards/*.json grafana-dashboards/

# 4. Start monitoring stack
docker-compose up -d

# 5. Access Grafana at https://monitoring.yourdomain.com
```

---

## 👥 Customer Onboarding

### How Customers Use Your API

**Step 1: Customer Signs Up**

You provide them with:
1. **API endpoint**: `https://api.yourdomain.com`
2. **API key**: `vla_live_abc123def456...`
3. **Documentation**: Link to your docs
4. **Tier**: free/pro/enterprise (determines rate limits)

**Step 2: Create API Key for Customer**

```bash
# SSH into any API server
ssh user@api-server-1.yourdomain.com
cd VLAAPI

# Run customer creation script
python scripts/create_customer.py

# Interactive prompts:
# Company name: Acme Robotics Inc.
# Email: tech@acmerobotics.com
# Tier: pro
# Monthly quota: 100000

# Output:
# ✅ Customer created!
# Customer ID: 550e8400-e29b-41d4-a716-446655440000
# API Key: vla_live_acme_abc123def456...
# Tier: pro
# Rate limits: 100 req/min, 10000 req/day, 100000 req/month
```

**Step 3: Customer Integrates**

They use the API from their code:

```python
# Customer's robot controller code
import requests
import base64

API_URL = "https://api.yourdomain.com/v1/inference"
API_KEY = "vla_live_acme_abc123def456..."  # You gave them this

# Get image from robot camera
with open("robot_camera.jpg", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode()

# Call your API
response = requests.post(
    API_URL,
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "model": "openvla-7b",
        "image": image_base64,
        "instruction": "pick up the object",
        "robot_config": {"type": "franka_panda"}
    }
)

# Get action
action = response.json()["action"]["values"]

# Send to their robot
their_robot.execute_action(action)
```

---

## 📊 Viewing Analytics & Dashboards

### Dashboard 1: YOUR Operations Dashboard (Grafana)

**URL:** `https://monitoring.yourdomain.com`

**What you see:**

```
┌─────────────────────────────────────────────────────────────┐
│  VLA API Operations Dashboard                     [Last 1h] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📈 Request Rate                  ⚡ Latency                 │
│  ┌─────────────────┐             ┌─────────────────┐        │
│  │     2,450       │             │   p50:  120ms   │        │
│  │    req/min      │             │   p95:  180ms   │        │
│  │                 │             │   p99:  250ms   │        │
│  └─────────────────┘             └─────────────────┘        │
│                                                               │
│  🎯 Success Rate                 🖥️ GPU Utilization         │
│  ┌─────────────────┐             ┌─────────────────┐        │
│  │     99.2%       │             │  Server 1: 78%  │        │
│  │   (2,430/2,450) │             │  Server 2: 82%  │        │
│  │                 │             │  Server 3: 75%  │        │
│  └─────────────────┘             └─────────────────┘        │
│                                                               │
│  📊 Requests by Customer (Top 5)                             │
│  ┌────────────────────────────────────────────────┐         │
│  │ Acme Robotics      ████████████░░  1,200 (49%) │         │
│  │ TechCorp           ██████░░░░░░░░    620 (25%) │         │
│  │ RoboFactory        ████░░░░░░░░░░    400 (16%) │         │
│  │ AutoMate Inc       ██░░░░░░░░░░░░    150 (6%)  │         │
│  │ BotWorks           █░░░░░░░░░░░░░     80 (3%)  │         │
│  └────────────────────────────────────────────────┘         │
│                                                               │
│  🔴 Recent Errors                                            │
│  ┌────────────────────────────────────────────────┐         │
│  │ 14:23  Model timeout (Server 2)                │         │
│  │ 14:15  Safety rejection (Customer: Acme)       │         │
│  │ 14:10  Rate limit exceeded (Customer: TechCorp)│         │
│  └────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

**What you can do:**
- Monitor real-time API health
- See which customers are using most resources
- Identify bottlenecks and errors
- Plan capacity scaling

---

### Dashboard 2: YOUR Business Dashboard

**URL:** `https://monitoring.yourdomain.com/d/business`

**What you see:**

```
┌─────────────────────────────────────────────────────────────┐
│  Business Metrics Dashboard                   [Last 30 days]│
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  💰 Monthly Revenue              👥 Active Customers         │
│  ┌─────────────────┐             ┌─────────────────┐        │
│  │   $45,800       │             │       23        │        │
│  │   +12% ↑        │             │      +3 ↑       │        │
│  └─────────────────┘             └─────────────────┘        │
│                                                               │
│  📞 API Calls by Tier            🔝 Top Customers           │
│  ┌─────────────────┐             ┌─────────────────┐        │
│  │ Enterprise: 65% │             │ Acme: $15,000   │        │
│  │ Pro: 28%        │             │ TechCorp: $8,500│        │
│  │ Free: 7%        │             │ RoboFac: $6,200 │        │
│  └─────────────────┘             └─────────────────┘        │
│                                                               │
│  📈 Growth Trend (Last 6 months)                             │
│  ┌────────────────────────────────────────────────┐         │
│  │     Revenue ($1000s)                           │         │
│  │  50 │                                    ●     │         │
│  │  40 │                            ●       ●     │         │
│  │  30 │                    ●       ●       ●     │         │
│  │  20 │            ●       ●       ●       ●     │         │
│  │  10 │    ●       ●       ●       ●       ●     │         │
│  │   0 └────┴───────┴───────┴───────┴───────┴──  │         │
│  │     Jan   Feb    Mar    Apr    May    Jun     │         │
│  └────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

### Dashboard 3: Customer-Specific Analytics

**Query the database to get customer analytics:**

```bash
# SSH to database server
ssh user@db-server.yourdomain.com

# Connect to database
psql -U vlaapi -d vlaapi

# Query for specific customer
SELECT 
    c.company_name,
    COUNT(*) as total_requests,
    AVG(il.inference_latency_ms) as avg_latency,
    AVG(il.safety_score) as avg_safety_score,
    COUNT(CASE WHEN il.status = 'success' THEN 1 END) * 100.0 / COUNT(*) as success_rate
FROM vlaapi.inference_logs il
JOIN vlaapi.customers c ON il.customer_id = c.customer_id
WHERE il.timestamp >= NOW() - INTERVAL '30 days'
    AND c.company_name = 'Acme Robotics Inc.'
GROUP BY c.company_name;
```

**Output:**
```
    company_name     | total_requests | avg_latency | avg_safety_score | success_rate
--------------------+----------------+-------------+------------------+--------------
 Acme Robotics Inc. |         36,450 |       125.3 |            0.912 |        99.23
```

---

### Dashboard 4: Customer Portal (Optional - Build This)

**What customers see (if you build a customer dashboard):**

```
┌─────────────────────────────────────────────────────────────┐
│  Acme Robotics - API Dashboard         Logout  │  Docs     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🔑 Your API Key                                             │
│  ┌────────────────────────────────────────────────┐         │
│  │ vla_live_acme_abc123...  [Copy]  [Regenerate]  │         │
│  └────────────────────────────────────────────────┘         │
│                                                               │
│  📊 Usage (This Month)                                       │
│  ┌────────────────────────────────────────────────┐         │
│  │  36,450 / 100,000 requests used                │         │
│  │  ███████████████████░░░░░░░░░░  36.5%         │         │
│  │                                                 │         │
│  │  Resets in: 15 days                            │         │
│  └────────────────────────────────────────────────┘         │
│                                                               │
│  ⚡ Performance                                              │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ Avg Latency      │  │ Success Rate     │               │
│  │   125ms          │  │   99.2%          │               │
│  └──────────────────┘  └──────────────────┘               │
│                                                               │
│  📈 Usage Over Time (Last 7 days)                           │
│  ┌────────────────────────────────────────────────┐         │
│  │  6k │                                    ●     │         │
│  │  5k │                            ●       ●     │         │
│  │  4k │                    ●       ●       ●     │         │
│  │  3k │            ●       ●       ●       ●     │         │
│  │  2k │    ●       ●       ●       ●       ●     │         │
│  │   0 └────┴───────┴───────┴───────┴───────┴──  │         │
│  │     Mon   Tue   Wed   Thu   Fri   Sat   Sun   │         │
│  └────────────────────────────────────────────────┘         │
│                                                               │
│  📝 Recent Requests                                          │
│  ┌────────────────────────────────────────────────┐         │
│  │ Time      Model      Status    Latency Safety  │         │
│  │ 14:32:15  openvla-7b  ✓ Success  118ms  0.92   │         │
│  │ 14:32:10  openvla-7b  ✓ Success  122ms  0.89   │         │
│  │ 14:32:05  openvla-7b  ✗ Rejected  15ms  0.65   │         │
│  │ 14:32:00  openvla-7b  ✓ Success  130ms  0.94   │         │
│  └────────────────────────────────────────────────┘         │
│                                                               │
│  💳 Billing                                                  │
│  ┌────────────────────────────────────────────────┐         │
│  │ Current Plan: Pro ($500/month)                 │         │
│  │ Current Month: $458.00                         │         │
│  │ [View Invoice] [Upgrade to Enterprise]         │         │
│  └────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

## 💼 Complete Data Flow

### From Customer Request to Your Analytics

```
1. CUSTOMER sends request
   ↓
   POST https://api.yourdomain.com/v1/inference
   Authorization: Bearer vla_live_acme_abc123...
   Body: { "image": "...", "instruction": "..." }

2. LOAD BALANCER receives it
   ↓
   nginx distributes to least busy API server

3. API SERVER processes it
   ↓
   - Validates API key (checks Redis cache → PostgreSQL)
   - Checks rate limits (Redis)
   - Runs AI model (GPU)
   - Checks safety
   - Returns action

4. DATA IS LOGGED
   ↓
   PostgreSQL: inference_logs table
   - Customer ID
   - Request details
   - Action result
   - Performance metrics
   - Safety scores

5. METRICS COLLECTED
   ↓
   Prometheus scrapes /metrics endpoint
   - Request count
   - Latency distribution
   - GPU utilization
   - Error rates

6. YOU VIEW IT
   ↓
   Grafana dashboards show:
   - Real-time metrics
   - Customer usage
   - Revenue tracking
   - System health

7. ANALYTICS QUERIES
   ↓
   SQL queries on PostgreSQL:
   - Customer usage reports
   - Robot performance analysis
   - Safety incident tracking
   - Billing calculations
```

---

## 📈 Viewing Different Analytics

### Real-Time Metrics (Grafana)

**Access:** https://monitoring.yourdomain.com

**Dashboards available:**
1. **Operations** - API health, latency, errors
2. **Business** - Revenue, customers, growth
3. **Safety** - Incidents, safety scores, violations
4. **Customer Analytics** - Per-customer usage and performance

### Historical Data (PostgreSQL)

**Access via SQL:**

```sql
-- Total requests per customer this month
SELECT 
    c.company_name,
    COUNT(*) as requests,
    c.tier
FROM inference_logs il
JOIN customers c ON il.customer_id = c.customer_id
WHERE il.timestamp >= date_trunc('month', CURRENT_DATE)
GROUP BY c.company_name, c.tier
ORDER BY requests DESC;

-- Revenue by customer
SELECT 
    c.company_name,
    c.tier,
    COUNT(*) as requests,
    CASE c.tier
        WHEN 'enterprise' THEN COUNT(*) * 0.01
        WHEN 'pro' THEN COUNT(*) * 0.015
        WHEN 'free' THEN 0
    END as revenue
FROM inference_logs il
JOIN customers c ON il.customer_id = c.customer_id
WHERE il.timestamp >= date_trunc('month', CURRENT_DATE)
GROUP BY c.company_name, c.tier
ORDER BY revenue DESC;

-- Robot performance by type
SELECT 
    il.robot_type,
    COUNT(*) as total_inferences,
    AVG(il.inference_latency_ms) as avg_latency,
    AVG(il.safety_score) as avg_safety
FROM inference_logs il
WHERE il.timestamp >= NOW() - INTERVAL '7 days'
GROUP BY il.robot_type
ORDER BY total_inferences DESC;
```

### Custom Reports (Python Scripts)

Create `scripts/generate_report.py`:

```python
#!/usr/bin/env python3
"""Generate monthly customer usage report."""

import psycopg2
import pandas as pd
from datetime import datetime

# Connect to database
conn = psycopg2.connect(
    "postgresql://vlaapi:password@db-server:5432/vlaapi"
)

# Query data
query = """
SELECT 
    c.company_name,
    c.email,
    c.tier,
    COUNT(*) as total_requests,
    AVG(il.inference_latency_ms) as avg_latency,
    COUNT(CASE WHEN il.status = 'error' THEN 1 END) as errors
FROM inference_logs il
JOIN customers c ON il.customer_id = c.customer_id
WHERE il.timestamp >= date_trunc('month', CURRENT_DATE)
GROUP BY c.company_name, c.email, c.tier
ORDER BY total_requests DESC;
"""

df = pd.read_sql(query, conn)

# Generate report
report_filename = f"usage_report_{datetime.now().strftime('%Y-%m')}.csv"
df.to_csv(report_filename, index=False)

print(f"Report generated: {report_filename}")
print(df)
```

---

## 🔐 Security Considerations

### API Key Management

**Generate API key:**
```python
import secrets
import hashlib

def generate_api_key(prefix="vla_live"):
    """Generate secure API key."""
    random_part = secrets.token_urlsafe(32)
    api_key = f"{prefix}_{random_part}"
    
    # Store hash in database (never store raw key)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    return api_key, key_hash
```

### Rate Limiting per Customer

**Set in database:**
```sql
-- Update customer rate limits
UPDATE customers
SET rate_limit_per_minute = 1000,
    rate_limit_per_day = 50000,
    monthly_quota = 1000000
WHERE company_name = 'Acme Robotics Inc.';
```

---

## 📝 Summary

### What You Install Where

| Server | Install | Port | Purpose |
|--------|---------|------|---------|
| **API Servers** | Docker + VLA API | 8000 | Process AI requests |
| **Database** | PostgreSQL + pgvector | 5432 | Store all data |
| **Cache** | Redis | 6379 | Cache API keys, consent |
| **Load Balancer** | nginx | 80, 443 | Distribute traffic |
| **Monitoring** | Prometheus + Grafana | 9090, 3000 | View analytics |
| **Storage** | S3/MinIO | 9000 | Store training data |

### How Customers Use It

1. You give them: **API key + endpoint URL**
2. They send: **Image + instruction** to your API
3. They receive: **Robot action** (7-DoF)
4. They use: **Action in their robot controller**

### How You View Analytics

1. **Real-time**: Grafana at monitoring.yourdomain.com
2. **Historical**: SQL queries on PostgreSQL
3. **Custom**: Python scripts to generate reports
4. **Customer Portal**: Build web interface (optional)

### Data You Collect

- ✅ Every API request (customer, timestamp, model)
- ✅ Performance metrics (latency, GPU usage)
- ✅ Safety scores and incidents
- ✅ Robot types and actions
- ✅ Revenue and usage per customer

---

**Next Steps:**
1. Follow server setup instructions above
2. Deploy to your infrastructure
3. Create first customer API key
4. Set up monitoring dashboards
5. Start serving customers! 🚀

