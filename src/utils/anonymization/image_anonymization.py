"""
Image Anonymization Utilities for VLA Inference API
Supports face detection, text removal, EXIF stripping, and synthetic augmentation
"""

import cv2
import numpy as np
from PIL import Image
from typing import Optional, Tuple, List
import logging

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logging.warning("EasyOCR not available. Text detection will be disabled.")

logger = logging.getLogger(__name__)


class ImageAnonymizer:
    """
    Comprehensive image anonymization with multiple security levels
    """

    def __init__(self, use_gpu: bool = False):
        """
        Initialize image anonymizer with optional GPU acceleration

        Args:
            use_gpu: Enable GPU for OCR operations (requires CUDA)
        """
        self.use_gpu = use_gpu

        # Initialize face detection cascade
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                raise RuntimeError("Failed to load face cascade classifier")
        except Exception as e:
            logger.error(f"Failed to initialize face detection: {e}")
            self.face_cascade = None

        # Initialize OCR reader if available
        self.reader = None
        if EASYOCR_AVAILABLE:
            try:
                self.reader = easyocr.Reader(['en'], gpu=use_gpu)
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR: {e}")

    def anonymize_image(
        self,
        image: Image.Image,
        level: str = "full",
        blur_strength: int = 99
    ) -> Image.Image:
        """
        Anonymize image based on security level

        Args:
            image: PIL Image to anonymize
            level: Anonymization level - "partial", "full", or "maximum"
                - partial: Blur faces only
                - full: Blur faces + remove text + strip metadata
                - maximum: Full + synthetic noise augmentation
            blur_strength: Gaussian blur kernel size (must be odd)

        Returns:
            Anonymized PIL Image
        """
        if level not in ["partial", "full", "maximum"]:
            raise ValueError(f"Invalid anonymization level: {level}")

        # Convert to numpy array for processing
        img_array = np.array(image)

        # Ensure blur strength is odd
        if blur_strength % 2 == 0:
            blur_strength += 1

        # Apply face blurring for all levels
        if level in ["partial", "full", "maximum"]:
            img_array = self._blur_faces(img_array, blur_strength)

        # Apply text removal and metadata stripping for full/maximum
        if level in ["full", "maximum"]:
            img_array = self._remove_text(img_array, blur_strength)

        # Convert back to PIL Image
        anonymized_image = Image.fromarray(img_array)

        # Strip EXIF metadata for full/maximum
        if level in ["full", "maximum"]:
            anonymized_image = self._strip_exif(anonymized_image)

        # Add synthetic augmentation for maximum level
        if level == "maximum":
            anonymized_image = self.generate_synthetic_variant(anonymized_image)

        return anonymized_image

    def _blur_faces(self, img: np.ndarray, blur_strength: int = 99) -> np.ndarray:
        """
        Detect and blur faces in image using Haar Cascade

        Args:
            img: Input image array
            blur_strength: Gaussian blur kernel size

        Returns:
            Image with blurred faces
        """
        if self.face_cascade is None:
            logger.warning("Face detection not available, skipping face blur")
            return img

        # Convert to grayscale for face detection
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        # Blur each detected face
        for (x, y, w, h) in faces:
            # Extract face region with padding
            padding = int(max(w, h) * 0.2)
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(img.shape[1], x + w + padding)
            y2 = min(img.shape[0], y + h + padding)

            # Apply strong Gaussian blur
            face_region = img[y1:y2, x1:x2]
            blurred_face = cv2.GaussianBlur(face_region, (blur_strength, blur_strength), 0)
            img[y1:y2, x1:x2] = blurred_face

            logger.debug(f"Blurred face at ({x}, {y}) size {w}x{h}")

        logger.info(f"Blurred {len(faces)} face(s)")
        return img

    def _remove_text(self, img: np.ndarray, blur_strength: int = 99) -> np.ndarray:
        """
        Detect and remove text regions using EasyOCR

        Args:
            img: Input image array
            blur_strength: Gaussian blur kernel size

        Returns:
            Image with text regions blurred
        """
        if not EASYOCR_AVAILABLE or self.reader is None:
            logger.warning("EasyOCR not available, skipping text removal")
            return img

        try:
            # Detect text regions
            results = self.reader.readtext(img)

            # Blur each text region
            for (bbox, text, confidence) in results:
                if confidence < 0.3:  # Skip low-confidence detections
                    continue

                # Extract bounding box coordinates
                top_left = tuple(map(int, bbox[0]))
                bottom_right = tuple(map(int, bbox[2]))

                # Add padding around text
                padding = 5
                x1 = max(0, top_left[0] - padding)
                y1 = max(0, top_left[1] - padding)
                x2 = min(img.shape[1], bottom_right[0] + padding)
                y2 = min(img.shape[0], bottom_right[1] + padding)

                # Apply blur to text region
                text_region = img[y1:y2, x1:x2]
                if text_region.size > 0:
                    blurred_text = cv2.GaussianBlur(
                        text_region,
                        (blur_strength, blur_strength),
                        0
                    )
                    img[y1:y2, x1:x2] = blurred_text

                logger.debug(f"Removed text: '{text}' (confidence: {confidence:.2f})")

            logger.info(f"Removed {len(results)} text region(s)")
        except Exception as e:
            logger.error(f"Text removal failed: {e}")

        return img

    def _strip_exif(self, image: Image.Image) -> Image.Image:
        """
        Remove all EXIF metadata from image

        Args:
            image: PIL Image with potential metadata

        Returns:
            Image without EXIF metadata
        """
        # Create new image without metadata
        data = list(image.getdata())
        image_without_exif = Image.new(image.mode, image.size)
        image_without_exif.putdata(data)

        logger.info("Stripped EXIF metadata")
        return image_without_exif

    def generate_synthetic_variant(
        self,
        image: Image.Image,
        noise_level: float = 0.02,
        rotation_range: Tuple[float, float] = (-3, 3),
        color_shift: float = 0.1
    ) -> Image.Image:
        """
        Generate synthetic variant with augmentations for privacy

        Args:
            image: Input PIL Image
            noise_level: Gaussian noise standard deviation (0-1)
            rotation_range: Random rotation range in degrees
            color_shift: Color jitter factor (0-1)

        Returns:
            Augmented PIL Image
        """
        img_array = np.array(image).astype(np.float32) / 255.0

        # Add Gaussian noise
        if noise_level > 0:
            noise = np.random.normal(0, noise_level, img_array.shape)
            img_array = np.clip(img_array + noise, 0, 1)

        # Apply random rotation
        if rotation_range[0] != 0 or rotation_range[1] != 0:
            angle = np.random.uniform(rotation_range[0], rotation_range[1])
            img_array = (img_array * 255).astype(np.uint8)
            center = (img_array.shape[1] // 2, img_array.shape[0] // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            img_array = cv2.warpAffine(img_array, rotation_matrix,
                                       (img_array.shape[1], img_array.shape[0]))
            img_array = img_array.astype(np.float32) / 255.0

        # Apply color shift
        if color_shift > 0 and len(img_array.shape) == 3:
            shift = np.random.uniform(-color_shift, color_shift, 3)
            for i in range(3):
                img_array[:, :, i] = np.clip(img_array[:, :, i] + shift[i], 0, 1)

        # Convert back to uint8 and PIL Image
        img_array = (img_array * 255).astype(np.uint8)
        augmented_image = Image.fromarray(img_array)

        logger.info("Applied synthetic augmentation")
        return augmented_image

    def detect_sensitive_content(self, image: Image.Image) -> dict:
        """
        Detect potentially sensitive content in image

        Returns:
            Dictionary with detection results
        """
        results = {
            "faces_detected": 0,
            "text_detected": 0,
            "has_exif": False,
            "sensitivity_score": 0.0
        }

        img_array = np.array(image)

        # Check for faces
        if self.face_cascade is not None:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            results["faces_detected"] = len(faces)

        # Check for text
        if EASYOCR_AVAILABLE and self.reader is not None:
            try:
                text_results = self.reader.readtext(img_array)
                results["text_detected"] = len([r for r in text_results if r[2] > 0.3])
            except Exception as e:
                logger.error(f"Text detection failed: {e}")

        # Check for EXIF data
        try:
            exif_data = image.getexif()
            results["has_exif"] = len(exif_data) > 0
        except Exception:
            pass

        # Calculate sensitivity score (0-1)
        score = 0.0
        if results["faces_detected"] > 0:
            score += 0.4
        if results["text_detected"] > 0:
            score += 0.3
        if results["has_exif"]:
            score += 0.3
        results["sensitivity_score"] = min(score, 1.0)

        return results
