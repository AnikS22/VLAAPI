# Vercel Deployment Fix Guide

## Issues Fixed

1. ✅ Added `vercel.json` configuration file
2. ✅ Added Node.js version specification in `package.json`
3. ✅ Updated `next.config.mjs` for production optimization
4. ✅ Created `.env.example` for reference

## Deployment Checklist

### 1. Vercel Project Settings

When deploying to Vercel, make sure:

- **Root Directory**: Set to `frontend` (if deploying from monorepo)
- **Framework Preset**: Next.js (auto-detected)
- **Build Command**: `npm run build` (default)
- **Output Directory**: `.next` (default)
- **Install Command**: `npm install` (default)

### 2. Required Environment Variables

Add these in Vercel Dashboard → Settings → Environment Variables:

#### Required:
- `NEXT_PUBLIC_API_URL` = Your backend API URL (e.g., `https://api.yourdomain.com`)

#### Optional:
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` = Stripe publishable key (if using Stripe)

### 3. Common Deployment Issues & Fixes

#### Issue: Build fails with "Module not found"
**Fix**: Ensure all dependencies are in `package.json` and run `npm install` locally first.

#### Issue: "Cannot find module '@/...'"
**Fix**: Check `tsconfig.json` paths configuration. Already configured correctly.

#### Issue: Build succeeds but app shows blank page
**Fix**: 
- Check browser console for errors
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check network tab for API calls

#### Issue: "TypeError: Cannot read property..."
**Fix**: Ensure all environment variables are prefixed with `NEXT_PUBLIC_` for client-side access.

### 4. Testing Locally Before Deploying

```bash
cd frontend
npm install
npm run build
npm start
```

Visit `http://localhost:3000` to test the production build locally.

### 5. Vercel Deployment Steps

1. **Via Vercel Dashboard:**
   - Go to https://vercel.com/new
   - Import your Git repository
   - Set **Root Directory** to `frontend`
   - Add environment variables
   - Click **Deploy**

2. **Via Vercel CLI:**
   ```bash
   cd frontend
   npm i -g vercel
   vercel login
   vercel --prod
   ```

### 6. Post-Deployment

1. **Update Backend CORS:**
   Add your Vercel domain to backend CORS settings:
   ```
   CORS_ORIGINS=["https://your-app.vercel.app", "http://localhost:3000"]
   ```

2. **Test the deployment:**
   - Visit your Vercel URL
   - Try registering a new account
   - Test login functionality
   - Check API connectivity

### 7. Troubleshooting

If deployment still fails:

1. **Check Vercel Build Logs:**
   - Go to your project → Deployments → Click on failed deployment
   - Review the build logs for specific errors

2. **Common Build Errors:**
   - **"Command 'npm run build' exited with 1"**: Check TypeScript errors
   - **"Module not found"**: Verify all imports are correct
   - **"Environment variable not found"**: Ensure variables are set in Vercel

3. **Verify Configuration:**
   ```bash
   # Check if build works locally
   npm run build
   
   # Check for TypeScript errors
   npx tsc --noEmit
   
   # Check for linting errors
   npm run lint
   ```

## Files Created/Modified

- ✅ `vercel.json` - Vercel deployment configuration
- ✅ `package.json` - Added Node.js engine specification
- ✅ `next.config.mjs` - Production optimizations
- ✅ `.env.example` - Environment variable template

## Next Steps

1. Commit these changes to your repository
2. Push to GitHub/GitLab
3. Deploy to Vercel
4. Add environment variables in Vercel dashboard
5. Test the deployment

If you still encounter issues, check the Vercel build logs for specific error messages.

