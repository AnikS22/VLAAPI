# 🏗️ Quick Architecture Guide - Visual Summary

**5-minute overview of how everything connects**

---

## 🎯 The Big Picture

```
YOUR BUSINESS
└── You run 6 types of servers
    └── Customers call your API
        └── You see everything in dashboards
            └── You make money 💰
```

---

## 🖥️ Your 6 Server Types

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR INFRASTRUCTURE                       │
│                                                              │
│  1️⃣  API SERVERS (3+)          What: Process AI requests   │
│     ┌─────────────────┐         Where: api-1.yourco.com    │
│     │ FastAPI + GPU   │         Needs: NVIDIA GPU          │
│     │ Port 8000       │         Cost: $2-3/hr each         │
│     └─────────────────┘                                     │
│                                                              │
│  2️⃣  DATABASE SERVER (1)       What: Store everything      │
│     ┌─────────────────┐         Where: db.yourco.com       │
│     │ PostgreSQL      │         Needs: 500GB SSD           │
│     │ Port 5432       │         Cost: $0.50/hr             │
│     └─────────────────┘                                     │
│                                                              │
│  3️⃣  CACHE SERVER (1)          What: Speed up requests     │
│     ┌─────────────────┐         Where: cache.yourco.com    │
│     │ Redis           │         Needs: 8GB RAM             │
│     │ Port 6379       │         Cost: $0.20/hr             │
│     └─────────────────┘                                     │
│                                                              │
│  4️⃣  LOAD BALANCER (1)         What: Distribute traffic    │
│     ┌─────────────────┐         Where: api.yourco.com      │
│     │ nginx           │         Needs: 4GB RAM             │
│     │ Port 443(HTTPS) │         Cost: $0.10/hr             │
│     └─────────────────┘                                     │
│                                                              │
│  5️⃣  MONITORING (1)            What: Show dashboards       │
│     ┌─────────────────┐         Where: monitor.yourco.com  │
│     │ Grafana         │         Needs: 8GB RAM             │
│     │ Port 3000       │         Cost: $0.20/hr             │
│     └─────────────────┘                                     │
│                                                              │
│  6️⃣  STORAGE (1)               What: Save training data    │
│     ┌─────────────────┐         Where: S3/MinIO            │
│     │ S3 or MinIO     │         Needs: 1TB+ storage        │
│     │ Port 9000       │         Cost: $0.02/GB/month       │
│     └─────────────────┘                                     │
│                                                              │
│  💰 Total Cost: ~$6-8/hour = ~$4,500/month                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 How a Customer Request Flows

```
STEP 1: Customer sends request
┌──────────────────────────────────────────┐
│ Customer's Robot Controller              │
│                                          │
│ POST https://api.yourco.com/v1/inference│
│ Authorization: Bearer vla_live_abc123... │
│ Body: {                                  │
│   "image": "base64_image_data...",       │
│   "instruction": "pick up red cube"     │
│ }                                        │
└──────────────┬───────────────────────────┘
               │
               ↓
STEP 2: Your load balancer receives it
┌──────────────▼───────────────────────────┐
│ nginx Load Balancer                      │
│ - Checks SSL certificate                 │
│ - Applies rate limits                    │
│ - Picks least busy API server            │
└──────────────┬───────────────────────────┘
               │
               ↓
STEP 3: API server processes it
┌──────────────▼───────────────────────────┐
│ API Server (FastAPI)                     │
│                                          │
│ 1. Validate API key (Redis → PostgreSQL)│
│ 2. Check rate limits (Redis)            │
│ 3. Decode image                          │
│ 4. Run AI model on GPU (120ms)          │
│ 5. Check safety rules                    │
│ 6. Log everything (PostgreSQL)           │
│ 7. Update metrics (Prometheus)           │
└──────────────┬───────────────────────────┘
               │
               ↓
STEP 4: Response sent back
┌──────────────▼───────────────────────────┐
│ Response                                 │
│ {                                        │
│   "action": {                            │
│     "values": [0.15, -0.08, 0.22, ...]  │
│   },                                     │
│   "safety": {                            │
│     "overall_score": 0.92                │
│   }                                      │
│ }                                        │
└──────────────┬───────────────────────────┘
               │
               ↓
STEP 5: Customer uses action
┌──────────────▼───────────────────────────┐
│ Customer's Robot                         │
│ - Receives action vector                 │
│ - Moves to position [0.15, -0.08, 0.22] │
│ - Closes gripper                         │
│ - Task complete! ✓                       │
└──────────────────────────────────────────┘
```

