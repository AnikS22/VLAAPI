# Praxis Labs - Testing Guide

## Complete System Test

This guide walks through testing the entire Praxis Labs platform from user registration to admin monitoring.

### Prerequisites

1. **Backend running**:
```bash
python -m uvicorn src.api.main:app --reload
```

2. **Frontend running** (optional):
```bash
cd frontend
npm run dev
```

3. **Database migrated**:
```bash
psql -d vlaapi < migrations/001_create_users_and_auth.sql
```

4. **Admin user created** (for admin panel tests):
```sql
-- Connect to your database
psql -d vlaapi

-- Create admin user
INSERT INTO vlaapi.users (email, hashed_password, full_name, is_superuser, is_active, email_verified)
VALUES (
    'admin@praxislabs.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ND0azvKJMJtu', -- 'AdminPass123!'
    'Admin User',
    true,
    true,
    true
);
```

---

## Automated Testing

### Run Complete Flow Test

```bash
./scripts/test_complete_flow.sh
```

This script tests:
- ✅ User registration
- ✅ User login
- ✅ API key creation
- ✅ API key listing
- ✅ Inference execution
- ✅ Usage analytics
- ✅ Subscription info
- ✅ Admin login
- ✅ Admin stats
- ✅ Admin customer list

---

## Manual Testing

### 1. User Registration (Frontend)

**URL**: http://localhost:3000/auth/register

**Steps**:
1. Open registration page
2. Enter email: `test@example.com`
3. Enter password: `SecurePass123!` (must have uppercase, lowercase, digit)
4. Enter full name: `Test User`
5. Enter company: `Test Company`
6. Click "Create Account"

**Expected**:
- Redirects to `/dashboard`
- JWT token stored in localStorage
- User sees dashboard with 0 requests

---

### 2. Create API Key (Frontend)

**URL**: http://localhost:3000/dashboard/api-keys

**Steps**:
1. Click "Create API Key" button
2. Enter name: `Production Key`
3. Click "Create Key"
4. **IMPORTANT**: Copy the API key (shown only once!)

**Expected**:
- New API key created starting with `vla_live_`
- Key displayed in yellow warning box
- After clicking "Done", key is hidden forever
- Key appears in table with "Active" status

---

### 3. Run Inference (API)

**Using the API key from step 2**:

```bash
# Create a test image
echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" > /tmp/test_image.b64

# Run inference
curl -X POST http://localhost:8000/v1/inference \
  -H "X-API-Key: vla_live_YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "data:image/png;base64,'$(cat /tmp/test_image.b64)'",
    "instruction": "Pick up the red block",
    "robot_type": "franka_panda"
  }'
```

**Expected Response**:
```json
{
  "log_id": "uuid-here",
  "action": {
    "vector": [0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 1.0],
    "type": "pick_and_place"
  },
  "safety": {
    "score": 0.95,
    "passed": true,
    "flags": []
  },
  "performance": {
    "latency_ms": 145.2,
    "model_version": "openvla-7b-v1"
  }
}
```

---

### 4. View Analytics (Frontend)

**URL**: http://localhost:3000/dashboard/analytics

**Steps**:
1. Navigate to Analytics page
2. Select time range: "Last 7 days"

**Expected**:
- Usage chart shows request volume
- Success rate card shows 100% (if all succeeded)
- Safety chart shows 0 incidents
- Top instructions list shows recent commands

---

### 5. Test Playground (Frontend)

**URL**: http://localhost:3000/dashboard/playground

**Steps**:
1. Upload an image (any robot scene image)
2. Enter instruction: "Pick up the red object"
3. Select robot: "Franka Panda"
4. Click "Run Inference"

**Expected**:
- 7-DoF action vector displayed
- Safety score shown (0-100%)
- Latency displayed in milliseconds
- Inference ID shown

---

### 6. View History (Frontend)

**URL**: http://localhost:3000/dashboard/history

**Steps**:
1. View paginated list of inferences
2. Filter by status: "Success"
3. Click "View" on any row

**Expected**:
- Table shows all past inferences
- Modal shows full inference details
- Filters work correctly
- Pagination works

---

### 7. Settings & Billing (Frontend)

**URL**: http://localhost:3000/dashboard/settings

**Steps**:
1. Update profile information
2. Change password
3. Toggle consent preferences
4. View current subscription (Free tier)

**For paid tier upgrade**:
1. Click "Upgrade to Pro" ($499/month)
2. Redirects to Stripe checkout
3. Complete payment (use Stripe test cards)

---

### 8. Admin Panel Access (Frontend)

**URL**: http://localhost:3000/admin

