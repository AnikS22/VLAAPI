# Praxis Labs - Deployment Architecture

## 🏗️ What Goes Where

Here's the complete hosting setup for Praxis Labs:

---

## ✅ **FRONTEND - Vercel (Recommended)**

**What**: Next.js 14 application (the `frontend/` directory)

**Why Vercel**:
- Built specifically for Next.js
- Automatic deployments from Git
- Global CDN (fast worldwide)
- Free SSL certificates
- Serverless functions
- Automatic scaling
- **Free tier** available (perfect for MVP)

**Deployment Steps**:

```bash
cd frontend

# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

**Environment Variables** (add in Vercel dashboard):
```env
NEXT_PUBLIC_API_URL=https://api.praxislabs.com
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

**Custom Domain**: `app.praxislabs.com`

**Cost**: **FREE** (or $20/month Pro if you need more)

---

## ⚠️ **BACKEND - DigitalOcean/Railway/Render**

**What**: FastAPI Python application (the entire `VLAAPI/` root directory)

**Why NOT Vercel**:
- Vercel doesn't support Python backend applications well
- Vercel serverless functions have 10s timeout (too short for VLA inference)
- Need persistent connections for WebSockets
- Need GPU support (for VLA models)

### **Option 1: DigitalOcean App Platform** (Recommended for MVP)

**Pros**:
- Easy Python deployment
- Built-in PostgreSQL database
- Built-in Redis
- Good pricing ($5-24/month droplets)
- Can add GPU later

**Steps**:
1. Connect GitHub repo
2. Select Python app
3. Set environment variables
4. Deploy

**Cost**: ~$24/month (4GB RAM droplet) + $15/month (PostgreSQL) = **$39/month**

### **Option 2: Railway** (Easiest for beginners)

**Pros**:
- Extremely easy deployment
- Git push to deploy
- Built-in PostgreSQL and Redis
- Free $5 credit/month

**Steps**:
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Add PostgreSQL
railway add postgresql

# Add Redis
railway add redis

# Deploy
railway up
```

**Cost**: ~$20-30/month (pay as you go)

### **Option 3: Render** (Good balance)

**Pros**:
- Free tier for PostgreSQL
- Easy Python deployment
- Auto-deploy from Git

**Cost**: $25/month (web service) + Free (PostgreSQL) = **$25/month**

### **Option 4: AWS EC2** (For GPU support)

**Use this if you need VLA models running**:
- Instance type: `g4dn.xlarge` (1 GPU)
- Cost: ~$350/month
- Full control over environment

---

## 📊 **RECOMMENDED ARCHITECTURE (MVP)**

```
┌─────────────────────────────────────────────────────────────┐
│                         USERS                                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
        ┌───────▼──────┐       ┌───────▼──────┐
        │   VERCEL     │       │  DigitalOcean│
        │  (Frontend)  │       │   (Backend)  │
        │              │       │              │
        │ Next.js App  │◄──────┤  FastAPI     │
        │ Port: 443    │ HTTPS │  Port: 8000  │
        └──────────────┘       └───────┬──────┘
                                       │
                        ┌──────────────┼──────────────┐
                        │              │              │
                 ┌──────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
                 │ PostgreSQL │ │   Redis   │ │  Stripe   │
                 │  Database  │ │   Cache   │ │  Webhooks │
                 │            │ │           │ │           │
                 └────────────┘ └───────────┘ └───────────┘
                   DO Managed     DO Managed    3rd Party
                   $15/month      $10/month      Free
```

**Total Monthly Cost**: ~$64/month (MVP without GPU)

---

## 📦 **COMPLETE DEPLOYMENT SETUP**

### **1. Frontend on Vercel**

**Repository**: Your GitHub repo (only `frontend/` folder)

**Build Settings**:
- **Framework**: Next.js
- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Output Directory**: `.next`
- **Install Command**: `npm install`

**Environment Variables**:
```env
NEXT_PUBLIC_API_URL=https://api.praxislabs.com
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

**Domain**: `app.praxislabs.com`

---

### **2. Backend on DigitalOcean**