---

## 📊 What Gets Stored (Database Tables)

```
EVERY REQUEST CREATES RECORDS IN:

1. inference_logs
┌────────────────────────────────────────┐
│ customer_id    | abc-123-def            │
│ timestamp      | 2025-01-15 14:23:45    │
│ model          | openvla-7b             │
│ robot_type     | franka_panda           │
│ instruction    | "pick up red cube"     │
│ action         | [0.15, -0.08, 0.22...] │
│ safety_score   | 0.92                   │
│ latency_ms     | 145                    │
│ status         | success                │
└────────────────────────────────────────┘

2. customer usage tracking
┌────────────────────────────────────────┐
│ Acme Robotics  | 36,450 requests       │
│ TechCorp       | 8,200 requests        │
│ RoboFactory    | 5,100 requests        │
└────────────────────────────────────────┘

3. Performance metrics (Prometheus)
┌────────────────────────────────────────┐
│ vla_requests_total      | 49,750       │
│ vla_avg_latency_ms      | 128          │
│ vla_success_rate        | 99.2%        │
│ vla_gpu_utilization     | 78%          │
└────────────────────────────────────────┘
```

---

## 👁️ Your Dashboards (What You See)

### Dashboard 1: Operations (Grafana)

**URL:** `https://monitor.yourco.com`

```
┌─────────────────────────────────────────────────────┐
│  🖥️  VLA API Operations Dashboard                   │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Requests/Min: 2,450  ↑                             │
│  Success Rate: 99.2%  ✓                             │
│  Avg Latency:  128ms  ✓                             │
│  GPU Usage:    78%    ✓                             │
│                                                      │
│  [Live Graph showing last hour]                     │
│  ────────────────────────────────────               │
│      ▁▂▃▅▆▇█▇▆▅▃▂▁                                  │
│                                                      │
│  Active Customers:    23                            │
│  Top Customer:        Acme Robotics (49%)           │
│  Errors (last hour):  12 (0.8%)                     │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Dashboard 2: Business Metrics

```
┌─────────────────────────────────────────────────────┐
│  💰 Business Dashboard                               │
├─────────────────────────────────────────────────────┤
│                                                      │
│  This Month:                                        │
│    Revenue:     $45,800  (+12% from last month)     │
│    Customers:   23       (+3 new)                   │
│    API Calls:   2.1M     (+15%)                     │
│                                                      │
│  Top Customers (by revenue):                        │
│  1. Acme Robotics       $15,000                     │
│  2. TechCorp            $8,500                      │
│  3. RoboFactory         $6,200                      │
│                                                      │
│  Revenue by Tier:                                   │
│    Enterprise:  65%  ████████████████░░             │
│    Pro:         28%  ███████░░░░░░░░░░              │
│    Free:        7%   ██░░░░░░░░░░░░░░               │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Dashboard 3: Customer Details (SQL Query)

```sql
-- Run this to see customer usage
SELECT 
    company_name,
    tier,
    monthly_usage as requests,
    monthly_quota as limit,
    ROUND(monthly_usage::numeric / monthly_quota * 100, 1) as usage_pct
FROM customers
WHERE is_active = true
ORDER BY monthly_usage DESC;
```

**Results:**
```
company_name         | tier       | requests | limit   | usage_pct
--------------------+------------+----------+---------+-----------
Acme Robotics Inc.  | enterprise |   36,450 | 1000000 |      3.6
TechCorp LLC        | pro        |    8,200 |  100000 |      8.2
RoboFactory         | pro        |    5,100 |  100000 |      5.1
AutoMate Inc        | free       |      980 |   10000 |      9.8
```

---

## 💳 How Billing Works

### Pricing Tiers

```
FREE TIER
┌────────────────────────────────┐
│ Price: $0/month                │
│ Limits:                        │
│   - 10 requests/minute         │
│   - 1,000 requests/day         │
│   - 10,000 requests/month      │
│                                │
│ Good for: Testing              │
└────────────────────────────────┘

PRO TIER
┌────────────────────────────────┐
│ Price: $500/month              │
│ Limits:                        │
│   - 100 requests/minute        │
│   - 10,000 requests/day        │
│   - 100,000 requests/month     │
│                                │
│ Good for: Small production     │
└────────────────────────────────┘

ENTERPRISE TIER
┌────────────────────────────────┐
│ Price: $2,500/month base       │
│        + $0.01 per request     │
│ Limits:                        │
│   - 1,000 requests/minute      │
│   - 100,000 requests/day       │
│   - Unlimited monthly          │
│                                │
│ Good for: Large scale          │
└────────────────────────────────┘
```

