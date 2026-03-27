# Cerebrium — dots.ocr Deployment Guide

Deploy the dots.ocr VLM as a serverless GPU service on Cerebrium.
Scales to zero when idle — you only pay for actual inference time (~$3-15/month).

## Prerequisites

- Cerebrium account (https://www.cerebrium.ai — free tier available)
- Python 3.10+ with pip

## Step 1: Install CLI and Login

```bash
pip install cerebrium
cerebrium login
```

This opens a browser to authenticate.

## Step 2: Deploy

```bash
cd infra/cerebrium/dots-ocr
cerebrium deploy
```

First deployment takes 5-10 minutes (downloads model weights).
Subsequent deployments are fast (code changes only).

Output will show something like:
```
Deploying dots-ocr...
✓ Deployed successfully
Endpoint: https://api.cortex.cerebrium.ai/v4/p-XXXXX/dots-ocr/run
```

Note the endpoint URL and your project ID.

## Step 3: Get Your API Key

Go to https://dashboard.cerebrium.ai → Settings → API Keys.
Copy your JWT token.

## Step 4: Test the Deployment

```bash
curl -X POST "https://api.cortex.cerebrium.ai/v4/p-YOUR_PROJECT_ID/dots-ocr/run" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "test"}],
    "max_tokens": 10
  }'
```

First call triggers cold start (~2-10 seconds). Subsequent calls: ~3-5 seconds.

## Step 5: Configure Saldora

In your production `infra/docker/.env`:

```env
DOTS_OCR_SERVER_URL=https://api.cortex.cerebrium.ai/v4/p-YOUR_PROJECT_ID/dots-ocr
DOTS_OCR_API_KEY=YOUR_JWT_TOKEN
DOTS_OCR_MODEL_NAME=rednote-hilab/dots.ocr
```

**Important:** The Cerebrium endpoint format is different from vLLM's OpenAI API.
Saldora's OCR worker calls `/v1/chat/completions` on the configured URL, but
Cerebrium expects calls to `/run`. The OCR worker's OpenAI client needs the
base URL set to the Cerebrium endpoint, and the `run` function in `main.py`
handles the translation.

## Step 6: Verify in Saldora

1. Rebuild the OCR worker: `docker compose -f infra/docker/docker-compose.yml up --build -d --no-deps ocr-worker`
2. Upload an invoice
3. Check worker logs: `docker logs -f saldora-ocr-worker`
4. Check Cerebrium dashboard for request logs

## Cost Estimate

Cerebrium pricing: ~$0.000164/sec for T4, ~$0.0006/sec for A10.

| Invoices/month | GPU seconds (5s each) | A10 cost | T4 cost |
|---------------|----------------------|----------|---------|
| 1,000 | 5,000s | ~$3 | ~$0.82 |
| 5,000 | 25,000s | ~$15 | ~$4.10 |
| 10,000 | 50,000s | ~$30 | ~$8.20 |
| 50,000 | 250,000s | ~$150 | ~$41 |

Plus Claude API (~$0.0045/invoice) and compute costs (CPU + memory).

## Configuration Reference

### cerebrium.toml

| Field | Value | Description |
|-------|-------|-------------|
| `compute` | `AMPERE_A10` | GPU type (24GB VRAM) |
| `min_replicas` | `0` | Scale to zero |
| `max_replicas` | `2` | Max concurrent instances |
| `cooldown` | `60` | Seconds before scaling down |
| `memory` | `14.0` | GB of system RAM |

### Available GPU Options

| GPU | VRAM | Cost/sec | Suitable? |
|-----|------|----------|-----------|
| T4 | 16GB | ~$0.000164 | Yes (cheapest) |
| A10 | 24GB | ~$0.0006 | Yes (recommended) |
| A100 40GB | 40GB | ~$0.0012 | Overkill |

## Troubleshooting

**Cold start too slow:**
- Increase `cooldown` in cerebrium.toml to keep instances warm longer
- Set `min_replicas = 1` during business hours (costs ~$2/hr for A10)

**Model loading error:**
- Ensure `trust_remote_code=True` in engine_args
- Check Cerebrium dashboard logs for specific error

**Timeout:**
- Cerebrium default timeout is 300s — sufficient for cold starts
- Check OCR worker `task_soft_time_limit` is >= 300s
