"""Unit tests for the image and PDF preprocessing modules."""

import numpy as np
import pytest
from PIL import Image

from fakturaai_ml.preprocessing.image import ImagePreprocessor
from fakturaai_ml.preprocessing.pdf import PDFProcessor

# ---------------------------------------------------------------------------
# Helpers – synthetic image/PDF generation
# ---------------------------------------------------------------------------


def _make_white_image(w: int = 400, h: int = 600) -> Image.Image:
    """Create a plain white RGB image."""
    return Image.new("RGB", (w, h), color=(255, 255, 255))


def _make_noisy_image(w: int = 400, h: int = 600) -> Image.Image:
    """Create a white image with Gaussian noise."""
    rng = np.random.default_rng(42)
    base = np.full((h, w, 3), 200, dtype=np.uint8)
    noise = rng.integers(0, 80, size=(h, w, 3), dtype=np.uint8)
    noisy = np.clip(base.astype(np.int16) + noise.astype(np.int16), 0, 255).astype(np.uint8)
    return Image.fromarray(noisy, "RGB")


def _make_bordered_image(w: int = 400, h: int = 600, border: int = 40) -> Image.Image:
    """Create a white image with dark borders (simulating scanner artifacts)."""
    arr = np.full((h, w), 255, dtype=np.uint8)
    arr[:border, :] = 0  # top
    arr[-border:, :] = 0  # bottom
    arr[:, :border] = 0  # left
    arr[:, -border:] = 0  # right
    return Image.fromarray(arr, "L").convert("RGB")


def _make_low_contrast_image(w: int = 400, h: int = 600) -> Image.Image:
    """Create a very low-contrast grayscale image."""
    arr = np.full((h, w), 128, dtype=np.uint8)
    arr[100:200, 100:300] = 135  # barely visible rectangle
    return Image.fromarray(arr, "L").convert("RGB")


def _make_sample_pdf(pages: int = 1, text: str = "Test invoice content") -> bytes:
    """Create a minimal PDF with text using PyMuPDF."""
    import fitz

    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)  # A4
        # Insert multiple lines to ensure enough extractable text
        y = 72
        for line in (f"{text} - page {i + 1}",):
            page.insert_text((72, y), line, fontsize=12)
            y += 20
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _make_image_only_pdf() -> bytes:
    """Create a PDF that contains only an image (no text layer)."""
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # Insert a small white rectangle as an image
    img_data = Image.new("RGB", (100, 100), (255, 255, 255))
    import io

    buf = io.BytesIO()
    img_data.save(buf, format="PNG")
    page.insert_image(fitz.Rect(50, 50, 150, 150), stream=buf.getvalue())
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ===========================================================================
# ImagePreprocessor tests
# ===========================================================================


class TestImagePreprocessorProcess:
    """Tests for the main process() pipeline."""

    def test_process_returns_rgb_image(self):
        img = _make_white_image()
        preprocessor = ImagePreprocessor()
        result = preprocessor.process(img)
        assert isinstance(result, Image.Image)
        assert result.mode == "RGB"

    def test_grayscale_conversion_rgb(self):
        img = _make_white_image()
        assert img.mode == "RGB"
        preprocessor = ImagePreprocessor(deskew=False, denoise=False, enhance_contrast=False)
        result = preprocessor.process(img)
        assert result.mode == "RGB"

    def test_grayscale_conversion_rgba(self):
        img = Image.new("RGBA", (200, 200), (255, 255, 255, 255))
        preprocessor = ImagePreprocessor(deskew=False, denoise=False, enhance_contrast=False)
        result = preprocessor.process(img)
        assert result.mode == "RGB"

    def test_all_options_disabled(self):
        img = _make_white_image()
        preprocessor = ImagePreprocessor(
            deskew=False,
            denoise=False,
            enhance_contrast=False,
            binarize=False,
            remove_borders=False,
        )
        result = preprocessor.process(img)
        assert isinstance(result, Image.Image)
        assert result.mode == "RGB"
        assert result.size[0] > 0 and result.size[1] > 0


class TestDeskew:
    """Tests for _deskew()."""

    def test_deskew_returns_same_shape(self):
        preprocessor = ImagePreprocessor()
        arr = np.full((400, 600), 200, dtype=np.uint8)
        result = preprocessor._deskew(arr)
        assert result.shape == arr.shape

    def test_deskew_no_lines_returns_original(self):
        preprocessor = ImagePreprocessor()
        arr = np.full((100, 100), 128, dtype=np.uint8)  # uniform, no edges
        result = preprocessor._deskew(arr)
        np.testing.assert_array_equal(result, arr)


