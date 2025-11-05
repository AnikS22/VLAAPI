"""Image processing utilities for VLA inference."""

import base64
import io
from typing import Tuple

import numpy as np
from PIL import Image

from src.core.constants import MAX_IMAGE_SIZE_MB


def decode_image(image_data: str) -> Image.Image:
    """Decode base64-encoded image or load from URL.

    Args:
        image_data: Base64-encoded image string or URL

    Returns:
        PIL Image object

    Raises:
        ValueError: If image data is invalid
    """
    # Check if it's a URL (starts with http:// or https://)
    if image_data.startswith(("http://", "https://")):
        raise ValueError(
            "URL images not yet supported. Please use base64-encoded images."
        )

    # Decode base64
    try:
        # Remove data URI prefix if present (e.g., "data:image/png;base64,")
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]

        # Decode base64
        image_bytes = base64.b64decode(image_data)

        # Check size
        size_mb = len(image_bytes) / (1024 * 1024)
        if size_mb > MAX_IMAGE_SIZE_MB:
            raise ValueError(
                f"Image too large ({size_mb:.2f} MB). Maximum allowed: {MAX_IMAGE_SIZE_MB} MB"
            )

        # Load image
        image = Image.open(io.BytesIO(image_bytes))

        return image

    except Exception as e:
        raise ValueError(f"Failed to decode image: {e}")


def preprocess_image(
    image: Image.Image,
    target_size: Tuple[int, int] = (224, 224),
) -> Image.Image:
    """Preprocess image for VLA model input.

    Args:
        image: PIL Image
        target_size: Target image size (width, height)

    Returns:
        Preprocessed PIL Image
    """
    # Convert to RGB if needed
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Resize to target size
    image = image.resize(target_size, Image.Resampling.LANCZOS)

    return image


def image_to_numpy(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to numpy array.

    Args:
        image: PIL Image

    Returns:
        Numpy array with shape (H, W, C)
    """
    return np.array(image)
