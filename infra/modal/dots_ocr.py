"""Modal deployment for dots.ocr Vision-Language Model.

Runs the rednote-hilab/dots.ocr model on vLLM with an OpenAI-compatible
API. Scales to zero when idle, spins up on demand.

Deploy:
    modal deploy infra/modal/dots_ocr.py

Test locally:
    modal serve infra/modal/dots_ocr.py

The endpoint URL will be printed after deployment. Set it as:
    DOTS_OCR_SERVER_URL=https://<your-modal-app>.modal.run/v1
"""

import modal

MODEL_NAME = "rednote-hilab/dots.ocr"
GPU_TYPE = "A10G"  # 24GB VRAM, compute capability 8.6 (native FA2 support)
VLLM_PORT = 8000
API_SECRET = modal.Secret.from_name("dots-ocr-api-key")

# Build the image with vLLM, CUDA toolkit, and model weights baked in
vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.4.0-devel-ubuntu22.04", add_python="3.12")
    .pip_install(
        "vllm>=0.8.0",
        "torch>=2.5.0",
        "transformers>=4.45.0",
        "huggingface_hub>=0.26.0",
        "httpx>=0.28.0",
        "fastapi>=0.115.0",
    )
    .run_commands(
        f'python -c "from huggingface_hub import snapshot_download; snapshot_download(\'{MODEL_NAME}\')"',
    )
)

app = modal.App("saldora-dots-ocr")


@app.cls(
    image=vllm_image,
    gpu=GPU_TYPE,
    timeout=600,
    scaledown_window=300,
    secrets=[API_SECRET],
)
@modal.concurrent(max_inputs=4)
class DotsOCRServer:
    """vLLM server for dots.ocr, managed as a Modal class with lifecycle hooks."""

    @modal.enter()
    def start_vllm(self):
        """Start vLLM server and wait until it's ready (runs before serving)."""
        import subprocess
        import time

        import httpx

        self.process = subprocess.Popen(
            [
                "python",
                "-m",
                "vllm.entrypoints.openai.api_server",
                "--model",
                MODEL_NAME,
                "--trust-remote-code",
                "--chat-template-content-format",
                "string",
                "--max-model-len",
                "8192",
                "--gpu-memory-utilization",
                "0.90",
                "--port",
                str(VLLM_PORT),
                "--host",
                "127.0.0.1",
            ],
        )

        # Wait for vLLM to be fully ready (model load + CUDA compilation)
        for i in range(300):  # 5 min timeout
            try:
                resp = httpx.get(f"http://127.0.0.1:{VLLM_PORT}/health", timeout=2)
                if resp.status_code == 200:
                    print(f"vLLM ready after {i} seconds")
                    return
            except (httpx.ConnectError, httpx.ReadTimeout):
                time.sleep(1)

        raise RuntimeError("vLLM failed to start within 5 minutes")

    @modal.exit()
    def stop_vllm(self):
        """Stop vLLM server on container shutdown."""
        if hasattr(self, "process"):
            self.process.terminate()
            self.process.wait(timeout=10)

    @modal.asgi_app()
    def web(self):
        """Return ASGI app that proxies to the running vLLM server."""
        import os

        import httpx
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse, Response

        proxy_app = FastAPI()
        expected_key = os.environ.get("API_KEY", "")

        @proxy_app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
        async def proxy(request: Request, path: str):
            """Forward all requests to the local vLLM server."""
            # Verify API key
            auth = request.headers.get("authorization", "")
            provided_key = auth.removeprefix("Bearer ").strip()
            if not expected_key or provided_key != expected_key:
                return JSONResponse(
                    {"error": "Unauthorized"}, status_code=401
                )

            body = await request.body()
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.request(
                    method=request.method,
                    url=f"http://127.0.0.1:{VLLM_PORT}/{path}",
                    content=body,
                    headers={
                        k: v
                        for k, v in request.headers.items()
                        if k.lower() not in ("host", "content-length")
                    },
                )
                return Response(
                    content=resp.content,
                    status_code=resp.status_code,
                    media_type=resp.headers.get("content-type", "application/json"),
                )

        return proxy_app
