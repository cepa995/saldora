# OCR Worker Dockerfile
# The worker connects to the dots.ocr vLLM server via HTTP — no GPU needed here.
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies for OpenCV and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 worker
WORKDIR /app

# Copy and install ML package (base deps: torch, transformers, etc.)
COPY packages/ml /app/packages/ml
RUN pip install /app/packages/ml

# Install worker dependencies + openai client for dots.ocr server
RUN pip install celery[redis] boto3 httpx psycopg2-binary sqlalchemy openai

# Copy worker code
COPY workers/ocr_worker /app/ocr_worker

# Switch to non-root user
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -m celery -A ocr_worker.celery_app inspect ping -d celery@$HOSTNAME || exit 1

# Run Celery worker with solo pool
CMD ["python", "-m", "celery", "-A", "ocr_worker.celery_app", "worker", \
     "--loglevel=info", \
     "--pool=solo", \
     "--queues=ocr", \
     "--hostname=ocr-worker@%h"]
