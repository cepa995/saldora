# Saldora

AI-powered invoice processing platform for the Serbian market.

## Overview

Saldora helps accountants, agencies, and businesses in Serbia automatically extract data from invoices using AI-powered OCR. Supports both Cyrillic and Latin scripts.

## Project Structure

```
faktura-ai/
├── apps/
│   ├── web/          # Next.js frontend
│   └── api/          # FastAPI backend
├── packages/
│   └── ml/           # ML package (OCR pipeline)
├── workers/
│   └── ocr_worker/   # Celery worker for GPU tasks
├── infra/
│   ├── docker/       # Docker Compose configs
│   └── k8s/          # Kubernetes manifests
├── docs/
│   └── SRS.md        # Software Requirements Specification
└── scripts/          # Development scripts
```

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.12+
- Docker and Docker Compose
- (Optional) NVIDIA GPU with CUDA for ML acceleration

### Development Setup

```bash
# Clone and setup
git clone <repository>
cd faktura-ai
./scripts/setup-dev.sh

# Start development servers
npm run dev:all
```

### Manual Setup

```bash
# Install dependencies
npm install
cd apps/web && npm install && cd ../..

# Create Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e "packages/ml[dev]"
pip install -e "apps/api[dev]"

# Start infrastructure
docker compose -f infra/docker/docker-compose.yml up -d postgres redis minio

# Start development servers
npm run dev:web   # Web app at http://localhost:3000
npm run dev:api   # API at http://localhost:8000
```

## Architecture

### Frontend (Next.js)

- Modern React with App Router
- Tailwind CSS for styling
- TypeScript for type safety

### Backend (FastAPI)

- Async Python web framework
- PostgreSQL database
- Redis for caching and task queue
- JWT authentication

### ML Pipeline

- **Primary OCR**: dots.ocr (1.7B Vision-Language Model)
- **Fallback OCR**: EasyOCR (for Serbian Cyrillic)
- Field extraction with regex patterns
- PIB validation with mod-11 checksum
- Mathematical verification

### Task Queue (Celery)

- Redis as message broker
- GPU-accelerated OCR workers
- Batch processing support

## Environment Variables

Copy `infra/docker/.env.example` to `infra/docker/.env` and configure:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://...

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# Storage
STORAGE_ENDPOINT=http://localhost:9000
STORAGE_BUCKET=saldora-documents

# JWT
JWT_SECRET_KEY=your-secret-key

# ML
OCR_PRIMARY_ENGINE=dots
OCR_USE_GPU=true
```

## API Documentation

When running locally, access API docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Docker

```bash
# Start all services
npm run docker:up

# View logs
npm run docker:logs

# Stop services
npm run docker:down
```

## Testing

```bash
# Frontend tests
cd apps/web && npm test

# Backend tests
cd apps/api && pytest

# ML package tests
cd packages/ml && pytest
```

## License

Proprietary - All rights reserved

## Support

For issues and feature requests, contact the development team.