### Revenue Calculation

```python
# Example: Acme Robotics (Enterprise)
base_fee = 2500  # Base monthly fee
requests = 36450  # Total requests this month
per_request = 0.01  # $0.01 per request

total_revenue = base_fee + (requests * per_request)
# = $2,500 + $364.50
# = $2,864.50
```

---

## 🔑 Customer Onboarding Flow

```
STEP 1: Customer signs up
    ↓
  [You receive notification]
    ↓
STEP 2: You create API key
    $ python scripts/create_customer.py
    ↓
  Generated: vla_live_abc123def456...
    ↓
STEP 3: You send them:
    ✉️  Email with:
       - API Key
       - API endpoint URL
       - Documentation link
       - Rate limits
    ↓
STEP 4: Customer integrates
    [They add API calls to their code]
    ↓
STEP 5: They start making requests
    [You see activity in dashboard]
    ↓
STEP 6: You invoice them monthly
    [Based on usage from database]
```

---

## 📁 File Locations on Servers

### API Servers
```
/opt/vlaapi/
├── .env                    # Configuration
├── docker-compose.yml      # Docker setup
├── src/                    # Python code
│   ├── api/main.py        # Main API
│   └── services/          # AI models
└── logs/                   # Application logs
```

### Database Server
```
/var/lib/postgresql/15/main/
└── data/                   # Database files
```

### Monitoring Server
```
/opt/monitoring/
├── prometheus.yml          # Metrics config
├── grafana-dashboards/     # Dashboard JSONs
└── data/                   # Metrics storage
```

---

## 🚀 Deployment Checklist

### Before Launch
- [ ] API servers deployed and tested
- [ ] Database initialized with schema
- [ ] Redis running and accessible
- [ ] Load balancer configured with SSL
- [ ] Monitoring dashboards set up
- [ ] First customer account created
- [ ] Documentation published
- [ ] Pricing page live

### Weekly Tasks
- [ ] Check server health in Grafana
- [ ] Review error logs
- [ ] Monitor GPU utilization
- [ ] Check customer usage
- [ ] Send invoices

### Monthly Tasks
- [ ] Generate revenue reports
- [ ] Backup database
- [ ] Review and optimize costs
- [ ] Update capacity planning
- [ ] Customer satisfaction check

---

## 🎯 Key Metrics to Watch

```
HEALTH METRICS
✓ API Uptime:        > 99.9%
✓ Response Time:     < 200ms (p99)
✓ Error Rate:        < 1%
✓ GPU Utilization:   60-80% (not too low, not too high)

BUSINESS METRICS
✓ Active Customers:  Growing month-over-month
✓ Revenue:           $30K+ per month (to cover costs + profit)
✓ Usage per Customer: Increasing (shows value)
✓ Churn Rate:        < 5% per month

ALERTS (Set these up!)
🚨 Error rate > 5%           → Page on-call engineer
🚨 Latency > 500ms (p99)     → Investigate immediately
🚨 GPU temp > 85°C           → Check cooling
🚨 Database disk > 80% full  → Add storage
🚨 Customer usage spike      → May need scaling
```

---

## 💡 Quick Reference

### Important URLs
- **Customer API**: `https://api.yourco.com`
- **Monitoring**: `https://monitor.yourco.com`
- **Documentation**: `https://docs.yourco.com`

### Important Commands
```bash
# Check API health
curl https://api.yourco.com/health

# Create customer
python scripts/create_customer.py

# View logs
docker logs -f vlaapi-api-1

# Check database
psql -U vlaapi -d vlaapi -c "SELECT COUNT(*) FROM inference_logs;"

# Restart API server
docker-compose restart api
```

### Important Files
- `docs/DEPLOYMENT_AND_OPERATIONS.md` - Full deployment guide
- `docs/BEGINNERS_API_GUIDE.md` - How APIs work
- `scripts/create_customer.py` - Customer management
- `.env` - Configuration settings

---

## 📞 Support Resources

**For You (Operator):**
- Server setup: `docs/DEPLOYMENT_AND_OPERATIONS.md`
- Troubleshooting: Check Grafana dashboards
- Customer questions: Send them documentation

**For Customers:**
- API docs: `docs/VLA-API-README.md`
- Beginners guide: `docs/BEGINNERS_API_GUIDE.md`
- Examples: `examples/` folder

---

**Ready to deploy?** Follow `docs/DEPLOYMENT_AND_OPERATIONS.md` for complete setup! 🚀

