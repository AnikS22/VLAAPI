# Backend Deployment Options

**Current Status**: ⚠️ Railway trial expired - Upgrade required or use alternative

---

## ⚠️ Railway Trial Expired

Your Railway trial has expired. You have two options:

### Option A: Upgrade Railway ($5/month) ✅ **RECOMMENDED**

**Why Railway**:
- Easiest deployment (one command)
- Includes PostgreSQL + Redis in one plan
- Auto-scaling and monitoring
- $5/month covers everything

**Steps to Upgrade**:
1. Go to https://railway.com/account/billing
2. Click **"Upgrade to Hobby Plan"** ($5/month)
3. Enter payment details
4. Return here and run: `railway add --service "praxis-backend-api"`

**After Upgrading, Run**:
```bash
# Add backend service
railway add --service "praxis-backend-api"

# Deploy backend
railway up

# View logs
railway logs

# Get your backend URL
railway domain
```

---

### Option B: Use Render (FREE tier available) 💰 **FREE OPTION**

**Why Render**:
- **FREE PostgreSQL database** (500MB)
- **$7/month** for backend service (or FREE with 512MB RAM, spins down after inactivity)
- Simple deployment

**Setup Instructions**:

#### 1. Create Account
Go to https://render.com and sign up

#### 2. Deploy PostgreSQL (FREE)
1. Click **"New +"** → **"PostgreSQL"**
2. Name: `praxis-postgres`
3. Select **"Free"** plan
4. Click **"Create Database"**
5. Copy the **"Internal Database URL"**

#### 3. Deploy Backend Service
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Select your VLAAPI repository
4. Configure:
   - **Name**: `praxis-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn src.api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
   - **Plan**: Select **"Free"** or **"Starter" ($7/month)**

#### 4. Set Environment Variables
In Render dashboard, add these variables:

```bash
DATABASE_URL=<from Render PostgreSQL>
REDIS_URL=redis://localhost:6379  # Or use Upstash (free Redis)
JWT_SECRET_KEY=your-super-secret-key-change-this
STRIPE_SECRET_KEY=sk_live_...
CORS_ORIGINS=https://frontend-1gp6cxaq3-aniksahai-icloudcoms-projects.vercel.app
ENVIRONMENT=production
```

#### 5. Add Redis (Optional - Use Upstash Free)
Since Render doesn't offer free Redis:
1. Go to https://upstash.com
2. Create account and free Redis database
3. Copy the Redis URL
4. Add to Render env vars: `REDIS_URL=<upstash-url>`

**Cost**: **FREE** (PostgreSQL free + Backend free tier) or **$7/month** for always-on backend

---

### Option C: DigitalOcean App Platform ($10/month)

**Why DigitalOcean**:
- Production-grade infrastructure
- Easy scaling
- Good performance

**Setup**:
1. Go to https://cloud.digitalocean.com/apps
2. Click **"Create App"**
3. Connect GitHub repository
4. Select VLAAPI repo
5. Configure:
   - **Type**: Web Service
   - **Source Directory**: `/`
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `gunicorn src.api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080`
6. Add PostgreSQL database (click "Create Resource" → "Database")
7. Set environment variables (same as above)

**Cost**: $5-10/month (basic droplet) + $15/month (PostgreSQL)

---

### Option D: Run Locally (Development)

If you just want to test everything locally:

```bash
# 1. Install PostgreSQL and Redis locally
brew install postgresql redis  # macOS
# or
sudo apt install postgresql redis  # Ubuntu

# 2. Start services
brew services start postgresql
brew services start redis

# 3. Create database
createdb vlaapi

# 4. Set environment variables
cp .env.example .env
# Edit .env with local values

# 5. Run migration
psql -d vlaapi < migrations/001_create_users_and_auth.sql

# 6. Start backend
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Access**:
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🎯 Recommendation Based on Budget

| Budget | Recommendation | Cost | Best For |
|--------|---------------|------|----------|
| **Free** | Render Free | $0 | Testing/MVP |
| **$5-10/month** | Railway Hobby | $5 | Easy deployment |
| **$7/month** | Render Starter | $7 | Small production |
| **$15+/month** | DigitalOcean | $15+ | Scalable production |

---

## ✅ What I've Prepared for You

I've already created all the configuration files you need:

1. ✅ **`railway.json`** - Railway deployment config
2. ✅ **`Procfile`** - Process configuration
3. ✅ **`nixpacks.toml`** - Build configuration
4. ✅ **`runtime.txt`** - Python version
5. ✅ **`requirements.txt`** - Updated with gunicorn

**These files work for**:
- ✅ Railway (after upgrade)
- ✅ Render
- ✅ Heroku
- ✅ DigitalOcean
- ✅ Any platform that supports Procfile

---

## 🚀 Quick Start (Choose One)

### Railway (After Upgrade)
```bash
railway add --service "praxis-backend-api"
railway add --database postgres
railway add --database redis
railway up
```

### Render
1. Go to https://render.com
2. New → Web Service
3. Connect GitHub
4. Add environment variables
5. Click "Create Web Service"

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start backend
uvicorn src.api.main:app --reload
```

---

## 📋 Environment Variables Needed (All Platforms)

```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/vlaapi
REDIS_URL=redis://host:6379/0
JWT_SECRET_KEY=your-secret-key-min-32-chars
STRIPE_SECRET_KEY=sk_live_...
CORS_ORIGINS=https://your-frontend-url.vercel.app

# Optional but recommended
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_PRO=price_...
STRIPE_PRICE_ID_ENTERPRISE=price_...
ENVIRONMENT=production
DEBUG=false
```

---

## 🆘 Need Help?

**Railway Upgrade**: https://railway.com/account/billing
**Render Docs**: https://render.com/docs
**DigitalOcean Docs**: https://docs.digitalocean.com/products/app-platform/

---

## 💡 My Recommendation

**For Production**: Railway ($5/month) or Render ($7/month)
- Both are simple and include everything you need
- Railway is slightly easier if you upgrade
- Render has a better free tier if you're testing

**For Development**: Run locally
- Free and fast
- Full control
- Easy debugging

**What would you like to do?**
1. Upgrade Railway and continue ($5/month)
2. Use Render instead (FREE or $7/month)
3. Run locally for now (FREE)

Let me know and I'll help you complete the setup! 🚀
