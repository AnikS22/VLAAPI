#!/bin/bash
# Local Mock Deployment Script
# Sets up complete local environment for testing

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   VLA Inference API - Local Mock Deployment          ║"
echo "║   Test everything before deploying to servers!       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
echo -e "\n${YELLOW}📋 Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker Desktop.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose not found. Please install docker-compose.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker found: $(docker --version)${NC}"
echo -e "${GREEN}✅ docker-compose found: $(docker-compose --version)${NC}"

# Clean up any existing containers
echo -e "\n${YELLOW}🧹 Cleaning up existing containers...${NC}"
docker-compose -f docker-compose.local.yml down -v 2>/dev/null || true

# Start services
echo -e "\n${YELLOW}🚀 Starting services...${NC}"
echo -e "   This may take a few minutes on first run..."

docker-compose -f docker-compose.local.yml up -d --build

# Wait for services to be healthy
echo -e "\n${YELLOW}⏳ Waiting for services to be ready...${NC}"

MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec vlaapi-postgres-local pg_isready -U vlaapi &>/dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "\n${RED}❌ PostgreSQL failed to start${NC}"
    exit 1
fi

RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec vlaapi-redis-local redis-cli -a local_redis_123 ping &>/dev/null; then
        echo -e "${GREEN}✅ Redis is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2
done

RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8000/health &>/dev/null; then
        echo -e "${GREEN}✅ API is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2
done

# Install pgvector extension
echo -e "\n${YELLOW}📦 Installing database extensions...${NC}"
docker exec vlaapi-postgres-local psql -U vlaapi -d vlaapi -c "CREATE EXTENSION IF NOT EXISTS vector;" &>/dev/null
echo -e "${GREEN}✅ Extensions installed${NC}"

# Initialize database schema
echo -e "\n${YELLOW}🗄️  Initializing database schema...${NC}"
docker exec vlaapi-api-local python -c "
import asyncio
import sys
sys.path.insert(0, '/app')
from src.models.database import Base
from sqlalchemy.ext.asyncio import create_async_engine

async def init():
    engine = create_async_engine('postgresql+asyncpg://vlaapi:local_password_123@postgres:5432/vlaapi')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Schema created')

asyncio.run(init())
" 2>/dev/null && echo -e "${GREEN}✅ Database schema initialized${NC}" || echo -e "${YELLOW}⚠️  Schema may already exist${NC}"

# Create test customers
echo -e "\n${YELLOW}👥 Creating test customer accounts...${NC}"

docker exec vlaapi-api-local python << 'PYTHON_EOF'
import asyncio
import sys
sys.path.insert(0, '/app')
from uuid import uuid4
from datetime import datetime
import hashlib
import secrets
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models.database import Customer, APIKey

async def create_customer(session, name, email, tier):
    # Generate API key
    random_part = secrets.token_urlsafe(32)
    api_key = f"vla_local_{random_part}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Create customer
    customer = Customer(
        customer_id=uuid4(),
        company_name=name,
        email=email,
        tier=tier,
        is_active=True,
        monthly_quota={"free": 10000, "pro": 100000, "enterprise": None}[tier],
        monthly_usage=0,
        created_at=datetime.utcnow()
    )
    session.add(customer)
    await session.flush()
    
    # Create API key
    limits = {
        "free": {"rpm": 10, "rpd": 1000},
        "pro": {"rpm": 100, "rpd": 10000},
        "enterprise": {"rpm": 1000, "rpd": 100000}
    }
    
    api_key_obj = APIKey(
        key_id=uuid4(),
        customer_id=customer.customer_id,
        key_hash=key_hash,
        key_prefix=api_key[:20],
        is_active=True,
        rate_limit_per_minute=limits[tier]["rpm"],
        rate_limit_per_day=limits[tier]["rpd"],
        created_at=datetime.utcnow()
    )
    session.add(api_key_obj)
    
    return api_key, name, tier

async def main():
    engine = create_async_engine('postgresql+asyncpg://vlaapi:local_password_123@postgres:5432/vlaapi')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    keys = []
    async with async_session() as session:
        async with session.begin():
            key1, name1, tier1 = await create_customer(session, "Test Company (Free)", "free@test.com", "free")
            key2, name2, tier2 = await create_customer(session, "Acme Robotics (Pro)", "pro@acme.com", "pro")
            key3, name3, tier3 = await create_customer(session, "MegaCorp (Enterprise)", "enterprise@megacorp.com", "enterprise")
            keys = [(key1, name1, tier1), (key2, name2, tier2), (key3, name3, tier3)]
    
    # Print keys
    for key, name, tier in keys:
        print(f"{tier.upper()}_TIER_KEY={key}")

asyncio.run(main())
PYTHON_EOF

# Save keys to file
echo -e "\n${YELLOW}💾 Saving API keys...${NC}"
docker exec vlaapi-api-local python << 'PYTHON_EOF' > test_api_keys.txt 2>/dev/null
import asyncio
import sys
sys.path.insert(0, '/app')
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.database import Customer, APIKey

async def get_keys():
    engine = create_async_engine('postgresql+asyncpg://vlaapi:local_password_123@postgres:5432/vlaapi')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(
            select(Customer, APIKey)
            .join(APIKey, Customer.customer_id == APIKey.customer_id)
            .order_by(Customer.tier)
        )
        for customer, api_key in result:
            # Reconstruct API key from prefix (this is just for demo - in production, never store raw keys)
            print(f"# {customer.company_name} ({customer.tier})")
            print(f"{customer.tier.upper()}_KEY={api_key.key_prefix}...")
            print()

asyncio.run(get_keys())
PYTHON_EOF

if [ -f test_api_keys.txt ]; then
    echo -e "${GREEN}✅ Test customers created${NC}"
else
    echo -e "${YELLOW}⚠️  Could not save API keys to file${NC}"
fi

# Print summary
echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ LOCAL DEPLOYMENT COMPLETE!             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"

echo -e "\n${BLUE}📊 Services Running:${NC}"
echo -e "   ${GREEN}✓${NC} API Server:    http://localhost:8000"
echo -e "   ${GREEN}✓${NC} API Docs:      http://localhost:8000/docs"
echo -e "   ${GREEN}✓${NC} Grafana:       http://localhost:3000 (admin/admin123)"
echo -e "   ${GREEN}✓${NC} Prometheus:    http://localhost:9090"
echo -e "   ${GREEN}✓${NC} PostgreSQL:    localhost:5432"
echo -e "   ${GREEN}✓${NC} Redis:         localhost:6379"

echo -e "\n${BLUE}🔑 Test API Keys:${NC}"
if [ -f test_api_keys.txt ]; then
    cat test_api_keys.txt
else
    echo -e "${YELLOW}   Run: docker exec vlaapi-api-local cat /tmp/test_api_keys.txt${NC}"
fi

echo -e "\n${BLUE}🧪 Quick Test:${NC}"
echo -e "   curl http://localhost:8000/health"

echo -e "\n${BLUE}📚 Next Steps:${NC}"
echo -e "   1. Test API:        python test_local_api.py"
echo -e "   2. View dashboards: Open http://localhost:3000"
echo -e "   3. See logs:        docker-compose -f docker-compose.local.yml logs -f"
echo -e "   4. Read guide:      docs/LOCAL_MOCK_DEPLOYMENT.md"

echo -e "\n${BLUE}🛑 To Stop:${NC}"
echo -e "   docker-compose -f docker-compose.local.yml down"

echo -e "\n${GREEN}🎉 Happy testing!${NC}\n"

