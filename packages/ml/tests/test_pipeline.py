"""Unit tests for InvoicePipeline — fallback handling and preprocessing."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from PIL import Image

from fakturaai_ml.ocr.base import OCRResult
from fakturaai_ml.pipeline import InvoicePipeline


def _run(coro):
    """Run an async coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_test_image(width: int = 200, height: int = 200) -> Image.Image:
    """Create a test image with specified dimensions."""
    return Image.new("RGB", (width, height), (255, 255, 255))


def _make_image_bytes(width: int = 200, height: int = 200) -> bytes:
    """Create test image bytes (JPEG)."""
    import io

    image = _make_test_image(width, height)
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()


class TestPipelineFallbackDisabled:
    """Tests for fallback_engine='none' — no EasyOCR fallback."""

    def test_get_fallback_engine_returns_none_when_disabled(self):
        """When fallback_engine='none', _get_fallback_engine() returns None."""
        pipeline = InvoicePipeline(primary_engine="dots", fallback_engine="none")
        assert pipeline._get_fallback_engine() is None

    def test_get_fallback_engine_returns_engine_when_enabled(self):
        """When fallback_engine='easyocr', _get_fallback_engine() returns engine."""
        pipeline = InvoicePipeline(primary_engine="dots", fallback_engine="easyocr")
        engine = pipeline._get_fallback_engine()
        assert engine is not None
        assert engine.name == "easyocr"

    def test_no_fallback_on_low_confidence(self):
        """With fallback=none, low confidence should NOT trigger EasyOCR."""
        pipeline = InvoicePipeline(primary_engine="dots", fallback_engine="none")

        # Mock dots.ocr to return low confidence
        low_conf_result = OCRResult(
            text="some text", confidence=0.3, structured={"raw_text": "some text"}
        )
        mock_engine = MagicMock()
        mock_engine.skip_preprocessing = True
        mock_engine.recognize = AsyncMock(return_value=low_conf_result)
        pipeline._primary_engine = mock_engine
        pipeline._primary_engine_name = "dots"

        result = _run(pipeline.extract(_make_image_bytes()))

        # Should have used the low-confidence result, not tried EasyOCR
        mock_engine.recognize.assert_called_once()
        assert result.ocr_engine == "dots"

    def test_fallback_called_when_enabled_and_better(self):
        """With fallback=easyocr, low confidence triggers fallback."""
        pipeline = InvoicePipeline(primary_engine="dots", fallback_engine="easyocr")

        # Mock dots.ocr to return low confidence
        low_conf_result = OCRResult(
            text="bad text", confidence=0.3, structured={"raw_text": "bad text"}
        )
        mock_primary = MagicMock()
        mock_primary.skip_preprocessing = True
        mock_primary.recognize = AsyncMock(return_value=low_conf_result)
        pipeline._primary_engine = mock_primary

        # Mock EasyOCR to return higher confidence
        better_result = OCRResult(
            text="good text", confidence=0.9, structured={"raw_text": "good text"}
        )
        mock_fallback = MagicMock()
        mock_fallback.recognize = AsyncMock(return_value=better_result)
        pipeline._fallback_engine = mock_fallback

        result = _run(pipeline.extract(_make_image_bytes()))

        mock_primary.recognize.assert_called_once()
        mock_fallback.recognize.assert_called_once()
        assert result.ocr_engine == "easyocr"
        assert "good text" in result.invoice.raw_text


class TestPipelineSkipPreprocessing:
    """Tests for skip_preprocessing — VLMs get raw images, traditional OCR gets preprocessed."""

    def test_vlm_engine_gets_raw_image(self):
        """Engines with skip_preprocessing=True should get the original image."""
        pipeline = InvoicePipeline(primary_engine="dots", fallback_engine="none")

        mock_result = OCRResult(
            text="extracted", confidence=0.9, structured={"raw_text": "extracted" * 20}
        )
        mock_engine = MagicMock()
        mock_engine.skip_preprocessing = True
        mock_engine.recognize = AsyncMock(return_value=mock_result)
        pipeline._primary_engine = mock_engine

        # Spy on the image preprocessor
        pipeline.image_preprocessor.process = MagicMock(return_value=_make_test_image())

        _run(pipeline.extract(_make_image_bytes()))

        # Preprocessor should NOT have been called
        pipeline.image_preprocessor.process.assert_not_called()
        mock_engine.recognize.assert_called_once()

    def test_traditional_engine_gets_preprocessed_image(self):
        """Engines without skip_preprocessing should get preprocessed image."""
        pipeline = InvoicePipeline(primary_engine="easyocr", fallback_engine="none")

        mock_result = OCRResult(
            text="extracted", confidence=0.9, structured={"raw_text": "extracted" * 20}
        )
        mock_engine = MagicMock()
        mock_engine.skip_preprocessing = False
        mock_engine.recognize = AsyncMock(return_value=mock_result)
        pipeline._primary_engine = mock_engine

        # Spy on the image preprocessor
        original_process = pipeline.image_preprocessor.process
        pipeline.image_preprocessor.process = MagicMock(side_effect=original_process)

        _run(pipeline.extract(_make_image_bytes()))

        # Preprocessor SHOULD have been called
        pipeline.image_preprocessor.process.assert_called_once()
        mock_engine.recognize.assert_called_once()


