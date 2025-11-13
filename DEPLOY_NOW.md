# 🚀 Deploy to Cloud NOW - Complete Guide

**Your frontend is LIVE**: https://frontend-1gp6cxaq3-aniksahai-icloudcoms-projects.vercel.app

**Now let's deploy the backend in 10 minutes!**

---

## ⚡ FASTEST: Upgrade Railway ($5/month)

You're already logged in to Railway. Just upgrade and run 3 commands:

### Step 1: Upgrade (2 minutes)
1. **Open**: https://railway.com/account/billing
2. **Click**: "Upgrade to Hobby Plan" ($5/month)
3. **Enter**: Payment details
4. **Done**: You're upgraded!

### Step 2: Deploy (3 commands)
```bash
cd /Users/aniksahai/Desktop/VLAAPI

# Add services
railway add --database postgres
railway add --database redis

# Deploy backend
railway up
```

### Step 3: Setup Database (2 minutes)
```bash
# Run migration
railway run psql $DATABASE_URL < migrations/001_create_users_and_auth.sql

# Create admin user
railway run psql $DATABASE_URL << 'EOF'
INSERT INTO vlaapi.users (email, hashed_password, full_name, is_superuser, is_active, email_verified)
VALUES ('admin@praxislabs.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ND0azvKJMJtu', 'Admin User', true, true, true);
EOF
```

### Step 4: Get Backend URL
```bash
railway status
# Copy the URL shown
```

**DONE!** Skip to "Update Frontend" section below.

---

## 💰 FREE OPTION: Deploy to Render

No payment needed. Truly free (with limitations).

### Step 1: Create Render Account (1 minute)
1. Go to https://render.com
2. Sign up with GitHub
3. **Done**

### Step 2: Deploy PostgreSQL (2 minutes)
1. Click **"New +"** → **"PostgreSQL"**
2. Name: `praxis-postgres`
3. Database: `vlaapi`
4. Plan: **Free**
5. Click **"Create Database"**
6. **COPY the "Internal Database URL"** (starts with `postgresql://`)

### Step 3: Deploy Backend (3 minutes)
1. Click **"New +"** → **"Web Service"**
2. **Connect** your GitHub account
3. **Select** VLAAPI repository
4. Configure:
   - **Name**: `praxis-backend-api`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn src.api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
   - **Plan**: Free or Starter ($7/month for always-on)
5. **DON'T CLICK CREATE YET!**

### Step 4: Add Environment Variables (2 minutes)
Scroll down to **"Environment Variables"** and add:

```
DATABASE_URL = <paste the Internal Database URL from Step 2>
REDIS_URL = redis://localhost:6379/0
JWT_SECRET_KEY = your-random-secret-key-min-32-chars-change-this
STRIPE_SECRET_KEY = sk_test_your_stripe_test_key
STRIPE_PUBLISHABLE_KEY = pk_test_your_stripe_test_key
CORS_ORIGINS = https://frontend-1gp6cxaq3-aniksahai-icloudcoms-projects.vercel.app
ENVIRONMENT = production
DEBUG = false
```

**Generate JWT_SECRET_KEY**:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

6. **NOW CLICK** "Create Web Service"
7. Wait ~5 minutes for deployment
8. **COPY your backend URL**: `https://praxis-backend-api.onrender.com`

### Step 5: Run Database Migration (2 minutes)

**Option A - Using psql locally**:
```bash
# Get the EXTERNAL connection string from Render PostgreSQL dashboard
export DATABASE_URL="<external-connection-string>"

# Run migration
psql $DATABASE_URL < /Users/aniksahai/Desktop/VLAAPI/migrations/001_create_users_and_auth.sql
```

**Option B - Using Render SQL Editor**:
1. Go to your PostgreSQL service in Render
2. Click **"SQL Editor"**
3. Copy and paste the entire contents of `/Users/aniksahai/Desktop/VLAAPI/migrations/001_create_users_and_auth.sql`
4. Click **"Execute"**

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

## 🔗 Update Frontend (REQUIRED FOR BOTH OPTIONS)

### Step 1: Update Vercel Environment Variables
1. Go to https://vercel.com/aniksahai-icloudcoms-projects/frontend/settings/environment-variables
2. Add or update these variables:

```
NEXT_PUBLIC_API_URL = <your-backend-url-from-railway-or-render>
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY = pk_test_your_stripe_test_key
```

**Railway backend URL**: Get from `railway status`
**Render backend URL**: `https://praxis-backend-api.onrender.com`

