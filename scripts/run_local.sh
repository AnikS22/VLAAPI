#!/bin/bash

# Praxis Labs - Local Development Setup Script
# This script sets up and runs the backend API locally

set -e

echo "🚀 Praxis Labs - Local Development Setup"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "   Install Python 3.10+ from https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Python $(python3 --version) found"

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install postgresql@15
            brew services start postgresql@15
        else
            echo "❌ Please install Homebrew first: https://brew.sh"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt update
        sudo apt install -y postgresql postgresql-contrib
        sudo systemctl start postgresql
    else
        echo "❌ Unsupported OS. Please install PostgreSQL manually."
        exit 1
    fi
fi

echo "✅ PostgreSQL found"

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "⚠️  Redis not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install redis
        brew services start redis
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt install -y redis-server
        sudo systemctl start redis
    fi
fi

echo "✅ Redis found"

# Create database if it doesn't exist
echo ""
echo "📊 Setting up database..."
if ! psql -lqt | cut -d \| -f 1 | grep -qw vlaapi; then
    createdb vlaapi
    echo "✅ Database 'vlaapi' created"
else
    echo "✅ Database 'vlaapi' already exists"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file..."
    USERNAME=$(whoami)
    cat > .env << EOF
# Application
APP_NAME=Praxis Labs VLA API
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true

# API Server
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://$USERNAME@localhost:5432/vlaapi

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Authentication
JWT_SECRET_KEY=dev-secret-key-change-this-in-production-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30

# Stripe (use test keys)
STRIPE_SECRET_KEY=sk_test_your_test_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_test_key_here
STRIPE_WEBHOOK_SECRET=whsec_test_secret
STRIPE_PRICE_ID_PRO=price_test_pro
STRIPE_PRICE_ID_ENTERPRISE=price_test_enterprise

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Feature Flags
ENABLE_GPU_MONITORING=false
ENABLE_PROMETHEUS=true
ENABLE_EMBEDDINGS=false
EOF
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
echo "Installing dependencies (this may take a few minutes)..."
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Run database migration
echo ""
echo "🔄 Running database migrations..."
if psql -d vlaapi -c '\dt vlaapi.users' 2>/dev/null | grep -q users; then
    echo "✅ Database already migrated"
else
    psql -d vlaapi < migrations/001_create_users_and_auth.sql
    echo "✅ Database migration complete"
fi

# Create admin user if it doesn't exist
echo ""
echo "👤 Creating admin user..."
ADMIN_EXISTS=$(psql -d vlaapi -t -c "SELECT COUNT(*) FROM vlaapi.users WHERE email='admin@praxislabs.com'" 2>/dev/null || echo "0")
if [ "$ADMIN_EXISTS" -gt 0 ]; then
    echo "✅ Admin user already exists"
else
    psql -d vlaapi << 'EOF'
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
    echo "✅ Admin user created"
    echo "   Email: admin@praxislabs.com"
    echo "   Password: AdminPass123!"
fi

# Create logs directory
mkdir -p logs

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "🚀 Starting Praxis Labs API..."
echo ""
echo "📍 Backend API: http://localhost:8000"
echo "📖 API Docs: http://localhost:8000/docs"
echo "🔍 Health Check: http://localhost:8000/"
echo ""
echo "👤 Admin Login:"
echo "   Email: admin@praxislabs.com"
echo "   Password: AdminPass123!"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