**Method 1: DigitalOcean App Platform (Easiest)**

1. Go to DigitalOcean → Create → Apps
2. Connect GitHub repo
3. Select source: `VLAAPI` (root directory)
4. Detect Python app
5. Build Command: `pip install -r requirements.txt`
6. Run Command: `gunicorn src.api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`
7. Add environment variables (see below)
8. Deploy

**Method 2: DigitalOcean Droplet (More control)**

```bash
# SSH into droplet
ssh root@your-droplet-ip

# Install dependencies
apt update
apt install -y python3-pip postgresql-client redis-tools nginx

# Clone repo
git clone https://github.com/your-repo/VLAAPI.git
cd VLAAPI

# Install Python packages
pip3 install -r requirements.txt

# Set up environment
cp .env.example .env
nano .env  # Edit with your values

# Run migration
psql $DATABASE_URL < migrations/001_create_users_and_auth.sql

# Start with systemd (see DEPLOYMENT_GUIDE.md)
```

**Environment Variables**:
```env
DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/vlaapi
REDIS_URL=redis://redis-host:6379/0
JWT_SECRET_KEY=your-super-secret-key-change-this
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
CORS_ORIGINS=https://app.praxislabs.com
ENVIRONMENT=production
```

**Domain**: `api.praxislabs.com`

---

### **3. Database - PostgreSQL**

**Options**:

**Option A: DigitalOcean Managed Database** (Recommended)
- Go to DigitalOcean → Databases → Create
- Select PostgreSQL 15
- Choose $15/month plan (1GB RAM)
- Copy connection string
- Add to backend env as `DATABASE_URL`

**Option B: Railway**
- `railway add postgresql`
- Copy `DATABASE_URL` from Railway dashboard

**Option C: Supabase** (Free tier available)
- Create project at supabase.com
- Get connection string from settings
- Free tier: 500MB database

**Setup**:
```bash
# Run migration
psql "postgresql://user:pass@host:5432/vlaapi" < migrations/001_create_users_and_auth.sql

# Create admin user
psql "postgresql://user:pass@host:5432/vlaapi" << EOF
INSERT INTO vlaapi.users (email, hashed_password, full_name, is_superuser, is_active, email_verified)
VALUES (
    'admin@praxislabs.com',
    '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ND0azvKJMJtu',
    'Admin User',
    true,
    true,
    true
);
EOF
```

---

### **4. Redis - Cache**

**Options**:

**Option A: DigitalOcean Managed Redis**
- $10/month for 1GB
- Copy connection URL
- Add to backend env as `REDIS_URL`

**Option B: Railway**
- `railway add redis`
- Free in Railway's $5/month credit

**Option C: Upstash** (Serverless Redis)
- Free tier: 10k commands/day
- Perfect for MVP
- Get URL from upstash.com

---

### **5. Stripe - Billing**

**Setup**:
1. Create Stripe account
2. Get API keys from dashboard
3. Create products:
   - **Pro Plan**: $499/month recurring
   - **Enterprise Plan**: Custom pricing
4. Get price IDs
5. Configure webhook:
   - URL: `https://api.praxislabs.com/v1/billing/webhooks/stripe`
   - Events: `customer.subscription.*`, `invoice.payment_*`
   - Get webhook secret

**Environment Variables**:
```env
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...  # For frontend
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_PRO=price_...
STRIPE_PRICE_ID_ENTERPRISE=price_...
```

---

## 🌍 **DNS CONFIGURATION**

Buy domain (e.g., `praxislabs.com`) and configure:

**A Records**:
- `api.praxislabs.com` → DigitalOcean Droplet IP
- `praxislabs.com` → Vercel (automatic)
- `app.praxislabs.com` → Vercel (automatic)

