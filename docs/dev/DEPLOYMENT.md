# Saldora Deployment Guide

## Architecture Overview

```
                    ┌─────────────┐
                    │  Cloudflare  │
                    │  DNS + SSL   │
                    └──────┬──────┘
                           │ HTTPS
                           ▼
                    ┌─────────────┐
                    │   Hetzner    │
                    │  VPS (CX32)  │
                    │ 178.104.205.37│
                    └──────┬──────┘
                           │ port 80
                           ▼
                    ┌─────────────┐
                    │    Caddy     │
                    │ reverse proxy│
                    └──┬───────┬──┘
                       │       │
          saldora.rs   │       │  api.saldora.rs
                       ▼       ▼
                ┌────────┐ ┌────────┐
                │Next.js │ │FastAPI │
                │ :3000  │ │ :8000  │
                └────────┘ └───┬────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              ┌──────────┐ ┌───────┐ ┌────────┐
              │PostgreSQL│ │ Redis │ │ Celery │
              │  :5432   │ │ :6379 │ │ Worker │
              └──────────┘ └───────┘ └───┬────┘
                                         │ HTTPS
                                         ▼
                                  ┌─────────────┐
                                  │   Modal.com  │
                                  │  dots.ocr    │
                                  │  (A10G GPU)  │
                                  └─────────────┘
```

## Services

| Service | Container | Purpose |
|---------|-----------|---------|
| **Caddy** | `saldora-caddy` | Reverse proxy, routes `saldora.rs` → web, `api.saldora.rs` → API |
| **Next.js** | `saldora-web` | Frontend (port 3000) |
| **FastAPI** | `saldora-api` | Backend API (port 8000) |
| **PostgreSQL** | `saldora-postgres` | Database |
| **Redis** | `saldora-redis` | Cache + Celery broker |
| **OCR Worker** | `saldora-ocr-worker` | Celery worker, processes invoices via Modal |
| **Celery Beat** | `saldora-celery-beat` | Scheduled tasks (backups, retention, NBS rates) |

## External Services

