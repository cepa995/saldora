"""Base OCR engine interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from PIL import Image


@dataclass
class OCRResult:
    """Result from OCR engine."""

    text: str
    confidence: float  # 0.0 to 1.0
    structured: dict[str, Any] = field(default_factory=dict)
    bounding_boxes: list[dict[str, Any]] = field(default_factory=list)
    language_detected: str = "sr"


class OCREngine(ABC):
    """Abstract base class for OCR engines."""

    @abstractmethod
    async def recognize(self, image: Image.Image) -> OCRResult:
        """
        Perform OCR on an image.

        Args:
            image: PIL Image to process

        Returns:
            OCRResult with extracted text and metadata
        """
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if the model is loaded and ready."""
        pass

    @abstractmethod
    async def load(self) -> None:
        """Load the model into memory."""
        pass

    @abstractmethod
    async def unload(self) -> None:
        """Unload the model from memory."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the engine name."""
        pass

    @property
    @abstractmethod
    def supported_languages(self) -> list[str]:
        """Return list of supported language codes."""
        pass