class TestDenoise:
    """Tests for _denoise()."""

    def test_denoise_smooths_image(self):
        preprocessor = ImagePreprocessor()
        # NLMeans works by averaging similar patches — needs structured content
        # with additive noise (not pure random noise).
        rng = np.random.default_rng(42)
        # Horizontal gradient (structured signal)
        base = np.tile(np.linspace(50, 200, 300, dtype=np.uint8), (300, 1))
        # Add Gaussian noise
        noise = rng.normal(0, 25, (300, 300)).astype(np.int16)
        noisy = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        denoised = preprocessor._denoise(noisy)
        # Denoised should be closer to the original signal (lower MSE)
        mse_before = np.mean((noisy.astype(float) - base.astype(float)) ** 2)
        mse_after = np.mean((denoised.astype(float) - base.astype(float)) ** 2)
        assert mse_after < mse_before

    def test_denoise_preserves_shape(self):
        preprocessor = ImagePreprocessor()
        arr = np.full((200, 300), 128, dtype=np.uint8)
        result = preprocessor._denoise(arr)
        assert result.shape == arr.shape


class TestEnhanceContrast:
    """Tests for _enhance_contrast()."""

    def test_enhance_contrast_changes_image(self):
        preprocessor = ImagePreprocessor()
        arr = np.full((200, 200), 128, dtype=np.uint8)
        arr[50:150, 50:150] = 135  # subtle difference
        result = preprocessor._enhance_contrast(arr)
        # CLAHE should increase the spread of pixel values
        assert np.std(result) >= np.std(arr)

    def test_enhance_contrast_preserves_shape(self):
        preprocessor = ImagePreprocessor()
        arr = np.full((200, 300), 100, dtype=np.uint8)
        result = preprocessor._enhance_contrast(arr)
        assert result.shape == arr.shape


class TestBinarize:
    """Tests for _binarize()."""

    def test_binarize_produces_binary_values(self):
        preprocessor = ImagePreprocessor()
        rng = np.random.default_rng(42)
        arr = rng.integers(50, 200, (200, 200), dtype=np.uint8)
        result = preprocessor._binarize(arr)
        unique_values = set(np.unique(result))
        assert unique_values.issubset({0, 255})

    def test_binarize_preserves_shape(self):
        preprocessor = ImagePreprocessor()
        arr = np.full((200, 300), 128, dtype=np.uint8)
        result = preprocessor._binarize(arr)
        assert result.shape == arr.shape


class TestNormalizeResolution:
    """Tests for _normalize_resolution()."""

    def test_normalize_upscales_low_dpi(self):
        preprocessor = ImagePreprocessor(target_dpi=300)
        img = Image.new("RGB", (200, 300))
        img.info["dpi"] = (150, 150)

        result = preprocessor._normalize_resolution(img)
        # 300/150 = 2x scale
        assert result.width == 400
        assert result.height == 600

    def test_normalize_downscales_high_dpi(self):
        preprocessor = ImagePreprocessor(target_dpi=300)
        img = Image.new("RGB", (600, 900))
        img.info["dpi"] = (600, 600)

        result = preprocessor._normalize_resolution(img)
        # 300/600 = 0.5x scale
        assert result.width == 300
        assert result.height == 450

    def test_normalize_skips_when_no_dpi_info(self):
        preprocessor = ImagePreprocessor(target_dpi=300)
        img = Image.new("RGB", (200, 300))
        # No DPI info set

        result = preprocessor._normalize_resolution(img)
        assert result.size == (200, 300)  # unchanged

    def test_normalize_skips_when_close_to_target(self):
        preprocessor = ImagePreprocessor(target_dpi=300)
        img = Image.new("RGB", (200, 300))
        img.info["dpi"] = (295, 295)  # within 10 of target

        result = preprocessor._normalize_resolution(img)
        assert result.size == (200, 300)  # unchanged


class TestRemoveBorders:
    """Tests for _remove_borders()."""

    def test_remove_dark_borders(self):
        preprocessor = ImagePreprocessor()
        # White content (320x520) surrounded by 40px dark borders = 400x600
        arr = np.full((600, 400), 255, dtype=np.uint8)
        arr[:40, :] = 0
        arr[-40:, :] = 0
        arr[:, :40] = 0
        arr[:, -40:] = 0

        result = preprocessor._remove_borders(arr)
        # Result should be smaller — the dark borders were cropped
        assert result.shape[0] < arr.shape[0]
        assert result.shape[1] < arr.shape[1]

    def test_no_borders_returns_similar(self):
        preprocessor = ImagePreprocessor()
        arr = np.full((200, 300), 200, dtype=np.uint8)  # all bright, no borders
        result = preprocessor._remove_borders(arr)
        # Should not crop significantly
        assert result.shape[0] >= 190
        assert result.shape[1] >= 290

    def test_remove_borders_preserves_content(self):
        preprocessor = ImagePreprocessor()
        arr = np.full((600, 400), 255, dtype=np.uint8)
        arr[:30, :] = 0  # dark top border
        # Content area should still be mostly white
        result = preprocessor._remove_borders(arr)
        assert np.mean(result) > 200  # mostly white content preserved


