#!/bin/bash
# Remote GPU Server Deployment Script
# For Linux server with NVIDIA GPUs

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   VLA API - Remote GPU Deployment                        ║"
echo "║   For Linux servers with NVIDIA GPUs                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check we're on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}❌ This script is for Linux servers only${NC}"
    echo "   For local Mac deployment, use: ./scripts/local_deploy.sh"
    exit 1
fi

# Check for GPU
echo -e "\n${YELLOW}🔍 Checking for NVIDIA GPU...${NC}"
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}❌ nvidia-smi not found. Please install NVIDIA drivers first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ NVIDIA GPU detected:${NC}"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# Check Docker
echo -e "\n${YELLOW}🔍 Checking for Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker not found. Installing...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

echo -e "${GREEN}✅ Docker found: $(docker --version)${NC}"

# Check NVIDIA Container Toolkit
echo -e "\n${YELLOW}🔍 Checking NVIDIA Container Toolkit...${NC}"
if ! docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu20.04 nvidia-smi &> /dev/null; then
    echo -e "${YELLOW}⚠️  Installing NVIDIA Container Toolkit...${NC}"
    
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
      sudo tee /etc/apt/sources.list.d/nvidia-docker.list
    
    sudo apt update
    sudo apt install -y nvidia-container-toolkit
    sudo systemctl restart docker
fi

echo -e "${GREEN}✅ Docker can access GPU${NC}"

# Stop any existing deployment
echo -e "\n${YELLOW}🧹 Cleaning up any existing deployment...${NC}"
docker-compose -f docker-compose.remote.yml down 2>/dev/null || true

# Start deployment
echo -e "\n${YELLOW}🚀 Starting GPU deployment...${NC}"
echo -e "   ${BLUE}This will take 10-15 minutes on first run (downloading models)${NC}"
echo ""

docker-compose -f docker-compose.remote.yml up -d --build

# Wait for services
echo -e "\n${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 30

# Wait for PostgreSQL
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec vlaapi-postgres-remote pg_isready -U vlaapi &>/dev/null; then
        echo -e "${GREEN}✅ PostgreSQL ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2
done

# Wait for API (will take longer as it loads model)
echo -e "\n${YELLOW}⏳ Waiting for API to load model (this takes 5-10 minutes)...${NC}"
RETRY_COUNT=0
while [ $RETRY_COUNT -lt 120 ]; do  # 4 minutes max
    if curl -sf http://localhost:8000/health &>/dev/null; then
        echo -e "${GREEN}✅ API ready with GPU model loaded${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $((RETRY_COUNT % 10)) -eq 0 ]; then
        echo "   Still loading model... ($RETRY_COUNT/120)"
    fi
    sleep 2
done

# Initialize database
echo -e "\n${YELLOW}📦 Initializing database...${NC}"
docker exec vlaapi-postgres-remote psql -U vlaapi -d vlaapi -c "CREATE EXTENSION IF NOT EXISTS vector;" &>/dev/null || true

docker exec vlaapi-api-remote python -c "
import asyncio
import sys
sys.path.insert(0, '/app')
from src.models.database import Base
from sqlalchemy.ext.asyncio import create_async_engine

async def init():
    engine = create_async_engine('postgresql+asyncpg://vlaapi:remote_password_456@postgres:5432/vlaapi')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init())
" 2>/dev/null && echo -e "${GREEN}✅ Database initialized${NC}"

# Create test customer
echo -e "\n${YELLOW}👤 Creating test customer...${NC}"
API_KEY=$(docker exec vlaapi-api-remote python << 'PYTHON_EOF'
import asyncio, sys, hashlib, secrets
from uuid import uuid4
from datetime import datetime
sys.path.insert(0, '/app')
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models.database import Customer, APIKey

async def create():
    random_part = secrets.token_urlsafe(32)
    api_key = f"vla_remote_{random_part}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    engine = create_async_engine('postgresql+asyncpg://vlaapi:remote_password_456@postgres:5432/vlaapi')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        async with session.begin():
            customer = Customer(
                customer_id=uuid4(),
                company_name="Test Customer (Remote GPU)",
                email="test@remote.com",
                tier="pro",
                is_active=True,
                monthly_quota=100000,
                monthly_usage=0,
                created_at=datetime.utcnow()
            )
            session.add(customer)
            await session.flush()
            
            api_key_obj = APIKey(
                key_id=uuid4(),
                customer_id=customer.customer_id,
                key_hash=key_hash,
                key_prefix=api_key[:20],
                is_active=True,
                rate_limit_per_minute=100,
                rate_limit_per_day=10000,
                created_at=datetime.utcnow()
            )
            session.add(api_key_obj)
    
    return api_key

print(asyncio.run(create()))
PYTHON_EOF
)

# Save API key
echo "$API_KEY" > remote_api_key.txt

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

# Print summary
echo -e "\n${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            ✅ GPU DEPLOYMENT COMPLETE!                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${BLUE}🖥️  Server Information:${NC}"
echo -e "   IP Address: ${GREEN}$SERVER_IP${NC}"
echo -e "   GPU Status:"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader | \
  awk -F', ' '{printf "      GPU %d: %s (%.1f GB / %.1f GB, %s)\n", NR-1, $1, $2/1024, $3/1024, $4}'

echo -e "\n${BLUE}🔑 Test API Key (saved to remote_api_key.txt):${NC}"
echo -e "   ${GREEN}$API_KEY${NC}"

echo -e "\n${BLUE}📊 Services Running:${NC}"
echo -e "   ${GREEN}✓${NC} API Server:    http://$SERVER_IP:8000"
echo -e "   ${GREEN}✓${NC} API Docs:      http://$SERVER_IP:8000/docs"
echo -e "   ${GREEN}✓${NC} Grafana:       http://$SERVER_IP:3000 (admin/admin123)"
echo -e "   ${GREEN}✓${NC} Prometheus:    http://$SERVER_IP:9090"

echo -e "\n${BLUE}🧪 Quick Test:${NC}"
echo -e "   # From this server:"
echo -e "   ${YELLOW}curl http://localhost:8000/health${NC}"
echo ""
echo -e "   # From your Mac:"
echo -e "   ${YELLOW}curl http://$SERVER_IP:8000/health${NC}"

echo -e "\n${BLUE}🎯 Full Test from Your Mac:${NC}"
cat > test_remote_from_mac.sh << EOF
#!/bin/bash
# Run this script from your Mac to test the remote GPU server

SERVER_IP="$SERVER_IP"
API_KEY="$API_KEY"

echo "Testing remote GPU API..."

curl -X POST http://\$SERVER_IP:8000/v1/inference \\
  -H "Authorization: Bearer \$API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "openvla-7b",
    "image": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "instruction": "pick up the red cube"
  }' | jq
EOF

chmod +x test_remote_from_mac.sh
echo -e "   ${YELLOW}./test_remote_from_mac.sh${NC}"
echo -e "   (Script created: test_remote_from_mac.sh)"

echo -e "\n${BLUE}📚 Documentation:${NC}"
echo -e "   Full guide: docs/REMOTE_GPU_DEPLOYMENT.md"

echo -e "\n${BLUE}🛑 To Stop:${NC}"
echo -e "   docker-compose -f docker-compose.remote.yml down"

echo -e "\n${GREEN}🎉 GPU deployment ready! Now test from your Mac!${NC}\n"

