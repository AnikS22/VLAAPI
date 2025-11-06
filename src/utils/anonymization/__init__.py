"""
Anonymization Utilities for VLA Inference API

Comprehensive PII removal and data anonymization for images and text
Supports multiple security levels and privacy-preserving augmentation
"""

from typing import Union, Dict, Any
from PIL import Image
import logging

from .image_anonymization import ImageAnonymizer
from .text_anonymization import TextAnonymizer

__all__ = ['ImageAnonymizer', 'TextAnonymizer', 'anonymize_data', 'detect_sensitive_content']

logger = logging.getLogger(__name__)


def anonymize_data(
    data: Union[str, Image.Image, Dict[str, Any]],
    level: str = "full",
    data_type: str = "auto"
) -> Union[str, Image.Image, Dict[str, Any]]:
    """
    Universal anonymization function for any data type

    Args:
        data: Input data (text string, PIL Image, or dict with mixed types)
        level: Anonymization level - "basic", "partial", "full", or "maximum"
        data_type: Data type hint - "auto", "text", "image", or "mixed"

    Returns:
        Anonymized data in same format as input

    Examples:
        >>> # Anonymize text instruction
        >>> anonymized_text = anonymize_data("Call John at 555-1234", level="full")
        >>> print(anonymized_text)  # "Call [NAME] at [PHONE]"

        >>> # Anonymize image
        >>> from PIL import Image
        >>> img = Image.open("photo.jpg")
        >>> anonymized_img = anonymize_data(img, level="full")

        >>> # Anonymize mixed data
        >>> data = {"instruction": "Call John", "image": img}
        >>> anonymized = anonymize_data(data, level="full", data_type="mixed")
    """
    # Auto-detect data type
    if data_type == "auto":
        if isinstance(data, str):
            data_type = "text"
        elif isinstance(data, Image.Image):
            data_type = "image"
        elif isinstance(data, dict):
            data_type = "mixed"
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

    # Anonymize based on type
    if data_type == "text":
        anonymizer = TextAnonymizer(use_ner=True)
        return anonymizer.anonymize_instruction(data, level=level)

    elif data_type == "image":
        anonymizer = ImageAnonymizer(use_gpu=False)
        return anonymizer.anonymize_image(data, level=level)

    elif data_type == "mixed":
        if not isinstance(data, dict):
            raise ValueError("Mixed data type requires dictionary input")

        anonymized = {}
        text_anonymizer = None
        image_anonymizer = None

        for key, value in data.items():
            if isinstance(value, str):
                if text_anonymizer is None:
                    text_anonymizer = TextAnonymizer(use_ner=True)
                anonymized[key] = text_anonymizer.anonymize_instruction(value, level=level)

            elif isinstance(value, Image.Image):
                if image_anonymizer is None:
                    image_anonymizer = ImageAnonymizer(use_gpu=False)
                anonymized[key] = image_anonymizer.anonymize_image(value, level=level)

            else:
                # Keep other data types as-is
                anonymized[key] = value

        return anonymized

    else:
        raise ValueError(f"Unsupported data_type: {data_type}")


def detect_sensitive_content(
    data: Union[str, Image.Image, Dict[str, Any]],
    data_type: str = "auto"
) -> Dict[str, Any]:
    """
    Detect potentially sensitive content without anonymization

    Args:
        data: Input data to analyze
        data_type: Data type hint - "auto", "text", "image", or "mixed"

    Returns:
        Dictionary with sensitivity analysis results

    Example:
        >>> detection = detect_sensitive_content("Contact john.doe@email.com")
        >>> print(detection["sensitivity_score"])  # 0.2
        >>> print(detection["pii_detected"])  # {"emails": 1, ...}
    """
    # Auto-detect data type
    if data_type == "auto":
        if isinstance(data, str):
            data_type = "text"
        elif isinstance(data, Image.Image):
            data_type = "image"
        elif isinstance(data, dict):
            data_type = "mixed"
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

    results = {
        "data_type": data_type,
        "overall_sensitivity_score": 0.0,
        "details": {}
    }

    # Detect based on type
    if data_type == "text":
        anonymizer = TextAnonymizer(use_ner=True)
        pii_results = anonymizer.detect_pii(data)
        results["details"] = pii_results
        results["overall_sensitivity_score"] = pii_results["sensitivity_score"]

    elif data_type == "image":
        anonymizer = ImageAnonymizer(use_gpu=False)
        image_results = anonymizer.detect_sensitive_content(data)
        results["details"] = image_results
        results["overall_sensitivity_score"] = image_results["sensitivity_score"]

    elif data_type == "mixed":
        if not isinstance(data, dict):
            raise ValueError("Mixed data type requires dictionary input")

        sensitivity_scores = []

        for key, value in data.items():
            if isinstance(value, str):
                anonymizer = TextAnonymizer(use_ner=True)
                detection = anonymizer.detect_pii(value)
                results["details"][f"{key}_text"] = detection
                sensitivity_scores.append(detection["sensitivity_score"])

            elif isinstance(value, Image.Image):
                anonymizer = ImageAnonymizer(use_gpu=False)
                detection = anonymizer.detect_sensitive_content(value)
                results["details"][f"{key}_image"] = detection
                sensitivity_scores.append(detection["sensitivity_score"])

        # Average sensitivity score across all data items
        if sensitivity_scores:
            results["overall_sensitivity_score"] = sum(sensitivity_scores) / len(sensitivity_scores)

    # Add recommendation
    score = results["overall_sensitivity_score"]
    if score >= 0.7:
        results["recommendation"] = "maximum"
    elif score >= 0.4:
        results["recommendation"] = "full"
    elif score >= 0.2:
        results["recommendation"] = "partial"
    else:
        results["recommendation"] = "none"

    return results


# Privacy level presets
PRIVACY_LEVELS = {
    "none": {
        "text": None,
        "image": None,
        "description": "No anonymization applied"
    },
    "basic": {
        "text": "basic",
        "image": "partial",
        "description": "Remove high-confidence PII (emails, phones, faces)"
    },
    "standard": {
        "text": "full",
        "image": "full",
        "description": "Remove all PII including names and addresses"
    },
    "maximum": {
        "text": "maximum",
        "image": "maximum",
        "description": "Aggressive PII removal with synthetic augmentation"
    }
}


def get_privacy_level(level_name: str) -> Dict[str, str]:
    """
    Get privacy level configuration

    Args:
        level_name: Privacy level name (none, basic, standard, maximum)

    Returns:
        Dictionary with text and image anonymization levels
    """
    if level_name not in PRIVACY_LEVELS:
        raise ValueError(f"Invalid privacy level: {level_name}. "
                        f"Choose from: {list(PRIVACY_LEVELS.keys())}")
    return PRIVACY_LEVELS[level_name]
