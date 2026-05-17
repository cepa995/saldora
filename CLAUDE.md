# CLAUDE.md — Project Instructions for Claude Code

## Project

Saldora — AI-powered invoice processing SaaS for the Serbian market.
Monorepo: `apps/api` (FastAPI), `apps/web` (Next.js), `workers/`, `packages/`, `infra/`.

## Issue Workflow

We work issue-by-issue from GitHub milestones. For each issue:

1. **Branch from main:** `feature/{issue_number}-{short-description}` (e.g. `feature/16-s3-storage-service`)
2. **Implement** the issue requirements
3. **Commit** with a clear message. End with `Closes #{issue_number}`. Do NOT include `Co-Authored-By` lines.
4. **Push and open PR** targeting `main`. PR body must include:
   - `## Summary` — bullet points of what changed
   - `## Test plan` — checklist of what was verified
   - `Closes #{issue_number}` at the bottom
   - Assign the correct milestone
5. **Wait for review** — do not merge without explicit approval

## Commit Conventions

- Short imperative subject line (e.g. "Implement S3 storage service", not "Implemented" or "Adds")
- No `Co-Authored-By` or AI attribution in commits, PRs, or code comments
- Keep commits focused — one logical change per commit

## Code Standards

### Python (apps/api)
- Python 3.12+, FastAPI, SQLAlchemy 2.0 async, Pydantic v2
- Ruff for formatting and linting (config in `apps/api/pyproject.toml`)
- All public functions must have docstrings with Args/Returns sections
- Pre-commit hooks run ruff + tests automatically on commit

### TypeScript (apps/web)
- Next.js with App Router, TypeScript strict mode
- ESLint + Prettier via pre-commit hooks
- Serbian Latin script for all UI text (labels, messages, placeholders)

### Tests
- pytest with `asyncio_mode = "auto"` — no need for `@pytest.mark.asyncio`
- Test DB: `saldora_test` on localhost:5433
- Use the `client` fixture from `conftest.py` for API tests
- Mock external services (S3, Celery, Redis) — never depend on running infra in tests
- **CRITICAL: Run relevant tests every time you modify a feature.** Do not commit changes to billing, auth, export, or verification without running the corresponding test suite. At minimum run `pytest apps/api/tests/ -x -k <feature>` for the affected area.

## Key Architecture Decisions

- **Multi-tenant:** All data scoped by `organization_id` from authenticated user
- **S3 key format:** `organizations/{org_id}/invoices/{invoice_id}/original.{ext}`
- **Storage functions are sync** (boto3) — use `asyncio.to_thread()` from async context
- **Celery tasks dispatched via `send_task()`** — avoids importing heavy ML worker deps into the API
- **ZZPL** is the primary data protection law (Serbia), not GDPR
- **Manual billing** — customers receive an invoice from Saldora and pay by bank transfer; admin activates / extends the org via `scripts/admin_orgs.py`. No third-party payment processor is integrated today (Stripe is unavailable in Serbia; Paddle was scoped earlier but not adopted). See `docs/dev/architecture.md` §3.3.

## Reference Documents

All docs live under `docs/` in three subdirectories:

- `docs/product/` — what we're building and why
  - `SRS.md` / `SRS_sr.md` / `SRS_sr_simple.md` — Software Requirements Specification (EN / Serbian Latin / business-friendly Serbian)
  - `IMPLEMENTATION_GUIDE.md` — Milestone breakdown with issue references
  - `M20_accountant_meeting_agenda.md` — Pre-meeting strawman for hospitality forms (delete after meeting)
- `docs/dev/` — for developers
  - `DEVELOPER_GUIDE.md` — Setup, codebase tour, conventions
  - `DEPLOYMENT.md` — Production ops on Hetzner + Caddy + Cloudflare + Modal
  - `architecture.md` — Architectural decisions and trade-offs (why-we-built-it-this-way)
  - `AUTOMATION_RULES.md` — Rules engine reference
  - `ML_PROJECT_ARCHITECTURE_GUIDE.md` — ML pipeline architecture
- `docs/user-experience/` — for the agency staff using the app
  - `workflows.md` — Click-by-click reference of every supported workflow
