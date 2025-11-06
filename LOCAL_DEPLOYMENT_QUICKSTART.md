# 🚀 Local Mock Deployment - Quick Start

**Test everything locally in 5 minutes!**

---

## What You'll Get

✅ Complete API running locally (no servers needed!)  
✅ PostgreSQL database with test data  
✅ Redis cache  
✅ Grafana dashboards  
✅ 3 test customer accounts  
✅ Ability to test full customer workflows  

---

## One-Command Setup

```bash
./scripts/local_deploy.sh
```

**That's it!** The script will:
- Start all services in Docker
- Initialize database
- Create 3 test customers
- Give you API keys

---

## After Setup Complete

### Step 1: Get Your API Keys

```bash
cat test_api_keys.txt
```

You'll see something like:
```
FREE_TIER_KEY=vla_local_abc123...
PRO_TIER_KEY=vla_local_def456...
ENTERPRISE_TIER_KEY=vla_local_ghi789...
```

### Step 2: Test the API

Edit `test_local_api.py` and paste your keys, then run:

```bash
python test_local_api.py
```

You should see:
```
✅ ALL TESTS PASSED!
```

### Step 3: View Dashboards

Open in your browser:

- **Grafana:** http://localhost:3000 (login: admin/admin123)
- **Prometheus:** http://localhost:9090
- **API Docs:** http://localhost:8000/docs

---

## Make Test API Calls

```bash
# Replace with your actual key from test_api_keys.txt
export API_KEY="vla_local_YOUR_KEY_HERE"

# Test health
curl http://localhost:8000/health

# Test inference
curl -X POST http://localhost:8000/v1/inference \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openvla-7b",
    "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "instruction": "pick up the red cube"
  }'
```

---

## View Data

### Check Database

```bash
# Connect to PostgreSQL
docker exec -it vlaapi-postgres-local psql -U vlaapi -d vlaapi

# View customers
SELECT company_name, tier, monthly_usage FROM customers;

# View recent requests
SELECT timestamp, instruction, status FROM inference_logs ORDER BY timestamp DESC LIMIT 5;

# Exit
\q
```

### Check Redis

```bash
docker exec vlaapi-redis-local redis-cli -a local_redis_123

# View cached keys
KEYS *

# Exit
exit
```

---

## Simulate Traffic

Watch your dashboards fill with data!

```bash
# Install requests if needed
pip install requests

# Create traffic simulation script
cat > simulate_traffic.py << 'EOF'
import requests
import time

API_KEY = "vla_local_YOUR_KEY_HERE"  # Replace!
TEST_IMAGE = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

for i in range(100):
    response = requests.post(
        "http://localhost:8000/v1/inference",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "openvla-7b",
            "image": TEST_IMAGE,
            "instruction": f"test request {i}"
        }
    )
    print(f"{i+1}/100: {response.status_code}")
    time.sleep(0.5)
EOF

# Run it
python simulate_traffic.py
```

While it runs, watch Grafana at http://localhost:3000!

---

## Common Commands

### View Logs
```bash
# All services
docker-compose -f docker-compose.local.yml logs -f

# Just API
docker-compose -f docker-compose.local.yml logs -f api

# Just database
docker-compose -f docker-compose.local.yml logs -f postgres
```

### Restart Services
```bash
# Restart all
docker-compose -f docker-compose.local.yml restart

# Restart just API
docker-compose -f docker-compose.local.yml restart api
```

### Stop Everything
```bash
docker-compose -f docker-compose.local.yml down
```

### Reset Database (Start Fresh)
```bash
# Stop and remove all data
docker-compose -f docker-compose.local.yml down -v

# Start again
./scripts/local_deploy.sh
```

---

## What to Test

### ✅ Customer Workflows
- [x] Create customer account
- [x] Get API key
- [x] Make API calls
- [x] See data in database
- [x] View in dashboards

### ✅ API Functionality
- [x] Health check works
- [x] Inference endpoint works
- [x] Rate limiting works
- [x] Different tiers have different limits
- [x] Metrics collected

### ✅ Monitoring
- [x] Grafana shows data
- [x] Prometheus collecting metrics
- [x] Can query database
- [x] Can view logs

---

## Next Steps

### When Local Testing is Done

1. **Document what works**
   ```bash
   echo "✅ Local testing completed: $(date)" > local_test_passed.txt
   ```

2. **Get production servers**
   - See cost estimates in `docs/QUICK_ARCHITECTURE_GUIDE.md`

3. **Deploy to production**
   - Follow `docs/DEPLOYMENT_AND_OPERATIONS.md`
   - Use same Docker setup!
   - Just change:
     * `USE_MOCK_MODELS=false` (use real GPU models)
     * Database passwords
     * Domain names
     * SSL certificates

---

## Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker ps

# Check for port conflicts
lsof -i :8000  # API port
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :3000  # Grafana

# Kill conflicting processes or change ports
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker exec vlaapi-postgres-local pg_isready -U vlaapi

# Restart database
docker-compose -f docker-compose.local.yml restart postgres
```

### API Not Responding

```bash
# Check API logs
docker logs vlaapi-api-local

# Restart API
docker-compose -f docker-compose.local.yml restart api
```

---

## FAQ

**Q: Do I need a GPU?**  
A: No! Mock models work on any computer.

**Q: How much disk space?**  
A: About 2-3GB for Docker images and data.

**Q: Can I test with multiple customers?**  
A: Yes! You have 3 test accounts (free/pro/enterprise).

**Q: Will my data persist?**  
A: Yes, until you run `docker-compose down -v`.

**Q: Can I test the exact production setup?**  
A: Yes! This is identical to production (just with mock models).

---

## Full Documentation

- **This guide:** Quick start (you are here)
- **Complete guide:** `docs/LOCAL_MOCK_DEPLOYMENT.md`
- **Production deployment:** `docs/DEPLOYMENT_AND_OPERATIONS.md`
- **Architecture overview:** `docs/QUICK_ARCHITECTURE_GUIDE.md`

---

## Success Criteria

Before deploying to production, verify:

- ✅ All tests in `test_local_api.py` pass
- ✅ Can create customers
- ✅ API calls work with different API keys
- ✅ Rate limiting works
- ✅ Data appears in database
- ✅ Dashboards show metrics
- ✅ Can simulate traffic successfully

**If all ✅ → You're ready for production!** 🚀

---

**Questions?** Read `docs/LOCAL_MOCK_DEPLOYMENT.md` for detailed explanations.

