#!/bin/bash

# Praxis Labs - Railway Cloud Deployment Script
# This script deploys the backend to Railway cloud

set -e

echo "🚀 Praxis Labs - Railway Cloud Deployment"
echo "=========================================="
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

echo "✅ Railway CLI found"
echo ""

# Check login status
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged in to Railway"
    echo "Please run: railway login"
    exit 1
fi

echo "✅ Logged in to Railway as $(railway whoami)"
echo ""

# Check if trial has expired
echo "⚠️  IMPORTANT: Railway trial has expired"
echo ""
echo "Please upgrade to continue:"
echo "1. Go to: https://railway.com/account/billing"
echo "2. Click 'Upgrade to Hobby Plan' (\$5/month)"
echo "3. Enter payment details"
echo "4. Come back and press ENTER"
echo ""
read -p "Press ENTER after upgrading to continue..."
echo ""

# Try to create backend service
echo "📦 Creating backend service..."
if railway add --service "praxis-backend-api" 2>&1 | grep -q "trial has expired"; then
    echo "❌ Trial still expired. Please upgrade at https://railway.com/account/billing"
    exit 1
fi

echo "✅ Backend service created"
echo ""

# Add PostgreSQL
echo "🗄️  Adding PostgreSQL database..."
railway add --database postgres
echo "✅ PostgreSQL added"
echo ""

# Add Redis
echo "📮 Adding Redis cache..."
railway add --database redis
echo "✅ Redis added"
echo ""

# Link to backend service
echo "🔗 Linking to backend service..."
railway service
echo ""

# Get database URL
echo "📊 Fetching database connection..."
DB_URL=$(railway variables | grep DATABASE_URL | cut -d'=' -f2-)
REDIS_URL=$(railway variables | grep REDIS_URL | cut -d'=' -f2-)
echo "✅ Database URLs retrieved"
echo ""

# Set environment variables
echo "🔧 Setting environment variables..."

# Generate JWT secret
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

railway variables --set JWT_SECRET_KEY="$JWT_SECRET"
railway variables --set JWT_ALGORITHM="HS256"
railway variables --set JWT_EXPIRATION_MINUTES="30"
railway variables --set ENVIRONMENT="production"
railway variables --set DEBUG="false"
railway variables --set CORS_ORIGINS="https://frontend-1gp6cxaq3-aniksahai-icloudcoms-projects.vercel.app"
railway variables --set ENABLE_GPU_MONITORING="false"
railway variables --set ENABLE_PROMETHEUS="true"
railway variables --set ENABLE_EMBEDDINGS="false"

# Stripe test keys (replace with your real keys later)
railway variables --set STRIPE_SECRET_KEY="sk_test_your_test_key_here"
railway variables --set STRIPE_PUBLISHABLE_KEY="pk_test_your_test_key_here"
railway variables --set STRIPE_WEBHOOK_SECRET="whsec_test_secret"

echo "✅ Environment variables set"
echo ""

# Deploy backend
echo "🚀 Deploying backend to Railway..."
railway up
echo "✅ Backend deployed"
echo ""

# Wait for deployment
echo "⏳ Waiting for deployment to complete..."
sleep 30

# Get backend URL
BACKEND_URL=$(railway domain)
echo "✅ Backend URL: $BACKEND_URL"
echo ""

# Run database migration
echo "🔄 Running database migration..."
railway run psql $DATABASE_URL < migrations/001_create_users_and_auth.sql
echo "✅ Migration complete"
echo ""

# Create admin user
echo "👤 Creating admin user..."
railway run psql $DATABASE_URL << 'EOF'
INSERT INTO vlaapi.users (email, hashed_password, full_name, is_superuser, is_active, email_verified)
VALUES (
    'admin@praxislabs.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ND0azvKJMJtu',
    'Admin User',
    true,
    true,
    true
) ON CONFLICT (email) DO NOTHING;
EOF
echo "✅ Admin user created"
echo ""

echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "🌐 Backend URL: $BACKEND_URL"
echo "🔑 Admin Email: admin@praxislabs.com"
echo "🔐 Admin Password: AdminPass123!"
echo ""
echo "📋 Next Steps:"
echo "1. Update Vercel frontend:"
echo "   NEXT_PUBLIC_API_URL=$BACKEND_URL"
echo ""
echo "2. Test backend:"
echo "   curl $BACKEND_URL/"
echo ""
echo "3. View logs:"
echo "   railway logs"
echo ""
echo "4. Open dashboard:"
echo "   railway open"
echo ""
