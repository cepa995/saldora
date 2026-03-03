"""Main invoice processing pipeline."""

import logging
import time
from pathlib import Path
from typing import BinaryIO

from PIL import Image

from fakturaai_ml.extraction.fields import FieldExtractor
from fakturaai_ml.ocr.base import OCREngine
from fakturaai_ml.ocr.dots_ocr import DotsOCREngine
from fakturaai_ml.ocr.easyocr_fallback import EasyOCREngine
from fakturaai_ml.postprocessing.confidence import ConfidenceCalculator
from fakturaai_ml.preprocessing.image import ImagePreprocessor
from fakturaai_ml.preprocessing.pdf import PDFProcessor
from fakturaai_ml.types import ExtractedInvoice, ExtractionResult, ExtractionStatus
from fakturaai_ml.validation.math_check import MathValidator
from fakturaai_ml.validation.pib import PIBValidator

logger = logging.getLogger(__name__)


class InvoicePipeline:
    """
    Main pipeline for invoice OCR and data extraction.

    Supports both dots.ocr (primary) and EasyOCR (fallback) engines.
    Handles PDF and image inputs.

    Usage:
        pipeline = InvoicePipeline()
        result = await pipeline.extract(document_bytes)
    """

    def __init__(
        self,
        primary_engine: str = "dots",
        fallback_engine: str = "easyocr",
        confidence_threshold: float = 0.80,
        use_gpu: bool = True,
        model_path: str | None = None,
        use_llm: bool = False,
        llm_api_key: str | None = None,
        llm_model: str = "claude-sonnet-4-20250514",
    ):
        """
        Initialize the invoice processing pipeline.

        Args:
            primary_engine: Primary OCR engine ("dots" or "easyocr")
            fallback_engine: Fallback engine for low-confidence results
            confidence_threshold: Threshold below which to use fallback
            use_gpu: Whether to use GPU acceleration
            model_path: Custom path for model weights
            use_llm: Whether to use LLM-based field extraction (primary)
            llm_api_key: Anthropic API key for LLM extraction
            llm_model: Claude model to use for LLM extraction
        """
        self.confidence_threshold = confidence_threshold
        self.use_gpu = use_gpu

        # Initialize components
        self.image_preprocessor = ImagePreprocessor()
        self.pdf_processor = PDFProcessor()
        self.field_extractor = FieldExtractor()
        self.pib_validator = PIBValidator()
        self.math_validator = MathValidator()
        self.confidence_calculator = ConfidenceCalculator()

        # LLM extractor (primary field extraction when enabled)
        self._llm_extractor = None
        if use_llm:
            try:
                from fakturaai_ml.extraction.llm_extractor import LLMFieldExtractor

                self._llm_extractor = LLMFieldExtractor(api_key=llm_api_key, model=llm_model)
                logger.info("LLM field extraction enabled (model: %s)", llm_model)
            except Exception as e:
                logger.warning("Failed to initialize LLM extractor: %s", e)

        # Initialize OCR engines (lazy loading)
        self._primary_engine_name = primary_engine
        self._fallback_engine_name = fallback_engine
        self._primary_engine: OCREngine | None = None
        self._fallback_engine: OCREngine | None = None
        self._model_path = model_path

    def _get_primary_engine(self) -> OCREngine:
        """Lazy load primary OCR engine."""
        if self._primary_engine is None:
            if self._primary_engine_name == "dots":
                self._primary_engine = DotsOCREngine(
                    use_gpu=self.use_gpu,
                    model_path=self._model_path,
                )
            else:
                self._primary_engine = EasyOCREngine(use_gpu=self.use_gpu)
        return self._primary_engine

    def _get_fallback_engine(self) -> OCREngine | None:
        """Lazy load fallback OCR engine. Returns None if fallback is disabled."""
        if self._fallback_engine_name == "none":
            return None
        if self._fallback_engine is None:
            self._fallback_engine = EasyOCREngine(use_gpu=self.use_gpu)
        return self._fallback_engine

    async def extract(
        self,
        document: bytes | BinaryIO | Path,
        document_type: str | None = None,
    ) -> ExtractionResult:
        """
        Extract invoice data from a document.

        Args:
            document: Document as bytes, file handle, or path
            document_type: Optional hint for document type ("pdf", "image")

        Returns:
            ExtractionResult with extracted data and confidence scores
        """
        start_time = time.perf_counter()

        try:
            # Load document
            images = await self._load_document(document, document_type)

            if not images:
                return ExtractionResult(
                    status=ExtractionStatus.FAILED,
                    invoice=ExtractedInvoice(),
                    warnings=[],
                )

            # Process each page
            all_text = []
            all_structured = {}
            engine_used = self._primary_engine_name

            for i, image in enumerate(images):
                # Primary OCR
                primary_engine = self._get_primary_engine()

                # Skip preprocessing for VLM engines (they work best with raw images)
                skip_preprocess = getattr(primary_engine, "skip_preprocessing", False)
                if skip_preprocess:
                    processed_image = image
                else:
                    processed_image = self.image_preprocessor.process(image)

                ocr_result = await primary_engine.recognize(processed_image)

                # Check if fallback is needed
                if ocr_result.confidence < self.confidence_threshold:
                    fallback_engine = self._get_fallback_engine()
                    if fallback_engine is not None:
                        logger.info(
                            f"Primary OCR confidence {ocr_result.confidence:.2f} below "
                            "threshold, using fallback"
                        )
                        # Fallback (EasyOCR) benefits from preprocessing
                        fallback_image = self.image_preprocessor.process(image)
                        fallback_result = await fallback_engine.recognize(fallback_image)

                        # Use fallback if it's better
                        if fallback_result.confidence > ocr_result.confidence:
                            ocr_result = fallback_result
                            engine_used = self._fallback_engine_name
                    else:
                        logger.info(
                            f"Primary OCR confidence {ocr_result.confidence:.2f} below "
                            "threshold, no fallback engine configured"
                        )

                all_text.append(ocr_result.text)
                if ocr_result.structured:
                    all_structured[f"page_{i}"] = ocr_result.structured

            # Combine text from all pages
            combined_text = "\n\n".join(all_text)

            # Extract structured fields (LLM primary, regex fallback)
            extractor_used = "regex"
            if self._llm_extractor is not None:
                try:
                    invoice = self._llm_extractor.extract(combined_text, all_structured)
                    extractor_used = "llm"
                    logger.info("Field extraction via LLM succeeded")
                except Exception as e:
                    logger.warning("LLM extraction failed, falling back to regex: %s", e)
                    invoice = self.field_extractor.extract(combined_text, all_structured)
            else:
                invoice = self.field_extractor.extract(combined_text, all_structured)

            logger.info("Extractor used: %s", extractor_used)
            invoice.raw_text = combined_text
            invoice.raw_structured = all_structured

            # Derive missing amount fields
            self._derive_amounts(invoice)

            # Validate extracted data
            self._validate_invoice(invoice)

            # Calculate confidence scores
            field_confidences = self.confidence_calculator.calculate(invoice, ocr_result)
            overall_confidence = self.confidence_calculator.calculate_overall(field_confidences)

            # Build result
            processing_time = int((time.perf_counter() - start_time) * 1000)

            result = ExtractionResult(
                status=ExtractionStatus.SUCCESS
                if overall_confidence >= 0.6
                else ExtractionStatus.PARTIAL,
                invoice=invoice,
                overall_confidence=overall_confidence,
                field_confidences=field_confidences,
                processing_time_ms=processing_time,
                ocr_engine=engine_used,
                page_count=len(images),
            )

            # Add validation warnings
            self._add_validation_warnings(result, invoice)

            return result

        except Exception as e:
            logger.exception(f"Invoice extraction failed: {e}")
            processing_time = int((time.perf_counter() - start_time) * 1000)
            return ExtractionResult(
                status=ExtractionStatus.FAILED,
                invoice=ExtractedInvoice(),
                processing_time_ms=processing_time,
            )

    async def _load_document(
        self,
        document: bytes | BinaryIO | Path,
        document_type: str | None = None,
    ) -> list[Image.Image]:
        """Load document and convert to list of PIL Images."""
        # Handle different input types
        if isinstance(document, Path):
            with open(document, "rb") as f:
                data = f.read()
            if document_type is None:
                document_type = "pdf" if document.suffix.lower() == ".pdf" else "image"
        elif isinstance(document, bytes):
            data = document
        else:
            data = document.read()

        # Detect type if not specified
        if document_type is None:
            document_type = self._detect_document_type(data)

        # Process based on type
        if document_type == "pdf":
            return self.pdf_processor.to_images(data)
        else:
            image = (
                Image.open(data)
                if isinstance(data, BinaryIO)
                else Image.open(__import__("io").BytesIO(data))
            )
            return [image]

    def _detect_document_type(self, data: bytes) -> str:
        """Detect document type from magic bytes."""
        if data[:4] == b"%PDF":
            return "pdf"
        return "image"

    def _derive_amounts(self, invoice: ExtractedInvoice) -> None:
        """Fill in missing amount fields from available data.

        Handles common cases where OCR extracts some but not all amounts:
        - No tax fields → total_amount = subtotal (PDV-exempt invoice)
        - subtotal + tax_amount but no total → total = subtotal + tax
        - total + tax_amount but no subtotal → subtotal = total - tax
        - subtotal + tax_rate but no tax_amount → compute tax from rate

        Args:
            invoice: Extracted invoice to patch in-place.
        """
        from decimal import Decimal

        s = invoice.subtotal
        r = invoice.tax_rate
        ta = invoice.tax_amount
        t = invoice.total_amount

        # If tax_rate is 0 or tax_amount is 0, treat as no-tax invoice
        no_tax = (r is not None and r == 0) or (ta is not None and ta == 0)

        # Case 1: subtotal present, no total, and no tax (or zero tax)
        if t is None and s is not None:
            if ta is None and r is None:
                invoice.total_amount = s
                logger.info("Derived total_amount = subtotal (no tax fields)")
            elif no_tax:
                invoice.total_amount = s
                invoice.tax_amount = invoice.tax_amount or Decimal("0")
                logger.info("Derived total_amount = subtotal (zero tax)")
            elif ta is not None:
                invoice.total_amount = s + ta
                logger.info("Derived total_amount = subtotal + tax_amount")
            elif r is not None and r > 0:
                invoice.tax_amount = (s * r / Decimal("100")).quantize(Decimal("0.01"))
                invoice.total_amount = s + invoice.tax_amount
                logger.info("Derived tax_amount and total_amount from subtotal + rate")

        # Case 2: total present, no subtotal
        if invoice.subtotal is None and invoice.total_amount is not None:
            if invoice.tax_amount is not None:
                invoice.subtotal = invoice.total_amount - invoice.tax_amount
                logger.info("Derived subtotal = total_amount - tax_amount")
            elif no_tax:
                invoice.subtotal = invoice.total_amount
                logger.info("Derived subtotal = total_amount (zero tax)")

    def _validate_invoice(self, invoice: ExtractedInvoice) -> None:
        """Run validation checks on extracted invoice."""
        # PIB validation
        if invoice.seller.pib:
            self.pib_validator.validate(invoice.seller.pib, entity="seller_pib")
        if invoice.buyer.pib:
            self.pib_validator.validate(invoice.buyer.pib, entity="buyer_pib")

        # Math validation
        self.math_validator.validate(invoice)

    def _add_validation_warnings(
        self,
        result: ExtractionResult,
        invoice: ExtractedInvoice,
    ) -> None:
        """Add validation warnings to result."""
        # PIB warnings
        for warning in self.pib_validator.get_warnings():
            result.add_warning(warning)

        # Math warnings
        for warning in self.math_validator.get_warnings():
            result.add_warning(warning)

        # Same seller/buyer warning
        if invoice.seller.pib and invoice.buyer.pib and invoice.seller.pib == invoice.buyer.pib:
            from fakturaai_ml.types import ValidationWarning, WarningType

            result.add_warning(
                ValidationWarning(
                    warning_type=WarningType.SAME_SELLER_BUYER,
                    message="Prodavac i kupac imaju isti PIB",
                    field_name="buyer_pib",
                    severity="warning",
                )
            )

    async def health_check(self) -> dict[str, bool]:
        """Check if all components are healthy."""
        return {
            "primary_engine": self._primary_engine is not None,
            "fallback_engine": self._fallback_engine is not None,
            "preprocessor": True,
            "pdf_processor": True,
        }
