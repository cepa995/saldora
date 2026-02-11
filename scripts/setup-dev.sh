#!/bin/bash
# FakturaAI Development Setup Script

set -e

echo "🚀 Setting up FakturaAI development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

command -v node >/dev/null 2>&1 || { echo -e "${RED}Node.js is required but not installed.${NC}" >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo -e "${RED}npm is required but not installed.${NC}" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}Python 3 is required but not installed.${NC}" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Docker is required but not installed.${NC}" >&2; exit 1; }

echo -e "${GREEN}✓ All prerequisites met${NC}"

# Install Node.js dependencies
echo -e "\n${YELLOW}Installing Node.js dependencies...${NC}"
npm install
cd apps/web && npm install && cd ../..
echo -e "${GREEN}✓ Node.js dependencies installed${NC}"

# Create Python virtual environment
echo -e "\n${YELLOW}Setting up Python environment...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install -e "packages/ml[dev]"
pip install -e "apps/api[dev]"
echo -e "${GREEN}✓ Python packages installed${NC}"

# Copy environment file
echo -e "\n${YELLOW}Setting up environment...${NC}"
if [ ! -f "infra/docker/.env" ]; then
    cp infra/docker/.env.example infra/docker/.env
    echo -e "${GREEN}✓ Created .env file from example${NC}"
else
    echo -e "${YELLOW}⚠ .env file already exists, skipping${NC}"
fi

# Start Docker services
echo -e "\n${YELLOW}Starting Docker services...${NC}"
docker compose -f infra/docker/docker-compose.yml up -d postgres redis minio
echo -e "${GREEN}✓ Docker services started${NC}"

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
sleep 5

# Create MinIO bucket
echo -e "\n${YELLOW}Setting up MinIO bucket...${NC}"
docker exec fakturaai-minio mc alias set local http://localhost:9000 minioadmin minioadmin 2>/dev/null || true
docker exec fakturaai-minio mc mb local/fakturaai-documents --ignore-existing 2>/dev/null || true
echo -e "${GREEN}✓ MinIO bucket created${NC}"

echo -e "\n${GREEN}✅ Development environment setup complete!${NC}"
echo -e "\nNext steps:"
echo -e "  1. Start the web app: ${YELLOW}npm run dev:web${NC}"
echo -e "  2. Start the API: ${YELLOW}npm run dev:api${NC}"
echo -e "  3. Or start everything: ${YELLOW}npm run docker:up${NC}"
echo -e "\nServices:"
echo -e "  - Web App: http://localhost:3000"
echo -e "  - API: http://localhost:8000"
echo -e "  - API Docs: http://localhost:8000/docs"
echo -e "  - MinIO Console: http://localhost:9001"
echo -e "  - Flower (Celery): http://localhost:5555"
