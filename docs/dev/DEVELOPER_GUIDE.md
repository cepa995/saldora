# Saldora Developer Guide

A practical, hands-on guide to working with the Saldora codebase as it actually exists today.

Saldora (formerly faktura-ai) is an **intelligence layer for Serbian accounting agencies whose clients are hospitality businesses** — restaurants, cafes, bars, fast food. The wedge is OCR on paper invoices with many line items plus generation of legally-required Serbian hospitality forms (kalkulacije, šank lista, KEP, popis). Saldora is the pipeline; MiniMax stays the general ledger.

This guide is for developers contributing to the codebase. For architectural decisions and trade-offs read [`architecture.md`](./architecture.md). For production operations read [`DEPLOYMENT.md`](./DEPLOYMENT.md). For the formal requirements (and the hospitality thesis in §1) read [`../product/SRS.md`](../product/SRS.md). For the milestone roadmap read [`../product/IMPLEMENTATION_GUIDE.md`](../product/IMPLEMENTATION_GUIDE.md). For conventions specifically aimed at Claude / AI assistants read [`/CLAUDE.md`](../../CLAUDE.md).

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Where to Find What](#where-to-find-what)
3. [Project Structure Overview](#project-structure-overview)
4. [The Monorepo](#the-monorepo)
5. [Docker in This Project](#docker-in-this-project)
6. [Environment Variables](#environment-variables)
7. [Subscription Approval Gate](#subscription-approval-gate)
8. [Backend (FastAPI)](#backend-fastapi)
9. [Frontend (Next.js)](#frontend-nextjs)
10. [Client-First UI](#client-first-ui)
11. [Data Model](#data-model)
12. [Plans and Feature Gating](#plans-and-feature-gating)
13. [The OCR / ML Pipeline](#the-ocr--ml-pipeline)
14. [Modal Deployment for OCR](#modal-deployment-for-ocr)
15. [Celery: Async Task Processing](#celery-async-task-processing)
16. [Service Topology](#service-topology)
17. [Testing](#testing)
18. [Issue Workflow and Conventions](#issue-workflow-and-conventions)
19. [Common Development Tasks](#common-development-tasks)
20. [Debugging Tips](#debugging-tips)
21. [Production Deployment](#production-deployment)
22. [Dropped and Deferred Milestones](#dropped-and-deferred-milestones)
23. [Quick Reference](#quick-reference)

---

## Quick Start

### Option A: Automated setup (recommended)

```bash
./scripts/setup-dev.sh
```

The script:

- Checks prerequisites (Node.js 22+, Python 3.12, Docker)
- Installs Node.js and Python dependencies
- Creates `.venv/` at the repo root
- Copies `.env.example` to `.env`
- Starts PostgreSQL, Redis, MinIO via Docker
- Creates the MinIO storage bucket

### Option B: Manual setup

```bash
# 1. Install dependencies
npm install
cd apps/web && npm install && cd ../..
python3 -m venv .venv
source .venv/bin/activate
pip install -e "packages/ml[dev]"
pip install -e "apps/api[dev]"

# 2. Start infrastructure
docker compose -f infra/docker/docker-compose.yml up -d postgres redis minio

# 3. Run migrations against the dev DB
cd apps/api
alembic upgrade head

# 4. Backend (terminal 1)
uvicorn app.main:app --reload --port 8000

# 5. Frontend (terminal 2)
cd apps/web && npm run dev

# 6. Worker (terminal 3, optional unless you want to process invoices)
cd workers/ocr_worker
celery -A celery_app worker --loglevel=info --queues=ocr
```

### Option C: Everything in Docker

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

### Access points

| Service                 | URL                                            |
| ----------------------- | ---------------------------------------------- |
| Frontend                | http://localhost:3000                          |
| Backend API             | http://localhost:8000                          |
| Swagger Docs            | http://localhost:8000/docs                     |
| ReDoc                   | http://localhost:8000/redoc                    |
| MinIO API               | http://localhost:9010                          |
| MinIO Console           | http://localhost:9011 (minioadmin/minioadmin)  |
| Flower (Celery monitor) | http://localhost:5555                          |
| PostgreSQL              | localhost:5433 (user `saldora`, db `saldora`)  |
| Redis                   | localhost:6379                                 |

Note: PostgreSQL is exposed on **5433**, not 5432, to avoid conflicts with a local Postgres install. MinIO is on 9010/9011 for the same reason. If you see "connection refused on 5432", that's why.

---

## Where to Find What

| Doc                                    | What it covers                                               |
| -------------------------------------- | ------------------------------------------------------------ |
| `docs/product/SRS.md`                  | Formal Software Requirements Specification (English, ~4.8k lines). §1 carries the hospitality thesis; §4.17 lists dropped features. |
| `docs/product/SRS_sr.md`               | SRS in Serbian Latin                                         |
| `docs/product/SRS_sr_simple.md`        | Business-friendly Serbian version                            |
| `docs/product/IMPLEMENTATION_GUIDE.md` | Milestone breakdown (M1 → M21), post-pivot table             |
| `docs/product/M20_accountant_meeting_agenda.md` | Pre-meeting strawman for the hospitality forms work |
| `docs/dev/DEVELOPER_GUIDE.md`          | This file                                                    |
| `docs/dev/DEPLOYMENT.md`               | Production architecture and ops runbook                      |
| `docs/dev/architecture.md`             | Architectural decisions and trade-offs                       |
| `docs/dev/AUTOMATION_RULES.md`         | Rules engine reference                                       |
| `docs/dev/ML_PROJECT_ARCHITECTURE_GUIDE.md` | ML pipeline architecture                                |
| `docs/user-experience/workflows.md`    | Click-by-click reference of every supported workflow         |
| `CLAUDE.md`                            | Conventions specifically for Claude / AI assistants          |

If you only have time to read three: this guide, `architecture.md`, and CLAUDE.md.

---

## Project Structure Overview

```
faktura-ai/
├── apps/
│   ├── api/                  # FastAPI backend (Python 3.12)
│   │   ├── app/              # main.py, config.py, database.py, auth.py,
│   │   │                     # dependencies.py, plans.py, security.py,
│   │   │                     # middleware.py, routers/, models/,
│   │   │                     # schemas/, services/
│   │   ├── alembic/          # 17 migrations, current head 0017
│   │   ├── tests/            # pytest, asyncio_mode="auto"
│   │   └── pyproject.toml
│   └── web/                  # Next.js 16, TypeScript strict
│       └── src/
│           ├── app/
│           │   ├── (app)/[orgSlug]/    # Org-scoped pages
│           │   ├── (auth)/             # login, register, awaiting-approval, …
│           │   ├── politika-privatnosti/, uslovi-koriscenja/, verify-email/
│           │   └── page.tsx            # Landing
│           ├── components/, contexts/, lib/, i18n/
├── packages/
│   └── ml/                   # `fakturaai-ml` (legacy distribution name)
│       └── fakturaai_ml/     # pipeline.py, ocr/, extraction/, validation/, types.py
├── workers/
│   ├── ocr_worker/           # celery_app.py, tasks.py
│   └── Dockerfile
├── infra/
│   ├── docker/               # docker-compose.yml, docker-compose.prod.yml, Caddyfile
│   └── modal/dots_ocr.py     # Modal deployment for the OCR VLM
├── scripts/
│   ├── setup-dev.sh
│   ├── admin_orgs.py         # Approve / change-plan an org (manual gate)
│   ├── seed_test_data.py
│   └── generate_test_invoices.py
├── docs/                     # See "Where to Find What"
├── CLAUDE.md
└── package.json              # Monorepo root (npm workspaces)
```

---

## The Monorepo

### npm workspaces

Root `package.json` declares `apps/*` and `packages/*` as workspaces. npm only manages the JS/TS packages. The Python packages live under `apps/api`, `packages/ml`, and `workers/ocr_worker` and are managed by `pip` and `pyproject.toml`. Convenience scripts at the root (`npm run dev:api`) shell out to Python tools.

### Python package linkage

```
packages/ml/pyproject.toml           → installable as "fakturaai-ml"
                                       (package name kept legacy; module
                                       directory is `fakturaai_ml`)
apps/api/pyproject.toml              → installable as "saldora-api"
workers/ocr_worker/                  → imports from fakturaai_ml directly
```

`pip install -e packages/ml` registers `fakturaai_ml` as an importable package, and the worker can `from fakturaai_ml import InvoicePipeline`. The `-e` flag means changes to source are immediately reflected without reinstalling.

> The package distribution name (`fakturaai-ml`) is a leftover from the rename; the import path (`fakturaai_ml`) is what code uses. We have not renamed it because nothing breaks and migrations are not free.

### pyproject.toml essentials

The API's `pyproject.toml` declares the production deps (fastapi, uvicorn, pydantic, sqlalchemy 2.0, asyncpg, alembic, redis, celery, boto3, python-jose, passlib[argon2], httpx, anthropic, slowapi, resend) and a `[dev]` extra (pytest, pytest-asyncio, ruff). `[tool.pytest.ini_options]` sets `asyncio_mode = "auto"`.

Common commands:

```bash
pip install -e ".[dev]"    # Install with dev dependencies
ruff check .               # Lint
ruff format .              # Auto-format
pytest -x                  # Run tests, stop at first failure
```

---

## Docker in This Project

### Why Docker

Saldora depends on PostgreSQL, Redis, MinIO, Python 3.12, Node 22, and (in prod) a CUDA GPU on Modal. Docker normalizes that across machines.

### Concepts at a glance

| Concept              | What it means here                                                   |
| -------------------- | -------------------------------------------------------------------- |
| **Image**            | Snapshot of OS + software (`postgres:16-alpine`, `node:22-alpine`)   |
| **Container**        | Running instance (`saldora-postgres`, `saldora-api`)                 |
| **Volume**           | Persistent storage that survives restarts (`postgres_data`)          |
| **Dockerfile**       | Recipe for building a custom image                                   |
| **docker-compose**   | Defines multiple services and how they connect                       |
| **Health check**     | Command Docker runs to check if a service is ready                   |
| **Network**          | Internal DNS so containers talk to each other by name                |

### Local dev compose at a glance

The dev `docker-compose.yml` defines: `postgres` (port 5433), `redis` (6379), `minio` (9010 API, 9011 console), `api` (8000), `web` (3000), `dots-ocr-server` (only useful with a local GPU), `ocr-worker`, `flower` (5555). All containers use the `saldora-*` naming convention. The full file is at `infra/docker/docker-compose.yml` — read it directly for the source of truth.

A `dots-ocr-server` service exists for engineers with a local GPU, but **production runs the OCR VLM on Modal**, not on the VPS. See [Modal Deployment for OCR](#modal-deployment-for-ocr).

### Three ways to run the project

| Approach                | Infrastructure       | API           | Frontend     | Best for                          |
| ----------------------- | -------------------- | ------------- | ------------ | --------------------------------- |
| **Hybrid (recommended)** | Docker               | Local Python  | Local Node   | Day-to-day. Best debugging.       |
| **Full Docker**         | Docker               | Docker        | Docker       | Testing builds, CI                |
| **Minimal Docker**      | Docker (pg+redis+s3) | Local Python  | Local Node   | Fastest iteration                 |

```bash
# Hybrid
docker compose -f infra/docker/docker-compose.yml up -d postgres redis minio
npm run dev:all
```

### localhost vs container names

**Rule:** Inside Docker → container names (`postgres`, `redis`, `minio`, `api`, `web`). Browser or host shell → `localhost` with the published port (`localhost:5433`, `localhost:6379`, `localhost:9010`, `localhost:8000`, `localhost:3000`).

The one exception is `NEXT_PUBLIC_API_URL`. It's baked into the JS bundle at build time and runs in the **browser**, so it always points at `http://localhost:8000` (or the public API hostname in prod), never at `api:8000`.

### Common Docker commands

```bash
# Start / stop
docker compose -f infra/docker/docker-compose.yml up -d
docker compose -f infra/docker/docker-compose.yml down
docker compose -f infra/docker/docker-compose.yml down -v   # also delete volumes

# Logs
docker compose -f infra/docker/docker-compose.yml logs -f api
docker compose -f infra/docker/docker-compose.yml logs -f --tail=50 ocr-worker

# Status
docker compose -f infra/docker/docker-compose.yml ps

# Shells
docker exec -it saldora-postgres psql -U saldora -d saldora
docker exec -it saldora-redis redis-cli
docker exec -it saldora-api bash

# Rebuild
docker compose -f infra/docker/docker-compose.yml build api
docker compose -f infra/docker/docker-compose.yml up -d --build
```

---

## Environment Variables

`apps/api/app/config.py` defines `Settings` (Pydantic). Priority: env var → `.env` → default.

### Application

| Variable          | Default              | Description                                                        |
| ----------------- | -------------------- | ------------------------------------------------------------------ |
| `ENVIRONMENT`     | `development`        | One of `development`, `staging`, `production`. Hides Swagger in prod. |
| `DEBUG`           | `false`              | Debug mode                                                          |
| `APP_NAME`        | `Saldora API`        |                                                                    |
| `APP_VERSION`     | `0.1.0`              |                                                                    |
| `HOST`            | `0.0.0.0`            |                                                                    |
| `PORT`            | `8000`               |                                                                    |

### Database

| Variable                  | Default                                                                       |
| ------------------------- | ----------------------------------------------------------------------------- |
| `DATABASE_URL`            | `postgresql+asyncpg://saldora:saldora_dev@localhost:5433/saldora`             |
| `DATABASE_POOL_SIZE`      | `20`                                                                          |
| `DATABASE_MAX_OVERFLOW`   | `10`                                                                          |

The `+asyncpg` dialect tells SQLAlchemy to use the async driver. Migrations also run through asyncpg via Alembic's `async` env.

### Redis

| Variable                | Default                       |
| ----------------------- | ----------------------------- |
| `REDIS_URL`             | `redis://localhost:6379/0`    |
| `CELERY_BROKER_URL`     | `redis://localhost:6379/1`    |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2`    |

### JWT

| Variable                              | Default                  | Description                                |
| ------------------------------------- | ------------------------ | ------------------------------------------ |
| `JWT_SECRET_KEY`                      | `change-me-in-production`| **Must change** in staging/prod. Generate with `openssl rand -hex 32`. |
| `JWT_ALGORITHM`                       | `HS256`                  |                                            |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`     | `60`                     |                                            |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS`       | `7`                      |                                            |

### Storage (R2 in prod, MinIO locally)

| Variable                  | Default               | Description                                                     |
| ------------------------- | --------------------- | --------------------------------------------------------------- |
| `STORAGE_ENDPOINT`        | `None`                | MinIO: `http://minio:9000`. R2: `https://<acct>.r2.cloudflarestorage.com`. |
| `STORAGE_PUBLIC_ENDPOINT` | `None`                | URL the browser uses to fetch presigned objects (for MinIO this is `http://localhost:9010`). |
| `STORAGE_BUCKET`          | `saldora-documents`   |                                                                 |
| `STORAGE_ACCESS_KEY`      | `""`                  | MinIO: `minioadmin`                                              |
| `STORAGE_SECRET_KEY`      | `""`                  |                                                                 |
| `STORAGE_REGION`          | `auto`                |                                                                 |

### Email (Resend)

| Variable             | Default                 | Description                                                       |
| -------------------- | ----------------------- | ----------------------------------------------------------------- |
| `RESEND_API_KEY`     | `""`                    | Empty disables email sending (dev default)                        |
| `RESEND_FROM_EMAIL`  | `noreply@saldora.rs`    |                                                                   |
| `FRONTEND_URL`       | `http://localhost:3000` | Used in email links                                               |
| `ADMIN_EMAIL`        | `""`                    | Receives `new_org_registered` notifications. Empty = disabled.    |

Email templates and senders live in `apps/api/app/services/email.py`. Currently active senders:

- `send_invitation_email` — team invites
- `send_verification_email` — email verification
- `send_welcome_email`
- `send_password_reset_email`
- `send_admin_new_org_email` — fires on `/auth/create-organization` so the admin knows to approve the new org
- `send_archive_email` — monthly archive ZIP delivery

> The old `send_invoice_processed_email` was removed in PR #212. Per-invoice email notifications were noisy and not what agencies wanted; events show up in the client timeline now.

### Anthropic (LLM extraction)

| Variable               | Default                         | Description                                       |
| ---------------------- | ------------------------------- | ------------------------------------------------- |
| `ANTHROPIC_API_KEY`    | `""`                            |                                                   |
| `ANTHROPIC_MODEL`      | `claude-haiku-4-5-20251001`     | Used for structured field extraction              |
| `LLM_EXTRACTION_ENABLED` | `true` (worker)               | Set to `false` to disable LLM and rely on regex   |

### Billing

Saldora currently bills **manually**: agencies receive an invoice from us out-of-band (email PDF), pay by bank transfer, and `scripts/admin_orgs.py` flips their `Organization.subscription_status` to `active` (or `trial` on first month) and extends the subscription period. There is no third-party payment processor integration today.

- No env vars needed for billing — there's nothing to authenticate.
- The `apps/api/app/routers/billing.py` router serves read-only "your plan / your usage" views to the agency.
- A future automated billing rail (whatever it turns out to be — see `architecture.md` §3.3) will write to `Organization.subscription_status`, `plan`, and `subscription_canceled_at`. Stripe remains unavailable for Serbian merchants; Paddle was scoped earlier but not adopted.

> **Do not add Stripe.** Stripe is not available to Serbian businesses. Any automated-billing work has to start from a Serbia-friendly rail.

### NBS exchange rates

| Variable                    | Default                            |
| --------------------------- | ---------------------------------- |
| `NBS_API_URL`               | `https://kurs.resenje.org/api/v1`  |
| `NBS_CACHE_TTL`             | `86400`                            |
| `NBS_REQUEST_TIMEOUT`       | `10`                               |
| `NBS_SUPPORTED_CURRENCIES`  | `["EUR","USD","CHF","GBP"]`        |

### OCR

| Variable                      | Default                                       |
| ----------------------------- | --------------------------------------------- |
| `OCR_CONFIDENCE_THRESHOLD`    | `0.80`                                        |
| `OCR_MAX_FILE_SIZE_MB`        | `20`                                          |
| `OCR_SUPPORTED_FORMATS`       | `["pdf","png","jpg","jpeg","tiff","webp"]`    |
| `DOTS_OCR_SERVER_URL`         | dev: `http://dots-ocr-server:8000/v1`. prod: Modal endpoint. |
| `DOTS_OCR_MODEL_NAME`         | `model`                                       |
| `DOTS_OCR_API_KEY`            | bearer for the Modal endpoint                 |

### Frontend

| Variable                | Default                | Description                          |
| ----------------------- | ---------------------- | ------------------------------------ |
| `NEXT_PUBLIC_API_URL`   | `http://localhost:8000`| Baked into the JS bundle at build time |

### Misc

| Variable      | Default | Description                                 |
| ------------- | ------- | ------------------------------------------- |
| `SENTRY_DSN`  | `None`  | Error tracking. `None` = disabled.          |
| `TESTING`     | unset   | Set to `1` only by the test fixtures. See [Testing](#testing). |

### Example `.env` for local dev

```bash
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=postgresql+asyncpg://saldora:saldora_dev@localhost:5433/saldora
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
STORAGE_ENDPOINT=http://localhost:9010
STORAGE_PUBLIC_ENDPOINT=http://localhost:9010
STORAGE_ACCESS_KEY=minioadmin
STORAGE_SECRET_KEY=minioadmin
STORAGE_BUCKET=saldora-documents
JWT_SECRET_KEY=change-me-locally
ANTHROPIC_API_KEY=sk-ant-...        # for LLM extraction
RESEND_API_KEY=                     # empty disables email sending
ADMIN_EMAIL=you@example.com         # receives new-org notifications
PADDLE_API_KEY=                     # empty unless testing checkout
```

---

## Subscription Approval Gate

Self-service registration is **gated** until an admin approves the org. There is no card-on-file flow today.

### Lifecycle

```
1. User submits /auth/register      → User row created (no organization yet)
2. User submits /auth/create-org    → Organization created with
                                       subscription_status = "pending"
                                       (in tests: "active" — see below)
                                     → send_admin_new_org_email() fires to ADMIN_EMAIL
3. User attempts to use the app     → require_role gate inspects org.subscription_status
                                       and 403s with code `subscription_pending_approval`
                                       if not in {"active", "trial"}
4. Frontend AuthContext sees the    → Routes user to /awaiting-approval
   subscription_status              → That page polls /auth/refresh until status flips
5. Admin runs admin_orgs.py         → Picks env, picks org, picks new status, picks plan
6. Admin script flips Postgres      → subscription_status = "active", plan = "starter"
7. User clicks "Check status"       → refreshUser() fetches new claims, redirect to dashboard
```

### Where it lives in code

- `apps/api/app/dependencies.py::require_role` — the actual gate. Checks `subscription_status` against `APPROVED_SUBSCRIPTION_STATUSES = {"active", "trial"}`.
- `apps/api/app/routers/auth.py::_initial_subscription_status` — sets `"pending"` normally, `"active"` when `TESTING=1`. This is intentional: tests should not be re-wired around the gate.
- `apps/api/app/services/email.py::send_admin_new_org_email` — admin notification.
- `apps/web/src/app/(auth)/awaiting-approval/page.tsx` — the landing page for pending users.
- `apps/web/src/contexts/AuthContext.tsx` — handles the redirect.
- `scripts/admin_orgs.py` — interactive CLI to flip status and plan.

### Approving an org

```bash
# Local stack (uses the saldora-postgres container directly)
python scripts/admin_orgs.py
# select "staging"  → pick org → set status to "active" → pick plan tier

# Production (SSHes into the Hetzner box)
python scripts/admin_orgs.py
# select "production" → pick org → set status → pick plan tier
```

The script prompts for both `subscription_status` (active / trial / pending / canceled) and a plan tier (`free / starter / pro / agency`). It's safe to run repeatedly; it just shows the current state and lets you pick a new one.

---

## Backend (FastAPI)

### Entry point: `apps/api/app/main.py`

The lifespan handler verifies DB, Redis, and storage connectivity at startup; the app shuts those down on exit. CORS allows `localhost:3000` and the production hostnames (`saldora.rs`, `www.saldora.rs`, `saldora.ai`, `www.saldora.ai`). Three middlewares run on every request:

- `SecurityHeadersMiddleware` — adds standard security headers
- `RequestContextMiddleware` — captures IP + User-Agent for audit logging
- `CORSMiddleware` — handles cross-origin

Sentry is initialized only when `SENTRY_DSN` is set. Swagger / ReDoc are served at `/docs` and `/redoc` only in development.

### Mounted routers (21 total)

| Prefix                          | Router                | Purpose                                                    |
| ------------------------------- | --------------------- | ---------------------------------------------------------- |
| `/api/v1/auth`                  | `auth.py`             | Register, login, refresh, logout, password reset, create-org |
| `/api/v1/api-keys`              | `api_keys.py`         | `sk_live_*` API keys for programmatic access               |
| `/api/v1/invoices`              | `invoices.py`         | Upload, batch upload, CRUD, status, verify                 |
| `/api/v1/export`                | `export.py`           | XLSX, CSV, JSON, MiniMax XML, audit ZIP                    |
| `/api/v1/webhooks`              | `webhooks.py`         | Reserved for future billing webhooks (not wired up today)  |
| `/api/v1/audit-logs`            | `audit_logs.py`       | Audit log queries                                          |
| `/api/v1/analytics`             | `analytics.py`        | Dashboard analytics                                        |
| `/api/v1/rules`                 | `rules.py`            | AutomationRule CRUD + per-client associations              |
| `/api/v1/clients`               | `clients.py`          | Client CRUD + `/clients/{id}/events` (timeline)            |
| `/api/v1/portfolio`             | `portfolio.py`        | Portfolio view (agency-wide health grid)                   |
| `/api/v1/billing`               | `billing.py`          | Read-only "your plan / usage" views (billing itself is manual — see Env Vars → Billing) |
| `/api/v1/organizations`         | `organizations.py`    | Org settings                                               |
| `/api/v1/users`                 | `users.py`            | Current user profile                                       |
| `/api/v1/team`                  | `team.py`             | Team members within an org                                 |
| `/api/v1/invitations`           | `invitations.py`      | Invite a user to an org                                    |
| `/api/v1/join-requests`         | `join_requests.py`    | Request to join an existing org                            |
| `/api/v1/exchange-rates`        | `exchange_rates.py`   | NBS rates lookup                                           |
| `/api/v1/compliance`            | `compliance.py`       | ZZPL: consent records, deletion requests, DPAs             |
| `/api/v1/reports`               | `reports.py`          | Reports (currently minimal; hospitality forms TBD)         |
| `/api/v1/archive`               | `archive.py`          | Period archives for tax inspection (10-year retention)     |
| `/api/v1/products`              | `products.py`         | Product catalog (pg_trgm fuzzy match for line items)       |

### Configuration: `apps/api/app/config.py`

`Settings(BaseSettings)` from Pydantic. Loads from env → `.env` → defaults. `extra="ignore"` so unknown env vars don't crash. `get_settings()` is `@lru_cache`d so settings load once per process.

```python
from app.config import get_settings
settings = get_settings()
```

### Authentication

Two mechanisms, both routed through `get_current_user` in `dependencies.py`:

1. **JWT Bearer** (`Authorization: Bearer <token>`) — primary, used by the web UI.
2. **API key** (`X-API-Key: sk_live_...`) — for programmatic clients. Keys are stored as Argon2 hashes in `api_keys`; only the first 8 chars after `sk_live_` are stored in plaintext as a lookup prefix. `last_used_at` is updated per request.

Login returns access + refresh tokens. Logout adds the JWT's `jti` to a Redis blacklist (`is_token_blacklisted` in `app/security.py`). The refresh endpoint also re-reads the org's current `subscription_status` so the UI flips off the awaiting-approval screen as soon as the admin approves.

### Role hierarchy

```python
ROLE_HIERARCHY = {"admin": 4, "manager": 3, "operator": 2, "viewer": 1}
```

`require_role("manager")` allows admin or manager. It also enforces:

- The user belongs to an organization.
- The org's `subscription_status` is in `{"active", "trial"}`.

If the subscription gate fails, the response is:

```json
{
  "detail": {
    "code": "subscription_pending_approval",
    "message": "Vaš nalog čeka odobrenje administratora. ...",
    "subscription_status": "pending"
  }
}
```

The frontend keys off `code` to render `/awaiting-approval`.

### Quotas and feature gates

`require_feature(Feature.MINIMAX_DIRECT_PUSH)` — checks the org's plan includes the feature. Returns a structured 403 with `code: "feature_unavailable"` and `required_plan` so the UI can render an upgrade CTA.

`check_invoice_quota()` — checks the org's monthly invoice count. 402 with `code: "invoice_limit_exceeded"` when the limit is hit.

`check_member_quota()` — counts active members + pending invites against `plan.user_limit`. 402 with `code: "member_limit_exceeded"`.

### Schemas

Pydantic v2 models in `apps/api/app/schemas/`. Validate input, document the API in Swagger, serialize output. **Use `Decimal` for money — never `float`.** Use `model_config = {"from_attributes": True}` to construct response models directly from SQLAlchemy ORM rows.

### Database access

`apps/api/app/database.py` exports `engine` and `get_db`. Endpoints inject the session: `db: AsyncSession = Depends(get_db)`. All queries are async — `await db.execute(select(Invoice).where(...))`.

### Storage (sync boto3 from async context)

`apps/api/app/services/storage.py` is sync (boto3 has no first-class async client). Async callers wrap calls:

```python
import asyncio
url = await asyncio.to_thread(generate_presigned_url, key)
```

S3 keys follow the multi-tenant pattern:

```
organizations/{org_id}/invoices/{invoice_id}/original.{ext}
organizations/{org_id}/exports/{export_id}.zip
organizations/{org_id}/archives/{period}.zip
```

### Celery dispatch

To avoid pulling heavy ML deps into the API image, the API never imports `ocr_worker.tasks`. It dispatches by name:

```python
from celery import current_app as celery
celery.send_task(
    "ocr_worker.tasks.process_invoice",
    args=[str(invoice.id), s3_key],
    queue="ocr",
)
```

The worker image has the ML deps; the API image stays slim.

---

## Frontend (Next.js)

Next.js 16, App Router, TypeScript strict mode, Tailwind v4. All UI text is in **Serbian Latin script**. ESLint + Prettier run via pre-commit.

### Route groups

```
src/app/
├── layout.tsx              # Root layout (Inter font, SR locale, providers)
├── page.tsx                # Public landing page
├── (auth)/                 # Auth route group — public pages
│   ├── layout.tsx
│   ├── login/
│   ├── register/
│   ├── password-reset/
│   ├── invite/
│   └── awaiting-approval/  # Subscription pending gate
├── (app)/[orgSlug]/        # Authenticated, org-scoped pages
│   ├── layout.tsx          # Sidebar, AuthContext guard, ClientContext
│   ├── page.tsx            # Default → redirects to dashboard
│   ├── dashboard/
│   ├── klijenti/
│   │   ├── page.tsx        # Client list
│   │   └── [clientId]/
│   │       └── page.tsx    # Client workspace (Timeline / Fakture / Izveštaji / Pravila)
│   ├── invoices/           # Global invoice list (kept; used from inside client workspace)
│   ├── rules/
│   ├── billing/
│   ├── settings/
│   ├── templates/
│   ├── upload/
│   ├── arhiviranje/
│   └── pdv-knjige/
├── politika-privatnosti/   # ZZPL privacy policy
├── uslovi-koriscenja/      # Terms of service
└── verify-email/
```

`(auth)` and `(app)` are route groups (parentheses): they don't add a URL segment, just let us share a layout among siblings. The `[orgSlug]` segment scopes the entire app shell to the current org so deep links resurvive a refresh.

### Server vs Client components

Server components are the App Router default; they can only fetch data and render. Client components opt in with `'use client'` at the top of the file and gain `useState`, `useEffect`, browser APIs.

Most of Saldora's interactive surfaces are client components (`AuthContext`, `ClientContext`, list views with filters). Static content (landing page, marketing pages, terms/privacy) stays server-rendered.

### Auth flow

`AuthContext` (in `src/contexts/AuthContext.tsx`) holds `{ user, isAuthenticated, isLoading }`. It:

- Reads the access token from `localStorage` on boot.
- Calls `/api/v1/auth/refresh` to get fresh user claims (orgSlug, role, subscriptionStatus).
- Routes the user based on those claims:
  - No org → `/register/organization`.
  - Org with `subscription_status` in `{"pending","canceled","expired",null}` → `/awaiting-approval`.
  - Otherwise → `/{orgSlug}/dashboard` if currently on an auth page.

The `/awaiting-approval` page has a "Check status" button that calls `refreshUser()`. Once the admin runs `admin_orgs.py`, the next refresh sees the new status and AuthContext routes the user into the app.

### Styling

Tailwind v4 with the `@tailwindcss/postcss` plugin. Utility-first; `globals.css` holds the few CSS variables we need.

---

## Client-First UI

The app is **client-first**, not feature-first. The primary axis of work is the client (one restaurant), not the feature (invoices, rules). An accountant with thirty restaurants picks one, does everything inside that restaurant's workspace, then moves on.

### Three surfaces

1. **Portfolio view (`/{orgSlug}/pregled`)** — agency-wide home. Grid of all clients with health indicators (invoices pending review, blocked, last activity). Click a card → open that client's workspace. Backend: `GET /api/v1/portfolio`.

2. **Client workspace (`/{orgSlug}/klijenti/{clientId}`)** — single-page surface for one client. Header with name + PIB + activity details + month navigation. Tabs:
   - **Hronologija** (Timeline) — default. Renders `client_events` for the current period. Backend: `GET /api/v1/clients/{id}/events?period=YYYY-MM`.
   - **Fakture** — invoice list pre-scoped to this client.
   - **Izveštaji** — reports pre-scoped to this client. Today minimal; hospitality forms (kalkulacije, šank lista, KEP, popis) land here after the accountant meeting.
   - **Pravila** — rules associated with this client via `rule_client_associations`, plus a "create rule for this client" CTA.

3. **Sidebar** — two sections:
   - *Client workspace*: Pregled portfelja, Klijenti (flat list)
   - *Agency operations*: Pravila (org-wide), Arhiviranje, Katalog proizvoda, Dashboard, Podešavanja, Team, Billing

   No top-level **Fakture** or **Izveštaji** entry — both are client-scoped and live inside the workspace.

### Event log: the mechanism behind the timeline

`client_events` is an append-only table written whenever something touches a client. The emitter lives at `apps/api/app/services/events.py::emit`. Events are emitted in the same DB transaction as the business operation — `emit` only adds the row to the caller's session; the caller commits.

Event types currently emitted:

- `invoice_uploaded`
- `invoice_verified`
- `invoice_exported`
- `accounting_intent_classified`
- `rule_fired`
- `client_assigned`

Future event types arrive as new capabilities ship: `form_generated`, `period_closed`, etc. The schema is stable; new types are just new rows.

For more on the philosophy of the redesign, see [`../product/SRS.md`](../product/SRS.md) §1 (current thesis) and §4.18 (the client-first UI requirement).

---

## Data Model

23 SQLAlchemy 2.0 async models in `apps/api/app/models/`. Every business entity is scoped by `organization_id` for tenancy.

### Core entities

| Model                      | File                          | Notes                                                                 |
| -------------------------- | ----------------------------- | --------------------------------------------------------------------- |
| `Organization`             | `organization.py`             | Tenant. Holds `plan`, `subscription_status`, `subscription_canceled_at`. (`payment_provider_*` columns exist but are unused — billing is manual today; see `architecture.md` §3.3.) |
| `User`                     | `user.py`                     | Belongs to one org. Role: admin/manager/operator/viewer.              |
| `Invitation`               | `invitation.py`               | Pending org invitations.                                              |
| `JoinRequest`              | `join_request.py`             | Self-service request to join an existing org.                         |
| `ApiKey`                   | `api_key.py`                  | `sk_live_*` keys, Argon2-hashed.                                      |
| `Client`                   | `client.py`                   | One end-customer of the agency (a restaurant).                        |
| `Invoice`                  | `invoice.py`                  | Core entity. Has `client_id`, `status`, OCR results, etc.             |
| `LineItem`                 | `line_item.py`                | One row of an invoice. Optional `client_id` for cross-invoice lookup. |
| `ProductCatalog`           | `product_catalog.py`          | Org-wide product identities; pg_trgm fuzzy match against line names.  |
| `AccountingIntent`         | `accounting_intent.py`        | LLM-suggested classification (account, cost center, …).               |
| `AutomationRule`           | `automation_rule.py`          | Org-wide rule (org_id-scoped, optionally with per-client associations).|
| `RuleClientAssociation`    | `rule_client_association.py` | Many-to-many: rule ↔ client. Lets one rule apply only to chosen clients. |
| `ClientEvent`              | `client_event.py`             | Append-only timeline event stream (see above).                        |

### Compliance and audit

| Model                      | File                          | Purpose                                                              |
| -------------------------- | ----------------------------- | -------------------------------------------------------------------- |
| `AuditLog`                 | `audit_log.py`                | All sensitive actions. Per-org, append-only. Supports tax audits.    |
| `CorrectionLog`            | `correction_log.py`           | Manual edits to OCR-extracted fields (quality signal).               |
| `ConsentRecord`            | `consent_record.py`           | ZZPL consent (org-level or user-level). org_id is nullable.          |
| `DataProcessingAgreement`  | `data_processing_agreement.py`| ZZPL DPA records.                                                    |
| `DeletionRequest`          | `deletion_request.py`         | ZZPL right-to-be-forgotten requests.                                 |

### Operational

| Model                      | File                          | Purpose                                                              |
| -------------------------- | ----------------------------- | -------------------------------------------------------------------- |
| `UsageRecord`              | `usage_record.py`             | Per-org per-month usage counters (used by quota gate).               |
| `ExchangeRate`             | `exchange_rate.py`            | NBS rates cache (EUR/USD/CHF/GBP → RSD).                             |
| `ExportTemplate`           | `export_template.py`          | User-defined export column mappings.                                 |
| `ScheduledExportLog`       | `scheduled_export_log.py`     | History of scheduled exports.                                        |
| `MinimaxConfig`            | `minimax_config.py`           | Per-org MiniMax credentials and orgID.                                |

### Schema migrations (Alembic)

`apps/api/alembic/` with 17 versioned files. Current head is **0017** (`backfill_subscription_status`). Run migrations:

```bash
cd apps/api
alembic upgrade head            # apply all
alembic current                 # show current revision
alembic history                 # see all migrations
alembic revision -m "add foo"   # create a new empty revision
alembic revision --autogenerate -m "add foo"   # diff-based (review before commit!)
alembic downgrade -1            # roll back one revision
```

Notable migrations:

- `0014_add_client_events.py` — the timeline event log table.
- `0015_add_rule_client_associations.py` — per-client rule scoping.
- `0017_backfill_subscription_status.py` — backfills approved status for orgs that existed before the gate landed.

### Key data conventions

- **PIB** is `VARCHAR(20)` — 9-digit for Serbian entities, but foreign suppliers can have longer tax IDs.
- **Currency** defaults to RSD; foreign-currency invoices store the original amount and the NBS rate at invoice date.
- **Decimals** for money. Never `Float`. Models use `Numeric(precision, scale)`.
- **UUIDs** for primary keys (`uuid4()` default). Easier multi-tenant joining than autoincrement IDs.
- **Timestamps** are `DateTime(timezone=True)`, server-default `func.now()`.
- **10-year retention** per Zakon o računovodstvu — `archive` router and Celery beat task handle period archiving.

---

## Plans and Feature Gating

`apps/api/app/plans.py` is the single source of truth.

### Tiers

| Tier      | Price (EUR/mo) | Invoice limit | User limit | Overage (EUR) |
| --------- | -------------- | ------------- | ---------- | ------------- |
| Free      | —              | 10            | 1          | none          |
| Starter   | 29             | 100           | 2          | 0.10          |
| Pro       | 79             | 400           | 5          | 0.07          |
| Agency    | 199            | 1500          | 15         | 0.05          |

### Feature flags

`Feature` enum in `plans.py`:

| Feature                | Free | Starter | Pro | Agency |
| ---------------------- | :--: | :-----: | :-: | :----: |
| `OCR_EXTRACTION`       | ✓    | ✓       | ✓   | ✓      |
| `EXPORT_CSV_XLSX_JSON` | ✓    | ✓       | ✓   | ✓      |
| `MINIMAX_XML_EXPORT`   | ✓    | ✓       | ✓   | ✓      |
| `NBS_EXCHANGE_RATES`   | ✓    | ✓       | ✓   | ✓      |
| `ACCOUNTING_INTENT`    |      |         | ✓   | ✓      |
| `MINIMAX_DIRECT_PUSH`  |      |         | ✓   | ✓      |
| `AUDIT_EXPORT`         |      |         | ✓   | ✓      |
| `PDV_BOOKS`            |      |         | ✓   | ✓      |
| `AUTOMATION_RULES`     |      |         |     | ✓      |
| `CLIENT_MANAGEMENT`    |      |         |     | ✓      |

> **Hospitality forms** (M20, post-accountant-meeting) and the **Reports** surface upgrades will likely sit at the Agency tier, since hospitality portfolios are the agency-tier ICP. The exact boundary lands when the meeting produces a forms spec.

To gate an endpoint:

```python
from app.plans import Feature
from app.dependencies import require_feature

@router.post("/exports/minimax-direct")
async def push_to_minimax(
    user: User = Depends(require_feature(Feature.MINIMAX_DIRECT_PUSH)),
    ...
):
    ...
```

The error response includes a `required_plan` so the frontend can render an upgrade CTA without hard-coding plan names.

---

## The OCR / ML Pipeline

Lives in `packages/ml/`, importable as `from fakturaai_ml import InvoicePipeline`.

### Pipeline flow

```
PDF/image
   │
   ▼  Load (PDF → page images)
   ▼  dots.ocr VLM  (Modal/vLLM, OpenAI-compatible)        — raw color, no preprocessing
   ▼  Anthropic Claude Haiku                                — structured JSON extraction
   ▼  Validate                                              — PIB mod-11, math tolerance
   ▼  Confidence (per-field + overall)
   ▼
ExtractionResult { status, invoice, confidence, warnings, … }
```

### OCR engine: dots.ocr only

**Primary (and only)**: `rednote-hilab/dots.ocr` — a Vision-Language Model that reads the raw image and returns structured markdown. We run it on Modal in production; `OCR_USE_GPU=true` on Modal, A10G (24GB VRAM, native FA2 support).

There is **no automatic CPU fallback**. If dots.ocr fails, the invoice goes to manual review with `status = "review"` and the user fixes the fields by hand. EasyOCR is still installed as a dep for legacy code paths but is not used in the production path; the engineering team decided automatic fallback was hiding more problems than it was solving.

### LLM extraction: Anthropic Claude Haiku

Once the VLM returns the raw markdown, we hand it to Claude Haiku (`ANTHROPIC_MODEL=claude-haiku-4-5-20251001`) with a structured-output prompt that returns JSON matching the `ExtractedInvoice` dataclass. This is more accurate than regex and far cheaper than running a second vision pass.

`LLM_EXTRACTION_ENABLED=false` on the worker disables the LLM step and falls back to regex extraction (for offline development or if the Anthropic API is down).

### Type system

`packages/ml/fakturaai_ml/types.py` defines `ExtractedInvoice`, `LineItemData`, `CompanyData`, `FieldConfidence`, `ValidationWarning`, `ExtractionResult`. ML uses Python `@dataclass`, not Pydantic — the boundary back to the API is the worker's `_serialize_result` function, which dumps the dataclasses to dicts that the API persists.

### Validation rules

**PIB mod-11 checksum:**

```
PIB digits 1-8, weights [2,3,4,5,6,7,8,9]
Sum: 1×2 + 2×3 + ... + 8×9
Remainder: sum % 11
Check digit: 11 - remainder (10 → 0, 11 → 0)
Must match digit 9.
```

Foreign tax IDs are not validated this way; we mark them `verified=False` and let the user confirm.

**Math tolerance** (from SRS section 4.9.5):

| Total                 | Tolerance |
| --------------------- | --------- |
| 0 – 10,000 RSD        | ±1 RSD    |
| 10,001 – 100,000 RSD  | ±5 RSD    |
| 100,001 – 1,000,000   | ±10 RSD   |
| > 1,000,000 RSD       | ±50 RSD   |

Checks performed:

1. Σ line items ≈ subtotal
2. subtotal × tax_rate ≈ tax_amount
3. subtotal + tax_amount ≈ total_amount
4. Per line: `qty × unit_price` (or with discount/tax_base if present) ≈ line total

### Product catalog and pg_trgm

Each `LineItem` description is fuzzy-matched against `ProductCatalog` using PostgreSQL `pg_trgm`. New unique line names accumulate as candidate products; an accountant promotes them to canonical entries with a single click. This is the data backbone for the (deferred) hospitality forms: `extracted line item → product identity → kalkulacija`.

---

## Modal Deployment for OCR

`infra/modal/dots_ocr.py` is the deployment script for the OCR VLM. Modal gives us a GPU-on-demand without paying for an always-on GPU box.

### Properties

- **GPU**: A10G (24 GB VRAM, compute capability 8.6, native FlashAttention 2).
- **Scale-to-zero**: idle = 0 containers = 0 cost.
- **Cold start**: ~2 minutes (model weights are baked into the image, so it's just vLLM startup + warmup).
- **Idle warm window**: 5 minutes (`scaledown_window=300`). After last request, the container stays up for 5 minutes before terminating.
- **Concurrency**: `@modal.concurrent(max_inputs=4)` — one container handles up to 4 simultaneous OCR requests before Modal spawns another.
- **API surface**: OpenAI-compatible `/v1/chat/completions`. The OCR engine in `packages/ml/fakturaai_ml/ocr/dots_ocr.py` calls it as if it were OpenAI.

### Deploying / updating

```bash
modal deploy infra/modal/dots_ocr.py
# Output includes the endpoint URL (https://<app>.modal.run/v1)
# Set DOTS_OCR_SERVER_URL on the worker to that value.
```

The bearer token comes from a Modal Secret (`dots-ocr-api-key`). Only the worker has it; even logging in to the Modal dashboard does not show it after creation.

### Cost shape

- **Idle**: $0.
- **Per invoice**: ~$0.005 of GPU time (1-2 seconds active per page).
- **At 10K invoices/month**: ~$60 (matches DEPLOYMENT.md).

### When to skip Modal locally

For local development you usually do not need OCR — most tests mock the worker. If you want to iterate on the OCR path, two options:

1. **Use the dev Modal endpoint** — `modal serve infra/modal/dots_ocr.py` spins up a temporary endpoint URL. Set `DOTS_OCR_SERVER_URL` to it.
2. **Run vLLM locally** — bring up the `dots-ocr-server` service from the dev compose. Requires an NVIDIA GPU and ~6 GB free VRAM.

---

## Celery: Async Task Processing

OCR takes seconds-to-minutes; users cannot wait synchronously.

```
WITHOUT Celery
User → API → OCR (30s) → Response

WITH Celery
User → API → enqueue → return job ID (100ms)
                 │
                 └→ Worker picks up → OCR → save result → emit ClientEvent
User → poll /invoices/{id} → see updated status
```

### Redis databases

Three Redis databases on the same Redis instance:

```
redis://localhost:6379/0  → Cache (JWT blacklist, presigned URL cache)
redis://localhost:6379/1  → Celery broker (task queue)
redis://localhost:6379/2  → Celery results (so /status can poll)
```

### Celery configuration

Key knobs in `workers/ocr_worker/celery_app.py`:

- `worker_prefetch_multiplier=1` and `worker_concurrency=1` — one task at a time per worker (Modal handles the parallelism).
- `task_soft_time_limit=120`, `task_time_limit=180` — invoices that take longer than 3 min get killed.
- `task_acks_late=True` + `task_reject_on_worker_lost=True` — if the worker dies mid-task, Celery requeues it.
- `result_expires=3600` — task results stay in Redis for 1 hour, long enough for the frontend to poll.
- All tasks routed to a single `ocr` queue (single worker in prod).

### Tasks

| Task                                       | Schedule         | Purpose                                                |
| ------------------------------------------ | ---------------- | ------------------------------------------------------ |
| `ocr_worker.tasks.process_invoice`         | on demand        | Run OCR + LLM + validation; update invoice; emit event |
| `ocr_worker.tasks.process_batch`           | on demand        | Multiple invoices in one task                          |
| `ocr_worker.tasks.health_check`            | on demand        | Liveness probe                                         |
| `ocr_worker.tasks.fetch_nbs_exchange_rates`| weekdays 08:30   | Pull EUR/USD/CHF/GBP rates from NBS                    |
| `ocr_worker.tasks.aggregate_daily_usage`   | daily 02:00      | Reconcile per-org invoice counts in `usage_records`    |
| `ocr_worker.tasks.enforce_data_retention`  | daily 03:00      | ZZPL retention sweeps                                  |
| `ocr_worker.tasks.backup_database`         | daily 04:00      | pg_dump → ZIP with manifest → R2                       |
| Monthly archive generation                 | 1st of month 06:00 | Generate org archive ZIPs, email billing contact     |

The schedule lives in `celery_app.py` under `app.conf.beat_schedule`. The `saldora-celery-beat` container runs Celery Beat in production.

### Calling from the API

```python
# Inside an async endpoint
from celery import current_app as celery

celery.send_task(
    "ocr_worker.tasks.process_invoice",
    args=[str(invoice.id), s3_key],
    queue="ocr",
)
```

`send_task` is preferred over `process_invoice.delay(...)` because the API process never imports `ocr_worker.tasks` (and therefore never imports `fakturaai_ml`, which pulls in torch). Stays slim.

### Running the worker

```bash
# Local dev
cd workers/ocr_worker
celery -A celery_app worker --loglevel=info --queues=ocr

# With Flower
docker compose -f infra/docker/docker-compose.yml up -d flower
# http://localhost:5555
```

---

## Service Topology

### End-to-end upload flow

```
Browser ──POST /api/v1/invoices/upload──▶  FastAPI
                                             │
   1. require_role("operator") → check sub   │
   2. check_invoice_quota() → 402 if hit     │
   3. Upload bytes to R2/MinIO               │
   4. Insert Invoice + emit                  │
      invoice_uploaded ClientEvent           │
   5. celery.send_task("...process_invoice")─┼──▶ Redis (broker)
   6. Return 202 { id, status:"processing" } │       │
                                             │       │
                                       Celery worker picks up
                                             │
                          ┌──────────────────▼──────────────────┐
                          │  saldora-ocr-worker                 │
                          │  1. Download original from R2       │
                          │  2. dots.ocr ──HTTPS──▶ Modal (A10G)│
                          │  3. Claude Haiku ──HTTPS──▶ Anthropic│
                          │  4. Validate (PIB, math)            │
                          │  5. Persist Invoice + LineItems     │
                          │  6. Emit invoice_processed event    │
                          └─────────────────────────────────────┘
```

### Connection strings cheat sheet

| Service        | From host        | From Docker container | From browser    |
| -------------- | ---------------- | --------------------- | --------------- |
| PostgreSQL     | `localhost:5433` | `postgres:5432`       | n/a             |
| Redis          | `localhost:6379` | `redis:6379`          | n/a             |
| MinIO API      | `localhost:9010` | `minio:9000`          | n/a             |
| MinIO console  | `localhost:9011` | n/a                   | `localhost:9011`|
| FastAPI        | `localhost:8000` | `api:8000`            | `localhost:8000`|
| Next.js        | `localhost:3000` | `web:3000`            | `localhost:3000`|
| Flower         | `localhost:5555` | n/a                   | `localhost:5555`|

Production wiring is on the Hetzner box; see [`DEPLOYMENT.md`](./DEPLOYMENT.md).

---

## Testing

### Where tests live

```
apps/api/tests/
├── conftest.py                 # Test fixtures (test_engine, client, sample_user, …)
├── test_auth_api.py
├── test_clients.py
├── test_client_events.py
├── test_invoice_upload.py
├── test_invoice_crud.py
├── test_invoice_verification.py
├── test_export_audit.py
├── test_minimax_client.py
├── test_minimax_mapper.py
├── test_compliance.py
├── test_data_retention.py
├── test_db_backup.py
└── ... (40+ test files)

packages/ml/tests/
└── ... (pipeline, validation, extraction)

workers/ocr_worker/tests/
└── ... (task wiring, serialization)
```

### Test database

Separate DB on the same Postgres container: **`saldora_test`** at `localhost:5433`. Created by `conftest.py` at session start.

```python
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://saldora:saldora_dev@localhost:5433/saldora_test",
)
```

The fixture creates all tables via `Base.metadata.create_all`, drops the schema at session end, and uses `NullPool` so each request creates a fresh connection on the current event loop (asyncpg connections are loop-bound; a pool causes "attached to a different loop" errors with pytest-asyncio).

### `TESTING=1` and the subscription gate

```python
# apps/api/tests/conftest.py
import os
os.environ["TESTING"] = "1"   # MUST be set before app import
```

`apps/api/app/routers/auth.py::_initial_subscription_status()` reads `TESTING` and returns `"active"` instead of `"pending"` for new orgs. This means:

- All existing test fixtures that create an org keep working without changes.
- The subscription gate logic itself is tested in `test_auth_api.py` by creating an org and then explicitly setting its `subscription_status` to `"pending"` before calling a protected endpoint.

### Running tests

```bash
# All API tests
cd apps/api
pytest

# A specific file
pytest tests/test_invoice_upload.py

# Stop at first failure, print on stdout
pytest -x -s

# Match by keyword
pytest -k "verification"

# With coverage
pytest --cov=app --cov-report=term-missing

# ML tests
cd packages/ml && pytest

# Worker tests
cd workers/ocr_worker && pytest
```

### Test conventions

- `pytest_asyncio` with `asyncio_mode = "auto"`. **Do not** add `@pytest.mark.asyncio`.
- Use the `client` fixture (httpx `AsyncClient` against the in-process app).
- Mock external services (S3, Celery, Anthropic, Resend, Modal). Tests never hit real infra.
- Use `monkeypatch` or `unittest.mock.patch` for env vars. Don't mutate `os.environ` directly.
- Per CLAUDE.md: **run the relevant tests every time you modify a feature**, especially billing, auth, export, or verification. Pre-commit runs ruff + tests.

```bash
# Quick affected-area run
pytest tests/ -x -k billing
pytest tests/ -x -k auth
pytest tests/ -x -k export
pytest tests/ -x -k verification
```

---

## Issue Workflow and Conventions

### Per-issue workflow

1. **Branch from main**: `feature/{issue_number}-{short-description}` (e.g. `feature/211-responsive-design`).
2. **Implement** the issue scope. Don't gold-plate — keep commits focused.
3. **Run tests** for the affected area before committing.
4. **Commit** with a clear, imperative-mood message ending with `Closes #{issue_number}`. Do **not** include `Co-Authored-By` lines or AI attribution.
5. **Push and open PR** to `main`. PR body must include:
   - `## Summary` — bullet points of what changed
   - `## Test plan` — checklist of what was verified
   - `Closes #{issue_number}` at the bottom
   - Assign the milestone if the issue is part of one.
6. **Wait for review**. Don't merge without approval.

### Commit conventions

- Imperative subject line, no trailing period: `Implement dots.ocr Modal client`, not `Implemented...`.
- One logical change per commit.
- No emojis (unless the original file already has them in headers — match the surrounding style).
- No `Co-Authored-By: Claude ...` or "Generated with Claude" lines.
- The body explains the *why*. The subject explains the *what*.

### Code standards

- **Python (apps/api)**: Python 3.12+, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Ruff. Public functions get docstrings with Args/Returns sections.
- **TypeScript (apps/web)**: Next.js App Router, TypeScript strict mode, ESLint + Prettier. UI text is **Serbian Latin script**.
- **Pre-commit hooks**: Ruff + tests on commit. Don't bypass them with `--no-verify`.
- **Tests**: pytest with `asyncio_mode = "auto"`. Mock external services.

### Architecture decisions worth knowing

- **Multi-tenant** by `organization_id` from the authenticated user — every model carries it.
- **S3 keys**: `organizations/{org_id}/invoices/{invoice_id}/original.{ext}`.
- **Storage functions are sync** (boto3); call them from async code with `asyncio.to_thread()`.
- **Celery tasks dispatched via `send_task()`** — keeps heavy ML deps out of the API image.
- **ZZPL** is the primary data protection law (Serbia), not GDPR. GDPR is a reference framework only.
- **Manual billing.** Agencies pay by bank transfer; admin activates / extends via `scripts/admin_orgs.py`. No third-party payment processor integrated (Stripe is unavailable in Serbia). See `architecture.md` §3.3.
- **No model training/retraining** — pre-trained dots.ocr only.
- **APR API** requires a commercial contract or licensed intermediary. We don't currently call it; PIB validation is local-only.

---

## Common Development Tasks

### Add a new API endpoint

1. Decide which router. If it's truly new, create one in `apps/api/app/routers/your_router.py` and mount it in `main.py`.
2. Add request/response schemas to `apps/api/app/schemas/your_thing.py`.
3. Write the endpoint in the router. Inject `db: AsyncSession = Depends(get_db)` and `user: User = Depends(require_role("operator"))` (or whichever role).
4. If it touches a client, emit a `ClientEvent` via `app.services.events.emit`.
5. If it should be plan-gated, wrap with `Depends(require_feature(Feature.X))`.
6. Add tests in `apps/api/tests/test_your_router.py`.
7. Run `pytest -x -k your_router`.

### Add a new database table

1. Create the model in `apps/api/app/models/your_model.py`. Inherit from `Base, UUIDMixin` (and add a `created_at`).
2. Import it in `apps/api/app/models/__init__.py`.
3. Generate a migration: `alembic revision --autogenerate -m "Add your_model"`. Review the generated SQL — autogen sometimes misses constraints.
4. Apply it: `alembic upgrade head`.
5. Add tests for any new endpoints that touch it.

### Add a new frontend page

```tsx
// Org-scoped page: apps/web/src/app/(app)/[orgSlug]/your-page/page.tsx
'use client';

import { useTranslations } from 'next-intl';

export default function YourPage() {
  const t = useTranslations('yourPage');
  return <h1>{t('title')}</h1>;
}
```

For dynamic routes: `[id]/page.tsx`. Add an `i18n` key in `apps/web/src/i18n/`. If the page should appear in the sidebar, edit the sidebar component (it's not auto-generated).

### Add a Python dependency

```bash
# Edit apps/api/pyproject.toml under [project] dependencies
pip install -e "apps/api[dev]"
# Or for ML:
# Edit packages/ml/pyproject.toml
pip install -e "packages/ml[dev]"
```

### Add a Node.js dependency

```bash
cd apps/web
npm install <pkg>
```

### Add a Celery task

```python
# workers/ocr_worker/tasks.py
@app.task(name="ocr_worker.tasks.your_task")
def your_task(arg1: str) -> dict:
    return {"ok": True}
```

Add the route in `celery_app.py`:

```python
task_routes={
    "ocr_worker.tasks.your_task": {"queue": "ocr"},
}
```

Call it from the API:

```python
celery.send_task("ocr_worker.tasks.your_task", args=["hello"], queue="ocr")
```

### Approve a pending org

```bash
python scripts/admin_orgs.py
# select environment → org → status → plan tier
```

### Reset local DB

```bash
docker compose -f infra/docker/docker-compose.yml down -v   # nukes the volume
docker compose -f infra/docker/docker-compose.yml up -d postgres
cd apps/api && alembic upgrade head
```

### Seed test data

```bash
python scripts/seed_test_data.py
python scripts/generate_test_invoices.py
```

---

## Debugging Tips

### Service status

```bash
docker compose -f infra/docker/docker-compose.yml ps
# All saldora-* containers should be Up (healthy)
```

### Database

```bash
# From host
psql postgresql://saldora:saldora_dev@localhost:5433/saldora

# From inside Docker
docker exec -it saldora-postgres psql -U saldora -d saldora

# Quick check
docker exec saldora-postgres pg_isready -U saldora

# Migration status
cd apps/api && alembic current
```

### Redis

```bash
redis-cli -h localhost -p 6379 PING               # PONG

# Inspect Celery queues
redis-cli -n 1 LLEN celery                        # pending tasks
redis-cli -n 2 KEYS "*"                           # task results

redis-cli MONITOR                                 # live commands
```

### API

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/services        # checks Redis + Celery workers

# Swagger
open http://localhost:8000/docs

# Auth flow
curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"x@y","password":"p"}'
```

### Logs

```bash
docker compose -f infra/docker/docker-compose.yml logs -f api
docker compose -f infra/docker/docker-compose.yml logs -f ocr-worker
docker compose -f infra/docker/docker-compose.yml logs -f --tail=50 postgres

# Multiple
docker compose -f infra/docker/docker-compose.yml logs -f api ocr-worker
```

When running locally, uvicorn / Celery print to the terminal directly.

### Common issues

| Symptom                                             | Likely cause                                     | Fix                                                          |
| --------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------ |
| `connection refused` on `:5432`                     | Local Postgres on 5432; ours is on 5433.         | Use `localhost:5433`.                                        |
| `connection refused` on `:5433`                     | Container not running.                            | `docker compose up -d postgres`                              |
| CORS error in browser                                | Wrong `NEXT_PUBLIC_API_URL`.                      | Set to `http://localhost:8000`.                              |
| `relation "X" does not exist`                        | Migrations not run.                               | `alembic upgrade head`                                       |
| `subscription_pending_approval` after registering    | Working as designed.                              | Run `python scripts/admin_orgs.py` to approve.               |
| Worker not picking up tasks                          | Worker connected to a different Redis or queue.   | Check `CELERY_BROKER_URL` and `--queues=ocr`.                |
| `ModuleNotFoundError: fakturaai_ml`                  | ML package not installed.                          | `pip install -e packages/ml`                                 |
| Upload returns 415                                   | Set `Content-Type` manually with FormData.        | Don't set it; the browser adds the boundary.                 |
| `attached to a different loop` in tests              | Tried to run async tests without `NullPool`.      | Use the `client` fixture from `conftest.py`.                 |
| Modal cold start of 2 minutes on first invoice       | Working as designed (scale-to-zero).              | Frontend shows an indeterminate spinner; second invoice is fast. |

---

## Production Deployment

The full operations runbook lives in [`DEPLOYMENT.md`](./DEPLOYMENT.md). High-level summary:

- **VPS**: Hetzner CX32 at `178.104.205.37`, app user `saldora`.
- **Reverse proxy**: Caddy. `saldora.rs` → `web:3000`, `api.saldora.rs` → `api:8000`.
- **DNS + edge**: Cloudflare (proxied), free plan.
- **Storage**: Cloudflare R2 (S3-compatible). Bucket `saldora-documents`.
- **OCR**: Modal (`infra/modal/dots_ocr.py`), A10G GPU, scale-to-zero.
- **LLM extraction**: Anthropic Claude Haiku.
- **Email**: Resend (transactional + monthly archive emails).
- **Database backups**: Daily 04:00 UTC via Celery beat → R2, 30-day retention, ZIP with manifest checksums.
- **Cost**: ~€115/month for 10K invoices.

Common ops:

```bash
# Deploy new code
ssh saldora@178.104.205.37 \
  'cd /home/saldora/app && git pull && \
   docker compose -f infra/docker/docker-compose.prod.yml \
                  --env-file infra/docker/.env.prod up -d --build'

# Run migrations
ssh saldora@178.104.205.37 'docker exec saldora-api alembic upgrade head'

# Tail API logs
ssh saldora@178.104.205.37 'docker logs saldora-api -f'

# Approve a prod org
python scripts/admin_orgs.py   # then select "production"
```

Modal deploys are independent of the VPS:

```bash
modal deploy infra/modal/dots_ocr.py
```

Update `DOTS_OCR_SERVER_URL` in `.env.prod` if the Modal endpoint URL changes.

---

## Dropped and Deferred Milestones

Saldora has been through one significant repositioning. Knowing what's *not* in the codebase saves new contributors from chasing dead leads.

### Dropped (closed, will not be built)

- **M14 — Paušal Module.** Self-employed flat-rate entrepreneurs (paušalci) are not the buyer. Some M14.x issues were merged and then reverted. The `direction` field on invoices, `client_type` on clients, `customers` table, `invoice_counters`, paušal-specific routers, and the KPO ledger are all gone. If you find references to paušal/KPO/`customers` anywhere, that's a leftover and probably a bug.
- **M16 — Client Portal.** Hospitality owners are not portal users. Documents arrive at the agency by email/WhatsApp/paper, not through a self-serve portal. The agency remains the sole user class.
- **M18 — Compliance Watchdog.** Scheduled rule evaluation producing alerts. The rules engine continues to fire on events; a separate scheduled watchdog layer was paušal-era thinking.

### Active

- **M19 — Client-First UI.** Mostly shipped. Portfolio view, per-client workspace, timeline event log, agency vs. client sidebar split.

### Deferred (will be built later, scope not yet defined)

- **M15 — Foreign Invoice Reverse-Charge.** Revisit only if hospitality agencies report it as a pain. Today the NBS exchange rate service + AccountingIntent handle foreign invoices for the hospitality case.
- **M20 — Hospitality Legal Forms.** Kalkulacije, šank lista, cenovnik, KEP, popis. Specified after a meeting with an actual restaurant accountant. Will likely add a `markup` per `(client, product)` and a per-form generator under `apps/api/app/services/forms/`. Tab additions inside the **Izveštaji** surface of the client workspace.
- **M21 — Close Checklist + Period Semantics.** Comes after M20. Period entity with close/lock semantics.

### Out-of-milestone, low-priority

- **SEF ingestion as a data source** — pulling the agency's already-SEF'd invoices into the pipeline for visibility.
- **Public Serbian tax calendar widget** — marketing/SEO.
- **Rule template marketplace** — extends the existing rules engine.
- **Pricing page update** — once hospitality positioning is solidified externally.

---

## Quick Reference

### Commands

| What                              | Command                                                                           |
| --------------------------------- | --------------------------------------------------------------------------------- |
| **Setup (first time)**            | `./scripts/setup-dev.sh`                                                          |
| Start infrastructure              | `docker compose -f infra/docker/docker-compose.yml up -d postgres redis minio`    |
| Start everything (Docker)         | `docker compose -f infra/docker/docker-compose.yml up -d`                          |
| Start backend (local)             | `cd apps/api && uvicorn app.main:app --reload --port 8000`                        |
| Start frontend (local)            | `cd apps/web && npm run dev`                                                       |
| Start worker (local)              | `cd workers/ocr_worker && celery -A celery_app worker -l info -Q ocr`             |
| Stop everything                   | `docker compose -f infra/docker/docker-compose.yml down`                           |
| Stop + delete data                | `docker compose -f infra/docker/docker-compose.yml down -v`                        |
| Apply migrations                  | `cd apps/api && alembic upgrade head`                                              |
| New migration (autogen)           | `cd apps/api && alembic revision --autogenerate -m "..."`                         |
| Run all tests                     | `cd apps/api && pytest -x`                                                         |
| Run tests by area                 | `pytest -x -k billing`                                                             |
| Lint Python                       | `cd apps/api && ruff check . && ruff format --check .`                            |
| Lint frontend                     | `cd apps/web && npm run lint`                                                      |
| DB shell                          | `docker exec -it saldora-postgres psql -U saldora -d saldora`                      |
| Redis shell                       | `docker exec -it saldora-redis redis-cli`                                          |
| Approve a pending org             | `python scripts/admin_orgs.py`                                                     |
| Deploy Modal OCR                  | `modal deploy infra/modal/dots_ocr.py`                                             |
| Deploy app to prod                | `ssh saldora@... 'cd app && git pull && docker compose ... up -d --build'`        |

### Ports

| Port  | Service             | Notes                                                |
| ----- | ------------------- | ---------------------------------------------------- |
| 3000  | Next.js frontend    |                                                      |
| 8000  | FastAPI backend     | `/docs` for Swagger in development                   |
| 5433  | PostgreSQL          | Mapped from container 5432; avoids conflict with local pg |
| 6379  | Redis               | DB 0 cache, DB 1 broker, DB 2 results                |
| 9010  | MinIO API           | Mapped from container 9000                           |
| 9011  | MinIO Console       | Mapped from container 9001                           |
| 5555  | Flower              | Celery dashboard                                     |
| 8100  | dots-ocr-server     | Local vLLM (only if you bring it up)                 |

### Container names (dev and prod)

| Container             | Service                                                  |
| --------------------- | -------------------------------------------------------- |
| `saldora-postgres`    | PostgreSQL 16                                            |
| `saldora-redis`       | Redis 7                                                  |
| `saldora-minio`       | MinIO (dev only; prod uses Cloudflare R2)                |
| `saldora-api`         | FastAPI                                                  |
| `saldora-web`         | Next.js                                                  |
| `saldora-ocr-worker`  | Celery worker                                            |
| `saldora-celery-beat` | Celery Beat (prod only)                                  |
| `saldora-caddy`       | Reverse proxy (prod only)                                |
| `saldora-flower`      | Celery dashboard (dev only)                              |
| `saldora-dots-ocr`    | Local vLLM (dev with GPU only; prod uses Modal)          |

### Key files

| When you want to…                            | Look at…                                                          |
| -------------------------------------------- | ----------------------------------------------------------------- |
| Add or change an API endpoint                | `apps/api/app/routers/*.py`                                       |
| Add request/response schemas                 | `apps/api/app/schemas/*.py`                                       |
| Add a SQLAlchemy model                       | `apps/api/app/models/*.py` + `models/__init__.py`                 |
| Change a config default                      | `apps/api/app/config.py`                                          |
| Change plan limits or features               | `apps/api/app/plans.py`                                           |
| Add a feature gate to an endpoint            | `Depends(require_feature(Feature.X))` from `app.dependencies`     |
| Approve a pending org                        | `scripts/admin_orgs.py`                                           |
| Add an environment variable                  | `apps/api/app/config.py` + `infra/docker/docker-compose.yml`      |
| Edit OCR pipeline                            | `packages/ml/fakturaai_ml/pipeline.py`                            |
| Edit field extraction                        | `packages/ml/fakturaai_ml/extraction/`                            |
| Edit validation                              | `packages/ml/fakturaai_ml/validation/`                            |
| Edit the Modal OCR deployment                | `infra/modal/dots_ocr.py`                                         |
| Add a Celery task                            | `workers/ocr_worker/tasks.py` + `celery_app.py`                   |
| Add a frontend page                          | `apps/web/src/app/(app)/[orgSlug]/<route>/page.tsx`               |
| Add a React component                        | `apps/web/src/components/<Name>.tsx`                              |
| Edit the awaiting-approval landing           | `apps/web/src/app/(auth)/awaiting-approval/page.tsx`              |
| Edit the AuthContext / role routing          | `apps/web/src/contexts/AuthContext.tsx`                           |
| Edit Docker services for dev                 | `infra/docker/docker-compose.yml`                                 |
| Edit Docker services for prod                | `infra/docker/docker-compose.prod.yml`                            |
| Run prod ops                                 | `docs/dev/DEPLOYMENT.md`                                          |
| Read product strategy                         | `docs/product/SRS.md` §1 (current thesis)                         |
| Read milestone state                         | `docs/product/IMPLEMENTATION_GUIDE.md`                            |
| Read formal requirements                     | `docs/product/SRS.md` / `docs/product/SRS_sr.md`                  |
| Read architectural decisions                  | `docs/dev/architecture.md`                                        |
| Read AI-assistant conventions                 | `CLAUDE.md`                                                       |
