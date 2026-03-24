"""dots.ocr vLLM server on Cerebrium.

Serves the rednote-hilab/dots.ocr vision-language model via an
OpenAI-compatible chat completions API. Called by Saldora's OCR worker.
"""

import json
import time
from typing import Any

from pydantic import BaseModel
from vllm import SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine

# Initialize vLLM engine at import time (runs once on cold start)
engine_args = AsyncEngineArgs(
    model="rednote-hilab/dots.ocr",
    trust_remote_code=True,
    max_model_len=8192,
    gpu_memory_utilization=0.90,
)
engine = AsyncLLMEngine.from_engine_args(engine_args)


class Message(BaseModel):
    """OpenAI-compatible chat message."""

    role: str
    content: Any  # str or list (for multimodal with image_url)


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    model: str = "rednote-hilab/dots.ocr"
    messages: list[dict]
    max_tokens: int = 4096
    temperature: float = 0.0
    top_p: float = 1.0


class Choice(BaseModel):
    """Single completion choice."""

    index: int = 0
    message: dict
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]


async def run(
    messages: list[dict],
    model: str = "rednote-hilab/dots.ocr",
    max_tokens: int = 4096,
    temperature: float = 0.0,
    top_p: float = 1.0,
    run_id: str = "req-001",
    **kwargs,
) -> dict:
    """Process a chat completion request.

    Extracts the text prompt from messages and runs inference.
    Returns an OpenAI-compatible response.

    Args:
        messages: List of chat messages.
        model: Model name (ignored — always uses dots.ocr).
        max_tokens: Maximum tokens to generate.
        temperature: Sampling temperature.
        top_p: Top-p sampling parameter.
        run_id: Unique request ID.

    Returns:
        OpenAI-compatible chat completion response dict.
    """
    # Extract prompt text from messages
    prompt_parts = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            prompt_parts.append(content)
        elif isinstance(content, list):
            # Multimodal: extract text parts
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    prompt_parts.append(part["text"])

    prompt = " ".join(prompt_parts)

    sampling_params = SamplingParams(
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )

    # Generate (non-streaming)
    results = []
    async for output in engine.generate(prompt, sampling_params, run_id):
        results = output.outputs

    generated_text = results[0].text if results else ""
    finish_reason = results[0].finish_reason if results else "stop"

    response = ChatCompletionResponse(
        id=run_id,
        created=int(time.time()),
        model=model,
        choices=[
            Choice(
                message={"role": "assistant", "content": generated_text},
                finish_reason=finish_reason or "stop",
            )
        ],
    )

    return response.model_dump()
