"""OCR engines package."""

from fakturaai_ml.ocr.base import OCREngine, OCRResult
from fakturaai_ml.ocr.dots_ocr import DotsOCREngine
from fakturaai_ml.ocr.easyocr_fallback import EasyOCREngine

__all__ = ["OCREngine", "OCRResult", "DotsOCREngine", "EasyOCREngine"]
