"""Table extraction from documents."""

import logging
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)


class TableExtractor:
    """
    Extract tables from invoice images.

    Uses computer vision techniques to detect table structures
    when OCR engines don't provide structured table output.
    """

    def __init__(self):
        """Initialize table extractor."""
        pass

    def extract_tables(
        self,
        image: Image.Image,
        ocr_text: str,
    ) -> list[dict[str, Any]]:
        """
        Extract tables from image.

        Args:
            image: PIL Image to process
            ocr_text: OCR text for reference

        Returns:
            List of detected tables with rows and cells
        """
        # This is a placeholder for table extraction logic
        # In production, you might use:
        # - OpenCV for line detection
        # - LayoutParser for layout analysis
        # - Custom transformer models for table detection

        # For now, return empty - dots.ocr handles tables natively
        return []

    def detect_table_regions(
        self,
        image: Image.Image,
    ) -> list[tuple[int, int, int, int]]:
        """
        Detect bounding boxes of tables in image.

        Returns:
            List of (x1, y1, x2, y2) bounding boxes
        """
        import cv2
        import numpy as np

        img_array = np.array(image.convert("L"))

        # Detect horizontal and vertical lines
        # This is a basic approach - production would use ML

        # Apply edge detection
        edges = cv2.Canny(img_array, 50, 150)

        # Detect lines
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=100,
            minLineLength=50,
            maxLineGap=5,
        )

        if lines is None:
            return []

        # Find regions with many lines (likely tables)
        # This is simplified - real implementation would be more sophisticated
        regions = []

        # Group lines into potential table regions
        h_lines = []
        v_lines = []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)

            if angle < 10:  # Horizontal
                h_lines.append((min(y1, y2), min(x1, x2), max(x1, x2)))
            elif angle > 80:  # Vertical
                v_lines.append((min(x1, x2), min(y1, y2), max(y1, y2)))

        # Find intersecting line regions
        if len(h_lines) >= 2 and len(v_lines) >= 2:
            # Get bounding box of all lines
            all_y = [line[0] for line in h_lines]
            all_x = [line[0] for line in v_lines]

            if all_y and all_x:
                y1, y2 = min(all_y), max(all_y)
                x1, x2 = min(all_x), max(all_x)

                if (x2 - x1) > 100 and (y2 - y1) > 50:
                    regions.append((x1, y1, x2, y2))

        return regions