**SSL Certificates**:
- Vercel: Automatic (Let's Encrypt)
- Backend: Use Nginx + Certbot or DigitalOcean's automatic SSL

---

## 💰 **COST BREAKDOWN**

### **MVP Setup (Without GPU)**

| Service | Provider | Cost/Month |
|---------|----------|------------|
| Frontend | Vercel | FREE |
| Backend API | DigitalOcean Droplet (4GB) | $24 |
| Database | DigitalOcean PostgreSQL | $15 |
| Redis | DigitalOcean Redis | $10 |
| Domain | Namecheap/Google | $1 |
| Stripe | Stripe | Free (2.9% + $0.30 per transaction) |
| **Total** | | **$50/month** |

### **With GPU (For VLA Models)**

| Service | Provider | Cost/Month |
|---------|----------|------------|
| Frontend | Vercel | FREE |
| Backend API | AWS EC2 g4dn.xlarge (GPU) | $350 |
| Database | AWS RDS PostgreSQL | $50 |
| Redis | AWS ElastiCache | $30 |
| Domain | Route53 | $1 |
| **Total** | | **$431/month** |

---

## 🚀 **QUICK START DEPLOYMENT**

### **Step 1: Deploy Frontend to Vercel** (5 minutes)

```bash
cd frontend

# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel --prod

# Add environment variables in Vercel dashboard
# NEXT_PUBLIC_API_URL=https://api.praxislabs.com
```

### **Step 2: Deploy Backend to Railway** (10 minutes)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Create new project
railway init

# Add PostgreSQL
railway add postgresql

# Add Redis
railway add redis

# Deploy
railway up

# Get database URL
railway variables

# Run migration
railway run psql $DATABASE_URL < migrations/001_create_users_and_auth.sql
```

### **Step 3: Configure Stripe** (5 minutes)

1. Create Stripe account
2. Create Pro product ($499/month)
3. Get API keys
4. Add webhook: `https://your-railway-app.railway.app/v1/billing/webhooks/stripe`
5. Add keys to Railway environment variables

### **Step 4: Test Everything** (5 minutes)

```bash
# Visit frontend
open https://your-app.vercel.app

# Register new user
# Create API key
# Run inference
# Check admin panel
```

**DONE!** 🎉

---

## 🔄 **CI/CD AUTO-DEPLOYMENT**

### **Frontend (Vercel)**
- Automatic: Push to `main` branch → Auto-deploy
- Preview: Push to any branch → Preview URL

### **Backend (Railway/DigitalOcean)**
- Railway: Push to `main` → Auto-deploy
- DigitalOcean App Platform: Push to `main` → Auto-deploy
- Manual: SSH and `git pull && systemctl restart praxis-api`

---

## 🔧 **ALTERNATIVE SETUPS**

### **All-in-One Railway** ($30/month)
- Frontend: Railway (can host Next.js)
- Backend: Railway
- Database: Railway PostgreSQL
- Redis: Railway Redis

### **All-in-One Render** ($25/month)
- Frontend: Render Static Site
- Backend: Render Web Service
- Database: Render PostgreSQL (Free tier)

### **Serverless AWS**
- Frontend: AWS Amplify
- Backend: AWS Lambda + API Gateway
- Database: AWS RDS or Aurora Serverless
- Redis: AWS ElastiCache

---

## 📊 **MONITORING & LOGS**

**Vercel**:
- Built-in analytics
- Real-time logs in dashboard

**Backend**:
- Railway: Built-in logs and metrics
- DigitalOcean: `/metrics` endpoint with Prometheus

**Database**:
- Built-in monitoring in managed database dashboards

---

## ✅ **RECOMMENDED FOR YOU**

**Best MVP Setup** (easiest + cheapest):

1. **Frontend**: Vercel (FREE)
2. **Backend**: Railway ($20-30/month, includes everything)
3. **Database**: Railway PostgreSQL (included)
4. **Redis**: Railway Redis (included)
5. **Stripe**: Stripe (free + transaction fees)

**Total**: ~$30/month all-in-one

**Commands**:
```bash
# Deploy frontend to Vercel
cd frontend && vercel --prod

# Deploy backend to Railway
railway init
railway add postgresql
railway add redis
railway up
```

That's it! 🚀

---

**Questions?** See `docs/DEPLOYMENT_GUIDE.md` for detailed step-by-step instructions.