| Service | Purpose | Dashboard |
|---------|---------|-----------|
| **Cloudflare** | DNS, SSL, CDN, DDoS protection | [dash.cloudflare.com](https://dash.cloudflare.com) |
| **Cloudflare R2** | Document storage (S3-compatible) | Cloudflare → R2 |
| **Modal** | GPU OCR server (dots.ocr on A10G) | [modal.com](https://modal.com/apps/cepa995/main/deployed/saldora-dots-ocr) |
| **Resend** | Transactional email | [resend.com](https://resend.com) |
| **Anthropic** | LLM field extraction (Claude Haiku) | [console.anthropic.com](https://console.anthropic.com) |

## Costs

| Service | Monthly Cost |
|---------|-------------|
| Hetzner VPS (CX32) | €8 |
| Modal (10K invoices) | ~$60 |
| Cloudflare (free plan) | $0 |
| Cloudflare R2 (10GB free) | $0 |
| Anthropic (10K invoices) | ~$45 |
| Resend (free tier, 3K emails) | $0 |
| **Total** | **~€115/month** |

---

## SSH Access

```bash
# Connect as app user
ssh saldora@178.104.205.37

# Connect as root (system admin only)
ssh root@178.104.205.37
```

App files are at `/home/saldora/app/`.

---

## Common Commands

### Check Service Status

```bash
# All containers
ssh saldora@178.104.205.37 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Specific service
ssh saldora@178.104.205.37 'docker ps -f name=saldora-api'
```

### View Logs

```bash
# API logs (last 50 lines)
ssh saldora@178.104.205.37 'docker logs saldora-api --tail 50'

# API logs (follow in real-time)
ssh saldora@178.104.205.37 'docker logs saldora-api -f'

# Worker logs (see invoice processing)
ssh saldora@178.104.205.37 'docker logs saldora-ocr-worker --tail 50'

# All services logs
ssh saldora@178.104.205.37 'cd /home/saldora/app && docker compose -f infra/docker/docker-compose.prod.yml --env-file infra/docker/.env.prod logs --tail 20'

# Caddy logs (reverse proxy / routing issues)
ssh saldora@178.104.205.37 'docker logs saldora-caddy --tail 20'

# Celery beat logs (scheduled tasks)
ssh saldora@178.104.205.37 'docker logs saldora-celery-beat --tail 20'

# Database logs
ssh saldora@178.104.205.37 'docker logs saldora-postgres --tail 20'
```

### Restart Services

```bash
# Restart a single service
ssh saldora@178.104.205.37 'docker restart saldora-api'

# Restart all services
ssh saldora@178.104.205.37 'cd /home/saldora/app && docker compose -f infra/docker/docker-compose.prod.yml --env-file infra/docker/.env.prod restart'

# Force recreate (picks up new env vars)
ssh saldora@178.104.205.37 'cd /home/saldora/app && docker compose -f infra/docker/docker-compose.prod.yml --env-file infra/docker/.env.prod up --force-recreate -d'
```

### Deploy New Code

```bash
# Pull latest code and rebuild
ssh saldora@178.104.205.37 'cd /home/saldora/app && git pull && docker compose -f infra/docker/docker-compose.prod.yml --env-file infra/docker/.env.prod up -d --build'

# Rebuild only specific service (faster)
ssh saldora@178.104.205.37 'cd /home/saldora/app && git pull && docker compose -f infra/docker/docker-compose.prod.yml --env-file infra/docker/.env.prod up -d --build api'
```

### Run Database Migrations

```bash
ssh saldora@178.104.205.37 'docker exec saldora-api alembic upgrade head'
```

### Database Access

```bash
# Open psql shell
ssh saldora@178.104.205.37 'docker exec -it saldora-postgres psql -U saldora -d saldora'

# Run a quick query
ssh saldora@178.104.205.37 'docker exec saldora-postgres psql -U saldora -d saldora -c "SELECT COUNT(*) FROM invoices;"'
```

### Trigger Manual Tasks

```bash
# Run database backup now
ssh saldora@178.104.205.37 'docker exec saldora-ocr-worker celery -A ocr_worker.celery_app call ocr_worker.tasks.backup_database --queue=ocr'

# Run usage aggregation
ssh saldora@178.104.205.37 'docker exec saldora-ocr-worker celery -A ocr_worker.celery_app call ocr_worker.tasks.aggregate_daily_usage --queue=ocr'

# Run data retention
ssh saldora@178.104.205.37 'docker exec saldora-ocr-worker celery -A ocr_worker.celery_app call ocr_worker.tasks.enforce_data_retention --queue=ocr'
```

### Check Disk Space

```bash
ssh saldora@178.104.205.37 'df -h / && echo "---" && docker system df'
```

### Clean Up Docker (free disk space)

```bash
# Remove unused images and build cache
ssh saldora@178.104.205.37 'docker system prune -af'
```

---

## Scheduled Tasks (Celery Beat)

| Task | Schedule | Purpose |
|------|----------|---------|
| NBS exchange rates | Weekdays 08:30 | Fetch EUR/USD/CHF/GBP rates from NBS |
| Usage aggregation | Daily 02:00 | Reconcile invoice counts per org |
| Data retention | Daily 03:00 | Clean up expired data per ZZPL |
| Database backup | Daily 04:00 | pg_dump → ZIP with checksums → R2 |
| Monthly archives | 1st of month 06:00 | Generate org archive ZIPs, email to billing contact |

---

## Configuration Files

| File | Location on Server | Purpose |
|------|-------------------|---------|
| Docker Compose | `/home/saldora/app/infra/docker/docker-compose.prod.yml` | Service definitions |
| Environment | `/home/saldora/app/infra/docker/.env.prod` | All secrets (chmod 600) |
| Caddyfile | `/home/saldora/app/infra/docker/Caddyfile` | Reverse proxy routing |
| Modal OCR | `/home/saldora/app/infra/modal/dots_ocr.py` | GPU OCR deployment |

---

## Modal OCR Management

```bash
# Deploy/update the OCR server
modal deploy infra/modal/dots_ocr.py

# Check deployment status
# Visit: https://modal.com/apps/cepa995/main/deployed/saldora-dots-ocr

# The OCR server scales to zero when idle (saves money).
# First request after idle has ~2 min cold start (model loading).
# Container stays warm 5 min after last request.
```

---

## Troubleshooting

### Site not loading
1. Check Cloudflare DNS: `saldora.rs` → `178.104.205.37` (proxied)
2. Check Caddy: `docker logs saldora-caddy --tail 20`
3. Check services: `docker ps`

### API returning 500
1. Check API logs: `docker logs saldora-api --tail 50`
2. Check DB connection: `docker exec saldora-postgres pg_isready -U saldora`
3. Check migrations: `docker exec saldora-api alembic current`

### Invoices stuck in "processing"
1. Check worker logs: `docker logs saldora-ocr-worker --tail 50`
2. Check Modal dashboard for OCR errors
3. Check Redis is up: `docker exec saldora-redis redis-cli -a <password> ping`

### Celery beat not running tasks
1. Check logs: `docker logs saldora-celery-beat --tail 20`
2. Verify Redis connection in logs
3. Restart: `docker restart saldora-celery-beat`

---

## Backup & Recovery

### Automated backups
- Daily at 04:00 UTC via Celery beat
- Stored in R2: `backups/db/saldora_YYYY-MM-DD.zip`
- Each ZIP contains: SQL dump (gzip) + manifest.json with checksums
- 30-day retention (older backups auto-deleted)

### Manual backup
```bash
ssh saldora@178.104.205.37 'docker exec saldora-ocr-worker celery -A ocr_worker.celery_app call ocr_worker.tasks.backup_database --queue=ocr'
```

### Restore from backup
```bash
# Download the backup ZIP from R2
# Extract the .sql.gz file
# Restore:
gunzip saldora_2026-04-14.sql.gz
docker exec -i saldora-postgres psql -U saldora -d saldora < saldora_2026-04-14.sql
```
