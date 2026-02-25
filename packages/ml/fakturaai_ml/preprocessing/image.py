"""Image preprocessing for optimal OCR performance."""

import logging

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Preprocesses invoice images for optimal OCR performance.

    Applies:
    - Grayscale conversion
    - Deskewing (rotation correction)
    - Noise reduction
    - Contrast enhancement
    - Binarization (optional)
    - Resolution normalization
    """

    def __init__(
        self,
        target_dpi: int = 300,
        denoise: bool = True,
        deskew: bool = True,
        enhance_contrast: bool = True,
        binarize: bool = False,
        remove_borders: bool = True,
    ):
        """
        Initialize preprocessor.

        Args:
            target_dpi: Target resolution (300 DPI recommended for OCR)
            denoise: Apply noise reduction
            deskew: Correct document rotation
            enhance_contrast: Apply contrast enhancement
            binarize: Convert to black/white (can help with some documents)
            remove_borders: Remove dark scanner borders/artifacts
        """
        self.target_dpi = target_dpi
        self.denoise = denoise
        self.deskew = deskew
        self.enhance_contrast = enhance_contrast
        self.binarize = binarize
        self.remove_borders = remove_borders

    def process(self, image: Image.Image) -> Image.Image:
        """
        Apply preprocessing pipeline to image.

        Args:
            image: PIL Image to process

        Returns:
            Preprocessed PIL Image
        """
        # Normalize resolution (operates on PIL Image for DPI metadata)
        image = self._normalize_resolution(image)

        # Convert to numpy array
        img_array = np.array(image)

        # Convert to grayscale if RGB
        if len(img_array.shape) == 3:
            if img_array.shape[2] == 4:  # RGBA
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
            else:  # RGB
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Deskew
        if self.deskew:
            img_array = self._deskew(img_array)

        # Remove borders
        if self.remove_borders:
            img_array = self._remove_borders(img_array)

        # Denoise
        if self.denoise:
            img_array = self._denoise(img_array)

        # Enhance contrast
        if self.enhance_contrast:
            img_array = self._enhance_contrast(img_array)

        # Binarize
        if self.binarize:
            img_array = self._binarize(img_array)

        # Convert back to PIL and to RGB for consistency
        result = Image.fromarray(img_array)
        if result.mode != "RGB":
            result = result.convert("RGB")

        return result

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Correct document rotation using Hough transform."""
        try:
            # Detect edges
            edges = cv2.Canny(image, 50, 150, apertureSize=3)

            # Detect lines using Hough transform
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi / 180,
                threshold=100,
                minLineLength=100,
                maxLineGap=10,
            )

            if lines is None or len(lines) == 0:
                return image

            # Calculate angles of detected lines
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if x2 - x1 != 0:
                    angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                    # Only consider near-horizontal lines
                    if -45 < angle < 45:
                        angles.append(angle)

            if not angles:
                return image

            # Get median angle (more robust than mean)
            median_angle = np.median(angles)

            # Only rotate if angle is significant
            if abs(median_angle) < 0.5:
                return image

            # Rotate image
            height, width = image.shape[:2]
            center = (width // 2, height // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(
                image,
                rotation_matrix,
                (width, height),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )

            logger.debug(f"Deskewed image by {median_angle:.2f} degrees")
            return rotated

        except Exception as e:
            logger.warning(f"Deskew failed: {e}")
            return image

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """Apply noise reduction."""
        try:
            # Non-local means denoising (good for scanned documents)
            denoised = cv2.fastNlMeansDenoising(
                image,
                h=10,  # Filter strength
                templateWindowSize=7,
                searchWindowSize=21,
            )
            return denoised
        except Exception as e:
            logger.warning(f"Denoising failed: {e}")
            return image

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance contrast using CLAHE."""
        try:
            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image)
            return enhanced
        except Exception as e:
            logger.warning(f"Contrast enhancement failed: {e}")
            return image

    def _binarize(self, image: np.ndarray) -> np.ndarray:
        """Convert to black and white using Otsu's method."""
        try:
            # Otsu's binarization
            _, binary = cv2.threshold(
                image,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU,
            )
            return binary
        except Exception as e:
            logger.warning(f"Binarization failed: {e}")
            return image

    def _normalize_resolution(self, image: Image.Image) -> Image.Image:
        """Scale image to target DPI if current DPI is known and differs."""
        try:
            dpi_info = image.info.get("dpi")
            if not dpi_info:
                return image

            current_dpi = dpi_info[0]  # Use horizontal DPI
            if current_dpi <= 0 or abs(current_dpi - self.target_dpi) < 10:
                return image

            scale = self.target_dpi / current_dpi
            new_width = int(image.width * scale)
            new_height = int(image.height * scale)

            resized = image.resize((new_width, new_height), Image.LANCZOS)
            resized.info["dpi"] = (self.target_dpi, self.target_dpi)

            logger.debug(f"Normalized resolution from {current_dpi} to {self.target_dpi} DPI")
            return resized

        except Exception as e:
            logger.warning(f"Resolution normalization failed: {e}")
            return image

    def _remove_borders(self, image: np.ndarray) -> np.ndarray:
        """Remove dark borders and scanner artifacts."""
        try:
            # Threshold to find dark regions
            _, thresh = cv2.threshold(image, 50, 255, cv2.THRESH_BINARY)

            # Find contours of bright regions
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return image

            # Get bounding box of the largest bright region
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)

            # Only crop if the detected content area is significantly smaller
            img_h, img_w = image.shape[:2]
            area_ratio = (w * h) / (img_w * img_h)
            if area_ratio < 0.5:
                return image  # Content too small, likely a detection error

            # Add small padding to avoid cutting content
            pad = 5
            x = max(0, x - pad)
            y = max(0, y - pad)
            w = min(img_w - x, w + 2 * pad)
            h = min(img_h - y, h + 2 * pad)

            cropped = image[y : y + h, x : x + w]
            if cropped.size == 0:
                return image

            logger.debug(f"Removed borders: cropped from {img_w}x{img_h} to {w}x{h}")
            return cropped

        except Exception as e:
            logger.warning(f"Border removal failed: {e}")
            return image

    def estimate_quality(self, image: Image.Image) -> float:
        """
        Estimate image quality for OCR.

        Returns score from 0.0 (poor) to 1.0 (excellent).
        """
        img_array = np.array(image.convert("L"))

        # Check resolution
        resolution_score = min(1.0, min(image.size) / 1000)

        # Check contrast (standard deviation of pixel values)
        contrast_score = min(1.0, np.std(img_array) / 50)

        # Check blur using Laplacian variance
        laplacian_var = cv2.Laplacian(img_array, cv2.CV_64F).var()
        blur_score = min(1.0, laplacian_var / 500)

        # Weighted average
        quality = resolution_score * 0.3 + contrast_score * 0.3 + blur_score * 0.4

        return quality
