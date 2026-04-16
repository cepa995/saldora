# OCR Worker Dockerfile
# The worker connects to the dots.ocr vLLM server via HTTP — no GPU needed here.
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
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
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 worker
WORKDIR /app

# Install CPU-only PyTorch first — the worker talks to external services
# (dots.ocr vLLM server, Claude API) via HTTP so CUDA is unnecessary.
# This avoids downloading ~2 GB of nvidia_cu* packages.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy and install ML package in editable mode so volume mounts work in dev
COPY packages/ml /app/packages/ml
RUN pip install -e /app/packages/ml

# Install worker dependencies + openai client for dots.ocr server
RUN pip install celery[redis] boto3 httpx psycopg2-binary sqlalchemy openai anthropic

# Copy worker code
COPY workers/ocr_worker /app/ocr_worker

# Switch to non-root user
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -m celery -A ocr_worker.celery_app inspect ping -d celery@$HOSTNAME || exit 1

# Run Celery worker with prefork pool (8 concurrent tasks — worker is I/O bound, sends HTTPS to Modal)
CMD ["python", "-m", "celery", "-A", "ocr_worker.celery_app", "worker", \
     "--loglevel=info", \
     "--pool=prefork", \
     "--concurrency=8", \
     "--queues=ocr", \
     "--hostname=ocr-worker@%h"]
