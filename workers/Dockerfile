# OCR Worker Dockerfile with GPU support
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3-pip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 worker
WORKDIR /app

# Copy and install ML package first (changes less frequently)
COPY packages/ml /app/packages/ml
RUN pip3 install /app/packages/ml[gpu]

# Copy worker code
COPY workers/ocr_worker /app/ocr_worker

# Download models during build (optional - can also be done at runtime)
# RUN python3 -c "from fakturaai_ml import InvoicePipeline; p = InvoicePipeline(); import asyncio; asyncio.run(p._get_primary_engine().load())"

# Switch to non-root user
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD celery -A ocr_worker.celery_app inspect ping -d celery@$HOSTNAME || exit 1

# Run Celery worker
CMD ["celery", "-A", "ocr_worker.celery_app", "worker", \
     "--loglevel=info", \
     "--concurrency=1", \
     "--queues=ocr", \
     "--hostname=ocr-worker@%h"]
