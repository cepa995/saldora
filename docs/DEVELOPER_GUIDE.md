  # Saldora Developer Guide

  A practical, hands-on guide to understanding and working with the Saldora codebase.

  ---

  ## Table of Contents

  1. [Quick Start](#quick-start)
  2. [Project Structure Overview](#1-project-structure-overview)
  3. [The Monorepo](#2-the-monorepo---how-it-all-fits-together)
  4. [Understanding Docker in This Project](#3-understanding-docker-in-this-project)
  5. [Environment Variables by Environment](#4-environment-variables-by-environment)
  6. [How the Backend Works](#5-how-the-backend-works)
  7. [How the Frontend Works](#6-how-the-frontend-works)
  8. [The ML Pipeline](#7-the-ml-pipeline)
  9. [Celery: Async Task Processing](#8-celery-async-task-processing)
  10. [How Services Connect](#9-how-services-connect)
  11. [Implementing the TODOs (Step-by-Step)](#10-implementing-the-todos-step-by-step)
  12. [Common Development Tasks](#11-common-development-tasks)
  13. [Debugging Tips](#12-debugging-tips)
  14. [Project Status & What's Left](#13-project-status--whats-left)
  15. [Quick Reference](#quick-reference)

  ---

  ## Quick Start

  ### Option A: Automated setup (recommended)

  ```bash
  # One command does everything
  ./scripts/setup-dev.sh
  ```

  This script will:
  - Check prerequisites (Node.js, Python 3, Docker)
  - Install all Node.js and Python dependencies
  - Create a Python virtual environment at `.venv/`
  - Copy `.env.example` to `.env`
  - Start PostgreSQL, Redis, and MinIO via Docker
  - Create the MinIO storage bucket

  ### Option B: Manual setup

  ```bash
  # 1. Install dependencies
  npm install                              # Root monorepo deps
  cd apps/web && npm install && cd ../..   # Frontend deps
  python3 -m venv .venv                    # Create Python venv
  source .venv/bin/activate                # Activate it
  pip install -e "packages/ml[dev]"        # ML package
  pip install -e "apps/api[dev]"           # API package

  # 2. Start infrastructure
  docker compose -f infra/docker/docker-compose.yml up -d postgres redis minio

  # 3. Start backend (Terminal 1)
  cd apps/api
  source ../../.venv/bin/activate
  uvicorn app.main:app --reload --port 8000

  # 4. Start frontend (Terminal 2)
  cd apps/web
  npm run dev

  # 5. (Optional) Start Celery worker (Terminal 3)
  cd workers/ocr_worker
  celery -A celery_app worker --loglevel=info
  ```

  ### Option C: Everything in Docker

  ```bash
  docker compose -f infra/docker/docker-compose.yml up -d
  ```

  ### Access Points

  | Service | URL |
  |---------|-----|
  | Frontend | http://localhost:3000 |
  | Backend API | http://localhost:8000 |
  | Swagger Docs | http://localhost:8000/docs |
  | ReDoc | http://localhost:8000/redoc |
  | MinIO Console | http://localhost:9001 (minioadmin/minioadmin) |
  | Flower (Celery monitor) | http://localhost:5555 |

  ---

  ## 1. Project Structure Overview

  ```
  faktura-ai/
  ├── apps/                          # Deployable applications
  │   ├── api/                       # FastAPI backend (Python 3.12)
  │   │   ├── app/
  │   │   │   ├── main.py            # App entry point, CORS, router mounting
  │   │   │   ├── config.py          # Settings from environment variables
  │   │   │   ├── routers/           # API endpoint definitions
  │   │   │   │   ├── auth.py        #   /api/v1/auth/* (register, login, tokens)
  │   │   │   │   ├── invoices.py    #   /api/v1/invoices/* (upload, CRUD, status)
  │   │   │   │   ├── export.py      #   /api/v1/export/* (XLSX, CSV, JSON, audit)
  │   │   │   │   └── webhooks.py    #   /api/v1/webhooks/* (Stripe, APR)
  │   │   │   └── schemas/           # Request/response Pydantic models
  │   │   │       ├── auth.py        #   UserCreate, TokenResponse, etc.
  │   │   │       ├── invoice.py     #   InvoiceResponse, ProcessingStatus, etc.
  │   │   │       └── export.py      #   ExportRequest, AuditExportRequest, etc.
  │   │   ├── pyproject.toml         # Python dependencies and build config
  │   │   └── Dockerfile             # Container image (python:3.12-slim)
  │   │
  │   └── web/                       # Next.js frontend (React 19, TypeScript)
  │       ├── src/
  │       │   ├── app/
  │       │   │   ├── layout.tsx     # Root layout (Inter font, SR metadata)
  │       │   │   ├── page.tsx       # Landing page (rich, animated)
  │       │   │   └── upload/
  │       │   │       └── page.tsx   # Upload page with FileUpload component
  │       │   └── components/
  │       │       ├── FileUpload.tsx  # Drag-and-drop upload (react-dropzone)
  │       │       └── index.ts       # Component barrel exports
  │       ├── package.json           # Next 16, React 19, Tailwind 4
  │       ├── next.config.ts
  │       ├── tsconfig.json
  │       └── Dockerfile             # Container image (node:22-alpine)
  │
  ├── packages/                      # Shared libraries
  │   └── ml/                        # fakturaai_ml - OCR pipeline
  │       ├── fakturaai_ml/
  │       │   ├── __init__.py        # Exports: InvoicePipeline
  │       │   ├── types.py           # Data classes (ExtractedInvoice, etc.)
  │       │   ├── pipeline.py        # Main orchestrator (272 lines)
  │       │   ├── ocr/
  │       │   │   ├── base.py        # OCREngine abstract base class
  │       │   │   ├── dots_ocr.py    # Primary: dots.ocr VLM (calls vLLM server via OpenAI API)
  │       │   │   └── easyocr_fallback.py  # Legacy fallback (disabled — poor Serbian support)
  │       │   ├── extraction/
  │       │   │   ├── fields.py      # Regex-based field extraction (Cyrillic + Latin)
  │       │   │   └── tables.py      # Table extraction (stub)
  │       │   ├── preprocessing/
  │       │   │   ├── image.py       # Image enhancement, deskew, binarization
  │       │   │   └── pdf.py         # PDF to images (pdf2image)
  │       │   ├── postprocessing/
  │       │   │   └── confidence.py  # Confidence scoring
  │       │   └── validation/
  │       │       ├── pib.py         # Serbian PIB mod-11 checksum
  │       │       └── math_check.py  # Invoice math validation
  │       └── playground/            # DotsOCR demo and model weights
  │
  ├── workers/                       # Background job processors
  │   ├── ocr_worker/
  │   │   ├── celery_app.py          # Celery configuration (Redis broker)
  │   │   └── tasks.py               # process_invoice, process_batch tasks
  │   └── Dockerfile                 # CUDA 12.4 GPU image
  │
  ├── infra/
  │   └── docker/
  │       ├── docker-compose.yml     # 7 services for local dev
  │       └── .env.example           # Environment variable template
  │
  ├── scripts/
  │   └── setup-dev.sh               # One-command dev setup
  │
  ├── docs/                          # Documentation
  │   ├── ARCHITECTURE.md            # Design decisions deep-dive
  │   ├── DEVELOPER_GUIDE.md         # This file
  │   ├── MILESTONES.md              # Project timeline
  │   ├── SRS.md                     # Software Requirements Specification
  │   ├── ML_PROJECT_ARCHITECTURE_GUIDE.md
  │   └── DOTS_OCR_USER_GUIDE.md
  │
  ├── package.json                   # Monorepo root (npm workspaces)
  └── README.md
  ```

  ---

  ## 2. The Monorepo - How It All Fits Together

  ### What Is a Monorepo?

  A monorepo is a single git repository that contains multiple projects. Instead of having separate repos for the frontend, backend, ML library, and workers, everything lives together. This means:

  - **One `git clone`** gets you the entire system
  - **Atomic commits** - a change that touches both frontend and backend can be one commit
  - **Shared tooling** - one CI/CD pipeline, one set of linting rules
  - **Easy cross-references** - the worker can import from `packages/ml` directly

  ### How npm Workspaces Work

  The root `package.json` defines workspaces:

  ```json
  {
    "workspaces": ["apps/*", "packages/*"],
    "scripts": {
      "dev": "npm run dev:web",
      "dev:web": "npm -w @fakturaai/web run dev",
      "dev:api": "cd apps/api && uvicorn app.main:app --reload",
      "dev:all": "docker compose ... up -d postgres redis minio && concurrently \"npm run dev:web\" \"npm run dev:api\"",
      "docker:up": "docker compose -f infra/docker/docker-compose.yml up -d",
      "docker:down": "docker compose -f infra/docker/docker-compose.yml down",
      "setup": "./scripts/setup-dev.sh"
    }
  }
  ```

  **Key detail:** npm workspaces only manage Node.js packages. The Python packages (`apps/api`, `packages/ml`, `workers/`) are managed by `pip` and `pyproject.toml`. The root `package.json` provides convenience scripts (`npm run dev:api`) that shell out to Python tools.

  ### How Python Packages Connect

  ```
  packages/ml/pyproject.toml   →  installable as "fakturaai-ml"
  apps/api/pyproject.toml      →  installable as "fakturaai-api"
  workers/ocr_worker/           →  imports from fakturaai_ml directly
  ```

  When you run `pip install -e "packages/ml"`, Python registers `fakturaai_ml` as an importable package. Then the worker can do:

  ```python
  from fakturaai_ml import InvoicePipeline
  ```

  The `-e` flag means "editable" - changes to the source code are immediately reflected without reinstalling.

  ### Understanding pyproject.toml

  This is Python's equivalent of `package.json`. Here's what each section means:

  ```toml
  [project]
  name = "fakturaai-api"           # Package name
  version = "0.1.0"                # Version
  requires-python = ">=3.12"       # Python version requirement

  dependencies = [                 # Production dependencies (like package.json "dependencies")
      "fastapi>=0.110.0",          # Web framework (like Express)
      "uvicorn[standard]>=0.27.0", # ASGI server (like node itself)
      "pydantic>=2.0.0",           # Data validation (like Zod)
      "sqlalchemy>=2.0.0",         # Database ORM (like Prisma/TypeORM)
      "asyncpg>=0.29.0",           # Async PostgreSQL driver
      "redis>=5.0.0",              # Redis client (like ioredis)
      "celery>=5.3.0",             # Task queue (like BullMQ)
      "boto3>=1.34.0",             # AWS/S3 SDK
      "python-jose>=3.3.0",        # JWT handling (like jsonwebtoken)
      "passlib[argon2]>=1.7.4",    # Password hashing (like bcrypt)
      "httpx>=0.27.0",             # HTTP client (like axios)
      "python-multipart>=0.0.9",   # File uploads (like multer)
      "sentry-sdk>=1.40.0",        # Error tracking
  ]

  [project.optional-dependencies]
  dev = [                          # Dev-only (like package.json "devDependencies")
      "pytest>=8.0.0",
      "ruff>=0.2.0",               # Linter (like ESLint)
  ]

  [build-system]
  requires = ["hatchling"]         # Build tool
  build-backend = "hatchling.build"

  [tool.ruff]                      # Linter configuration
  line-length = 100
  ```

  **Common commands:**
  ```bash
  pip install -e .           # Install package in editable mode (like npm install)
  pip install -e ".[dev]"    # Install with dev dependencies
  ruff check .               # Run linter
  ruff format .              # Auto-format code
  ```

  ---

  ## 3. Understanding Docker in This Project

  ### Why Docker?

  Saldora depends on several services (PostgreSQL, Redis, MinIO) and runtimes (Python 3.12, Node 22, CUDA). Without Docker, every developer would have to install and configure each one manually. Docker gives you:

  - **Reproducible environments** - same versions everywhere
  - **One-command infrastructure** - `docker compose up` starts everything
  - **Isolation** - services don't conflict with your system packages
  - **Production parity** - dev and prod run the same containers

  ### Docker Concepts Used in This Project

  | Concept | What It Means Here |
  |---------|-------------------|
  | **Image** | A snapshot of an OS + software (e.g., `postgres:16-alpine` is Alpine Linux with PostgreSQL 16 installed) |
  | **Container** | A running instance of an image (e.g., `fakturaai-postgres` is your running database) |
  | **Volume** | Persistent storage that survives container restarts (`postgres_data` keeps your DB data) |
  | **Dockerfile** | Recipe for building a custom image (how to package our API code) |
  | **docker-compose.yml** | Defines multiple services and how they connect |
  | **Health check** | A command Docker runs to check if a service is ready |
  | **Network** | Docker creates an internal network so containers can talk to each other by name |

  ### How docker-compose.yml Works (Annotated)

  ```yaml
  # infra/docker/docker-compose.yml

  services:
    # ── INFRASTRUCTURE SERVICES ────────────────────────────────────
    # These are pre-built images we just run (no Dockerfile needed)

    postgres:
      image: postgres:16-alpine           # Pre-built image from Docker Hub
      container_name: fakturaai-postgres   # Fixed name for easy reference
      environment:
        POSTGRES_USER: fakturaai           # Creates this user on first start
        POSTGRES_PASSWORD: fakturaai_dev   # Sets password for that user
        POSTGRES_DB: fakturaai             # Creates this database on first start
      volumes:
        - postgres_data:/var/lib/postgresql/data   # Named volume = data persists
      ports:
        - "5432:5432"                      # host_port:container_port
      healthcheck:
        test: ["CMD-SHELL", "pg_isready -U fakturaai"]
        interval: 10s                      # Check every 10s
        timeout: 5s                        # Fail if check takes >5s
        retries: 5                         # Mark unhealthy after 5 failures

    redis:
      image: redis:7-alpine
      container_name: fakturaai-redis
      ports:
        - "6379:6379"
      volumes:
        - redis_data:/data                 # Persists Redis data
      healthcheck:
        test: ["CMD", "redis-cli", "ping"]

    minio:
      image: minio/minio:latest
      container_name: fakturaai-minio
      environment:
        MINIO_ROOT_USER: minioadmin
        MINIO_ROOT_PASSWORD: minioadmin
      command: server /data --console-address ":9001"   # Enable web console
      ports:
        - "9000:9000"     # S3-compatible API
        - "9001:9001"     # Web console UI
      volumes:
        - minio_data:/data

    # ── APPLICATION SERVICES ───────────────────────────────────────
    # These are built from our Dockerfiles

    api:
      build:
        context: ../..                     # Build context is repo root
        dockerfile: apps/api/Dockerfile    # Which Dockerfile to use
      container_name: fakturaai-api
      environment:
        # IMPORTANT: Inside Docker, use container names (postgres, redis, minio)
        # not localhost! Docker creates an internal DNS network.
        DATABASE_URL: postgresql+asyncpg://fakturaai:fakturaai_dev@postgres:5432/fakturaai
        REDIS_URL: redis://redis:6379/0
        CELERY_BROKER_URL: redis://redis:6379/1
        STORAGE_ENDPOINT: http://minio:9000     # "minio" not "localhost"
        STORAGE_ACCESS_KEY: minioadmin
        STORAGE_SECRET_KEY: minioadmin
        ENVIRONMENT: development
      ports:
        - "8000:8000"
      depends_on:
        postgres:
          condition: service_healthy       # Wait until postgres healthcheck passes
        redis:
          condition: service_healthy
      volumes:
        - ../../apps/api:/app              # Mount source code for hot reload
      command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

    web:
      build:
        context: ../..
        dockerfile: apps/web/Dockerfile
      container_name: fakturaai-web
      environment:
        NEXT_PUBLIC_API_URL: http://localhost:8000   # This runs in the BROWSER,
                                                      # so it uses localhost, not "api"
      ports:
        - "3000:3000"
      volumes:
        - ../../apps/web:/app
        - /app/node_modules              # Anonymous volume - don't override node_modules
        - /app/.next                     # Don't override .next build cache
      command: npm run dev

    ocr-worker:
      build:
        context: ../..
        dockerfile: workers/Dockerfile
      container_name: fakturaai-ocr-worker
      environment:
        CELERY_BROKER_URL: redis://redis:6379/1
        CELERY_RESULT_BACKEND: redis://redis:6379/2
        STORAGE_ENDPOINT: http://minio:9000
        STORAGE_ACCESS_KEY: minioadmin
        STORAGE_SECRET_KEY: minioadmin
        OCR_PRIMARY_ENGINE: dots
        OCR_FALLBACK_ENGINE: none
        DOTS_OCR_SERVER_URL: http://dots-ocr-server:8000/v1
        DOTS_OCR_MODEL_NAME: model
      depends_on:
        redis:
          condition: service_healthy
        dots-ocr-server:
          condition: service_healthy
      volumes:
        - ../../packages/ml:/app/packages/ml
        - ../../workers/ocr_worker:/app/ocr_worker

    flower:
      image: mher/flower:2.0
      container_name: fakturaai-flower
      environment:
        CELERY_BROKER_URL: redis://redis:6379/1
      ports:
        - "5555:5555"
      depends_on:
        - redis

  volumes:                               # Named volumes (persist between restarts)
    postgres_data:
    redis_data:
    minio_data:
  ```

  ### Three Ways to Run the Project

  | Approach | Infrastructure | API | Frontend | Best For |
  |----------|---------------|-----|----------|----------|
  | **Hybrid (recommended)** | Docker | Local Python | Local Node | Day-to-day development. Best debugging experience. |
  | **Full Docker** | Docker | Docker | Docker | Testing docker builds, CI, or when you don't want to install Python/Node. |
  | **Minimal Docker** | Docker (only postgres, redis, minio) | Local Python | Local Node | Fastest iteration, lowest resource usage. |

  **Hybrid (recommended):**
  ```bash
  # Start only infrastructure
  docker compose -f infra/docker/docker-compose.yml up -d postgres redis minio

  # Run API and frontend locally (better error messages, faster restarts)
  npm run dev:all
  # Or separately:
  npm run dev:api    # Terminal 1
  npm run dev:web    # Terminal 2
  ```

  **Full Docker:**
  ```bash
  docker compose -f infra/docker/docker-compose.yml up -d
  # Everything starts: postgres, redis, minio, api, web, ocr-worker, flower
  ```

  ### localhost vs Container Names

  This is the most common source of confusion:

  ```
  ┌─────────────────────────────────────────────────────────────────┐
  │                    YOUR MACHINE (HOST)                           │
  │                                                                  │
  │  Browser → http://localhost:3000    (frontend)                  │
  │  curl    → http://localhost:8000    (API)                       │
  │  psql    → localhost:5432           (database)                  │
  │  redis-cli → localhost:6379         (redis)                     │
  │                                                                  │
  │  ┌─────────────────────────────────────────────────────────────┐│
  │  │              DOCKER NETWORK (internal)                       ││
  │  │                                                              ││
  │  │  api → postgres:5432      (container-to-container)          ││
  │  │  api → redis:6379                                           ││
  │  │  api → minio:9000                                           ││
  │  │  ocr-worker → redis:6379                                    ││
  │  │  ocr-worker → minio:9000                                    ││
  │  │                                                              ││
  │  │  EXCEPTION: NEXT_PUBLIC_API_URL uses localhost:8000          ││
  │  │  because the browser runs on YOUR machine, not in Docker    ││
  │  └─────────────────────────────────────────────────────────────┘│
  └─────────────────────────────────────────────────────────────────┘
  ```

  **Rule:** If code runs **inside Docker** → use container names (`postgres`, `redis`, `minio`).
  If code runs **in the browser** or **on your machine** → use `localhost`.

  ### Dockerfiles Explained

  We have three custom Dockerfiles:

  **apps/api/Dockerfile** (Python API):
  ```dockerfile
  FROM python:3.12-slim              # Base image: Debian with Python 3.12
  ENV PYTHONDONTWRITEBYTECODE=1      # Don't create .pyc files
  ENV PYTHONUNBUFFERED=1             # Print output immediately (important for logs)

  RUN apt-get install -y curl        # Needed for healthcheck
  RUN useradd -m -u 1000 api        # Non-root user (security)

  COPY apps/api/pyproject.toml /app/ # Copy deps first (Docker cache optimization)
  RUN pip install -e ".[dev]"        # Install dependencies (cached if deps unchanged)

  COPY apps/api/app /app/app         # Copy source code

  USER api                           # Run as non-root
  EXPOSE 8000
  HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

  **apps/web/Dockerfile** (Next.js Frontend):
  ```dockerfile
  FROM node:22-alpine                # Alpine = smaller image (~180MB vs ~900MB)
  COPY apps/web/package*.json ./     # Cache optimization: deps before code
  RUN npm ci                         # Clean install (deterministic)
  COPY apps/web/ ./
  ARG NEXT_PUBLIC_API_URL            # Build-time argument
  ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
  RUN npm run build                  # Build static + server bundles
  EXPOSE 3000
  CMD ["npm", "start"]               # Production server
  ```

  **workers/Dockerfile** (OCR Worker with GPU):
  ```dockerfile
  FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04   # CUDA for GPU acceleration
  # Installs Python 3.12, OpenCV deps (libgl1, libglib2.0, etc.)
  COPY packages/ml /app/packages/ml  # ML package (changes less often)
  RUN pip3 install /app/packages/ml[gpu]  # Install with GPU extras
  COPY workers/ocr_worker /app/ocr_worker
  USER worker
  CMD ["celery", "-A", "ocr_worker.celery_app", "worker",
      "--loglevel=info", "--concurrency=1", "--queues=ocr"]
  ```

  ### Docker Commands You'll Use

  ```bash
  # Start/stop
  docker compose -f infra/docker/docker-compose.yml up -d              # Start all
  docker compose -f infra/docker/docker-compose.yml up -d postgres redis minio  # Start only infra
  docker compose -f infra/docker/docker-compose.yml down                # Stop all
  docker compose -f infra/docker/docker-compose.yml down -v             # Stop + delete data

  # Logs
  docker compose -f infra/docker/docker-compose.yml logs -f api        # Follow API logs
  docker compose -f infra/docker/docker-compose.yml logs -f --tail=50 postgres  # Last 50 lines

  # Status
  docker compose -f infra/docker/docker-compose.yml ps                 # Show running services
  docker ps                                                             # All running containers

  # Rebuild after Dockerfile changes
  docker compose -f infra/docker/docker-compose.yml build api          # Rebuild one service
  docker compose -f infra/docker/docker-compose.yml up -d --build      # Rebuild and restart all

  # Shell into a container
  docker exec -it fakturaai-postgres psql -U fakturaai -d fakturaai    # PostgreSQL shell
  docker exec -it fakturaai-redis redis-cli                            # Redis shell
  docker exec -it fakturaai-api bash                                   # API container shell
  ```

  ---

  ## 4. Environment Variables by Environment

  ### How Configuration Works

  The API uses Pydantic Settings (`app/config.py`), which loads configuration in this priority order:

  ```
  1. Environment variables (highest priority - always wins)
  2. .env file (if present)
  3. Default values in code (lowest priority)
  ```

  This means you never need to change `config.py` for different environments. You just set environment variables.

  ```python
  # apps/api/app/config.py

  class Settings(BaseSettings):
      model_config = SettingsConfigDict(
          env_file=".env",           # Load from .env file
          case_sensitive=False,      # DATABASE_URL = database_url
      )

      environment: Literal["development", "staging", "production"] = "development"
      database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fakturaai"
      # ... more settings
  ```

  ### Complete Variable Reference

  #### Application

  | Variable | Default | Description |
  |----------|---------|-------------|
  | `ENVIRONMENT` | `development` | One of: `development`, `staging`, `production`. Controls Sentry sample rate, Swagger docs visibility, and debug mode. |
  | `DEBUG` | `false` | Enable debug mode |
  | `APP_NAME` | `Saldora API` | Application name |
  | `APP_VERSION` | `0.1.0` | Application version |
  | `HOST` | `0.0.0.0` | Server bind address |
  | `PORT` | `8000` | Server port |

  #### Database

  | Variable | Default | Description |
  |----------|---------|-------------|
  | `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/fakturaai` | Full PostgreSQL connection string. The `+asyncpg` part tells SQLAlchemy to use the async driver. |
  | `DATABASE_POOL_SIZE` | `20` | Max number of persistent DB connections |
  | `DATABASE_MAX_OVERFLOW` | `10` | Additional connections allowed beyond pool_size (temporary, during spikes) |

  #### Redis

  | Variable | Default | Description |
  |----------|---------|-------------|
  | `REDIS_URL` | `redis://localhost:6379/0` | Redis connection for caching (DB 0) |
  | `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Redis connection for Celery task queue (DB 1) |
  | `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Redis connection for Celery results (DB 2) |

  #### JWT Authentication

  | Variable | Default | Description |
  |----------|---------|-------------|
  | `JWT_SECRET_KEY` | `change-me-in-production` | **MUST change in staging/prod.** Generate with: `openssl rand -hex 32` |
  | `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
  | `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access token lifetime (1 hour) |
  | `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime (1 week) |

  #### Storage (S3/R2/MinIO)

  | Variable | Default | Description |
  |----------|---------|-------------|
  | `STORAGE_ENDPOINT` | `None` | S3 endpoint URL. MinIO: `http://localhost:9000`. Cloudflare R2: `https://<account_id>.r2.cloudflarestorage.com`. AWS S3: leave as `None`. |
  | `STORAGE_BUCKET` | `fakturaai-documents` | Bucket name for document storage |
  | `STORAGE_ACCESS_KEY` | `""` | S3 access key (MinIO: `minioadmin`) |
  | `STORAGE_SECRET_KEY` | `""` | S3 secret key (MinIO: `minioadmin`) |
  | `STORAGE_REGION` | `auto` | S3 region |

  #### Integrations

  | Variable | Default | Description |
  |----------|---------|-------------|
  | `APR_API_URL` | `https://api.apr.gov.rs` | Serbian Business Registry API |
  | `APR_API_TIMEOUT` | `10` | APR API timeout in seconds |
  | `APR_CACHE_TTL` | `86400` | Cache APR results for 24 hours |
  | `STRIPE_SECRET_KEY` | `""` | Stripe API key (starts with `sk_test_` or `sk_live_`) |
  | `STRIPE_WEBHOOK_SECRET` | `""` | Stripe webhook signing secret (starts with `whsec_`) |
  | `SENTRY_DSN` | `None` | Sentry error tracking DSN. `None` = disabled. |

  #### ML Processing

  | Variable | Default | Description |
  |----------|---------|-------------|
  | `OCR_CONFIDENCE_THRESHOLD` | `0.80` | Below this, fallback OCR engine is tried |
  | `OCR_MAX_FILE_SIZE_MB` | `20` | Max upload file size |
  | `OCR_SUPPORTED_FORMATS` | `["pdf","png","jpg","jpeg","tiff","webp"]` | Accepted file types |
  | `OCR_PRIMARY_ENGINE` | `dots` | Primary OCR engine (`dots` or `easyocr`) |
  | `OCR_FALLBACK_ENGINE` | `easyocr` | Fallback OCR engine |
  | `OCR_USE_GPU` | `true` | Enable GPU acceleration |

  #### Frontend

  | Variable | Default | Description |
  |----------|---------|-------------|
  | `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API URL (baked into the JS bundle at build time) |

  ### Example .env Files by Environment

  #### Local Development (`infra/docker/.env`)

  ```bash
  ENVIRONMENT=development
  DEBUG=true

  DATABASE_URL=postgresql+asyncpg://fakturaai:fakturaai_dev@localhost:5432/fakturaai
  REDIS_URL=redis://localhost:6379/0
  CELERY_BROKER_URL=redis://localhost:6379/1
  CELERY_RESULT_BACKEND=redis://localhost:6379/2

  STORAGE_ENDPOINT=http://localhost:9000
  STORAGE_ACCESS_KEY=minioadmin
  STORAGE_SECRET_KEY=minioadmin
  STORAGE_BUCKET=fakturaai-documents

  JWT_SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
  JWT_ALGORITHM=HS256

  # Leave empty for dev - disables Stripe/Sentry/APR
  STRIPE_SECRET_KEY=
  STRIPE_WEBHOOK_SECRET=
  SENTRY_DSN=

  OCR_PRIMARY_ENGINE=dots
  OCR_FALLBACK_ENGINE=none
  DOTS_OCR_SERVER_URL=http://localhost:8100/v1   # vLLM server (dots-ocr-server in docker-compose)
  DOTS_OCR_MODEL_NAME=model
  ```

  #### Staging

  ```bash
  ENVIRONMENT=staging
  DEBUG=false

  DATABASE_URL=postgresql+asyncpg://fakturaai:${DB_PASSWORD}@staging-db.internal:5432/fakturaai
  REDIS_URL=redis://staging-redis.internal:6379/0
  CELERY_BROKER_URL=redis://staging-redis.internal:6379/1
  CELERY_RESULT_BACKEND=redis://staging-redis.internal:6379/2

  # Cloudflare R2 for staging
  STORAGE_ENDPOINT=https://abc123.r2.cloudflarestorage.com
  STORAGE_ACCESS_KEY=${R2_ACCESS_KEY}
  STORAGE_SECRET_KEY=${R2_SECRET_KEY}
  STORAGE_BUCKET=fakturaai-staging-documents
  STORAGE_REGION=auto

  JWT_SECRET_KEY=${JWT_SECRET}                     # From secrets manager
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

  APR_API_URL=https://api.apr.gov.rs
  STRIPE_SECRET_KEY=sk_test_...                    # Test key
  STRIPE_WEBHOOK_SECRET=whsec_...
  SENTRY_DSN=https://xxx@yyy.ingest.sentry.io/zzz

  OCR_PRIMARY_ENGINE=dots
  OCR_USE_GPU=true

  NEXT_PUBLIC_API_URL=https://api.staging.saldora.ai
  ```

  #### Production

  ```bash
  ENVIRONMENT=production
  DEBUG=false

  DATABASE_URL=postgresql+asyncpg://fakturaai:${DB_PASSWORD}@prod-db.internal:5432/fakturaai
  DATABASE_POOL_SIZE=50                            # Higher for production traffic
  DATABASE_MAX_OVERFLOW=20

  REDIS_URL=redis://prod-redis.internal:6379/0
  CELERY_BROKER_URL=redis://prod-redis.internal:6379/1
  CELERY_RESULT_BACKEND=redis://prod-redis.internal:6379/2

  # Cloudflare R2 or AWS S3
  STORAGE_ENDPOINT=https://abc123.r2.cloudflarestorage.com
  STORAGE_ACCESS_KEY=${R2_ACCESS_KEY}
  STORAGE_SECRET_KEY=${R2_SECRET_KEY}
  STORAGE_BUCKET=fakturaai-documents
  STORAGE_REGION=auto

  JWT_SECRET_KEY=${JWT_SECRET}                     # Rotated regularly
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30               # Shorter in prod
  JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

  APR_API_URL=https://api.apr.gov.rs
  APR_CACHE_TTL=86400

  STRIPE_SECRET_KEY=sk_live_...                    # Live key!
  STRIPE_WEBHOOK_SECRET=whsec_...
  SENTRY_DSN=https://xxx@yyy.ingest.sentry.io/zzz

  OCR_PRIMARY_ENGINE=dots
  OCR_USE_GPU=true
  OCR_CONFIDENCE_THRESHOLD=0.80

  NEXT_PUBLIC_API_URL=https://api.saldora.ai
  ```

  ### What Changes Between Environments

  | What | Development | Staging | Production |
  |------|-------------|---------|------------|
  | Database | Docker (localhost) | Managed PostgreSQL | Managed PostgreSQL (HA) |
  | Redis | Docker (localhost) | Managed Redis | Managed Redis (cluster) |
  | Storage | MinIO (localhost) | Cloudflare R2 | Cloudflare R2 |
  | OCR Engine | EasyOCR (CPU) | dots.ocr (GPU) | dots.ocr (GPU) |
  | Swagger Docs | Enabled (`/docs`) | Enabled | **Disabled** |
  | Sentry | Off | On (100% sample) | On (10% sample) |
  | JWT Secret | Hardcoded default | From secrets manager | From secrets manager |
  | Stripe | Not connected | Test keys | **Live keys** |
  | Debug | true | false | false |
  | DB Pool Size | 20 | 20 | 50 |

  ---

  ## 5. How the Backend Works

  ### 5.1 Entry Point: main.py

  This is where everything starts. Let's walk through the actual code:

  ```python
  # apps/api/app/main.py

  settings = get_settings()    # Load configuration (cached with @lru_cache)

  # 1. Sentry - Error tracking (only if DSN is configured)
  if settings.sentry_dsn:
      sentry_sdk.init(
          dsn=settings.sentry_dsn,
          environment=settings.environment,
          # In production: only track 10% of requests (cost savings)
          # In dev/staging: track everything
          traces_sample_rate=0.1 if settings.environment == "production" else 1.0,
      )

  # 2. Lifespan - Runs code on startup and shutdown
  @asynccontextmanager
  async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
      # STARTUP: Initialize connections
      # TODO: Initialize database connection pool
      # TODO: Initialize Redis connection
      # TODO: Warm up ML models (optional)
      yield
      # SHUTDOWN: Clean up
      # TODO: Close database connections
      # TODO: Close Redis connections

  # 3. App creation
  app = FastAPI(
      title=settings.app_name,
      version=settings.app_version,
      # Hide API docs in production (security through obscurity + cleanliness)
      docs_url="/docs" if settings.environment != "production" else None,
      redoc_url="/redoc" if settings.environment != "production" else None,
      lifespan=lifespan,
  )

  # 4. CORS - Which domains can call our API from a browser
  app.add_middleware(
      CORSMiddleware,
      allow_origins=[
          "http://localhost:3000",          # Local dev
          "https://saldora.ai",           # Production
          "https://www.saldora.ai",       # Production (www)
      ],
      allow_credentials=True,               # Allow cookies/tokens
      allow_methods=["*"],
      allow_headers=["*"],
  )

  # 5. Mount routers (like Express app.use("/path", router))
  app.include_router(auth.router,     prefix="/api/v1/auth",     tags=["Authentication"])
  app.include_router(invoices.router, prefix="/api/v1/invoices",  tags=["Invoices"])
  app.include_router(export.router,   prefix="/api/v1/export",    tags=["Export"])
  app.include_router(webhooks.router, prefix="/api/v1/webhooks",  tags=["Webhooks"])

  # 6. Health check (used by Docker healthcheck, load balancers, monitoring)
  @app.get("/health")
  async def health_check():
      return {"status": "healthy", "version": settings.app_version}
  ```

  ### 5.2 Configuration: config.py

  ```python
  # apps/api/app/config.py

  class Settings(BaseSettings):
      model_config = SettingsConfigDict(
          env_file=".env",          # Automatically loads .env file
          env_file_encoding="utf-8",
          case_sensitive=False,     # DATABASE_URL = database_url = Database_Url
      )

      # Each field name maps to an environment variable
      environment: Literal["development", "staging", "production"] = "development"
      database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fakturaai"
      jwt_secret_key: str = "change-me-in-production"
      # ... 66 total settings

  @lru_cache
  def get_settings() -> Settings:
      """Get cached settings instance."""
      return Settings()
  ```

  **Why `@lru_cache`?** Loading settings involves reading files and env vars. Caching means it only happens once, and every call to `get_settings()` returns the same instance.

  **How to use settings anywhere:**
  ```python
  from app.config import get_settings
  settings = get_settings()
  print(settings.database_url)
  ```

  ### 5.3 Routers: Defining Endpoints

  Routers group related endpoints, like Express routers. The project has four:

  | Router | Prefix | File | Endpoints |
  |--------|--------|------|-----------|
  | Auth | `/api/v1/auth` | `routers/auth.py` | register, login, refresh, logout, password-reset |
  | Invoices | `/api/v1/invoices` | `routers/invoices.py` | upload, batch upload, CRUD, status, verify |
  | Export | `/api/v1/export` | `routers/export.py` | create export, templates, audit export, PDV books (KPR/KIR) |
  | Webhooks | `/api/v1/webhooks` | `routers/webhooks.py` | Stripe, APR |

  **Example: The upload endpoint (with full annotations):**

  ```python
  # apps/api/app/routers/invoices.py

  router = APIRouter()
  settings = get_settings()

  @router.post(
      "/upload",
      response_model=ProcessingStatus,          # Tells Swagger what the response looks like
      status_code=status.HTTP_202_ACCEPTED,     # 202 = "Accepted for processing" (not done yet)
  )
  async def upload_invoice(
      # FastAPI automatically extracts the file from the multipart form data
      file: Annotated[UploadFile, File(description="Invoice document (PDF, PNG, JPG)")],
      # Query parameters
      priority: str = Query(default="normal", regex="^(normal|high)$"),
      callback_url: str | None = None,
  ) -> ProcessingStatus:
      """Docstring becomes the description in Swagger UI."""

      # Validate file type against allowed MIME types
      if file.content_type not in ["application/pdf", "image/png", "image/jpeg", ...]:
          raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}")

      # Read entire file into memory and check size
      content = await file.read()
      if len(content) > settings.ocr_max_file_size_mb * 1024 * 1024:
          raise HTTPException(status_code=413, detail=f"File too large. Max {settings.ocr_max_file_size_mb}MB")

      # TODO: The actual implementation goes here
      # 1. Save file to S3/R2
      # 2. Create document record in database
      # 3. Create invoice record with status "processing"
      # 4. Queue OCR task with Celery
      # 5. Return job ID and estimated time
      raise HTTPException(status_code=501, detail="Upload processing not yet implemented")
  ```

  ### 5.4 Schemas: Data Validation

  Schemas define the shape of data going in and out of the API. They're Pydantic models that:
  - **Validate input** automatically (wrong type → 422 error)
  - **Document the API** (appear in Swagger UI)
  - **Serialize output** (convert Python objects to JSON)

  ```python
  # apps/api/app/schemas/invoice.py

  class CompanyInfo(BaseModel):
      pib: str = Field(description="Tax ID (PIB) - 9 digits")
      name: str
      address: str | None = None          # Optional field
      verified: bool = Field(default=False)

  class InvoiceResponse(BaseModel):
      id: UUID
      status: Literal["processing", "review", "verified", "exported", "error"]
      confidence_score: float | None = Field(ge=0, le=100)   # 0-100 range enforced

      # Parties
      seller: CompanyInfo | None
      buyer: CompanyInfo | None

      # Amounts (Decimal for financial precision - never use float for money!)
      subtotal: Decimal | None
      total_amount: Decimal | None

      # Timestamps
      created_at: datetime
      updated_at: datetime

      model_config = {"from_attributes": True}   # Allow creating from SQLAlchemy ORM objects
  ```

  ### 5.5 The Complete API Endpoint Map

  ```
  GET  /                                    → API info (name, version, docs link)
  GET  /health                              → Health check

  POST /api/v1/auth/register                → Create user account
  POST /api/v1/auth/login                   → Get access + refresh tokens
  POST /api/v1/auth/refresh                 → Refresh access token
  POST /api/v1/auth/logout                  → Invalidate tokens
  POST /api/v1/auth/password-reset/request  → Send reset email
  POST /api/v1/auth/password-reset/confirm  → Set new password

  POST /api/v1/invoices/upload              → Upload single invoice (returns job ID)
  POST /api/v1/invoices/upload/batch        → Upload multiple invoices (max 50)
  GET  /api/v1/invoices                     → List invoices (filters, sorting, pagination)
  GET  /api/v1/invoices/{id}                → Get invoice details
  PATCH /api/v1/invoices/{id}               → Update invoice (manual corrections)
  DELETE /api/v1/invoices/{id}              → Delete invoice + document
  GET  /api/v1/invoices/{id}/status         → Poll processing status
  POST /api/v1/invoices/{id}/verify         → Mark as verified

  POST /api/v1/export                       → Export invoices (XLSX, CSV, JSON)
  GET  /api/v1/export/templates             → List export templates
  POST /api/v1/export/audit                 → Tax audit export (ZIP archive)
  GET  /api/v1/export/pdv-books/preview     → Preview PDV book entry count (Pro+)
  POST /api/v1/export/pdv-books             → Generate PDV book (KPR/KIR) as XLSX/CSV (Pro+)

  POST /api/v1/webhooks/stripe              → Stripe payment events
  POST /api/v1/webhooks/apr                 → APR data updates
  GET  /api/v1/webhooks/test                → Webhook connectivity test
  ```

  ---

  ## 6. How the Frontend Works

  ### 6.1 Next.js App Router

  **File-based routing** - the file path determines the URL:

  ```
  src/app/
  ├── layout.tsx        →  Root layout (wraps ALL pages)
  ├── page.tsx          →  /                  (landing page)
  └── upload/
      └── page.tsx      →  /upload            (upload page)

  # Future pages would follow the same pattern:
  ├── dashboard/
  │   └── page.tsx      →  /dashboard
  ├── invoices/
  │   └── [id]/
  │       └── page.tsx  →  /invoices/abc-123  (dynamic route)
  └── settings/
      └── page.tsx      →  /settings
  ```

  ### 6.2 Server vs Client Components

  Next.js has two types of components, and understanding the difference is critical:

  ```tsx
  // SERVER COMPONENT (default) - renders on the server, sends HTML to browser
  // apps/web/src/app/page.tsx
  export default function Home() {
    // CAN: fetch data, access database, read files, use secrets
    // CANNOT: useState, useEffect, onClick, useRef, browser APIs
    return <div>This HTML is generated on the server</div>
  }

  // CLIENT COMPONENT - renders in the browser
  // apps/web/src/components/FileUpload.tsx
  'use client';  // <-- This magic directive makes it a client component

  import { useState, useCallback } from 'react';

  export function FileUpload() {
    // CAN: useState, useEffect, onClick, browser APIs, react-dropzone
    // CANNOT: directly access database, read server files, use secrets
    const [file, setFile] = useState<File | null>(null);
    return <button onClick={() => setFile(...)}>Upload</button>
  }
  ```

  **When to use which:**
  - Default to **Server Components** for pages, layouts, and static content
  - Use **Client Components** (add `'use client'`) when you need interactivity, state, or browser APIs

  ### 6.3 The FileUpload Component

  The `FileUpload.tsx` component (399 lines) is the most complex frontend piece. It handles:

  ```
  ┌──────────────────────────────────────────┐
  │          FileUpload Component            │
  │                                          │
  │  States:                                 │
  │  ┌──────────┐  drop file  ┌───────────┐ │
  │  │  pending  │ ──────────→│ uploading  │ │
  │  │(dropzone) │            │(progress %)│ │
  │  └──────────┘             └─────┬─────┘ │
  │                                 │        │
  │                          ┌──────▼──────┐ │
  │                          │ processing  │ │
  │                          │  (spinner)  │ │
  │                          └──────┬──────┘ │
  │                          ┌──────▼──────┐ │
  │              ┌───────────│   result    │ │
  │              │           └─────────────┘ │
  │         ┌────▼───┐    ┌────────────┐     │
  │         │success │    │   error    │     │
  │         │(green) │    │  (red msg) │     │
  │         └────────┘    └────────────┘     │
  └──────────────────────────────────────────┘
  ```

  **Key implementation details:**
  - Uses `react-dropzone` for drag-and-drop
  - Accepts: PDF, JPEG, PNG, TIFF, BMP, WEBP (max 20MB)
  - Shows image thumbnails or PDF icon
  - Progress bar during upload
  - Calls `POST /api/v1/invoices/upload` with FormData

  ### 6.4 Making API Calls

  The frontend talks to the backend via `fetch()`:

  ```tsx
  // Upload flow
  const handleUpload = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    // 1. Upload file
    const response = await fetch('http://localhost:8000/api/v1/invoices/upload', {
      method: 'POST',
      body: formData,         // No Content-Type header - browser sets it with boundary
    });
    const { id: jobId } = await response.json();

    // 2. Poll for completion
    const pollStatus = async () => {
      const res = await fetch(`http://localhost:8000/api/v1/invoices/${jobId}/status`);
      const status = await res.json();

      if (status.status === 'processing') {
        setTimeout(pollStatus, 2000);    // Check again in 2 seconds
      } else {
        // Done - display results or error
      }
    };
    pollStatus();
  };
  ```

  ### 6.5 Styling

  The project uses **Tailwind CSS v4** with the `@tailwindcss/postcss` plugin. Styles are utility-first:

  ```tsx
  // Instead of writing CSS files:
  <div className="flex items-center gap-4 p-6 bg-white rounded-lg shadow-sm">
    <h2 className="text-xl font-semibold text-gray-900">Upload</h2>
  </div>
  ```

  The landing page (`page.tsx`) uses extensive Tailwind with custom animations, gradients, and responsive design.

  ---

  ## 7. The ML Pipeline

  ### Overview

  The ML pipeline lives in `packages/ml/` and is installable as `fakturaai_ml`. It processes invoice images/PDFs and extracts structured data.

  ### Pipeline Flow

  ```
                        Document (PDF/Image)
                                │
                                ▼
                      ┌──────────────────┐
                      │  Load Document   │
                      │  (PDF → images)  │
                      └────────┬─────────┘
                              │
                      ┌────────▼─────────┐
                      │  dots.ocr VLM    │  ← Raw color image (no preprocessing)
                      │  (vLLM server)   │     Called via OpenAI API over HTTP
                      └────────┬─────────┘
                              │
                      confidence < 0.80?
                        ┌──────┴──────┐
                        │ YES         │ NO
                        ▼             ▼
                save for manual   use OCR result
                review by user
                      │
                      ▼
            ┌──────────────────┐
            │ Extract Fields   │  ← Regex patterns for:
            │ (Cyrillic +      │     PIB, MB, invoice number,
            │  Latin)           │     dates, amounts, VAT
            └────────┬─────────┘
                    │
            ┌────────▼─────────┐
            │   Validate       │  ← PIB checksum (mod-11)
            │                  │  ← Math checks (subtotal + tax = total)
            │                  │  ← Tolerance rules by amount
            └────────┬─────────┘
                    │
            ┌────────▼─────────┐
            │ Calculate        │  ← Per-field confidence
            │ Confidence       │  ← Overall confidence
            └────────┬─────────┘
                    │
                    ▼
              ExtractionResult
              {
                status: "success" | "partial" | "failed",
                invoice: { seller, buyer, amounts, ... },
                overall_confidence: 0.92,
                field_confidences: [...],
                warnings: [...],
                processing_time_ms: 165
              }
  ```

  ### OCR Engines

  **Primary: dots.ocr (DotsOCREngine)**
  - A Vision-Language Model from Hugging Face (`rednote-hilab/dots.ocr`)
  - Requires vLLM >= 0.11.0 and a GPU with >= 6GB VRAM
  - Best for structured document understanding
  - Supports 100+ languages including Serbian (Cyrillic + Latin)
  - Temperature: 0 (deterministic output)

  **Fallback: EasyOCR (EasyOCREngine)**
  - Explicit Serbian Cyrillic support
  - Works well on CPU (slower but no GPU needed)
  - Used when dots.ocr confidence is below 80%
  - Good for pure text extraction when VLM struggles

  **For local development**, the docker-compose sets `OCR_PRIMARY_ENGINE=easyocr` and `OCR_USE_GPU=false` so you don't need a GPU.

  ### Type System

  The ML pipeline uses Python dataclasses (not Pydantic) for its internal types:

  ```python
  # packages/ml/fakturaai_ml/types.py

  @dataclass
  class ExtractedInvoice:
      invoice_number: str | None = None
      invoice_date: date | None = None
      due_date: date | None = None
      seller: CompanyData = field(default_factory=CompanyData)
      buyer: CompanyData = field(default_factory=CompanyData)
      subtotal: Decimal | None = None
      tax_rate: Decimal | None = None
      tax_amount: Decimal | None = None
      total_amount: Decimal | None = None
      currency: str = "RSD"
      line_items: list[LineItemData] = field(default_factory=list)
      raw_text: str = ""
      raw_structured: dict = field(default_factory=dict)

  @dataclass
  class ExtractionResult:
      status: ExtractionStatus       # SUCCESS, PARTIAL, FAILED
      invoice: ExtractedInvoice
      overall_confidence: float      # 0.0 to 1.0
      field_confidences: list[FieldConfidence]
      warnings: list[ValidationWarning]
      is_blocked: bool               # True if any blocking warning
      processing_time_ms: int
      ocr_engine: str                # "dots" or "easyocr"
      page_count: int
  ```

  ### Validation Rules

  **PIB (Serbian Tax ID) - mod-11 checksum:**
  ```
  PIB: 123456789  (9 digits)
  Weights: [2, 3, 4, 5, 6, 7, 8, 9]  (applied to first 8 digits)
  Sum: 1×2 + 2×3 + 3×4 + 4×5 + 5×6 + 6×7 + 7×8 + 8×9
  Remainder: sum % 11
  Check digit: 11 - remainder (if 10→0, if 11→0)
  Must match 9th digit.
  ```

  **Math tolerance (from SRS section 4.9.5):**

  | Invoice Total | Allowed Tolerance |
  |---------------|-------------------|
  | 0 - 10,000 RSD | ±1 RSD |
  | 10,001 - 100,000 RSD | ±5 RSD |
  | 100,001 - 1,000,000 RSD | ±10 RSD |
  | > 1,000,000 RSD | ±50 RSD |

  Checks performed:
  1. Sum of line items = subtotal (within tolerance)
  2. subtotal × tax_rate = tax_amount (within tolerance)
  3. subtotal + tax_amount = total_amount (within tolerance)
  4. Each line item: quantity × unit_price = line total (within tolerance); when `discount` is present, applies as `qty × price × (1 - discount/100) ≈ tax_base`; when `tax_base` is present, uses it directly as the verified base

  ---

  ## 8. Celery: Async Task Processing

  ### Why Celery?

  OCR takes 5-30 seconds per invoice. You can't make the user wait that long.

  ```
  WITHOUT Celery:
  User → API → OCR (30s) → Response
                ↑
                └── User stares at spinner for 30 seconds

  WITH Celery:
  User → API → Queue task → Return job ID (100ms)
                  │
                  └→ Worker picks up task → OCR (30s) → Save result
                                                            │
  User → Poll GET /status ──────────────────────────────→ Get result
  ```

  ### Redis: Three Databases

  Redis has 16 databases (numbered 0-15). We use three:

  ```
  redis://localhost:6379/0  →  Cache (JWT tokens, API response cache)
  redis://localhost:6379/1  →  Celery Broker (task queue - messages waiting to be processed)
  redis://localhost:6379/2  →  Celery Results (completed task results for polling)
  ```

  **Why separate?** Isolation. You can flush the cache (`FLUSHDB` on DB 0) without losing queued tasks (DB 1) or results (DB 2).

  ### Celery Architecture

  ```
  ┌─────────────┐     enqueue task      ┌──────────────┐
  │  FastAPI     │  ────────────────→   │  Redis DB 1  │
  │  (Producer)  │                      │  (Broker)    │
  │              │                      │              │
  │  process_    │                      │  Queue: ocr  │
  │  invoice.    │                      │  [task1,     │
  │  delay(...)  │                      │   task2,     │
  └─────────────┘                      │   task3]     │
                                        └──────┬───────┘
                                              │
                                        pick up task
                                              │
                                        ┌──────▼───────┐
                                        │ Celery Worker │
                                        │ (Consumer)    │
                                        │               │
                                        │ concurrency=1 │  ← One task at a time (GPU bound)
                                        │ queue=ocr     │
                                        │ timeout=180s  │
                                        └──────┬────────┘
                                              │
                                        store result
                                              │
                                        ┌──────▼───────┐
                                        │  Redis DB 2  │
                                        │  (Backend)   │
                                        │              │
                                        │  Results     │
                                        │  expire: 1hr │
                                        └──────────────┘
  ```

  ### Celery Configuration

  ```python
  # workers/ocr_worker/celery_app.py

  app = Celery("ocr_worker", broker=REDIS_URL, backend=RESULT_BACKEND)

  app.conf.update(
      task_serializer="json",               # Serialize tasks as JSON (not pickle)
      worker_prefetch_multiplier=1,         # Only fetch 1 task at a time
      worker_concurrency=1,                 # Process 1 task at a time (GPU limitation)
      task_soft_time_limit=120,             # Warn after 2 minutes
      task_time_limit=180,                  # Kill after 3 minutes
      result_expires=3600,                  # Results available for 1 hour
      task_acks_late=True,                  # Acknowledge AFTER completion (not before)
      task_reject_on_worker_lost=True,      # If worker crashes, requeue the task

      task_routes={                         # Route tasks to specific queues
          "ocr_worker.tasks.process_invoice": {"queue": "ocr"},
          "ocr_worker.tasks.process_batch":   {"queue": "ocr"},
      },
  )
  ```

  ### Task Definition

  ```python
  # workers/ocr_worker/tasks.py

  # Pipeline is expensive to initialize (loads ML models).
  # Lazy loading means it's only created when the first task arrives.
  _pipeline = None

  def get_pipeline():
      global _pipeline
      if _pipeline is None:
          from fakturaai_ml import InvoicePipeline
          _pipeline = InvoicePipeline(
              primary_engine=os.getenv("OCR_PRIMARY_ENGINE", "dots"),
              use_gpu=os.getenv("OCR_USE_GPU", "true").lower() == "true",
          )
      return _pipeline

  @app.task(bind=True, base=OCRTask, name="ocr_worker.tasks.process_invoice")
  def process_invoice(self, invoice_id, document_path, callback_url=None, priority="normal"):
      # 1. Download document from S3/MinIO
      self.update_state(state="PROCESSING", meta={"progress": 10, "stage": "downloading"})
      document_bytes = _download_document(document_path)

      # 2. Run OCR pipeline
      self.update_state(state="PROCESSING", meta={"progress": 20, "stage": "preprocessing"})
      pipeline = get_pipeline()
      result = loop.run_until_complete(pipeline.extract(document_bytes))  # async → sync bridge

      # 3. Save results
      self.update_state(state="PROCESSING", meta={"progress": 90, "stage": "saving"})
      result_dict = _serialize_result(result)
      _save_extraction_result(invoice_id, result_dict)

      # 4. Optional webhook notification
      if callback_url:
          _send_webhook(callback_url, invoice_id, result_dict)

      return result_dict
  ```

  ### Running the Worker

  ```bash
  # Development (CPU mode)
  cd workers/ocr_worker
  OCR_PRIMARY_ENGINE=easyocr OCR_USE_GPU=false celery -A celery_app worker --loglevel=info

  # Production (GPU mode)
  celery -A ocr_worker.celery_app worker --loglevel=info --concurrency=1 --queues=ocr

  # Monitor with Flower
  docker compose -f infra/docker/docker-compose.yml up -d flower
  # Then open http://localhost:5555
  ```

  ---

  ## 9. How Services Connect

  ### The Complete Request Flow

  ```
  ┌─────────────────────────────────────────────────────────────────┐
  │                         USER BROWSER                             │
  │  http://localhost:3000/upload                                   │
  └─────────────────────────────────────────────────────────────────┘
                                │
                                │ User drops file
                                ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                    NEXT.JS FRONTEND (:3000)                      │
  │                                                                  │
  │  FileUpload component:                                          │
  │  1. Validates file type (PDF, PNG, JPG, TIFF, WEBP)            │
  │  2. Validates file size (<= 20MB)                               │
  │  3. POST /api/v1/invoices/upload (FormData)                     │
  └─────────────────────────────────────────────────────────────────┘
                                │
                                │ HTTP POST (multipart/form-data)
                                │ CORS allows localhost:3000 → :8000
                                ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                    FASTAPI BACKEND (:8000)                       │
  │                                                                  │
  │  1. Receive file via UploadFile                                 │
  │  2. Validate MIME type and size (server-side)                   │
  │  3. Upload to MinIO ──────────────────────────┐                 │
  │  4. Create DB record ────────────────────────┐│                 │
  │  5. Queue Celery task ──────────────────────┐││                 │
  │  6. Return {id, status: "queued"} (202)     │││                 │
  └─────────────────────────────────────────────┼┼┼─────────────────┘
                                                │││
              ┌─────────────────────────────────┘││
              │  ┌───────────────────────────────┘│
              │  │  ┌─────────────────────────────┘
              ▼  ▼  ▼
  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────────┐
  │ MINIO (:9000)│  │POSTGRES(:5432│  │       REDIS (:6379)         │
  │              │  │              │  │                              │
  │ fakturaai-   │  │ invoices     │  │ DB 0: Cache                 │
  │ documents/   │  │ users        │  │ DB 1: Celery Broker ◄── task│
  │ invoices/    │  │ companies    │  │ DB 2: Celery Results        │
  │ {id}/orig.pdf│  │ audit_log    │  │                              │
  └──────────────┘  └──────────────┘  └──────────────┬──────────────┘
                                                    │
                                              Worker picks up task
                                                    │
                                      ┌──────────────▼──────────────┐
                                      │       CELERY WORKER         │
                                      │                              │
                                      │  process_invoice():         │
                                      │  1. Download from MinIO     │
                                      │  2. Preprocess image        │
                                      │  3. Run OCR (dots/easyocr)  │
                                      │  4. Extract fields (regex)  │
                                      │  5. Validate (PIB, math)    │
                                      │  6. Calculate confidence    │
                                      │  7. Save to PostgreSQL      │
                                      │  8. Store result in Redis   │
                                      └──────────────┬──────────────┘
                                                    │
                                Frontend polls GET /invoices/{id}/status
                                                    │
  ┌──────────────────────────────────────────────────▼──────────────┐
  │                    FRONTEND RECEIVES RESULT                      │
  │                                                                  │
  │  {                                                              │
  │    "status": "review",                                          │
  │    "confidence_score": 92.0,                                    │
  │    "invoice_number": "2024-001",                                │
  │    "seller": { "pib": "123456789", "name": "Firma DOO" },     │
  │    "total_amount": "12000.00",                                  │
  │    "warnings": ["PIB checksum mismatch for buyer"],            │
  │    "field_confidences": [                                       │
  │      { "field": "total", "confidence": 98, "needs_review": false }│
  │    ]                                                            │
  │  }                                                              │
  └─────────────────────────────────────────────────────────────────┘
  ```

  ### Connection Strings Summary

  | Service | From Your Machine | From Docker Container | From Browser |
  |---------|-------------------|-----------------------|--------------|
  | PostgreSQL | `localhost:5432` | `postgres:5432` | N/A |
  | Redis | `localhost:6379` | `redis:6379` | N/A |
  | MinIO S3 API | `localhost:9000` | `minio:9000` | N/A |
  | MinIO Console | `localhost:9001` | N/A | `localhost:9001` |
  | FastAPI | `localhost:8000` | `api:8000` | `localhost:8000` |
  | Next.js | `localhost:3000` | `web:3000` | `localhost:3000` |
  | Flower | `localhost:5555` | N/A | `localhost:5555` |

  ---

  ## 10. Implementing the TODOs (Step-by-Step)

  Most backend endpoints currently return `501 NOT_IMPLEMENTED`. Here's a guide to implementing them in the right order, with concrete examples.

  ### Implementation Order

  ```
  Phase 1: Foundation (do these first)
    ├── 1. Database models (SQLAlchemy)
    ├── 2. Database connection in lifespan
    ├── 3. Database migrations (Alembic)
    └── 4. Dependency injection setup

  Phase 2: Authentication
    ├── 5. User registration
    ├── 6. Login (JWT tokens)
    ├── 7. Token refresh
    └── 8. Auth middleware (protect routes)

  Phase 3: Core Features
    ├── 9. S3 storage service
    ├── 10. Invoice upload (connect to S3 + Celery)
    ├── 11. Invoice CRUD (list, get, update, delete)
    ├── 12. Processing status (poll Celery)
    └── 13. Invoice verification

  Phase 4: Export & Integrations
    ├── 14. Export to XLSX/CSV/JSON
    ├── 15. Audit export
    ├── 16. Stripe webhooks
    └── 17. APR integration
  ```

  ### Phase 1: Foundation

  #### Step 1: Database Models

  Create `apps/api/app/models/` directory with SQLAlchemy models:

  ```python
  # apps/api/app/models/base.py
  from datetime import datetime
  from uuid import uuid4

  from sqlalchemy import DateTime, func
  from sqlalchemy.dialects.postgresql import UUID
  from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


  class Base(DeclarativeBase):
      """Base class for all database models."""
      pass


  class TimestampMixin:
      """Adds created_at and updated_at columns."""
      created_at: Mapped[datetime] = mapped_column(
          DateTime(timezone=True), server_default=func.now()
      )
      updated_at: Mapped[datetime] = mapped_column(
          DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
      )
  ```

  ```python
  # apps/api/app/models/user.py
  from uuid import uuid4
  from sqlalchemy import String, Boolean, ForeignKey
  from sqlalchemy.dialects.postgresql import UUID
  from sqlalchemy.orm import Mapped, mapped_column, relationship

  from app.models.base import Base, TimestampMixin


  class User(Base, TimestampMixin):
      __tablename__ = "users"

      id: Mapped[uuid4] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
      email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
      password_hash: Mapped[str] = mapped_column(String(255))
      first_name: Mapped[str | None] = mapped_column(String(100))
      last_name: Mapped[str | None] = mapped_column(String(100))
      organization_id: Mapped[uuid4] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
      role: Mapped[str] = mapped_column(String(20), default="member")
      email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

      # Relationships
      organization = relationship("Organization", back_populates="members")
  ```

  ```python
  # apps/api/app/models/invoice.py
  from decimal import Decimal
  from uuid import uuid4
  from sqlalchemy import String, Numeric, Date, Text, JSON, ForeignKey
  from sqlalchemy.dialects.postgresql import UUID
  from sqlalchemy.orm import Mapped, mapped_column

  from app.models.base import Base, TimestampMixin


  class Invoice(Base, TimestampMixin):
      __tablename__ = "invoices"

      id: Mapped[uuid4] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
      organization_id: Mapped[uuid4] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
      status: Mapped[str] = mapped_column(String(20), default="processing")

      # Core fields
      invoice_number: Mapped[str | None] = mapped_column(String(100))
      invoice_date: Mapped[Date | None] = mapped_column(Date)
      due_date: Mapped[Date | None] = mapped_column(Date)

      # Parties (stored as JSON for flexibility)
      seller: Mapped[dict | None] = mapped_column(JSON)
      buyer: Mapped[dict | None] = mapped_column(JSON)

      # Amounts
      subtotal: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
      tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
      tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
      total_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
      currency: Mapped[str] = mapped_column(String(3), default="RSD")

      # Document
      document_path: Mapped[str | None] = mapped_column(String(500))

      # OCR results
      confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
      field_confidences: Mapped[dict | None] = mapped_column(JSON)
      warnings: Mapped[list | None] = mapped_column(JSON)
      raw_ocr_text: Mapped[str | None] = mapped_column(Text)
  ```

  #### Step 2: Database Connection in Lifespan

  ```python
  # apps/api/app/database.py
  from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
  from app.config import get_settings

  settings = get_settings()

  engine = create_async_engine(
      settings.database_url,
      pool_size=settings.database_pool_size,
      max_overflow=settings.database_max_overflow,
  )

  async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


  async def get_db() -> AsyncSession:
      """Dependency that provides a database session."""
      async with async_session() as session:
          yield session
  ```

  Then update `main.py` lifespan:

  ```python
  # apps/api/app/main.py

  @asynccontextmanager
  async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
      # STARTUP
      from app.database import engine
      from app.models.base import Base

      # Create tables (for development; use Alembic migrations in production)
      async with engine.begin() as conn:
          await conn.run_sync(Base.metadata.create_all)

      yield

      # SHUTDOWN
      await engine.dispose()
  ```

  #### Step 3: Dependency Injection

  FastAPI's `Depends()` is how you inject shared resources into endpoints:

  ```python
  # apps/api/app/dependencies.py
  from fastapi import Depends
  from sqlalchemy.ext.asyncio import AsyncSession
  from app.database import get_db


  async def get_current_user(
      db: AsyncSession = Depends(get_db),
      # token: str = Depends(oauth2_scheme),  # Extract JWT from header
  ):
      # TODO: Decode JWT, find user in database
      pass
  ```

  Then use in routers:

  ```python
  @router.get("/{invoice_id}")
  async def get_invoice(
      invoice_id: UUID,
      db: AsyncSession = Depends(get_db),          # Injected database session
      user: User = Depends(get_current_user),       # Injected authenticated user
  ):
      # Now you have a database session and the current user
      result = await db.execute(
          select(Invoice).where(
              Invoice.id == invoice_id,
              Invoice.organization_id == user.organization_id,  # Access control
          )
      )
      invoice = result.scalar_one_or_none()
      if not invoice:
          raise HTTPException(status_code=404, detail="Invoice not found")
      return invoice
  ```

  ### Phase 2: Authentication Example

  Here's how `register` would look when implemented:

  ```python
  # apps/api/app/routers/auth.py

  from passlib.hash import argon2
  from app.database import get_db
  from app.models.user import User
  from app.models.organization import Organization

  @router.post("/register", response_model=UserResponse, status_code=201)
  async def register(
      user_data: UserCreate,
      db: AsyncSession = Depends(get_db),
  ):
      # 1. Check email uniqueness
      existing = await db.execute(select(User).where(User.email == user_data.email))
      if existing.scalar_one_or_none():
          raise HTTPException(status_code=409, detail="Email already registered")

      # 2. Hash password with Argon2
      password_hash = argon2.hash(user_data.password)

      # 3. Create organization (if name provided)
      org = Organization(name=user_data.organization_name or f"{user_data.email}'s org")
      db.add(org)
      await db.flush()  # Get the org.id

      # 4. Create user
      user = User(
          email=user_data.email,
          password_hash=password_hash,
          first_name=user_data.first_name,
          last_name=user_data.last_name,
          organization_id=org.id,
          role="admin",  # First user is admin
      )
      db.add(user)
      await db.commit()
      await db.refresh(user)

      # 5. TODO: Send verification email

      return user
  ```

  ### Phase 3: Invoice Upload Example

  ```python
  # apps/api/app/routers/invoices.py

  import uuid
  import boto3
  from app.database import get_db
  from app.models.invoice import Invoice

  @router.post("/upload", response_model=ProcessingStatus, status_code=202)
  async def upload_invoice(
      file: Annotated[UploadFile, File(...)],
      db: AsyncSession = Depends(get_db),
      user: User = Depends(get_current_user),
  ):
      # Validation (already implemented) ...

      # 1. Save file to S3/MinIO
      invoice_id = uuid.uuid4()
      document_path = f"organizations/{user.organization_id}/invoices/{invoice_id}/original{_get_extension(file.content_type)}"

      s3 = boto3.client("s3",
          endpoint_url=settings.storage_endpoint,
          aws_access_key_id=settings.storage_access_key,
          aws_secret_access_key=settings.storage_secret_key,
      )
      s3.put_object(
          Bucket=settings.storage_bucket,
          Key=document_path,
          Body=content,
          ContentType=file.content_type,
      )

      # 2. Create database record
      invoice = Invoice(
          id=invoice_id,
          organization_id=user.organization_id,
          status="processing",
          document_path=document_path,
      )
      db.add(invoice)
      await db.commit()

      # 3. Queue Celery task
      from ocr_worker.tasks import process_invoice
      process_invoice.delay(
          invoice_id=str(invoice_id),
          document_path=document_path,
          callback_url=callback_url,
          priority=priority,
      )

      # 4. Return immediately
      return ProcessingStatus(
          id=invoice_id,
          status="queued",
          progress=0,
          created_at=invoice.created_at,
      )
  ```

  ---

  ## 11. Common Development Tasks

  ### Add a New API Endpoint

  1. **Define schema** (if new data shape needed):
  ```python
  # apps/api/app/schemas/my_schema.py
  class MyResponse(BaseModel):
      id: UUID
      name: str
  ```

  2. **Add to router** (existing or new file):
  ```python
  # apps/api/app/routers/invoices.py
  @router.get("/stats")
  async def get_stats(db: AsyncSession = Depends(get_db)):
      result = await db.execute(text("SELECT COUNT(*) FROM invoices"))
      return {"total": result.scalar()}
  ```

  3. **If new router file**, register in `main.py`:
  ```python
  from app.routers import new_router
  app.include_router(new_router.router, prefix="/api/v1/new", tags=["New"])
  ```

  ### Add a New Frontend Page

  1. **Create the file** (path = URL):
  ```tsx
  // apps/web/src/app/dashboard/page.tsx
  export default function Dashboard() {
    return <h1>Dashboard</h1>
  }
  ```

  2. **Access at:** `http://localhost:3000/dashboard` (no registration needed)

  3. **For dynamic routes:**
  ```tsx
  // apps/web/src/app/invoices/[id]/page.tsx
  export default function InvoicePage({ params }: { params: { id: string } }) {
    return <h1>Invoice: {params.id}</h1>
  }
  // Access at: /invoices/abc-123
  ```

  ### Add a Python Dependency

  ```bash
  # 1. Edit pyproject.toml, add to dependencies array:
  #    "new-package>=1.0.0"

  # 2. Reinstall
  cd apps/api
  pip install -e ".[dev]"

  # 3. If it's for the ML package:
  cd packages/ml
  pip install -e ".[dev]"
  ```

  ### Add a Node.js Dependency

  ```bash
  # For the frontend
  cd apps/web
  npm install new-package

  # For root monorepo (dev tools like concurrently)
  npm install -D new-package    # at repo root
  ```

  ### Create a New Celery Task

  ```python
  # workers/ocr_worker/tasks.py

  @app.task(name="ocr_worker.tasks.new_task")
  def new_task(arg1: str, arg2: int):
      # Do work
      return {"result": "done"}
  ```

  Add routing in `celery_app.py`:
  ```python
  task_routes={
      "ocr_worker.tasks.new_task": {"queue": "default"},
  }
  ```

  Call from the API:
  ```python
  from ocr_worker.tasks import new_task
  new_task.delay("hello", 42)
  ```

  ---

  ## 12. Debugging Tips

  ### Check if Services are Running

  ```bash
  # Docker containers and their health
  docker compose -f infra/docker/docker-compose.yml ps

  # Expected output:
  # NAME                 STATUS          PORTS
  # fakturaai-postgres   Up (healthy)    0.0.0.0:5432->5432/tcp
  # fakturaai-redis      Up (healthy)    0.0.0.0:6379->6379/tcp
  # fakturaai-minio      Up (healthy)    0.0.0.0:9000-9001->9000-9001/tcp
  ```

  ### Test Database Connection

  ```bash
  # From your machine
  psql postgresql://fakturaai:fakturaai_dev@localhost:5432/fakturaai

  # From inside Docker
  docker exec -it fakturaai-postgres psql -U fakturaai -d fakturaai

  # Quick check
  docker exec fakturaai-postgres pg_isready -U fakturaai
  ```

  ### Test Redis Connection

  ```bash
  # Connect
  redis-cli -h localhost -p 6379

  # Test
  redis-cli PING        # Should return PONG

  # Check Celery queue
  redis-cli -n 1 LLEN celery            # Pending tasks in queue
  redis-cli -n 2 KEYS "*"               # Completed task results

  # Monitor all commands in real-time
  redis-cli MONITOR
  ```

  ### Test API Endpoints

  ```bash
  # Health check
  curl http://localhost:8000/health

  # API root
  curl http://localhost:8000/

  # With httpie (more readable)
  http GET localhost:8000/health
  http GET localhost:8000/api/v1/invoices

  # Upload file
  curl -X POST -F "file=@invoice.pdf" http://localhost:8000/api/v1/invoices/upload

  # Check Swagger docs (interactive)
  open http://localhost:8000/docs
  ```

  ### View Logs

  ```bash
  # Docker service logs
  docker compose -f infra/docker/docker-compose.yml logs -f api          # API logs
  docker compose -f infra/docker/docker-compose.yml logs -f ocr-worker   # Worker logs
  docker compose -f infra/docker/docker-compose.yml logs -f postgres     # DB logs

  # Follow multiple services
  docker compose -f infra/docker/docker-compose.yml logs -f api ocr-worker

  # Last 50 lines only
  docker compose -f infra/docker/docker-compose.yml logs --tail=50 api

  # When running locally (not in Docker)
  # API: output appears directly in terminal where you ran uvicorn
  # Worker: output appears in the celery terminal
  ```

  ### Common Issues

  | Problem | Cause | Fix |
  |---------|-------|-----|
  | `connection refused` on :5432 | PostgreSQL not running | `docker compose up -d postgres` |
  | CORS error in browser | Frontend calling wrong API URL | Check `NEXT_PUBLIC_API_URL` |
  | `relation "invoices" does not exist` | Tables not created | Run migrations or `Base.metadata.create_all()` |
  | Worker not picking up tasks | Worker not connected to same Redis | Check `CELERY_BROKER_URL` matches |
  | MinIO `Access Denied` | Wrong credentials or bucket missing | Check `STORAGE_ACCESS_KEY` and create bucket |
  | `ModuleNotFoundError: fakturaai_ml` | ML package not installed | `pip install -e packages/ml` |
  | Upload returns 415 | Wrong Content-Type header | Don't set Content-Type manually with FormData |

  ---

  ## 13. Project Status & What's Left

  ### What's Fully Implemented

  - Project structure and monorepo configuration
  - Frontend UI (landing page with animations, upload page, FileUpload component)
  - ML pipeline with dual OCR engines (dots.ocr + EasyOCR fallback)
  - Field extraction with Cyrillic + Latin regex patterns
  - PIB validation (mod-11 checksum)
  - Invoice math validation with tolerance rules
  - Celery task queue configuration and task definitions
  - Docker Compose development stack (7 services)
  - Pydantic schemas for all API request/response shapes
  - API routing structure with validation logic
  - Type definitions (dataclasses for ML, Pydantic for API)

  ### What's Partially Implemented

  - API endpoints (routing and validation done, business logic returns 501)
  - Webhook handlers (Stripe signature verification code exists but is commented out)
  - Worker helper functions (`_download_document` works, `_save_extraction_result` is a stub)

  ### What's Not Yet Implemented

  | Feature | Files to Create/Edit | Depends On |
  |---------|---------------------|------------|
  | SQLAlchemy models | `app/models/*.py` | Nothing |
  | Database connection pool | `app/database.py`, `app/main.py` | Models |
  | Alembic migrations | `alembic/` directory | Models |
  | User registration | `app/routers/auth.py` | Models, database |
  | Login / JWT tokens | `app/routers/auth.py`, `app/auth.py` | Models, database |
  | Auth middleware | `app/dependencies.py` | JWT logic |
  | S3 storage service | `app/services/storage.py` | Settings |
  | Invoice upload (full) | `app/routers/invoices.py` | Auth, storage, Celery |
  | Invoice CRUD | `app/routers/invoices.py` | Auth, models |
  | Processing status | `app/routers/invoices.py` | Celery result backend |
  | Export (XLSX/CSV/JSON) | `app/routers/export.py` | Models, storage |
  | Audit export | `app/routers/export.py` | Models, storage |
  | PDV books (KPR/KIR) | `app/routers/export.py`, `app/services/export/pdv_books.py` | AccountingIntent, plans |
  | Stripe webhooks | `app/routers/webhooks.py` | Stripe SDK |
  | APR company lookup | `app/services/apr.py` | httpx, Redis cache |
  | Tests | `tests/` directory | All of the above |
  | Frontend API integration | `src/components/*.tsx` | Backend endpoints |

  ---

  ## Quick Reference

  ### Commands

  | What | Command |
  |------|---------|
  | **Setup (first time)** | `./scripts/setup-dev.sh` |
  | Start infrastructure | `docker compose -f infra/docker/docker-compose.yml up -d postgres redis minio` |
  | Start everything (Docker) | `docker compose -f infra/docker/docker-compose.yml up -d` |
  | Start backend (local) | `cd apps/api && source ../../.venv/bin/activate && uvicorn app.main:app --reload` |
  | Start frontend (local) | `cd apps/web && npm run dev` |
  | Start both (local) | `npm run dev:all` (requires infrastructure running) |
  | Start worker (local) | `cd workers/ocr_worker && celery -A celery_app worker -l info` |
  | Stop everything | `docker compose -f infra/docker/docker-compose.yml down` |
  | Stop + delete data | `docker compose -f infra/docker/docker-compose.yml down -v` |
  | View API docs | http://localhost:8000/docs |
  | View Celery tasks | http://localhost:5555 |
  | View MinIO console | http://localhost:9001 |
  | Run Python linter | `cd apps/api && ruff check .` |
  | Run frontend linter | `cd apps/web && npm run lint` |
  | Rebuild Docker images | `docker compose -f infra/docker/docker-compose.yml build` |
  | DB shell | `docker exec -it fakturaai-postgres psql -U fakturaai -d fakturaai` |
  | Redis shell | `docker exec -it fakturaai-redis redis-cli` |

  ### Ports

  | Port | Service | Notes |
  |------|---------|-------|
  | 3000 | Next.js frontend | Landing page, upload UI |
  | 8000 | FastAPI backend | API + Swagger docs at /docs |
  | 5432 | PostgreSQL | Database |
  | 6379 | Redis | Cache (DB 0), Celery broker (DB 1), Celery results (DB 2) |
  | 9000 | MinIO S3 API | S3-compatible document storage |
  | 9001 | MinIO Console | Web UI for browsing stored files |
  | 5555 | Flower | Celery task monitoring dashboard |

  ### Key Files to Know

  | When you want to... | Look at... |
  |---------------------|------------|
  | Add/change an API endpoint | `apps/api/app/routers/*.py` |
  | Add/change request/response shapes | `apps/api/app/schemas/*.py` |
  | Change configuration defaults | `apps/api/app/config.py` |
  | Change environment variables | `infra/docker/.env.example` |
  | Understand the OCR pipeline | `packages/ml/fakturaai_ml/pipeline.py` |
  | Add regex patterns for extraction | `packages/ml/fakturaai_ml/extraction/fields.py` |
  | Add validation rules | `packages/ml/fakturaai_ml/validation/*.py` |
  | Modify Celery task behavior | `workers/ocr_worker/tasks.py` |
  | Change Docker services | `infra/docker/docker-compose.yml` |
  | Add a frontend page | `apps/web/src/app/<route>/page.tsx` |
  | Add a React component | `apps/web/src/components/<Name>.tsx` |
