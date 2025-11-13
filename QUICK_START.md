# Praxis Labs - Quick Start Guide

**Status**: ✅ Frontend LIVE | ⚠️ Backend - Choose Deployment Option

---

## 🎉 Frontend is LIVE!

**URL**: https://frontend-1gp6cxaq3-aniksahai-icloudcoms-projects.vercel.app

Your complete frontend with all 16 pages is deployed and ready!

---

## ⚠️ Backend Deployment - Railway Trial Expired

Your Railway trial has expired. Choose one of these options:

---

## Option 1: Run Locally (Fastest - 2 minutes) 🏃

**Perfect for**: Testing everything right now, FREE

**One-Command Setup**:
```bash
./scripts/run_local.sh
```

This automatically:
- ✅ Installs PostgreSQL and Redis (if needed)
- ✅ Creates database and runs migrations
- ✅ Creates admin user
- ✅ Installs dependencies
- ✅ Starts backend on http://localhost:8000

**Then**:
1. Frontend will work at: http://localhost:3000 (if you run `npm run dev` in frontend/)
2. Backend API: http://localhost:8000
3. API Docs: http://localhost:8000/docs

**Login Credentials**:
- Email: `admin@praxislabs.com`
- Password: `AdminPass123!`

---

## Option 2: Railway ($5/month) - Easiest Cloud Deployment

**Perfect for**: Production, automatic scaling, all-in-one

**Steps**:
1. **Upgrade Railway**: https://railway.com/account/billing
2. **Click "Upgrade to Hobby"** ($5/month)
3. **Run these commands**:
   ```bash
   railway add --service "praxis-backend-api"
   railway add --database postgres
   railway add --database redis
   railway up
   ```

**What you get**:
- ✅ Backend API (auto-scaling)
- ✅ PostgreSQL database (managed)
- ✅ Redis cache (managed)
- ✅ Auto-deployments from Git
- ✅ Free SSL certificates

**Cost**: $5/month (covers everything)

---

## Option 3: Render (FREE or $7/month)

**Perfect for**: Free tier testing or budget production

**Setup** (10 minutes):
1. Go to https://render.com
2. Create account
3. Click "New +" → "PostgreSQL" (FREE plan)
4. Click "New +" → "Web Service"
5. Connect GitHub → Select VLAAPI repo
6. Use these settings:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn src.api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
7. Add environment variables (see below)
8. Click "Create Web Service"

**Environment Variables for Render**:
```bash
DATABASE_URL=<from Render PostgreSQL service>
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your-secret-key-change-this
STRIPE_SECRET_KEY=sk_live_...
CORS_ORIGINS=https://frontend-1gp6cxaq3-aniksahai-icloudcoms-projects.vercel.app
ENVIRONMENT=production
```

**Cost**:
- FREE tier: $0 (spins down after 15min inactivity)
- Starter: $7/month (always on)

---

## 🎯 My Recommendation

### For Right Now (Testing)
**→ Run Locally** (Option 1)
- Takes 2 minutes
- Completely FREE
- Test everything immediately
- Command: `./scripts/run_local.sh`

### For Production
**→ Railway** (Option 2) if you want easiest deployment
**→ Render** (Option 3) if you want free tier or lower cost

---

## 📋 After Backend is Running

### Update Frontend
Once your backend is deployed, update the frontend:

1. Go to https://vercel.com/aniksahai-icloudcoms-projects/frontend
2. Click "Settings" → "Environment Variables"
3. Add/Update:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
   ```
4. Click "Deployments" → "Redeploy"

### Test Everything
```bash
# Run automated test suite
./scripts/test_complete_flow.sh
```

Or manually:
1. Visit frontend URL
2. Register new user
3. Create API key
4. Test playground
5. View analytics
6. Check admin panel

---

## 🔑 Important Credentials

### Admin User
- Email: `admin@praxislabs.com`
- Password: `AdminPass123!`
- **Change this password after first login!**

### Stripe Test Mode
- Use test API keys for development
- Test card: `4242 4242 4242 4242`
- Any future expiry date
- Any 3-digit CVC

---

## 📚 Full Documentation

- `docs/DEPLOYMENT_STATUS.md` - Current deployment status
- `docs/BACKEND_DEPLOYMENT_OPTIONS.md` - Detailed deployment options
- `docs/DEPLOYMENT_GUIDE.md` - Production deployment guide
- `docs/TESTING_GUIDE.md` - Complete testing instructions
- `FINAL_DELIVERY.md` - Full project summary

---

## 🆘 Need Help?

**Local Setup Issues**:
```bash
# Check if services are running
psql -d vlaapi -c "SELECT 1"  # PostgreSQL
redis-cli ping  # Redis

# View backend logs
tail -f logs/app.log
```

**Railway Issues**:
- Dashboard: https://railway.com/project/000d0aaa-a51c-479c-a0e6-bdb61695cee4
- Docs: https://docs.railway.com

**Render Issues**:
- Dashboard: https://dashboard.render.com
- Docs: https://render.com/docs

---

## ✅ What's Already Done

- ✅ Complete backend API (35+ endpoints)
- ✅ Complete frontend (16 pages, 16 components)
- ✅ Authentication system (JWT)
- ✅ API key management
- ✅ Analytics dashboard
- ✅ Admin panel
- ✅ Stripe billing integration
- ✅ Database migrations
- ✅ Automated tests
- ✅ **Frontend deployed to Vercel**
- ✅ Railway configuration files
- ✅ Local development script

**All you need to do**: Choose a backend deployment option!

---

## 🚀 Quick Command Reference

### Local Development
```bash
./scripts/run_local.sh                    # Start everything
./scripts/test_complete_flow.sh           # Run tests
```

### Railway (After Upgrade)
```bash
railway up                                # Deploy
railway logs                              # View logs
railway open                              # Open dashboard
```

### Check Status
```bash
curl http://localhost:8000/               # Local
curl https://your-backend-url/            # Production
```

---

**Which option do you want to use?**
1. Run locally (fastest, free)
2. Upgrade Railway ($5/month)
3. Use Render (free or $7/month)

Let me know and I'll help you complete the setup! 🚀
