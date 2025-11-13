# Deploy to Render - Step by Step

**Time**: 10 minutes | **Cost**: FREE PostgreSQL + $7/month for backend (or FREE with spin-down)

---

## Quick Deploy (Automatic)

1. **Click this button**: [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

2. **Or go to**: https://dashboard.render.com/select-repo?type=blueprint

3. **Select your VLAAPI repository**

4. **Render will automatically**:
   - Create PostgreSQL database (FREE)
   - Deploy backend service
   - Set up environment variables

---

## Manual Setup (If automatic fails)

### Step 1: Create PostgreSQL Database (2 min)

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"PostgreSQL"**
3. Settings:
   - **Name**: `praxis-postgres`
   - **Database**: `vlaapi`
   - **User**: `vlaapi`
   - **Region**: `Oregon (US West)`
   - **Plan**: **Free** (500MB)
4. Click **"Create Database"**
5. **COPY** the "Internal Database URL" (you'll need this)

### Step 2: Deploy Backend Service (3 min)

1. Click **"New +"** → **"Web Service"**
2. **Connect GitHub** and select `VLAAPI` repository
3. Settings:
   - **Name**: `praxis-backend-api`
   - **Region**: `Oregon (US West)` (same as database)
   - **Branch**: `main`
   - **Root Directory**: `.` (leave blank)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn src.api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120`
4. **Plan**: Select **"Free"** (spins down after 15min) or **"Starter $7/month"** (always on)
5. Click **"Create Web Service"** (don't deploy yet!)

### Step 3: Add Environment Variables (2 min)

In the Render dashboard for your web service, go to **"Environment"** and add:

#### Required Variables:
```
DATABASE_URL = <paste Internal Database URL from Step 1>
REDIS_URL = redis://localhost:6379/0
JWT_SECRET_KEY = <generate random 32+ character string>
STRIPE_SECRET_KEY = sk_test_your_test_key
STRIPE_PUBLISHABLE_KEY = pk_test_your_test_key
CORS_ORIGINS = https://frontend-1gp6cxaq3-aniksahai-icloudcoms-projects.vercel.app
ENVIRONMENT = production
DEBUG = false
```

#### Optional Variables:
```
STRIPE_WEBHOOK_SECRET = whsec_...
STRIPE_PRICE_ID_PRO = price_...
STRIPE_PRICE_ID_ENTERPRISE = price_...
ENABLE_GPU_MONITORING = false
ENABLE_PROMETHEUS = true
ENABLE_EMBEDDINGS = false
```

**To generate JWT_SECRET_KEY**:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 4: Deploy

1. Click **"Manual Deploy"** → **"Deploy latest commit"**
2. Wait ~5 minutes for deployment
3. Copy your backend URL: `https://praxis-backend-api.onrender.com`

### Step 5: Run Database Migration (2 min)

**Option A: Using Render Shell**
1. In Render dashboard, click your PostgreSQL service
2. Click **"Connect"** → **"External Connection"**
3. Copy the `psql` command
4. Run locally:
   ```bash
   # Use the psql command from Render, then:
   \i /Users/aniksahai/Desktop/VLAAPI/migrations/001_create_users_and_auth.sql
   ```

**Option B: Using SQL Editor**
1. Click PostgreSQL service → **"SQL Editor"**
2. Copy contents of `migrations/001_create_users_and_auth.sql`
3. Paste and **"Execute"**

**Option C: Upload and Execute**
```bash
# Get connection string from Render
export DATABASE_URL="<your-external-database-url>"

# Run migration
psql $DATABASE_URL < migrations/001_create_users_and_auth.sql
```

### Step 6: Create Admin User

In the SQL Editor or psql, run:
```sql
INSERT INTO vlaapi.users (email, hashed_password, full_name, is_superuser, is_active, email_verified)
VALUES (
    'admin@praxislabs.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ND0azvKJMJtu',
    'Admin User',
    true,
    true,
    true
);
```

---

## ✅ Verify Backend is Working

Test your backend:
```bash
curl https://praxis-backend-api.onrender.com/
```

Expected response:
```json
{
  "name": "Praxis Labs VLA API",
  "version": "1.0.0",
  "status": "running"
}
```

---

## 🔗 Update Frontend (Vercel)

1. Go to https://vercel.com/aniksahai-icloudcoms-projects/frontend
2. Click **"Settings"** → **"Environment Variables"**
3. Add or update:
   ```
   NEXT_PUBLIC_API_URL = https://praxis-backend-api.onrender.com
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY = pk_test_your_test_key
   ```
4. Go to **"Deployments"**
5. Click **"⋯"** on latest deployment → **"Redeploy"**
6. Wait ~2 minutes

---

## 🧪 Test Complete Flow

### 1. Test Backend Health
```bash
curl https://praxis-backend-api.onrender.com/
```

### 2. Test Frontend
Visit: https://frontend-1gp6cxaq3-aniksahai-icloudcoms-projects.vercel.app

### 3. Test Registration
1. Click "Sign up"
2. Register new user
3. Should redirect to dashboard

### 4. Test API Key Creation
1. Go to "API Keys" page
2. Click "Create API Key"
3. Copy the key (shown once!)

### 5. Test Inference (Optional)
```bash
curl -X POST https://praxis-backend-api.onrender.com/v1/inference \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "instruction": "Pick up the red block",
    "robot_type": "franka_panda"
  }'
```

### 6. Test Admin Panel
1. Visit frontend
2. Login as `admin@praxislabs.com` / `AdminPass123!`
3. Go to `/admin`
4. Should see admin dashboard

---

## 💰 Cost Breakdown

| Service | Plan | Cost |
|---------|------|------|
| PostgreSQL | Free | $0 |
| Backend | Free (with spin-down) | $0 |
| Backend | Starter (always on) | $7/month |
| Frontend (Vercel) | Free | $0 |
| **Total (Free)** | | **$0** |
| **Total (Starter)** | | **$7/month** |

---

## ⚠️ Important Notes

### Free Tier Limitations:
- Backend spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds (cold start)
- PostgreSQL limited to 500MB storage

### Recommended for Production:
- Upgrade to **Starter Plan** ($7/month) for always-on backend
- Consider **Upstash** for Redis (free tier): https://upstash.com
- Set up proper Stripe production keys

---

## 🔧 Troubleshooting

### Backend won't start
1. Check logs in Render dashboard
2. Verify all environment variables are set
3. Ensure `DATABASE_URL` is correct

### Database connection failed
1. Verify PostgreSQL service is running
2. Check `DATABASE_URL` format: `postgresql://user:pass@host:5432/dbname`
3. Ensure backend and database are in same region

### Frontend can't connect to backend
1. Check `NEXT_PUBLIC_API_URL` in Vercel
2. Verify CORS settings in backend
3. Check backend is running (not spun down)

### Migration failed
1. Check PostgreSQL is running
2. Verify database URL
3. Try running SQL manually in Render SQL Editor

---

## 📚 Next Steps

1. **Set up Redis** (optional): Use Upstash for free Redis
2. **Configure Stripe**: Add production webhook
3. **Custom Domain**: Add to both Render and Vercel
4. **Monitoring**: Enable Render metrics
5. **Backups**: Set up automatic database backups

---

**Need help?** Check Render docs: https://render.com/docs