**Prerequisites**: User must have `is_superuser=true` in database

**Steps**:
1. Login as admin user
2. Navigate to `/admin`

**Expected**:
- Admin navigation with red theme
- Access to 4 admin pages

---

### 9. Admin Overview (Frontend)

**URL**: http://localhost:3000/admin

**Expected Data**:
- Total customers count
- Total requests (30d)
- Monthly Recurring Revenue (MRR)
- Safety incidents count
- Tier distribution chart
- System health status
- Top 10 customers by usage
- Recent critical incidents

---

### 10. Customer Management (Frontend)

**URL**: http://localhost:3000/admin/customers

**Steps**:
1. Search for customer by email
2. Click "View Details" on a customer
3. Change tier from "Free" to "Pro"
4. Click "Update Tier"

**Expected**:
- Customer list with pagination
- Search filters work
- Detail modal shows usage stats
- Tier update saves successfully

---

### 11. Safety Review (Frontend)

**URL**: http://localhost:3000/admin/safety

**Steps**:
1. Filter by severity: "Critical"
2. View incident patterns
3. Click "View" on an incident

**Expected**:
- Incidents listed by severity
- Pattern analysis shows trends
- Detail modal shows full incident info

---

### 12. System Monitoring (Frontend)

**URL**: http://localhost:3000/admin/monitoring

**Expected (refreshes every 10s)**:
- System health: API, Database, Redis, Queue
- API metrics: Requests/min, latency, error rate
- GPU metrics: Utilization, memory, temperature
- Queue depth and throughput
- Resource usage: CPU, memory, disk

---

## API Testing with curl

### Authentication
```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123!","full_name":"Test User"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=SecurePass123!"
```

### API Keys
```bash
# Create
curl -X POST http://localhost:8000/v1/api-keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"key_name":"Test Key","scopes":["inference"]}'

# List
curl http://localhost:8000/v1/api-keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Analytics
```bash
curl "http://localhost:8000/v1/analytics/usage?days=7" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Admin (requires superuser)
```bash
# Stats
curl http://localhost:8000/admin/stats \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN"

# Customers
curl "http://localhost:8000/admin/customers?page=1&limit=50" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN"
```

---

## Data Verification

### Check Database After Tests

```sql
-- Check user was created
SELECT email, full_name, is_active, email_verified FROM vlaapi.users WHERE email = 'test@example.com';

-- Check customer was created
SELECT email, company_name, tier, monthly_usage, monthly_quota FROM vlaapi.customers WHERE email = 'test@example.com';

-- Check API key was created
SELECT key_name, key_prefix, is_active, created_at FROM vlaapi.api_keys WHERE customer_id = (SELECT customer_id FROM vlaapi.customers WHERE email = 'test@example.com');

-- Check inference was logged
SELECT log_id, instruction, status, safety_score, latency_ms, timestamp FROM vlaapi.inference_logs WHERE customer_id = (SELECT customer_id FROM vlaapi.customers WHERE email = 'test@example.com') ORDER BY timestamp DESC LIMIT 5;
```

---

## Troubleshooting

### "API key not found"
- Ensure you're using the full API key (starts with `vla_live_`)
- Check the key is active in the database
- Verify you copied the entire key

### "Not authorized. Admin access required"
- Ensure user has `is_superuser=true` in database
- Re-login to get fresh JWT token
- Check you're using admin JWT, not regular user JWT

### "Model not loaded"
- VLA models are large and may not load in dev environment
- Check logs: `tail -f logs/app.log`
- Inference endpoint will return 503 if model unavailable

### Frontend not connecting to backend
- Verify `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
- Should be `http://localhost:8000`
- Restart frontend after changing env vars

---

## Success Criteria

✅ **User Flow**:
- User can register and login
- User can create and manage API keys
- User can run inferences successfully
- User can view analytics and history
- User can update profile and settings

✅ **Admin Flow**:
- Admin can view system stats
- Admin can manage customers
- Admin can review safety incidents
- Admin can monitor system health

✅ **Data Collection**:
- Inferences are logged in database
- Usage stats are aggregated correctly
- Safety incidents are tracked
- Analytics display real data

---

## Next Steps

After successful testing:

1. **Deploy Backend**: DigitalOcean, AWS, or GCP
2. **Deploy Frontend**: Vercel or Netlify
3. **Configure Stripe**: Production webhook URLs
4. **Set up Monitoring**: Prometheus + Grafana
5. **Load Testing**: k6 or Locust
6. **Security Audit**: OWASP ZAP scan
7. **Performance Optimization**: Query optimization, caching
