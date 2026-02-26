"""Unit tests for OCR engine implementations (dots.ocr and EasyOCR)."""

import asyncio
import base64
import io
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from fakturaai_ml.ocr.base import OCRResult
from fakturaai_ml.ocr.dots_ocr import DotsOCREngine
from fakturaai_ml.ocr.easyocr_fallback import EasyOCREngine


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


class TestDotsOCRSmartResize:
    """Tests for _smart_resize() — image resizing for model token budget."""

    def test_small_image_unchanged(self):
        """Images within bounds should stay close to original size."""
        h, w = DotsOCREngine._smart_resize(420, 588)
        assert h == 420
        assert w == 588

    def test_dimensions_divisible_by_factor(self):
        """Output dimensions must be divisible by 28."""
        h, w = DotsOCREngine._smart_resize(425, 600)
        assert h % 28 == 0
        assert w % 28 == 0

    def test_large_image_downscaled(self):
        """High-res images (e.g., 2480x3508) must be shrunk to fit max_pixels."""
        h, w = DotsOCREngine._smart_resize(3508, 2480)
        assert h * w <= 2822400
        assert h % 28 == 0
        assert w % 28 == 0
        # Should be significantly smaller than the original
        assert h < 3508
        assert w < 2480

    def test_tiny_image_upscaled(self):
        """Very small images should be upscaled to meet min_pixels."""
        h, w = DotsOCREngine._smart_resize(28, 28)
        assert h * w >= 3136

    def test_preserves_aspect_ratio(self):
        """Aspect ratio should be approximately preserved."""
        original_ratio = 3508 / 2480
        h, w = DotsOCREngine._smart_resize(3508, 2480)
        new_ratio = h / w
        assert abs(original_ratio - new_ratio) < 0.1

    def test_custom_max_pixels(self):
        """Custom max_pixels parameter is respected."""
        h, w = DotsOCREngine._smart_resize(1000, 1000, max_pixels=100000)
        assert h * w <= 100000


class TestDotsOCRDataUri:
    """Tests for _pil_to_data_uri() — base64 image encoding."""

    def test_returns_valid_data_uri(self):
        """Output should be a valid PNG data URI."""
        image = _make_test_image()
        uri = DotsOCREngine._pil_to_data_uri(image)
        assert uri.startswith("data:image/png;base64,")

    def test_base64_is_decodable(self):
        """The base64 portion should decode to valid PNG bytes."""
        image = _make_test_image()
        uri = DotsOCREngine._pil_to_data_uri(image)
        b64_data = uri.split("base64,")[1]
        decoded = base64.b64decode(b64_data)
        # PNG magic bytes
        assert decoded[:4] == b"\x89PNG"

    def test_roundtrip(self):
        """Encoding and decoding should produce equivalent image."""
        image = _make_test_image(100, 50)
        uri = DotsOCREngine._pil_to_data_uri(image)
        b64_data = uri.split("base64,")[1]
        decoded = base64.b64decode(b64_data)
        restored = Image.open(io.BytesIO(decoded))
        assert restored.size == (100, 50)
        assert restored.mode == "RGB"


