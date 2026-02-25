"""Unit tests for OCR engine implementations (dots.ocr and EasyOCR)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from fakturaai_ml.ocr.base import OCRResult
from fakturaai_ml.ocr.dots_ocr import DotsOCREngine
from fakturaai_ml.ocr.easyocr_fallback import EasyOCREngine


def _run(coro):
    """Run an async coroutine in a new event loop."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_test_image() -> Image.Image:
    return Image.new("RGB", (200, 200), (255, 255, 255))


# ===========================================================================
# DotsOCREngine tests
# ===========================================================================


class TestDotsOCRProperties:
    """Tests for DotsOCREngine properties and initial state."""

    def test_name_property(self):
        engine = DotsOCREngine()
        assert engine.name == "dots.ocr"

    def test_supported_languages_includes_serbian(self):
        engine = DotsOCREngine()
        langs = engine.supported_languages
        assert "sr_cyrl" in langs
        assert "sr_latn" in langs
        assert "en" in langs

    def test_is_loaded_initially_false(self):
        engine = DotsOCREngine()
        assert engine.is_loaded() is False


class TestDotsOCRParseOutput:
    """Tests for _parse_output() helper."""

    def test_parse_json_object(self):
        engine = DotsOCREngine()
        result = engine._parse_output('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_parse_json_array(self):
        engine = DotsOCREngine()
        result = engine._parse_output('[{"text": "hello"}, {"text": "world"}]')
        assert "items" in result
        assert len(result["items"]) == 2

    def test_parse_plain_text(self):
        engine = DotsOCREngine()
        result = engine._parse_output("This is plain text, not JSON")
        assert result["raw_text"] == "This is plain text, not JSON"
        assert result["format"] == "markdown"

    def test_parse_markdown(self):
        engine = DotsOCREngine()
        result = engine._parse_output("# Header\n\nSome content")
        assert "raw_text" in result
        assert "Header" in result["raw_text"]


class TestDotsOCRExtractPlainText:
    """Tests for _extract_plain_text() helper."""

    def test_extract_from_raw_text(self):
        engine = DotsOCREngine()
        text = engine._extract_plain_text({"raw_text": "Faktura 12345"})
        assert text == "Faktura 12345"

    def test_extract_from_nested_structure(self):
        engine = DotsOCREngine()
        text = engine._extract_plain_text(
            {
                "header": {"title": "Faktura"},
                "body": ["Red 1", "Red 2"],
                "footer": "Ukupno: 1000",
            }
        )
        assert "Faktura" in text
        assert "Red 1" in text
        assert "Red 2" in text
        assert "Ukupno: 1000" in text


class TestDotsOCREstimateConfidence:
    """Tests for _estimate_confidence() helper."""

    def test_base_confidence(self):
        engine = DotsOCREngine()
        # Base 0.85, but raw_text="" (<100 chars) → -0.15 penalty = 0.70
        conf = engine._estimate_confidence({"some_key": "some_value"})
        assert conf == pytest.approx(0.70, abs=0.01)

    def test_base_confidence_with_long_text(self):
        engine = DotsOCREngine()
        # Base 0.85, raw_text > 100 chars → no penalty
        conf = engine._estimate_confidence({"raw_text": "x" * 200})
        assert conf == pytest.approx(0.85, abs=0.01)

    def test_boost_with_tables(self):
        engine = DotsOCREngine()
        # Base 0.85 + 0.05 (tables), raw_text > 100 chars → no penalty = 0.90
        conf = engine._estimate_confidence({"tables": [{"row": "data"}], "raw_text": "x" * 200})
        assert conf == pytest.approx(0.90, abs=0.01)

    def test_boost_with_layout(self):
        engine = DotsOCREngine()
        # Base 0.85 + 0.05 (regions), raw_text > 100 chars → no penalty = 0.90
        conf = engine._estimate_confidence({"regions": [{"type": "header"}], "raw_text": "x" * 200})
        assert conf == pytest.approx(0.90, abs=0.01)

    def test_penalty_short_text(self):
        engine = DotsOCREngine()
        conf = engine._estimate_confidence({"raw_text": "short"})
        assert conf == pytest.approx(0.70, abs=0.01)

    def test_confidence_clamped_to_1(self):
        engine = DotsOCREngine()
        conf = engine._estimate_confidence(
            {
                "tables": True,
                "regions": True,
                "raw_text": "x" * 200,
            }
        )
        assert conf <= 1.0


class TestDotsOCRBuildPrompt:
    """Tests for _build_prompt() helper."""

    def test_has_required_keys(self):
        engine = DotsOCREngine()
        img = _make_test_image()
        prompt = engine._build_prompt(img, task="full")
        assert "prompt" in prompt
        assert "multi_modal_data" in prompt
        assert "image" in prompt["multi_modal_data"]

    def test_prompt_contains_task_text(self):
        engine = DotsOCREngine()
        img = _make_test_image()
        prompt = engine._build_prompt(img, task="text")
        assert "text" in prompt["prompt"].lower()


class TestDotsOCRRecognize:
    """Tests for recognize() graceful failure handling."""

    def test_returns_empty_on_load_failure(self):
        engine = DotsOCREngine()
        # Patch load to raise (simulating vLLM not available / no GPU)
        engine.load = AsyncMock(side_effect=ImportError("No module named 'vllm'"))

        result = _run(engine.recognize(_make_test_image()))
        assert isinstance(result, OCRResult)
        assert result.confidence == 0.0
        assert result.text == ""

    def test_returns_empty_on_inference_failure(self):
        engine = DotsOCREngine()
        engine._loaded = True
        engine._model = MagicMock()
        # Patch vLLM SamplingParams import to fail
        with patch.dict("sys.modules", {"vllm": None}):
            result = _run(engine.recognize(_make_test_image()))
        assert isinstance(result, OCRResult)
        assert result.confidence == 0.0


# ===========================================================================
# EasyOCREngine tests
# ===========================================================================


class TestEasyOCRProperties:
    """Tests for EasyOCREngine properties and initial state."""

    def test_name_property(self):
        engine = EasyOCREngine()
        assert engine.name == "easyocr"

    def test_supported_languages(self):
        engine = EasyOCREngine()
        langs = engine.supported_languages
        assert "sr_cyrl" in langs
        assert "en" in langs

    def test_is_loaded_initially_false(self):
        engine = EasyOCREngine()
        assert engine.is_loaded() is False

    def test_default_languages(self):
        engine = EasyOCREngine()
        assert "sr_cyrl" in engine.languages
        assert "en" in engine.languages


class TestEasyOCRCombineTextBlocks:
    """Tests for _combine_text_blocks() helper."""

    def test_reading_order(self):
        engine = EasyOCREngine()
        blocks = [
            {"text": "right", "confidence": 0.9, "box": {"x1": 200, "y1": 10, "x2": 300, "y2": 30}},
            {"text": "left", "confidence": 0.9, "box": {"x1": 10, "y1": 10, "x2": 100, "y2": 30}},
            {
                "text": "below",
                "confidence": 0.9,
                "box": {"x1": 10, "y1": 100, "x2": 100, "y2": 120},
            },
        ]
        text = engine._combine_text_blocks(blocks)
        lines = text.split("\n")
        # First line should have "left" before "right" (same y, sorted by x)
        assert "left" in lines[0]
        assert "right" in lines[0]
        assert lines[0].index("left") < lines[0].index("right")
        # "below" should be on a separate line
        assert "below" in lines[1]

    def test_empty_blocks(self):
        engine = EasyOCREngine()
        assert engine._combine_text_blocks([]) == ""


class TestEasyOCRDetectLanguage:
    """Tests for _detect_language() helper."""

    def test_cyrillic_text(self):
        engine = EasyOCREngine()
        assert engine._detect_language("Фактура број 123") == "sr_cyrl"

    def test_latin_text(self):
        engine = EasyOCREngine()
        assert engine._detect_language("Faktura broj 123") == "sr_latn"

    def test_empty_text(self):
        engine = EasyOCREngine()
        assert engine._detect_language("") == "sr"


class TestEasyOCRRecognize:
    """Tests for recognize() graceful failure handling."""

    def test_returns_empty_on_load_failure(self):
        engine = EasyOCREngine()
        engine.load = AsyncMock(side_effect=ImportError("No module named 'easyocr'"))

        result = _run(engine.recognize(_make_test_image()))
        assert isinstance(result, OCRResult)
        assert result.confidence == 0.0
        assert result.text == ""
