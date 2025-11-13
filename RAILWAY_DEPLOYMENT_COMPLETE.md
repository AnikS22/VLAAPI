# 🚀 Railway Deployment - Final Steps

## 📊 Current Status

✅ **Database Services**: PostgreSQL + Redis running
✅ **Backend Service**: Created (dynamic-upliftment)
✅ **Environment Variables**: All configured
✅ **Build Configuration**: Fixed with custom Dockerfile
⏳ **Backend Deployment**: In progress (Build ID: ec707459-a00f-41d6-95ff-b2a9c0e5f0f6)

---

## 🔍 Monitor Deployment (FASTEST METHOD)

### Option 1: Railway Web Dashboard (RECOMMENDED)
**Open this link for live build logs**:
https://railway.com/project/661efeb4-765c-40f2-b07e-66e0050fb43d/service/75b14633-87e8-4a60-a246-b80fc2bb6854?id=ec707459-a00f-41d6-95ff-b2a9c0e5f0f6&

You'll see:
- Real-time build logs
- Deployment progress
- Any errors instantly
- Container startup logs

### Option 2: Command Line (slower)
```bash
# Check logs
railway logs

# Test health endpoint (repeat until it works)
curl https://dynamic-upliftment-production.up.railway.app/

# Expected when ready:
# {"name":"Praxis Labs VLA API","version":"1.0.0","status":"running"}
```

---

## ✅ Once Deployment Succeeds:

The build should complete in **5-10 minutes**. When the backend responds with JSON (not 404), proceed:

### 1. Run Database Migration

```bash
cd /Users/aniksahai/Desktop/VLAAPI

# Run migration
railway run psql $DATABASE_URL < migrations/001_create_users_and_auth.sql
```

### 2. Create Admin User

```bash
railway run psql $DATABASE_URL << 'EOF'
INSERT INTO vlaapi.users (email, hashed_password, full_name, is_superuser, is_active, email_verified)
VALUES (
    'admin@praxislabs.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ND0azvKJMJtu',
    'Admin User',
    true,
    true,
    true
);
EOF
```

### 3. Update Vercel Frontend

1. Go to: https://vercel.com/aniksahai-icloudcoms-projects/frontend/settings/environment-variables

2. Add/Update:
   ```
   NEXT_PUBLIC_API_URL = https://dynamic-upliftment-production.up.railway.app
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY = pk_test_51QKdGaE5w2m6zN5cjx6mDqRKvB0e9Z8xpvfMSg1NTqyxN4vVl72bZ3DK9X9NpGzzTWYZ6IKwG2RmPHGfnKqqYJHs00fPGF9sUO
   ```

3. Redeploy: Go to Deployments → Click "..." next to latest → "Redeploy"

### 4. Test Complete Flow

```bash
# 1. Backend health
curl https://dynamic-upliftment-production.up.railway.app/

# 2. Frontend
open https://frontend-1gp6cxaq3-aniksahai-icloudcoms-projects.vercel.app

# 3. Register user → Create API key → Test admin panel
```

---

## 🔧 Technical Details

### Files Created/Modified:
1. **Dockerfile**: Custom Python 3.10-slim image
2. **railway.json**: Set to use DOCKERFILE builder
3. **Removed**: nixpacks.toml (was causing conflicts)

### Environment Variables Set:
```bash
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis-rb-B.REDIS_URL}}
JWT_SECRET_KEY=W5_iD3xQM7vlKFK26VYELeZWxaEWj0WUL1n0X8Fz680
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://frontend-1gp6cxaq3-aniksahai-icloudcoms-projects.vercel.app
ENABLE_GPU_MONITORING=false
ENABLE_PROMETHEUS=true
ENABLE_EMBEDDINGS=false
STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
STRIPE_PUBLISHABLE_KEY=${STRIPE_PUBLISHABLE_KEY}
```

---

## 🎯 Your Complete Stack URLs

**Frontend**: https://frontend-1gp6cxaq3-aniksahai-icloudcoms-projects.vercel.app

**Backend**: https://dynamic-upliftment-production.up.railway.app

**Railway Dashboard**: https://railway.com/project/661efeb4-765c-40f2-b07e-66e0050fb43d

**PostgreSQL**: Running on Railway (internal)

**Redis**: Running on Railway (internal)

---

## 💰 Cost Breakdown

**Railway Hobby Plan**: $5/month includes:
- Backend API (always-on)
- PostgreSQL database
- Redis cache
- 5GB storage
- Auto-scaling
- Custom domains

**Vercel**: FREE (Hobby plan)

**Total**: **$5/month**

---

## 🔑 Admin Credentials (After Migration)

**Email**: admin@praxislabs.com
**Password**: AdminPass123!

⚠️ **IMPORTANT**: Change this password immediately after first login!

---

## 🆘 If Build Fails

Check the Railway dashboard logs for specific errors. Common issues:

1. **Out of memory**: Upgrade to higher tier
2. **Missing dependency**: Check requirements.txt
3. **Port binding**: Dockerfile uses $PORT correctly
4. **Database connection**: Environment variables are linked correctly

---

## ✅ Success Checklist

After deployment completes:

- [ ] Backend health endpoint returns JSON
- [ ] Database migration completed
- [ ] Admin user created
- [ ] Vercel environment variables updated
- [ ] Vercel redeployed
- [ ] Frontend connects to backend (no CORS errors)
- [ ] User registration works
- [ ] API key creation works
- [ ] Admin panel accessible

---

**Status**: ⏳ Waiting for Docker build to complete (monitor via Railway dashboard)

**Next**: Once deployment succeeds, run database migrations and update Vercel!
