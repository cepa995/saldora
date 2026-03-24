"""dots.ocr engine implementation.

Uses the official dots.ocr inference approach: a vLLM server running
the model, called via the OpenAI-compatible chat completions API.
"""

import base64
import io
import logging
import math
import os
from typing import Any

from PIL import Image

from fakturaai_ml.ocr.base import OCREngine, OCRResult

logger = logging.getLogger(__name__)


class DotsOCREngine(OCREngine):
    """
    dots.ocr Vision-Language Model for document OCR.

    Connects to a vLLM server running rednote-hilab/dots.ocr and calls it
    via the OpenAI-compatible chat completions API (the official approach).

    Requirements:
        - A running vLLM server serving dots.ocr
        - openai Python package
    """

    MODEL_ID = "rednote-hilab/dots.ocr"

    # Official dots.ocr prompt templates
    PROMPT_OCR = "Extract the text content from this image."
    PROMPT_LAYOUT = (
        "Please output the layout information from the PDF image, "
        "including each layout element's bbox, its category, and the "
        "corresponding text content within the bbox.\n\n"
        "1. Bbox format: [x1, y1, x2, y2]\n\n"
        "2. Layout Categories: The possible categories are "
        "['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer', "
        "'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title'].\n\n"
        "3. Text Extraction & Formatting Rules:\n"
        "    - Picture: For the 'Picture' category, the text field should be omitted.\n"
        "    - Formula: Format its text as LaTeX.\n"
        "    - Table: Format its text as HTML.\n"
        "    - All Others (Text, Title, etc.): Format their text as Markdown.\n\n"
        "4. Constraints:\n"
        "    - The output text must be the original text from the image, "
        "with no translation.\n"
        "    - All layout elements must be sorted according to human reading order.\n\n"
        "5. Final Output: The entire output must be a single JSON object."
    )

    def __init__(
        self,
        use_gpu: bool = True,
        model_path: str | None = None,
        max_tokens: int = 4096,
    ):
        """
        Initialize dots.ocr engine.

        Args:
            use_gpu: Whether to use GPU acceleration (unused — GPU is on the server side)
            model_path: Model name for the vLLM server
            max_tokens: Maximum tokens to generate
        """
        self.use_gpu = use_gpu
        self.model_path = model_path or self.MODEL_ID
        self.max_tokens = max_tokens
        self._client = None
        self._loaded = False
        self._server_url = os.getenv("DOTS_OCR_SERVER_URL", "http://localhost:8100/v1")
        self._model_name = os.getenv("DOTS_OCR_MODEL_NAME", "model")
        self._api_key = os.getenv("DOTS_OCR_API_KEY", "unused")

    @property
    def name(self) -> str:
        return "dots.ocr"

    @property
    def supported_languages(self) -> list[str]:
        return [
            "sr",
            "sr_cyrl",
            "sr_latn",
            "ru",
            "en",
            "de",
            "fr",
            "it",
            "es",
        ]

    def is_loaded(self) -> bool:
        return self._loaded

    async def load(self) -> None:
        """Connect to the vLLM server."""
        if self._loaded:
            return

        try:
            from openai import OpenAI

            logger.info("Connecting to dots.ocr vLLM server at %s", self._server_url)
            self._client = OpenAI(api_key=self._api_key, base_url=self._server_url)

            # Verify connection with a models list call
            models = self._client.models.list()
            logger.info(
                "dots.ocr server connected, available models: %s", [m.id for m in models.data]
            )

            self._loaded = True

        except ImportError:
            logger.error("openai package not installed. Install with: pip install openai")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to dots.ocr server: {e}")
            raise

    async def unload(self) -> None:
        """Disconnect from server."""
        self._client = None
        self._loaded = False

    @property
    def skip_preprocessing(self) -> bool:
        """VLMs work best with original color images — skip preprocessing."""
        return True

    async def recognize(self, image: Image.Image) -> OCRResult:
        """
        Perform OCR using dots.ocr via vLLM server.

        Args:
            image: PIL Image to process

        Returns:
            OCRResult with extracted text, tables, and layout
        """
        try:
            if not self._loaded:
                await self.load()

            # Ensure image is RGB
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Resize to fit model's max token budget (avoids 400 errors)
            new_h, new_w = self._smart_resize(image.height, image.width)
            if (new_h, new_w) != (image.height, image.width):
                logger.info(
                    "Resizing image from %dx%d to %dx%d for model constraints",
                    image.width,
                    image.height,
                    new_w,
                    new_h,
                )
                image = image.resize((new_w, new_h), Image.LANCZOS)

            # Convert image to base64 data URI
            image_uri = self._pil_to_data_uri(image)

            # Build messages following the official dots.ocr format
            prompt_text = self.PROMPT_OCR
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_uri},
                        },
                        {
                            "type": "text",
                            "text": f"<|img|><|imgpad|><|endofimg|>{prompt_text}",
                        },
                    ],
                }
            ]

            # Call vLLM server via OpenAI client
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                max_completion_tokens=self.max_tokens,
                temperature=0.0,
                top_p=1.0,
            )
            generated_text = response.choices[0].message.content or ""

            # Parse the structured output
            structured = self._parse_output(generated_text)
            plain_text = self._extract_plain_text(structured)
            confidence = self._estimate_confidence(structured)

            return OCRResult(
                text=plain_text,
                confidence=confidence,
                structured=structured,
                language_detected="sr",
            )

        except Exception as e:
            logger.error(f"dots.ocr recognition failed: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                structured={},
            )

    @staticmethod
    def _smart_resize(
        height: int,
        width: int,
        factor: int = 28,
        min_pixels: int = 3136,
        max_pixels: int = 2822400,
    ) -> tuple[int, int]:
        """Resize dimensions to fit model constraints.

        Ported from the official dots.ocr repository (image_utils.py).
        Ensures dimensions are divisible by factor and total pixels
        are within [min_pixels, max_pixels].

        Args:
            height: Original image height
            width: Original image width
            factor: Dimensions must be divisible by this
            min_pixels: Minimum total pixel count
            max_pixels: Maximum total pixel count (default keeps tokens < 8192)

        Returns:
            Tuple of (new_height, new_width)
        """

        def round_by(n: int, f: int) -> int:
            return round(n / f) * f

        def floor_by(n: int, f: int) -> int:
            return math.floor(n / f) * f

        def ceil_by(n: int, f: int) -> int:
            return math.ceil(n / f) * f

        h_bar = max(factor, round_by(height, factor))
        w_bar = max(factor, round_by(width, factor))

        if h_bar * w_bar > max_pixels:
            beta = math.sqrt((height * width) / max_pixels)
            h_bar = max(factor, floor_by(int(height / beta), factor))
            w_bar = max(factor, floor_by(int(width / beta), factor))
        elif h_bar * w_bar < min_pixels:
            beta = math.sqrt(min_pixels / (height * width))
            h_bar = ceil_by(int(height * beta), factor)
            w_bar = ceil_by(int(width * beta), factor)

        return h_bar, w_bar

    @staticmethod
    def _pil_to_data_uri(image: Image.Image) -> str:
        """Convert a PIL Image to a base64 data URI."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    def _parse_output(self, output: str) -> dict[str, Any]:
        """Parse dots.ocr output into structured format."""
        import json

        try:
            if output.strip().startswith("{"):
                return json.loads(output)
            elif output.strip().startswith("["):
                return {"items": json.loads(output)}
            else:
                return {"raw_text": output, "format": "markdown"}
        except json.JSONDecodeError:
            return {"raw_text": output, "format": "text"}

    def _extract_plain_text(self, structured: dict[str, Any]) -> str:
        """Extract plain text from structured output."""
        if "raw_text" in structured:
            return structured["raw_text"]

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
        confidence = 0.85

        if "table" in structured or "tables" in structured:
            confidence += 0.05
        if "layout" in structured or "regions" in structured:
            confidence += 0.05

        raw_text = structured.get("raw_text", "")
        if len(raw_text) < 100:
            confidence -= 0.15

        return min(max(confidence, 0.0), 1.0)