class TestPipelineLLMFallback:
    """Tests for the LLM-extractor failure path.

    When the LLM call raises (e.g. Anthropic 529 Overloaded), the pipeline
    silently fell back to regex without telling the user. These tests pin
    the new behavior: a warning is emitted and raw_llm_output is populated
    with the failure marker so the debug surface stays useful.
    """

    def _build_pipeline_with_failing_llm(self, exc: Exception) -> InvoicePipeline:
        """Construct a pipeline whose LLM extractor always raises ``exc``."""
        pipeline = InvoicePipeline(primary_engine="dots", fallback_engine="none")

        ocr_result = OCRResult(
            text="Some invoice text", confidence=0.95, structured={"raw_text": "Some invoice text"}
        )
        mock_engine = MagicMock()
        mock_engine.skip_preprocessing = True
        mock_engine.recognize = AsyncMock(return_value=ocr_result)
        pipeline._primary_engine = mock_engine

        failing = MagicMock()
        failing.extract = MagicMock(side_effect=exc)
        pipeline._llm_extractor = failing
        return pipeline

    def test_llm_failure_attaches_warning(self):
        """A failed LLM extraction surfaces a LLM_EXTRACTION_FAILED warning."""
        from fakturaai_ml.types import WarningType

        pipeline = self._build_pipeline_with_failing_llm(
            RuntimeError("Error code: 529 - Overloaded")
        )

        result = _run(pipeline.extract(_make_image_bytes()))

        warning_types = [w.warning_type for w in result.warnings]
        assert WarningType.LLM_EXTRACTION_FAILED in warning_types

    def test_llm_failure_populates_raw_llm_output(self):
        """raw_llm_output carries the failure marker for the debug panel."""
        pipeline = self._build_pipeline_with_failing_llm(
            RuntimeError("Error code: 529 - Overloaded")
        )

        result = _run(pipeline.extract(_make_image_bytes()))

        assert result.invoice.raw_llm_output is not None
        assert "LLM extraction failed" in result.invoice.raw_llm_output
        assert "RuntimeError" in result.invoice.raw_llm_output

    def test_llm_success_does_not_attach_warning(self):
        """Happy path: no LLM_EXTRACTION_FAILED warning."""
        from fakturaai_ml.types import ExtractedInvoice, WarningType

        pipeline = InvoicePipeline(primary_engine="dots", fallback_engine="none")
        ocr_result = OCRResult(
            text="Some invoice", confidence=0.95, structured={"raw_text": "Some invoice"}
        )
        mock_engine = MagicMock()
        mock_engine.skip_preprocessing = True
        mock_engine.recognize = AsyncMock(return_value=ocr_result)
        pipeline._primary_engine = mock_engine

        succeeding = MagicMock()
        succeeding_invoice = ExtractedInvoice()
        succeeding_invoice.raw_llm_output = '{"invoice_number": "INV-1"}'
        succeeding.extract = MagicMock(return_value=succeeding_invoice)
        pipeline._llm_extractor = succeeding

        result = _run(pipeline.extract(_make_image_bytes()))

        warning_types = [w.warning_type for w in result.warnings]
        assert WarningType.LLM_EXTRACTION_FAILED not in warning_types


class TestPipelineEngineInitialization:
    """Tests for engine lazy loading and configuration."""

    def test_dots_engine_created_by_default(self):
        """Primary engine defaults to dots.ocr."""
        pipeline = InvoicePipeline()
        engine = pipeline._get_primary_engine()
        assert engine.name == "dots.ocr"

    def test_easyocr_engine_selectable(self):
        """Primary engine can be set to easyocr."""
        pipeline = InvoicePipeline(primary_engine="easyocr")
        engine = pipeline._get_primary_engine()
        assert engine.name == "easyocr"

    def test_engine_lazy_loaded(self):
        """Engine should not be created until first access."""
        pipeline = InvoicePipeline()
        assert pipeline._primary_engine is None
        pipeline._get_primary_engine()
        assert pipeline._primary_engine is not None

    def test_engine_reused_on_second_call(self):
        """Engine should be cached after first creation."""
        pipeline = InvoicePipeline()
        engine1 = pipeline._get_primary_engine()
        engine2 = pipeline._get_primary_engine()
        assert engine1 is engine2
