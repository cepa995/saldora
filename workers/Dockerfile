# OCR Worker Dockerfile with GPU support
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies + Python 3.12 via deadsnakes PPA (Ubuntu 22.04 ships 3.10)
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.12 as default and install pip
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && python3 -m ensurepip --upgrade \
    && python3 -m pip install --upgrade pip

# Create non-root user
RUN useradd -m -u 1000 worker
WORKDIR /app

# Copy and install ML package (base deps include torch, transformers, easyocr)
# Note: [gpu] extra skipped — flash-attn requires torch at build time.
# GPU acceleration works via CUDA base image + torch auto-detection.
COPY packages/ml /app/packages/ml
RUN python3 -m pip install /app/packages/ml

# Install worker dependencies (not in ML package)
RUN python3 -m pip install celery[redis] boto3 httpx psycopg2-binary sqlalchemy

# Copy worker code
COPY workers/ocr_worker /app/ocr_worker

# Download models during build (optional - can also be done at runtime)
# RUN python3 -c "from fakturaai_ml import InvoicePipeline; p = InvoicePipeline(); import asyncio; asyncio.run(p._get_primary_engine().load())"

# Switch to non-root user
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -m celery -A ocr_worker.celery_app inspect ping -d celery@$HOSTNAME || exit 1

# Run Celery worker
CMD ["python3", "-m", "celery", "-A", "ocr_worker.celery_app", "worker", \
     "--loglevel=info", \
     "--concurrency=1", \
     "--queues=ocr", \
     "--hostname=ocr-worker@%h"]
