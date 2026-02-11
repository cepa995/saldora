"""PDF processing and conversion to images."""

import logging
from io import BytesIO

from PIL import Image

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Process PDF documents and convert to images for OCR.

    Uses PyMuPDF (fitz) for PDF rendering.
    """

    def __init__(
        self,
        dpi: int = 200,
        max_pages: int = 50,
    ):
        """
        Initialize PDF processor.

        Args:
            dpi: Resolution for PDF rendering (200 recommended for balance of
                 quality and speed)
            max_pages: Maximum pages to process per document
        """
        self.dpi = dpi
        self.max_pages = max_pages
        self._zoom = dpi / 72  # PyMuPDF uses 72 DPI as base

    def to_images(self, pdf_bytes: bytes) -> list[Image.Image]:
        """
        Convert PDF to list of PIL Images.

        Args:
            pdf_bytes: PDF file as bytes

        Returns:
            List of PIL Images, one per page
        """
        try:
            import fitz  # PyMuPDF

            images = []
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            page_count = min(len(doc), self.max_pages)
            if len(doc) > self.max_pages:
                logger.warning(f"PDF has {len(doc)} pages, processing only first {self.max_pages}")

            for page_num in range(page_count):
                page = doc[page_num]

                # Render page to image
                mat = fitz.Matrix(self._zoom, self._zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)

                # Convert to PIL Image
                img_bytes = pix.tobytes("png")
                image = Image.open(BytesIO(img_bytes))
                images.append(image)

            doc.close()
            return images

        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            raise

    def get_page_count(self, pdf_bytes: bytes) -> int:
        """Get the number of pages in a PDF."""
        try:
            import fitz

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            logger.error(f"Failed to get PDF page count: {e}")
            return 0

    def extract_text(self, pdf_bytes: bytes) -> str:
        """
        Extract embedded text from PDF (if available).

        This can be used as a fallback or supplement to OCR
        for PDFs with text layer.
        """
        try:
            import fitz

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            text_parts = []
            for page in doc:
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)

            doc.close()
            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return ""

    def is_scanned(self, pdf_bytes: bytes) -> bool:
        """
        Check if PDF is likely a scanned document (no text layer).

        Returns True if PDF appears to be image-based.
        """
        try:
            import fitz

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            total_chars = 0
            for page in doc:
                text = page.get_text()
                total_chars += len(text.strip())

            doc.close()

            # If very little text extracted, likely scanned
            return total_chars < 100

        except Exception:
            return True  # Assume scanned on error
