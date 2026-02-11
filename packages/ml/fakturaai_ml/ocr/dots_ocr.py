"""dots.ocr engine implementation."""

import logging
from typing import Any

from PIL import Image

from fakturaai_ml.ocr.base import OCREngine, OCRResult

logger = logging.getLogger(__name__)


class DotsOCREngine(OCREngine):
    """
    dots.ocr Vision-Language Model for document OCR.

    Uses the rednote-hilab/dots.ocr model via vLLM for inference.
    Provides state-of-the-art multilingual document parsing including
    text, tables, and layout detection.

    Requirements:
        - vLLM >= 0.11.0
        - GPU with >= 6GB VRAM
    """

    MODEL_ID = "rednote-hilab/dots.ocr"

    def __init__(
        self,
        use_gpu: bool = True,
        model_path: str | None = None,
        max_tokens: int = 4096,
    ):
        """
        Initialize dots.ocr engine.

        Args:
            use_gpu: Whether to use GPU acceleration
            model_path: Custom model path (defaults to HuggingFace)
            max_tokens: Maximum tokens to generate
        """
        self.use_gpu = use_gpu
        self.model_path = model_path or self.MODEL_ID
        self.max_tokens = max_tokens
        self._model = None
        self._processor = None
        self._loaded = False

    @property
    def name(self) -> str:
        return "dots.ocr"

    @property
    def supported_languages(self) -> list[str]:
        # dots.ocr supports 100+ languages including Cyrillic
        return [
            "sr",
            "sr_cyrl",
            "sr_latn",  # Serbian
            "ru",  # Russian
            "en",  # English
            "de",
            "fr",
            "it",
            "es",  # Western European
            # ... and many more
        ]

    def is_loaded(self) -> bool:
        return self._loaded

    async def load(self) -> None:
        """Load dots.ocr model via vLLM."""
        if self._loaded:
            return

        try:
            from vllm import LLM, SamplingParams  # noqa: F401

            logger.info(f"Loading dots.ocr model from {self.model_path}")

            self._model = LLM(
                model=self.model_path,
                trust_remote_code=True,
                gpu_memory_utilization=0.90,
                max_model_len=8192,
            )

            self._loaded = True
            logger.info("dots.ocr model loaded successfully")

        except ImportError:
            logger.error("vLLM not installed. Install with: pip install fakturaai-ml[dots]")
            raise
        except Exception as e:
            logger.error(f"Failed to load dots.ocr model: {e}")
            raise

    async def unload(self) -> None:
        """Unload model from memory."""
        if self._model is not None:
            del self._model
            self._model = None
            self._loaded = False

            # Force garbage collection
            import gc

            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    async def recognize(self, image: Image.Image) -> OCRResult:
        """
        Perform OCR using dots.ocr.

        Args:
            image: PIL Image to process

        Returns:
            OCRResult with extracted text, tables, and layout
        """
        if not self._loaded:
            await self.load()

        try:
            from vllm import SamplingParams

            # Prepare the prompt for dots.ocr
            # The model uses special prompts for different tasks
            prompt = self._build_prompt(image, task="full")

            sampling_params = SamplingParams(
                max_tokens=self.max_tokens,
                temperature=0.0,  # Deterministic for OCR
                top_p=1.0,
            )

            # Run inference
            outputs = self._model.generate([prompt], sampling_params)
            generated_text = outputs[0].outputs[0].text

            # Parse the structured output
            structured = self._parse_output(generated_text)

            # Extract plain text from structured output
            plain_text = self._extract_plain_text(structured)

            # Calculate confidence (dots.ocr doesn't provide per-character confidence,
            # so we estimate based on structure completeness)
            confidence = self._estimate_confidence(structured)

            return OCRResult(
                text=plain_text,
                confidence=confidence,
                structured=structured,
                language_detected="sr",  # Default for Serbian invoices
            )

        except Exception as e:
            logger.error(f"dots.ocr recognition failed: {e}")
            # Return empty result on failure
            return OCRResult(
                text="",
                confidence=0.0,
                structured={},
            )

    def _build_prompt(self, image: Image.Image, task: str = "full") -> dict[str, Any]:
        """Build the prompt for dots.ocr inference."""
        import base64
        import io

        # Convert image to base64
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode()

        # dots.ocr uses specific task prompts
        task_prompts = {
            "full": "Extract all text, tables, and structure from this document.",
            "text": "Extract all text from this document.",
            "table": "Extract all tables from this document.",
            "layout": "Analyze the layout of this document.",
        }

        return {
            "prompt": task_prompts.get(task, task_prompts["full"]),
            "multi_modal_data": {
                "image": f"data:image/png;base64,{image_base64}",
            },
        }

    def _parse_output(self, output: str) -> dict[str, Any]:
        """Parse dots.ocr output into structured format."""
        import json

        try:
            # dots.ocr outputs JSON/Markdown, try to parse
            if output.strip().startswith("{"):
                return json.loads(output)
            elif output.strip().startswith("["):
                return {"items": json.loads(output)}
            else:
                # Treat as markdown/plain text
                return {"raw_text": output, "format": "markdown"}
        except json.JSONDecodeError:
            return {"raw_text": output, "format": "text"}

    def _extract_plain_text(self, structured: dict[str, Any]) -> str:
        """Extract plain text from structured output."""
        if "raw_text" in structured:
            return structured["raw_text"]

        # Recursively extract text from nested structure
        texts = []

        def extract(obj: Any) -> None:
            if isinstance(obj, str):
                texts.append(obj)
            elif isinstance(obj, dict):
                for v in obj.values():
                    extract(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract(item)

        extract(structured)
        return "\n".join(texts)

    def _estimate_confidence(self, structured: dict[str, Any]) -> float:
        """Estimate overall confidence based on extraction completeness."""
        # Base confidence for successful extraction
        confidence = 0.85

        # Boost if we got structured tables
        if "table" in structured or "tables" in structured:
            confidence += 0.05

        # Boost if we got layout information
        if "layout" in structured or "regions" in structured:
            confidence += 0.05

        # Penalize if output seems incomplete
        raw_text = structured.get("raw_text", "")
        if len(raw_text) < 100:
            confidence -= 0.15

        return min(max(confidence, 0.0), 1.0)