class TestDotsOCRServerConnection:
    """Tests for load() — connecting to the vLLM server."""

    def test_load_connects_to_server(self):
        """load() should create an OpenAI client and verify the connection."""
        engine = DotsOCREngine()
        mock_client = MagicMock()
        mock_client.models.list.return_value = MagicMock(data=[MagicMock(id="model")])

        # Mock the openai module since it may not be installed locally
        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        with patch.dict("sys.modules", {"openai": mock_openai}):
            _run(engine.load())

        mock_openai.OpenAI.assert_called_once_with(api_key="unused", base_url=engine._server_url)
        mock_client.models.list.assert_called_once()
        assert engine.is_loaded() is True
        assert engine._client is mock_client

    def test_load_uses_env_vars(self):
        """Server URL and model name should come from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "DOTS_OCR_SERVER_URL": "http://custom-server:9000/v1",
                "DOTS_OCR_MODEL_NAME": "custom-model",
            },
        ):
            engine = DotsOCREngine()
        assert engine._server_url == "http://custom-server:9000/v1"
        assert engine._model_name == "custom-model"

    def test_load_raises_on_connection_failure(self):
        """load() should propagate connection errors."""
        engine = DotsOCREngine()
        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = MagicMock(
            models=MagicMock(list=MagicMock(side_effect=ConnectionError("Connection refused")))
        )
        with patch.dict("sys.modules", {"openai": mock_openai}):
            with pytest.raises(ConnectionError, match="Connection refused"):
                _run(engine.load())
        assert engine.is_loaded() is False

    def test_load_idempotent(self):
        """Calling load() twice should not reconnect."""
        engine = DotsOCREngine()
        engine._loaded = True
        engine._client = MagicMock()
        _run(engine.load())
        # Client should not have been replaced
        engine._client.models.list.assert_not_called()

    def test_unload_resets_state(self):
        """unload() should clear client and loaded flag."""
        engine = DotsOCREngine()
        engine._loaded = True
        engine._client = MagicMock()
        _run(engine.unload())
        assert engine.is_loaded() is False
        assert engine._client is None


class TestDotsOCRRecognize:
    """Tests for recognize() — the main OCR inference method."""

    def _make_mock_engine(self, response_text="Faktura br. 123"):
        """Create a DotsOCREngine with a mocked OpenAI client."""
        engine = DotsOCREngine()
        engine._loaded = True
        engine._client = MagicMock()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=response_text))]
        engine._client.chat.completions.create.return_value = mock_response
        return engine

    def test_successful_recognition(self):
        """recognize() should return OCRResult with extracted text."""
        engine = self._make_mock_engine("Faktura br. 123\nUkupno: 1000 RSD")
        result = _run(engine.recognize(_make_test_image()))

        assert isinstance(result, OCRResult)
        assert "Faktura br. 123" in result.text
        assert result.confidence > 0.0

    def test_calls_vllm_with_correct_format(self):
        """The API call should use the official dots.ocr message format."""
        engine = self._make_mock_engine()
        _run(engine.recognize(_make_test_image()))

        call_args = engine._client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]

        # Single user message with image_url + text content
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert len(content) == 2

        # First element: image as base64 data URI
        assert content[0]["type"] == "image_url"
        assert content[0]["image_url"]["url"].startswith("data:image/png;base64,")

        # Second element: text with special tokens prefix
        assert content[1]["type"] == "text"
        assert content[1]["text"].startswith("<|img|><|imgpad|><|endofimg|>")

    def test_uses_correct_model_name(self):
        """The API call should use the configured model name."""
        engine = self._make_mock_engine()
        _run(engine.recognize(_make_test_image()))

        call_args = engine._client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == engine._model_name

    def test_resizes_large_images(self):
        """Large images should be resized before sending."""
        engine = self._make_mock_engine()
        large_image = _make_test_image(2480, 3508)
        _run(engine.recognize(large_image))

        # Verify the API was called (image was processed, not rejected)
        engine._client.chat.completions.create.assert_called_once()

    def test_converts_non_rgb_to_rgb(self):
        """RGBA and other modes should be converted to RGB."""
        engine = self._make_mock_engine()
        rgba_image = Image.new("RGBA", (200, 200), (255, 255, 255, 128))
        result = _run(engine.recognize(rgba_image))

        assert isinstance(result, OCRResult)
        engine._client.chat.completions.create.assert_called_once()

    def test_returns_empty_on_server_error(self):
        """recognize() should return empty OCRResult on API failure."""
        engine = DotsOCREngine()
        engine._loaded = True
        engine._client = MagicMock()
        engine._client.chat.completions.create.side_effect = Exception("400 Bad Request")

        result = _run(engine.recognize(_make_test_image()))
        assert isinstance(result, OCRResult)
        assert result.confidence == 0.0
        assert result.text == ""

    def test_returns_empty_on_connection_failure(self):
        """recognize() should return empty OCRResult when server unreachable."""
        engine = DotsOCREngine()
        engine.load = AsyncMock(side_effect=ConnectionError("Connection refused"))

        result = _run(engine.recognize(_make_test_image()))
        assert isinstance(result, OCRResult)
        assert result.confidence == 0.0
        assert result.text == ""

    def test_handles_empty_response(self):
        """recognize() should handle empty/None response from server."""
        engine = self._make_mock_engine(response_text="")
        result = _run(engine.recognize(_make_test_image()))

        assert isinstance(result, OCRResult)
        assert result.text == ""

    def test_parses_json_response(self):
        """recognize() should parse structured JSON responses."""
        json_response = json.dumps({"items": [{"text": "Faktura", "category": "Title"}]})
        engine = self._make_mock_engine(json_response)
        result = _run(engine.recognize(_make_test_image()))

        assert "Faktura" in result.text
        assert "items" in result.structured

    def test_skip_preprocessing_property(self):
        """dots.ocr engine should have skip_preprocessing=True."""
        engine = DotsOCREngine()
        assert engine.skip_preprocessing is True


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
