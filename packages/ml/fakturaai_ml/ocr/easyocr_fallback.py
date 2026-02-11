"""EasyOCR fallback engine for Serbian Cyrillic."""

import logging
from typing import Any

import numpy as np
from PIL import Image

from fakturaai_ml.ocr.base import OCREngine, OCRResult

logger = logging.getLogger(__name__)


class EasyOCREngine(OCREngine):
    """
    EasyOCR engine with explicit Serbian Cyrillic support.

    Used as fallback when dots.ocr has low confidence,
    especially for Cyrillic text extraction.

    Supported scripts:
        - Serbian Cyrillic (sr_cyrl)
        - Serbian Latin (en)
        - Russian (ru) - helps with Cyrillic recognition
    """

    def __init__(
        self,
        use_gpu: bool = True,
        languages: list[str] | None = None,
    ):
        """
        Initialize EasyOCR engine.

        Args:
            use_gpu: Whether to use GPU acceleration
            languages: Language codes to use (defaults to Serbian + English)
        """
        self.use_gpu = use_gpu
        # Default languages for Serbian invoices
        self.languages = languages or ["sr_cyrl", "en"]
        self._reader = None
        self._loaded = False

    @property
    def name(self) -> str:
        return "easyocr"

    @property
    def supported_languages(self) -> list[str]:
        return [
            "sr_cyrl",  # Serbian Cyrillic
            "en",  # English / Latin
            "ru",  # Russian (Cyrillic support)
            "de",
            "fr",
            "it",
            "es",  # Western European
        ]

    def is_loaded(self) -> bool:
        return self._loaded

    async def load(self) -> None:
        """Load EasyOCR reader."""
        if self._loaded:
            return

        try:
            import easyocr

            logger.info(f"Loading EasyOCR with languages: {self.languages}")

            self._reader = easyocr.Reader(
                self.languages,
                gpu=self.use_gpu,
                model_storage_directory=None,  # Use default
                download_enabled=True,
                detector=True,
                recognizer=True,
            )

            self._loaded = True
            logger.info("EasyOCR loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load EasyOCR: {e}")
            raise

    async def unload(self) -> None:
        """Unload reader from memory."""
        if self._reader is not None:
            del self._reader
            self._reader = None
            self._loaded = False

            import gc

            gc.collect()

    async def recognize(self, image: Image.Image) -> OCRResult:
        """
        Perform OCR using EasyOCR.

        Args:
            image: PIL Image to process

        Returns:
            OCRResult with extracted text and bounding boxes
        """
        if not self._loaded:
            await self.load()

        try:
            # Convert PIL Image to numpy array
            image_np = np.array(image)

            # Run OCR
            results = self._reader.readtext(
                image_np,
                detail=1,  # Return bounding boxes
                paragraph=False,  # Don't merge into paragraphs yet
                contrast_ths=0.1,
                adjust_contrast=0.5,
                text_threshold=0.7,
                low_text=0.4,
                link_threshold=0.4,
            )

            # Process results
            texts = []
            bounding_boxes = []
            confidences = []

            for bbox, text, confidence in results:
                texts.append(text)
                confidences.append(confidence)

                # Convert bbox to standard format
                # EasyOCR returns [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                bounding_boxes.append(
                    {
                        "text": text,
                        "confidence": confidence,
                        "box": {
                            "x1": min(x_coords),
                            "y1": min(y_coords),
                            "x2": max(x_coords),
                            "y2": max(y_coords),
                        },
                    }
                )

            # Combine text (attempt to maintain reading order)
            combined_text = self._combine_text_blocks(bounding_boxes)

            # Calculate overall confidence
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                text=combined_text,
                confidence=overall_confidence,
                structured={"blocks": bounding_boxes},
                bounding_boxes=bounding_boxes,
                language_detected=self._detect_language(combined_text),
            )

        except Exception as e:
            logger.error(f"EasyOCR recognition failed: {e}")
            return OCRResult(
                text="",
                confidence=0.0,
                structured={},
            )

    def _combine_text_blocks(self, blocks: list[dict[str, Any]]) -> str:
        """
        Combine text blocks maintaining reading order.

        Groups blocks by vertical position, then sorts horizontally.
        """
        if not blocks:
            return ""

        # Sort by y1, then x1
        sorted_blocks = sorted(
            blocks,
            key=lambda b: (b["box"]["y1"], b["box"]["x1"]),
        )

        # Group into lines (blocks with similar y positions)
        lines: list[list[dict[str, Any]]] = []
        current_line: list[dict[str, Any]] = []
        current_y = None
        line_height_threshold = 20  # pixels

        for block in sorted_blocks:
            y = block["box"]["y1"]
            if current_y is None or abs(y - current_y) <= line_height_threshold:
                current_line.append(block)
                current_y = y if current_y is None else (current_y + y) / 2
            else:
                if current_line:
                    lines.append(current_line)
                current_line = [block]
                current_y = y

        if current_line:
            lines.append(current_line)

        # Sort each line horizontally and combine
        text_lines = []
        for line in lines:
            line_sorted = sorted(line, key=lambda b: b["box"]["x1"])
            line_text = " ".join(b["text"] for b in line_sorted)
            text_lines.append(line_text)

        return "\n".join(text_lines)

    def _detect_language(self, text: str) -> str:
        """Detect if text is primarily Cyrillic or Latin."""
        if not text:
            return "sr"

        cyrillic_count = sum(1 for c in text if "\u0400" <= c <= "\u04ff")
        latin_count = sum(1 for c in text if "A" <= c.upper() <= "Z")

        if cyrillic_count > latin_count:
            return "sr_cyrl"
        return "sr_latn"
