# Google Cloud Run GPU — dots.ocr Deployment Guide

Deploy the dots.ocr VLM as a serverless GPU service on Google Cloud Run.
Scales to zero when idle — you only pay for actual inference time (~$10-15/month for 5,000 invoices).

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed ([install guide](https://cloud.google.com/sdk/docs/install))
- Docker installed locally

## Step 1: Create a Google Cloud Project

```bash
# Create project (or use existing)
gcloud projects create saldora-production --name="Saldora"

# Set as active project
gcloud config set project saldora-production

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

## Step 2: Create Artifact Registry Repository

This stores your Docker image.

```bash
gcloud artifacts repositories create saldora \
  --repository-format=docker \
  --location=europe-west1 \
  --description="Saldora Docker images"
```

## Step 3: Build the dots.ocr Docker Image

Create a Dockerfile for the vLLM server that bakes in the model weights (faster cold starts).

```bash
# From the project root
cat > infra/cloud-run/Dockerfile.dots-ocr << 'EOF'
FROM vllm/vllm-openai:latest

# Download model weights at build time (baked into image = faster cold start)
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('rednote-hilab/dots.ocr')"

# vLLM server configuration
ENV MODEL_NAME=rednote-hilab/dots.ocr
ENV PORT=8000

CMD ["python", "-m", "vllm.entrypoints.openai.api_server", \
     "--model", "rednote-hilab/dots.ocr", \
     "--trust-remote-code", \
     "--chat-template-content-format", "string", \
     "--max-model-len", "8192", \
     "--gpu-memory-utilization", "0.90", \
     "--port", "8000", \
     "--host", "0.0.0.0"]
EOF
```

Build and push to Artifact Registry:

```bash
# Configure Docker to push to Artifact Registry
gcloud auth configure-docker europe-west1-docker.pkg.dev

# Build (this takes ~10-15 min — downloads the 1.7B model)
docker build \
  -f infra/cloud-run/Dockerfile.dots-ocr \
  -t europe-west1-docker.pkg.dev/saldora-production/saldora/dots-ocr:latest \
  .

# Push
docker push europe-west1-docker.pkg.dev/saldora-production/saldora/dots-ocr:latest
```

**Alternative: Build with Cloud Build (no local GPU needed):**

```bash
gcloud builds submit \
  --tag europe-west1-docker.pkg.dev/saldora-production/saldora/dots-ocr:latest \
  --dockerfile infra/cloud-run/Dockerfile.dots-ocr \
  --timeout=1800 \
  --machine-type=e2-highcpu-8
```

## Step 4: Deploy to Cloud Run with GPU

```bash
gcloud run deploy dots-ocr \
  --image europe-west1-docker.pkg.dev/saldora-production/saldora/dots-ocr:latest \
  --region europe-west1 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --cpu 4 \
  --memory 16Gi \
  --min-instances 0 \
  --max-instances 3 \
  --port 8000 \
  --timeout 300 \
  --concurrency 4 \
  --no-allow-unauthenticated \
  --set-env-vars="HF_HOME=/root/.cache/huggingface"
```

Key flags:
- `--min-instances 0` → scales to zero (pay nothing when idle)
- `--max-instances 3` → handles burst uploads
- `--gpu 1 --gpu-type nvidia-l4` → L4 GPU with 24GB VRAM
- `--timeout 300` → 5 min request timeout (for cold starts)
- `--no-allow-unauthenticated` → requires auth token (security)

## Step 5: Get the Service URL

```bash
gcloud run services describe dots-ocr \
  --region europe-west1 \
  --format="value(status.url)"
```

This returns something like: `https://dots-ocr-abc123-ew.a.run.app`

## Step 6: Create a Service Account for the OCR Worker

```bash
# Create service account
gcloud iam service-accounts create ocr-worker \
  --display-name="OCR Worker"

# Grant permission to invoke the Cloud Run service
gcloud run services add-iam-policy-binding dots-ocr \
  --region europe-west1 \
  --member="serviceAccount:ocr-worker@saldora-production.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Create a key file (for the Celery worker to authenticate)
gcloud iam service-accounts keys create /tmp/ocr-worker-key.json \
  --iam-account=ocr-worker@saldora-production.iam.gserviceaccount.com
```

## Step 7: Configure Saldora to Use Cloud Run

Since Cloud Run uses `--no-allow-unauthenticated`, the OCR worker needs to get
an identity token to call it. The simplest approach: use an API Gateway or
allow unauthenticated access with a custom API key header.

**Option A: Allow unauthenticated (simpler, use API key in code)**

```bash
gcloud run deploy dots-ocr \
  --region europe-west1 \
  --allow-unauthenticated \
  ... (same flags as above)
```

Then in your `.env` or `infra/docker/.env`:

```env
DOTS_OCR_SERVER_URL=https://dots-ocr-abc123-ew.a.run.app/v1
DOTS_OCR_MODEL_NAME=rednote-hilab/dots.ocr
DOTS_OCR_API_KEY=unused
```

**Option B: Authenticated (more secure)**

The OCR worker needs to fetch an identity token before each request. This
requires changes to the OpenAI client setup. For initial deployment, Option A
is recommended.

## Step 8: Test the Deployment

```bash
# Get the service URL
URL=$(gcloud run services describe dots-ocr --region europe-west1 --format="value(status.url)")

# Test with a simple request (first call triggers cold start — wait ~30s)
curl -X POST "$URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "rednote-hilab/dots.ocr",
    "messages": [{"role": "user", "content": "test"}],
    "max_tokens": 10
  }'
```

First request takes 20-40 seconds (cold start). Subsequent requests: 3-5 seconds.

## Step 9: Update Saldora Production Config

In your production environment variables:

```env
DOTS_OCR_SERVER_URL=https://dots-ocr-abc123-ew.a.run.app/v1
DOTS_OCR_MODEL_NAME=rednote-hilab/dots.ocr
DOTS_OCR_API_KEY=unused
```

## Cost Estimate

| Invoices/month | GPU seconds | GPU cost | vCPU+memory | Total |
|---------------|------------|---------|-------------|-------|
| 1,000 | 5,000s | ~$1 | ~$2 | **~$3** |
| 5,000 | 25,000s | ~$5 | ~$8 | **~$13** |
| 10,000 | 50,000s | ~$10 | ~$15 | **~$25** |
| 50,000 | 250,000s | ~$47 | ~$70 | **~$117** |

Plus Claude API costs ($0.0045/invoice).

## Monitoring

```bash
# View logs
gcloud run services logs read dots-ocr --region europe-west1

# View metrics (request count, latency, instance count)
# Go to: https://console.cloud.google.com/run/detail/europe-west1/dots-ocr/metrics
```

## Troubleshooting

**Cold start too slow:**
- Bake model weights into Docker image (Step 3)
- Set `--min-instances 1` during business hours (adds ~$0.67/hr)

**Out of memory:**
- Increase `--memory` to 32Gi
- The L4 has 24GB VRAM — more than enough for dots.ocr (1.7B)

**Requests timing out:**
- Increase `--timeout` (max 3600s)
- Check Cloud Run logs for errors

**Model not loading:**
- Verify `--trust-remote-code` is set
- Check that HuggingFace cache is accessible
