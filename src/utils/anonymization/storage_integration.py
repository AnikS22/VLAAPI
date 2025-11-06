"""
Storage Pipeline Integration for Anonymization

Automatically anonymize data before storage in S3 and vector databases
"""

from typing import Optional, Dict, Any
from PIL import Image
import logging
import io
import json

from . import anonymize_data, detect_sensitive_content, get_privacy_level

logger = logging.getLogger(__name__)


class AnonymizationPipeline:
    """
    Integration layer for anonymization in storage pipeline
    """

    def __init__(
        self,
        default_level: str = "standard",
        auto_detect: bool = True,
        fail_on_detection: bool = False
    ):
        """
        Initialize anonymization pipeline

        Args:
            default_level: Default privacy level (none, basic, standard, maximum)
            auto_detect: Automatically detect and adjust anonymization level
            fail_on_detection: Raise error if high-sensitivity content detected
        """
        self.default_level = default_level
        self.auto_detect = auto_detect
        self.fail_on_detection = fail_on_detection

    def process_before_storage(
        self,
        data: Dict[str, Any],
        privacy_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process data before storing in S3 or vector database

        Args:
            data: Dictionary containing instruction, image, and metadata
            privacy_level: Override default privacy level

        Returns:
            Anonymized data dictionary

        Example:
            >>> pipeline = AnonymizationPipeline(default_level="standard")
            >>> data = {
            ...     "instruction": "Pick up the red cup",
            ...     "image": PIL.Image.open("scene.jpg"),
            ...     "metadata": {"task_id": "123"}
            ... }
            >>> anonymized = pipeline.process_before_storage(data)
        """
        level = privacy_level or self.default_level

        if level == "none":
            logger.info("Anonymization disabled")
            return data

        # Auto-detect sensitivity if enabled
        if self.auto_detect:
            detection = detect_sensitive_content(data, data_type="mixed")
            detected_level = detection["recommendation"]

            logger.info(f"Detected sensitivity score: {detection['overall_sensitivity_score']:.2f}")
            logger.info(f"Recommended level: {detected_level}")

            # Use higher of default or detected level
            level_hierarchy = ["none", "basic", "standard", "maximum"]
            if level_hierarchy.index(detected_level) > level_hierarchy.index(level):
                logger.warning(f"Upgrading anonymization level from {level} to {detected_level}")
                level = detected_level

            # Fail if high-sensitivity detected and fail_on_detection is True
            if self.fail_on_detection and detection["overall_sensitivity_score"] >= 0.7:
                raise ValueError(
                    f"High-sensitivity content detected (score: {detection['overall_sensitivity_score']:.2f}). "
                    "Cannot store without explicit approval."
                )

        # Apply anonymization
        privacy_config = get_privacy_level(level)
        anonymized_data = data.copy()

        # Anonymize instruction text
        if "instruction" in data and privacy_config["text"]:
            anonymized_data["instruction"] = anonymize_data(
                data["instruction"],
                level=privacy_config["text"],
                data_type="text"
            )
            logger.debug("Anonymized instruction text")

        # Anonymize image
        if "image" in data and privacy_config["image"]:
            anonymized_data["image"] = anonymize_data(
                data["image"],
                level=privacy_config["image"],
                data_type="image"
            )
            logger.debug("Anonymized image")

        # Add anonymization metadata
        if "metadata" not in anonymized_data:
            anonymized_data["metadata"] = {}
        anonymized_data["metadata"]["anonymization"] = {
            "applied": True,
            "level": level,
            "text_level": privacy_config["text"],
            "image_level": privacy_config["image"]
        }

        logger.info(f"Applied {level} anonymization to data")
        return anonymized_data

    def process_before_embedding(
        self,
        text: str,
        privacy_level: Optional[str] = None
    ) -> str:
        """
        Process text before generating embeddings
        Optional: May want to preserve some structure for better embeddings

        Args:
            text: Input text
            privacy_level: Override default privacy level

        Returns:
            Anonymized text
        """
        level = privacy_level or self.default_level

        if level == "none":
            return text

        # For embeddings, we might want to preserve context
        # Use preserve_context=True to keep placeholder structure
        privacy_config = get_privacy_level(level)

        if privacy_config["text"]:
            from .text_anonymization import TextAnonymizer
            anonymizer = TextAnonymizer(use_ner=True)
            anonymized = anonymizer.anonymize_instruction(
                text,
                level=privacy_config["text"],
                preserve_context=True  # Keep structure for embeddings
            )
            logger.debug("Anonymized text before embedding generation")
            return anonymized

        return text

    def serialize_for_s3(
        self,
        data: Dict[str, Any],
        include_image: bool = True
    ) -> Dict[str, Any]:
        """
        Serialize anonymized data for S3 storage

        Args:
            data: Anonymized data dictionary
            include_image: Include image in serialization

        Returns:
            JSON-serializable dictionary
        """
        serialized = {}

        # Copy text fields
        if "instruction" in data:
            serialized["instruction"] = data["instruction"]

        if "metadata" in data:
            serialized["metadata"] = data["metadata"]

        # Serialize image if included
        if include_image and "image" in data:
            img = data["image"]
            if isinstance(img, Image.Image):
                # Convert to bytes for storage
                img_buffer = io.BytesIO()
                img.save(img_buffer, format="PNG")
                serialized["image_bytes"] = img_buffer.getvalue()
                serialized["image_format"] = "PNG"
            else:
                logger.warning("Image is not PIL.Image, skipping serialization")

        return serialized

    def deserialize_from_s3(
        self,
        serialized_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deserialize data retrieved from S3

        Args:
            serialized_data: Serialized data from S3

        Returns:
            Deserialized data dictionary
        """
        data = {}

        # Copy text fields
        if "instruction" in serialized_data:
            data["instruction"] = serialized_data["instruction"]

        if "metadata" in serialized_data:
            data["metadata"] = serialized_data["metadata"]

        # Deserialize image if present
        if "image_bytes" in serialized_data:
            img_buffer = io.BytesIO(serialized_data["image_bytes"])
            data["image"] = Image.open(img_buffer)

        return data


def create_anonymization_pipeline(config: Optional[Dict[str, Any]] = None) -> AnonymizationPipeline:
    """
    Factory function to create anonymization pipeline from config

    Args:
        config: Configuration dictionary with keys:
            - default_level: Default privacy level
            - auto_detect: Enable automatic detection
            - fail_on_detection: Fail on high-sensitivity detection

    Returns:
        Configured AnonymizationPipeline instance

    Example:
        >>> config = {
        ...     "default_level": "standard",
        ...     "auto_detect": True,
        ...     "fail_on_detection": False
        ... }
        >>> pipeline = create_anonymization_pipeline(config)
    """
    if config is None:
        config = {}

    return AnonymizationPipeline(
        default_level=config.get("default_level", "standard"),
        auto_detect=config.get("auto_detect", True),
        fail_on_detection=config.get("fail_on_detection", False)
    )