class TestEstimateQuality:
    """Tests for estimate_quality()."""

    def test_returns_float_between_0_and_1(self):
        preprocessor = ImagePreprocessor()
        img = _make_white_image(200, 200)
        score = preprocessor.estimate_quality(img)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_clear_image_scores_higher(self):
        preprocessor = ImagePreprocessor()
        # Clear image: large, high contrast, sharp edges
        clear = np.zeros((1200, 1200), dtype=np.uint8)
        clear[100:1100, 100:1100] = 255  # strong black/white contrast
        clear_img = Image.fromarray(clear, "L").convert("RGB")

        # Poor image: small, low contrast, blurry
        poor = np.full((100, 100), 128, dtype=np.uint8)
        poor_img = Image.fromarray(poor, "L").convert("RGB")

        assert preprocessor.estimate_quality(clear_img) > preprocessor.estimate_quality(poor_img)


# ===========================================================================
# PDFProcessor tests
# ===========================================================================


class TestPDFToImages:
    """Tests for PDFProcessor.to_images()."""

    def test_to_images_returns_list_of_pil_images(self):
        processor = PDFProcessor()
        pdf_bytes = _make_sample_pdf(pages=1)
        images = processor.to_images(pdf_bytes)
        assert isinstance(images, list)
        assert len(images) == 1
        assert isinstance(images[0], Image.Image)

    def test_to_images_multi_page(self):
        processor = PDFProcessor()
        pdf_bytes = _make_sample_pdf(pages=3)
        images = processor.to_images(pdf_bytes)
        assert len(images) == 3

    def test_max_pages_limit(self):
        processor = PDFProcessor(max_pages=2)
        pdf_bytes = _make_sample_pdf(pages=5)
        images = processor.to_images(pdf_bytes)
        assert len(images) == 2


class TestPDFPageCount:
    """Tests for PDFProcessor.get_page_count()."""

    def test_get_page_count(self):
        processor = PDFProcessor()
        pdf_bytes = _make_sample_pdf(pages=4)
        assert processor.get_page_count(pdf_bytes) == 4

    def test_get_page_count_invalid_pdf(self):
        processor = PDFProcessor()
        assert processor.get_page_count(b"not a pdf") == 0


class TestPDFExtractText:
    """Tests for PDFProcessor.extract_text()."""

    def test_extract_text_from_text_pdf(self):
        processor = PDFProcessor()
        pdf_bytes = _make_sample_pdf(pages=1, text="Faktura 12345")
        text = processor.extract_text(pdf_bytes)
        assert "Faktura 12345" in text

    def test_extract_text_multi_page(self):
        processor = PDFProcessor()
        pdf_bytes = _make_sample_pdf(pages=2, text="Invoice content")
        text = processor.extract_text(pdf_bytes)
        assert "page 1" in text
        assert "page 2" in text


class TestPDFIsScanned:
    """Tests for PDFProcessor.is_scanned()."""

    def test_is_scanned_false_for_text_pdf(self):
        processor = PDFProcessor()
        # Create PDF with plenty of text (>100 chars) via multiple pages
        long_text = "Faktura br 001 Prodavac Test DOO PIB 123456789 Kupac Acme DOO"
        pdf_bytes = _make_sample_pdf(pages=3, text=long_text)
        assert processor.is_scanned(pdf_bytes) is False

    def test_is_scanned_true_for_image_pdf(self):
        processor = PDFProcessor()
        pdf_bytes = _make_image_only_pdf()
        assert processor.is_scanned(pdf_bytes) is True

    def test_is_scanned_true_for_invalid_pdf(self):
        processor = PDFProcessor()
        assert processor.is_scanned(b"not a pdf") is True


class TestPDFInvalidInput:
    """Tests for error handling with invalid input."""

    def test_to_images_invalid_pdf_raises(self):
        processor = PDFProcessor()
        with pytest.raises(Exception):
            processor.to_images(b"not a pdf at all")
