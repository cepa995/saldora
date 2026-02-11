# dots.ocr User Guide for FakturaAI

A comprehensive guide for installing, testing, deploying, and scaling dots.ocr within the FakturaAI application.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Local Installation](#2-local-installation)
3. [Testing Locally](#3-testing-locally)
4. [Deployment](#4-deployment)
5. [Integration with FakturaAI](#5-integration-with-fakturaai)
6. [Scaling for Production](#6-scaling-for-production)
7. [API Reference](#7-api-reference)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Overview

### What is dots.ocr?

**dots.ocr** is a multilingual document parser that unifies layout detection and content recognition within a single vision-language model. Key features:

- **1.7B Parameters**: Compact yet powerful LLM foundation
- **State-of-the-Art Performance**: Best-in-class results on OmniDocBench
- **Multilingual Support**: 100+ languages including Serbian Cyrillic/Latin
- **Unified Architecture**: Single model for layout detection + text extraction
- **Multiple Output Formats**: JSON (structured), Markdown, HTML (tables), LaTeX (formulas)

### How It Fits in FakturaAI

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FakturaAI Architecture                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────────┐  │
│  │   Web   │───▶│   API   │───▶│  Redis  │───▶│   OCR Worker    │  │
│  │  (Next) │    │(FastAPI)│    │ (Queue) │    │  (dots.ocr)     │  │
│  └─────────┘    └─────────┘    └─────────┘    └────────┬────────┘  │
│                                                         │           │
│                                              ┌──────────▼──────────┐│
│                                              │   vLLM Server       ││
│                                              │   (GPU Instance)    ││
│                                              │   dots.ocr model    ││
│                                              └─────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Local Installation

### 2.1 Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Python** | 3.10 | 3.12 |
| **CUDA** | 11.8 | 12.8 |
| **GPU VRAM** | 8GB | 16GB+ |
| **RAM** | 16GB | 32GB |
| **Disk Space** | 20GB | 50GB |

### 2.2 Method 1: Conda Installation (Recommended)

```bash
# 1. Create and activate conda environment
conda create -n dots_ocr python=3.12
conda activate dots_ocr

# 2. Clone the repository (inside FakturaAI monorepo)
cd /home/cepa995/workspace/saas_projects/faktura-ai/packages/ml/playground/docs.ocr

# 3. Install PyTorch with CUDA support
# Check your CUDA version: nvcc --version
# For CUDA 12.8:
pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu128

# For CUDA 11.8:
pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu118

# 4. Install dots.ocr package
pip install -e .
```

### 2.3 Method 2: Docker Installation (Easier Setup)

```bash
# 1. Navigate to the docker directory
cd /home/cepa995/workspace/saas_projects/faktura-ai/packages/ml/playground/docs.ocr/docker

# 2. Download the model weights first
mkdir -p model/dots.ocr

# Download from HuggingFace
python ../tools/download_model.py --save_path ./model/dots.ocr

# Or download from ModelScope (faster in China)
python ../tools/download_model.py --type modelscope --save_path ./model/dots.ocr

# 3. Build and run with Docker Compose
docker compose up -d
```

### 2.4 Download Model Weights

> **Important**: Use a directory name **without periods** (e.g., `DotsOCR` instead of `dots.ocr`) for the model save path.

```bash
# Navigate to dots.ocr directory
cd /home/cepa995/workspace/saas_projects/faktura-ai/packages/ml/playground/docs.ocr

# Download from HuggingFace (default)
python tools/download_model.py

# Download from ModelScope (alternative)
python tools/download_model.py --type modelscope

# Verify the download
ls -la weights/DotsOCR/
# Expected files:
# - config.json
# - model-00001-of-00002.safetensors
# - model-00002-of-00002.safetensors
# - tokenizer.json
# - modeling_dots_ocr.py
```

---

## 3. Testing Locally

### 3.1 Start the vLLM Server

**Option A: Direct vLLM (Recommended for vLLM >= 0.11.0)**

```bash
# dots.ocr is officially integrated in vLLM >= 0.11.0
vllm serve rednote-hilab/dots.ocr \
    --trust-remote-code \
    --async-scheduling \
    --gpu-memory-utilization 0.95

# Or with local weights
vllm serve ./weights/DotsOCR \
    --trust-remote-code \
    --async-scheduling \
    --gpu-memory-utilization 0.95 \
    --served-model-name dotsocr-model
```

**Option B: Docker Compose**

```bash
cd /home/cepa995/workspace/saas_projects/faktura-ai/packages/ml/playground/docs.ocr/docker
docker compose up -d

# Check logs
docker logs -f dots-ocr-container
```

**Option C: HuggingFace Transformers (No vLLM)**

```bash
# Direct inference without server (slower, but simpler)
python demo/demo_hf.py
```

### 3.2 Test with Command Line

```bash
# Ensure vLLM server is running on port 8000

# Parse a single image
python dots_ocr/parser.py demo/demo_image1.jpg

# Parse a PDF document
python dots_ocr/parser.py demo/demo_pdf1.pdf --num_thread 64

# Layout detection only (faster, no text extraction)
python dots_ocr/parser.py demo/demo_image1.jpg --prompt prompt_layout_only_en

# Text extraction only (excludes headers/footers)
python dots_ocr/parser.py demo/demo_image1.jpg --prompt prompt_ocr

# Region-specific OCR with bounding box
python dots_ocr/parser.py demo/demo_image1.jpg \
    --prompt prompt_grounding_ocr \
    --bbox 163 241 1536 705
```

### 3.3 Test with Gradio Web UI

```bash
# Start the Gradio demo (default port 7860)
python demo/demo_gradio.py 7860

# Open in browser: http://localhost:7860
```

The Gradio interface provides:
- File upload for images and PDFs
- Multiple prompt mode selection
- Real-time layout visualization
- Markdown output preview
- JSON structured data view
- Downloadable results

### 3.4 Test with Python API

```python
from dots_ocr import DotsOCRParser

# Initialize parser (connects to vLLM server)
parser = DotsOCRParser(
    ip='localhost',
    port=8000,
    dpi=200,
    num_thread=64
)

# Parse a single image
results = parser.parse_file(
    input_path='path/to/invoice.jpg',
    output_dir='./output',
    prompt_mode='prompt_layout_all_en'
)

# Parse a PDF
results = parser.parse_file(
    input_path='path/to/document.pdf',
    output_dir='./output',
    prompt_mode='prompt_layout_all_en'
)

# Access results
for result in results:
    print(f"Page: {result.get('page_no', 0)}")
    print(f"Layout JSON: {result.get('layout_info_path')}")
    print(f"Markdown: {result.get('md_content_path')}")
    print(f"Visualization: {result.get('layout_image_path')}")
```

### 3.5 Verify Output Files

After parsing, check the output directory:

```
output/
└── invoice/
    ├── invoice.json          # Structured layout data with bboxes
    ├── invoice.md            # Formatted markdown content
    ├── invoice_nohf.md       # Markdown without headers/footers
    ├── invoice.jpg           # Visualization with bounding boxes
    └── invoice.jsonl         # Summary metadata
```

---

## 4. Deployment

### 4.1 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Production Architecture                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │   Staging    │    │  Production  │    │    GPU Node Pool         │  │
│  │   Cluster    │    │   Cluster    │    │  ┌────────────────────┐  │  │
│  │              │    │              │    │  │ vLLM Server 1      │  │  │
│  │  1 GPU Node  │    │  3+ GPU Nodes│    │  │ (dots.ocr)         │  │  │
│  │              │    │              │    │  ├────────────────────┤  │  │
│  │              │    │              │    │  │ vLLM Server 2      │  │  │
│  └──────────────┘    └──────────────┘    │  │ (dots.ocr)         │  │  │
│                                           │  ├────────────────────┤  │  │
│                                           │  │ vLLM Server N      │  │  │
│                                           │  │ (dots.ocr)         │  │  │
│                                           │  └────────────────────┘  │  │
│                                           └──────────────────────────┘  │
│                                                        ▲                 │
│                                                        │                 │
│  ┌─────────────────────────────────────────────────────┼─────────────┐  │
│  │                    Load Balancer                     │             │  │
│  │              (Round-robin / Least-connections)       │             │  │
│  └──────────────────────────────────────────────────────┴─────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Staging Deployment

**Step 1: Prepare Kubernetes Manifests**

Create `infra/k8s/staging/dots-ocr-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dots-ocr-server
  namespace: fakturaai-staging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: dots-ocr-server
  template:
    metadata:
      labels:
        app: dots-ocr-server
    spec:
      containers:
      - name: dots-ocr
        image: vllm/vllm-openai:v0.11.0
        command:
        - "vllm"
        - "serve"
        - "rednote-hilab/dots.ocr"
        - "--trust-remote-code"
        - "--async-scheduling"
        - "--gpu-memory-utilization"
        - "0.9"
        - "--tensor-parallel-size"
        - "1"
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "32Gi"
            cpu: "8"
          requests:
            nvidia.com/gpu: 1
            memory: "16Gi"
            cpu: "4"
        env:
        - name: HUGGING_FACE_HUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-token
              key: token
        volumeMounts:
        - name: model-cache
          mountPath: /root/.cache/huggingface
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: dots-ocr-model-cache
      nodeSelector:
        cloud.google.com/gke-accelerator: nvidia-tesla-t4
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
---
apiVersion: v1
kind: Service
metadata:
  name: dots-ocr-service
  namespace: fakturaai-staging
spec:
  selector:
    app: dots-ocr-server
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

**Step 2: Create PersistentVolumeClaim for Model Cache**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dots-ocr-model-cache
  namespace: fakturaai-staging
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: standard-rwo
```

**Step 3: Deploy to Staging**

```bash
# Create namespace
kubectl create namespace fakturaai-staging

# Create HuggingFace token secret
kubectl create secret generic hf-token \
    --from-literal=token=YOUR_HF_TOKEN \
    -n fakturaai-staging

# Apply manifests
kubectl apply -f infra/k8s/staging/dots-ocr-pvc.yaml
kubectl apply -f infra/k8s/staging/dots-ocr-deployment.yaml

# Verify deployment
kubectl get pods -n fakturaai-staging -l app=dots-ocr-server
kubectl logs -f deployment/dots-ocr-server -n fakturaai-staging
```

### 4.3 Production Deployment

**Step 1: Create Production Manifests**

Create `infra/k8s/production/dots-ocr-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dots-ocr-server
  namespace: fakturaai-production
spec:
  replicas: 3  # Multiple replicas for high availability
  selector:
    matchLabels:
      app: dots-ocr-server
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: dots-ocr-server
    spec:
      containers:
      - name: dots-ocr
        image: vllm/vllm-openai:v0.11.0
        command:
        - "vllm"
        - "serve"
        - "rednote-hilab/dots.ocr"
        - "--trust-remote-code"
        - "--async-scheduling"
        - "--gpu-memory-utilization"
        - "0.95"
        - "--tensor-parallel-size"
        - "1"
        - "--max-model-len"
        - "32768"
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "48Gi"
            cpu: "16"
          requests:
            nvidia.com/gpu: 1
            memory: "32Gi"
            cpu: "8"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
        env:
        - name: HUGGING_FACE_HUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-token
              key: token
        volumeMounts:
        - name: model-cache
          mountPath: /root/.cache/huggingface
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: dots-ocr-model-cache
      nodeSelector:
        cloud.google.com/gke-accelerator: nvidia-tesla-a100
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: dots-ocr-server
              topologyKey: kubernetes.io/hostname
---
apiVersion: v1
kind: Service
metadata:
  name: dots-ocr-service
  namespace: fakturaai-production
spec:
  selector:
    app: dots-ocr-server
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: dots-ocr-hpa
  namespace: fakturaai-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: dots-ocr-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: gpu_utilization
      target:
        type: AverageValue
        averageValue: "80"
```

**Step 2: Deploy to Production**

```bash
# Create namespace
kubectl create namespace fakturaai-production

# Create secrets
kubectl create secret generic hf-token \
    --from-literal=token=YOUR_HF_TOKEN \
    -n fakturaai-production

# Apply manifests
kubectl apply -f infra/k8s/production/

# Monitor rollout
kubectl rollout status deployment/dots-ocr-server -n fakturaai-production
```

### 4.4 GPU Cloud Provider Options

| Provider | GPU Type | Recommended Instance | Approx. Cost/hr |
|----------|----------|---------------------|-----------------|
| **GCP** | NVIDIA T4 | n1-standard-8 + 1xT4 | $0.95 |
| **GCP** | NVIDIA A100 | a2-highgpu-1g | $3.67 |
| **AWS** | NVIDIA T4 | g4dn.xlarge | $0.526 |
| **AWS** | NVIDIA A10G | g5.xlarge | $1.006 |
| **Azure** | NVIDIA T4 | NC4as_T4_v3 | $0.526 |
| **RunPod** | NVIDIA A100 | Community Cloud | $1.89 |

---

## 5. Integration with FakturaAI

### 5.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FakturaAI OCR Processing Flow                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. User uploads invoice                                                 │
│     │                                                                    │
│     ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ FastAPI (/api/v1/invoices/upload)                               │    │
│  │   - Validate file type (PDF, JPG, PNG)                          │    │
│  │   - Save to S3/MinIO                                            │    │
│  │   - Create invoice record (status: PENDING)                     │    │
│  │   - Queue Celery task                                           │    │
│  │   - Return job_id immediately                                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     │                                                                    │
│     ▼                                                                    │
│  2. Celery task queued to Redis                                         │
│     │                                                                    │
│     ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ OCR Worker (picks up task)                                      │    │
│  │   - Download document from S3                                   │    │
│  │   - Call dots.ocr vLLM API                                      │    │
│  │   - Parse structured response                                   │    │
│  │   - Extract invoice fields (PIB, amounts, dates)                │    │
│  │   - Validate with business rules                                │    │
│  │   - Save results to PostgreSQL                                  │    │
│  │   - Update invoice status (COMPLETED/FAILED)                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│     │                                                                    │
│     ▼                                                                    │
│  3. User polls for status or receives webhook                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 OCR Worker Implementation

Create/update `workers/ocr_worker/dots_ocr_client.py`:

```python
"""
dots.ocr client for FakturaAI OCR Worker
"""
import httpx
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any
from PIL import Image
import io


class DotsOCRClient:
    """
    Client for communicating with dots.ocr vLLM server
    """

    def __init__(
        self,
        host: str = "dots-ocr-service",
        port: int = 8000,
        protocol: str = "http",
        model_name: str = "rednote-hilab/dots.ocr",
        timeout: float = 120.0,
    ):
        self.base_url = f"{protocol}://{host}:{port}"
        self.model_name = model_name
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _encode_image(self, image: Image.Image) -> str:
        """Encode PIL Image to base64 string"""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _get_prompt(self, mode: str = "full") -> str:
        """Get the appropriate prompt for the task"""
        prompts = {
            "full": """Please output the layout information from the PDF image, including each layout element's bbox, its category, and the corresponding text content within the bbox.

1. Bbox format: [x1, y1, x2, y2]

2. Layout Categories: The possible categories are ['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer', 'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title'].

3. Text Extraction & Formatting Rules:
    - Picture: For the 'Picture' category, the text field should be omitted.
    - Formula: Format its text as LaTeX.
    - Table: Format its text as HTML.
    - All Others (Text, Title, etc.): Format their text as Markdown.

4. Constraints:
    - The output text must be the original text from the image, with no translation.
    - All layout elements must be sorted according to human reading order.

5. Final Output: The entire output must be a single JSON object.""",

            "layout_only": """Please output the layout information from the PDF image, including each layout element's bbox and its category.

1. Bbox format: [x1, y1, x2, y2]
2. Layout Categories: ['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer', 'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title']
3. All layout elements must be sorted according to human reading order.
4. Final Output: The entire output must be a single JSON object.""",

            "text_only": """Please output all the text from the PDF image in the correct reading order, formatted as markdown. Do not include any page headers or page footers."""
        }
        return prompts.get(mode, prompts["full"])

    async def parse_image(
        self,
        image: Image.Image,
        mode: str = "full",
        temperature: float = 0.1,
        max_tokens: int = 16384,
    ) -> Dict[str, Any]:
        """
        Parse a single image with dots.ocr

        Args:
            image: PIL Image to parse
            mode: "full" | "layout_only" | "text_only"
            temperature: Model temperature
            max_tokens: Maximum tokens for response

        Returns:
            Dict containing layout information and extracted text
        """
        image_b64 = self._encode_image(image)
        prompt = self._get_prompt(mode)

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = await self.client.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload
        )
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        return {
            "raw_response": content,
            "usage": result.get("usage", {}),
        }

    async def parse_document(
        self,
        images: List[Image.Image],
        mode: str = "full",
    ) -> List[Dict[str, Any]]:
        """
        Parse multiple images (e.g., PDF pages) concurrently

        Args:
            images: List of PIL Images
            mode: Parsing mode

        Returns:
            List of results, one per image
        """
        import asyncio

        tasks = [
            self.parse_image(image, mode=mode)
            for image in images
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        parsed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                parsed_results.append({
                    "page": i,
                    "error": str(result),
                    "success": False
                })
            else:
                parsed_results.append({
                    "page": i,
                    **result,
                    "success": True
                })

        return parsed_results
```

### 5.3 Celery Task Implementation

Update `workers/ocr_worker/tasks.py`:

```python
"""
Celery tasks for OCR processing with dots.ocr
"""
import asyncio
import json
from celery import shared_task
from PIL import Image
import fitz  # PyMuPDF
import io

from ocr_worker.celery_app import app
from ocr_worker.dots_ocr_client import DotsOCRClient
from fakturaai_ml.extraction import InvoiceExtractor
from fakturaai_ml.validation import InvoiceValidator


# Configuration from environment
import os
DOTS_OCR_HOST = os.getenv("DOTS_OCR_HOST", "dots-ocr-service")
DOTS_OCR_PORT = int(os.getenv("DOTS_OCR_PORT", "8000"))


def pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> list[Image.Image]:
    """Convert PDF bytes to list of PIL Images"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)

    doc.close()
    return images


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_invoice_with_dots_ocr(
    self,
    invoice_id: str,
    document_path: str,
    file_type: str,
):
    """
    Process an invoice document using dots.ocr

    Args:
        invoice_id: UUID of the invoice record
        document_path: S3 path to the document
        file_type: "pdf" | "image"
    """
    from app.services.storage import download_from_s3
    from app.services.invoice import update_invoice_status, save_ocr_results

    try:
        # Update status to PROCESSING
        update_invoice_status(invoice_id, "PROCESSING", progress=10)

        # Download document from S3
        document_bytes = download_from_s3(document_path)
        update_invoice_status(invoice_id, "PROCESSING", progress=20)

        # Convert to images
        if file_type == "pdf":
            images = pdf_to_images(document_bytes)
        else:
            images = [Image.open(io.BytesIO(document_bytes))]

        update_invoice_status(invoice_id, "PROCESSING", progress=30)

        # Run OCR with dots.ocr
        async def run_ocr():
            async with DotsOCRClient(
                host=DOTS_OCR_HOST,
                port=DOTS_OCR_PORT
            ) as client:
                return await client.parse_document(images, mode="full")

        ocr_results = asyncio.run(run_ocr())
        update_invoice_status(invoice_id, "PROCESSING", progress=60)

        # Extract invoice fields from OCR results
        extractor = InvoiceExtractor()
        extracted_data = extractor.extract_from_dots_ocr(ocr_results)
        update_invoice_status(invoice_id, "PROCESSING", progress=80)

        # Validate extracted data
        validator = InvoiceValidator()
        validation_result = validator.validate(extracted_data)

        # Save results
        save_ocr_results(
            invoice_id=invoice_id,
            ocr_results=ocr_results,
            extracted_data=extracted_data,
            validation_warnings=validation_result.warnings,
            confidence_score=validation_result.confidence,
        )

        update_invoice_status(invoice_id, "COMPLETED", progress=100)

        return {
            "invoice_id": invoice_id,
            "status": "success",
            "confidence": validation_result.confidence,
            "warnings": [w.message for w in validation_result.warnings],
        }

    except Exception as exc:
        update_invoice_status(invoice_id, "FAILED", error=str(exc))

        # Retry on transient failures
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

        return {
            "invoice_id": invoice_id,
            "status": "failed",
            "error": str(exc),
        }
```

### 5.4 Environment Configuration

Add to `.env.example`:

```bash
# dots.ocr Configuration
DOTS_OCR_HOST=localhost
DOTS_OCR_PORT=8000
DOTS_OCR_TIMEOUT=120
DOTS_OCR_MODEL_NAME=rednote-hilab/dots.ocr

# For Kubernetes deployment
# DOTS_OCR_HOST=dots-ocr-service
# DOTS_OCR_PORT=8000
```

### 5.5 Docker Compose Integration (Development)

Add to `infra/docker/docker-compose.yml`:

```yaml
  # dots.ocr vLLM Server (GPU required)
  dots-ocr:
    image: vllm/vllm-openai:v0.11.0
    container_name: fakturaai-dots-ocr
    command:
      - "vllm"
      - "serve"
      - "rednote-hilab/dots.ocr"
      - "--trust-remote-code"
      - "--async-scheduling"
      - "--gpu-memory-utilization"
      - "0.9"
    ports:
      - "8001:8000"  # Use 8001 to avoid conflict with API
    environment:
      - HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}
    volumes:
      - huggingface_cache:/root/.cache/huggingface
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
              device_ids: ['0']

volumes:
  huggingface_cache:
```

---

## 6. Scaling for Production

### 6.1 Scaling Strategies

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Scaling Architecture for 1000s of Users             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                        Load Balancer                              │   │
│  │              (Kubernetes Service / Nginx / Traefik)               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                               │                                          │
│         ┌─────────────────────┼─────────────────────┐                   │
│         ▼                     ▼                     ▼                   │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐           │
│  │  vLLM Pod   │       │  vLLM Pod   │       │  vLLM Pod   │           │
│  │   (GPU 1)   │       │   (GPU 2)   │       │   (GPU N)   │           │
│  │             │       │             │       │             │           │
│  │ Concurrent  │       │ Concurrent  │       │ Concurrent  │           │
│  │ Requests:   │       │ Requests:   │       │ Requests:   │           │
│  │   ~50-100   │       │   ~50-100   │       │   ~50-100   │           │
│  └─────────────┘       └─────────────┘       └─────────────┘           │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Horizontal Pod Autoscaler                      │   │
│  │                                                                    │   │
│  │   Scale Triggers:                                                 │   │
│  │   - GPU Utilization > 80%                                        │   │
│  │   - Request Queue Depth > 100                                    │   │
│  │   - Average Latency > 30s                                        │   │
│  │                                                                    │   │
│  │   Min Replicas: 2    Max Replicas: 10                            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 vLLM Performance Tuning

```bash
vllm serve rednote-hilab/dots.ocr \
    --trust-remote-code \
    --async-scheduling \
    --gpu-memory-utilization 0.95 \
    --max-model-len 32768 \
    --max-num-seqs 256 \
    --max-num-batched-tokens 32768 \
    --enable-prefix-caching \
    --disable-log-requests
```

**Key Parameters:**

| Parameter | Description | Recommended |
|-----------|-------------|-------------|
| `--gpu-memory-utilization` | GPU memory fraction | 0.90-0.95 |
| `--max-model-len` | Max context length | 32768 |
| `--max-num-seqs` | Max concurrent sequences | 256 |
| `--max-num-batched-tokens` | Max tokens per batch | 32768 |
| `--enable-prefix-caching` | Cache common prefixes | Enabled |
| `--tensor-parallel-size` | Multi-GPU parallelism | 1-2 |

### 6.3 Queue-Based Processing

For handling thousands of concurrent users:

```python
# In workers/ocr_worker/celery_app.py

from celery import Celery

app = Celery(
    "ocr_worker",
    broker="redis://redis:6379/1",
    backend="redis://redis:6379/2",
)

app.conf.update(
    # Task routing
    task_routes={
        "ocr_worker.tasks.process_invoice_with_dots_ocr": {
            "queue": "ocr_high_priority"
        },
        "ocr_worker.tasks.batch_process_invoices": {
            "queue": "ocr_batch"
        },
    },

    # Worker configuration
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_concurrency=4,          # 4 concurrent tasks per worker

    # Task limits
    task_time_limit=300,           # 5 minute hard limit
    task_soft_time_limit=240,      # 4 minute soft limit

    # Result expiration
    result_expires=3600,           # 1 hour

    # Rate limiting
    task_annotations={
        "ocr_worker.tasks.process_invoice_with_dots_ocr": {
            "rate_limit": "100/m",  # 100 tasks per minute
        }
    },
)
```

### 6.4 Caching Strategies

```python
# In workers/ocr_worker/cache.py

import hashlib
import redis
import json
from PIL import Image
import io

class OCRCache:
    """
    Cache OCR results to avoid re-processing identical documents
    """

    def __init__(self, redis_client: redis.Redis, ttl: int = 86400):
        self.redis = redis_client
        self.ttl = ttl  # 24 hours default

    def _get_image_hash(self, image: Image.Image) -> str:
        """Generate hash from image content"""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return hashlib.sha256(buffer.getvalue()).hexdigest()

    def get_cached_result(self, image: Image.Image) -> dict | None:
        """Check if result is cached"""
        key = f"ocr:result:{self._get_image_hash(image)}"
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    def cache_result(self, image: Image.Image, result: dict):
        """Cache OCR result"""
        key = f"ocr:result:{self._get_image_hash(image)}"
        self.redis.setex(key, self.ttl, json.dumps(result))
```

### 6.5 Monitoring & Observability

**Prometheus Metrics:**

```yaml
# Add to Kubernetes deployment
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: dots-ocr-metrics
  namespace: fakturaai-production
spec:
  selector:
    matchLabels:
      app: dots-ocr-server
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

**Key Metrics to Monitor:**

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `vllm:num_requests_running` | Active requests | > 90% capacity |
| `vllm:num_requests_waiting` | Queued requests | > 50 |
| `vllm:avg_prompt_throughput_toks_per_s` | Token throughput | < 500 |
| `vllm:gpu_cache_usage_perc` | GPU KV cache usage | > 95% |
| `vllm:e2e_request_latency_seconds` | Request latency | p99 > 60s |

**Grafana Dashboard Query Examples:**

```promql
# Requests per second
rate(vllm_request_success_total[5m])

# Average latency
histogram_quantile(0.95, rate(vllm_e2e_request_latency_seconds_bucket[5m]))

# GPU utilization
nvidia_gpu_duty_cycle

# Queue depth
vllm_num_requests_waiting
```

### 6.6 Capacity Planning

**Single GPU Throughput (T4/A10G):**

| Document Type | Pages | Processing Time | Throughput |
|---------------|-------|-----------------|------------|
| Single page invoice | 1 | ~3-5s | ~12-20/min |
| Multi-page PDF | 5 | ~15-25s | ~2-4/min |
| Complex tables | 1 | ~5-8s | ~7-12/min |

**Scaling Formula:**

```
Required GPUs = (Peak requests/minute) / (Throughput per GPU)

Example:
- Peak: 1000 documents/hour = ~17/min
- Throughput: 15/min per T4 GPU
- Required: ceil(17/15) = 2 GPUs minimum
- With 50% headroom: 3 GPUs recommended
```

---

## 7. API Reference

### 7.1 vLLM OpenAI-Compatible API

**Endpoint:** `POST /v1/chat/completions`

**Request:**

```json
{
  "model": "rednote-hilab/dots.ocr",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,{base64_image}"
          }
        },
        {
          "type": "text",
          "text": "Please output the layout information..."
        }
      ]
    }
  ],
  "temperature": 0.1,
  "max_tokens": 16384
}
```

**Response:**

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "rednote-hilab/dots.ocr",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "[{\"bbox\": [100, 200, 500, 300], \"category\": \"Text\", \"text\": \"...\"}]"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 1234,
    "completion_tokens": 5678,
    "total_tokens": 6912
  }
}
```

### 7.2 DotsOCRParser API

```python
from dots_ocr import DotsOCRParser

parser = DotsOCRParser(
    protocol='http',           # 'http' or 'https'
    ip='localhost',            # vLLM server host
    port=8000,                 # vLLM server port
    model_name='model',        # Model name for API
    temperature=0.1,           # Sampling temperature
    top_p=1.0,                 # Top-p sampling
    max_completion_tokens=16384,  # Max response tokens
    num_thread=64,             # Threads for PDF processing
    dpi=200,                   # PDF rendering DPI
    output_dir="./output",     # Output directory
    min_pixels=None,           # Min image pixels
    max_pixels=None,           # Max image pixels
    use_hf=False,              # Use HuggingFace instead of vLLM
)

# Parse file (auto-detects PDF vs image)
results = parser.parse_file(
    input_path='document.pdf',
    output_dir='./results',
    prompt_mode='prompt_layout_all_en',
)

# Parse single image
results = parser.parse_image(
    input_path='image.jpg',
    filename='output_name',
    prompt_mode='prompt_layout_all_en',
    save_dir='./results',
    fitz_preprocess=True,
)

# Parse PDF
results = parser.parse_pdf(
    input_path='document.pdf',
    filename='output_name',
    prompt_mode='prompt_layout_all_en',
    save_dir='./results',
)
```

### 7.3 Prompt Modes

| Mode | Description | Output |
|------|-------------|--------|
| `prompt_layout_all_en` | Full layout detection + text extraction | JSON with bboxes, categories, and text |
| `prompt_layout_only_en` | Layout detection only | JSON with bboxes and categories only |
| `prompt_ocr` | Text extraction only | Markdown text (no headers/footers) |
| `prompt_grounding_ocr` | Region-specific extraction | Text from specified bounding box |

---

## 8. Troubleshooting

### 8.1 Common Issues

**Issue: CUDA out of memory**

```bash
# Reduce GPU memory utilization
vllm serve ... --gpu-memory-utilization 0.8

# Or reduce max model length
vllm serve ... --max-model-len 16384
```

**Issue: Slow inference**

```bash
# Enable prefix caching
vllm serve ... --enable-prefix-caching

# Increase batch size
vllm serve ... --max-num-batched-tokens 32768
```

**Issue: Connection refused to vLLM server**

```bash
# Check if server is running
curl http://localhost:8000/health

# Check server logs
docker logs dots-ocr-container

# Verify port binding
netstat -tlnp | grep 8000
```

**Issue: JSON parsing failed in output**

```python
# The model sometimes outputs invalid JSON
# Use the filtered output fallback
result = parser.parse_file(input_path, ...)
if result.get('filtered'):
    # Use markdown text instead of JSON
    text = result.get('md_content_path')
```

### 8.2 Performance Optimization Tips

1. **Preprocessing**: Enable `fitz_preprocess` for low-DPI images
2. **Batch Processing**: Use `num_thread=64` for multi-page PDFs
3. **Caching**: Cache results for identical documents
4. **Image Size**: Optimal resolution is 1000-3000px width
5. **Queue Management**: Use separate queues for different priorities

### 8.3 Debugging Commands

```bash
# Test vLLM health
curl http://localhost:8000/health

# Check model info
curl http://localhost:8000/v1/models

# Test inference
python demo/demo_vllm.py --prompt_mode prompt_layout_all_en

# Check GPU utilization
nvidia-smi -l 1

# Monitor Celery workers
celery -A ocr_worker inspect active

# Check Redis queue depth
redis-cli LLEN celery
```

### 8.4 Log Locations

| Component | Log Location |
|-----------|--------------|
| vLLM Server | `docker logs dots-ocr-container` |
| Celery Worker | `docker logs fakturaai-ocr-worker` |
| Kubernetes | `kubectl logs -f deployment/dots-ocr-server` |
| Application | `./logs/ocr_worker.log` |

---

## Further Reading

- [dots.ocr GitHub Repository](https://github.com/rednote-hilab/dots.ocr)
- [vLLM Documentation](https://docs.vllm.ai/)
- [FakturaAI Architecture Guide](./ARCHITECTURE.md)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
- [Kubernetes GPU Scheduling](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