### Step 2: Redeploy Frontend
1. Go to https://vercel.com/aniksahai-icloudcoms-projects/frontend/deployments
2. Click **"⋯"** on the latest deployment
3. Click **"Redeploy"**
4. Wait ~2 minutes

---

## ✅ TEST EVERYTHING (5 minutes)

### 1. Test Backend Health
```bash
# Replace with your backend URL
curl https://your-backend-url/

# Expected response:
# {"name":"Praxis Labs VLA API","version":"1.0.0","status":"running"}
```

### 2. Test Frontend Connection
1. Visit: https://frontend-1gp6cxaq3-aniksahai-icloudcoms-projects.vercel.app
2. Should load without errors
3. Check browser console (F12) - should NOT see CORS errors

### 3. Test User Registration
1. Click **"Sign up"**
2. Fill in:
   - Email: `test@example.com`
   - Password: `TestPass123!`
   - Full Name: `Test User`
3. Click **"Create Account"**
4. **Expected**: Redirects to dashboard

### 4. Test API Key Creation
1. In dashboard, click **"API Keys"** in sidebar
2. Click **"Create API Key"**
3. Name: `Test Key`
4. Click **"Create Key"**
5. **COPY THE KEY** (shown only once!)
6. **Expected**: Key starts with `vla_live_`

### 5. Test Admin Panel
1. Logout
2. Login as:
   - Email: `admin@praxislabs.com`
   - Password: `AdminPass123!`
3. Go to `/admin` URL
4. **Expected**: See admin dashboard with system stats

### 6. Test API Endpoint (Optional)
```bash
# Use the API key you created
curl -X POST https://your-backend-url/v1/inference \
  -H "X-API-Key: vla_live_YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "instruction": "Pick up the red block",
    "robot_type": "franka_panda"
  }'

# Expected: JSON response with action vector
```

---

## 🎯 Checklist - Everything Working?

- [ ] ✅ Backend health check returns JSON
- [ ] ✅ Frontend loads without errors
- [ ] ✅ User registration works
- [ ] ✅ Login redirects to dashboard
- [ ] ✅ API key creation works
- [ ] ✅ API key is copyable
- [ ] ✅ Admin login works
- [ ] ✅ Admin panel accessible at `/admin`
- [ ] ✅ No CORS errors in browser console

**If ALL checked**: 🎉 **YOUR PLATFORM IS FULLY DEPLOYED AND WORKING!**

---

## 🆘 Troubleshooting

### Backend won't start
**Render**: Check logs in Render dashboard
**Railway**: Run `railway logs`

**Common issues**:
- Missing environment variables
- Database URL incorrect
- Missing `gunicorn` in requirements.txt (already added)

### Frontend shows "Failed to fetch"
1. Check `NEXT_PUBLIC_API_URL` in Vercel is correct
2. Verify backend is running (curl the health endpoint)
3. Check CORS_ORIGINS includes your Vercel URL

### Database migration failed
1. Verify PostgreSQL service is running
2. Check DATABASE_URL is correct
3. Try running migration manually via SQL editor

### Can't create API key
1. Check backend logs for errors
2. Verify you're logged in
3. Check database migration completed

### Admin panel shows "Not authorized"
1. Verify admin user was created
2. Check `is_superuser` is `true` in database
3. Try logging out and back in

---

## 💰 Cost Summary

### Railway (Easiest):
- **Cost**: $5/month (everything included)
- **Includes**: Backend + PostgreSQL + Redis
- **Best for**: Production, easy scaling

### Render (Cheapest):
- **Free tier**: $0 (backend spins down after 15min)
- **Starter**: $7/month (always on)
- **PostgreSQL**: FREE (500MB limit)
- **Best for**: MVP, testing

---

## 🚀 You're Done!

Your complete SaaS platform is now deployed:

- ✅ **Frontend**: Vercel (LIVE)
- ✅ **Backend**: Railway/Render (LIVE)
- ✅ **Database**: PostgreSQL (LIVE)
- ✅ **Authentication**: Working
- ✅ **API Keys**: Working
- ✅ **Admin Panel**: Working

**Next steps**:
1. Change admin password
2. Add real Stripe keys (for production)
3. Set up custom domain (optional)
4. Configure Stripe webhooks
5. Add team members

**Admin Credentials**:
- Email: admin@praxislabs.com
- Password: AdminPass123!
- **⚠️ CHANGE THIS PASSWORD NOW!**

---

**Need help?** All documentation is in the `/docs` folder.
