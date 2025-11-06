"""
Unit Tests for Anonymization Pipeline
"""

import unittest
from PIL import Image
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.anonymization import (
    TextAnonymizer,
    ImageAnonymizer,
    anonymize_data,
    detect_sensitive_content,
    get_privacy_level
)
from src.utils.anonymization.storage_integration import AnonymizationPipeline


class TestTextAnonymization(unittest.TestCase):
    """Test text anonymization functionality"""

    def setUp(self):
        self.anonymizer = TextAnonymizer(use_ner=False)  # Disable NER for basic tests

    def test_email_removal(self):
        """Test email address removal"""
        text = "Contact me at john.doe@example.com for more info"
        anonymized = self.anonymizer.anonymize_instruction(text, level="basic")
        self.assertIn("[EMAIL]", anonymized)
        self.assertNotIn("john.doe@example.com", anonymized)

    def test_phone_removal(self):
        """Test phone number removal"""
        test_cases = [
            "Call 555-123-4567",
            "Phone: (555) 123-4567",
            "Contact: 5551234567"
        ]
        for text in test_cases:
            anonymized = self.anonymizer.anonymize_instruction(text, level="basic")
            self.assertIn("[PHONE]", anonymized)

    def test_ssn_removal(self):
        """Test SSN removal"""
        text = "SSN: 123-45-6789"
        anonymized = self.anonymizer.anonymize_instruction(text, level="basic")
        self.assertIn("[SSN]", anonymized)
        self.assertNotIn("123-45-6789", anonymized)

    def test_multiple_pii(self):
        """Test removal of multiple PII types"""
        text = "John Doe, email: john@example.com, phone: 555-1234"
        anonymized = self.anonymizer.anonymize_instruction(text, level="full")
        self.assertIn("[EMAIL]", anonymized)
        self.assertIn("[PHONE]", anonymized)

    def test_preserve_context(self):
        """Test that placeholders preserve context"""
        text = "Email admin@company.com for support"
        anonymized = self.anonymizer.anonymize_instruction(
            text,
            level="basic"
        )
        # Should have placeholder
        self.assertIn("[EMAIL]", anonymized)
        # Should preserve surrounding text
        self.assertIn("for support", anonymized)

    def test_detect_pii(self):
        """Test PII detection without removal"""
        text = "Contact john@example.com or call 555-1234"
        detection = self.anonymizer.detect_pii(text)
        self.assertEqual(detection["emails"], 1)
        self.assertGreaterEqual(detection["phones"], 1)
        self.assertGreater(detection["sensitivity_score"], 0)


class TestImageAnonymization(unittest.TestCase):
    """Test image anonymization functionality"""

    def setUp(self):
        self.anonymizer = ImageAnonymizer(use_gpu=False)

    def create_test_image(self, size=(640, 480)):
        """Create a test RGB image"""
        return Image.fromarray(
            np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
        )

    def test_anonymize_basic(self):
        """Test basic image anonymization"""
        img = self.create_test_image()
        anonymized = self.anonymizer.anonymize_image(img, level="partial")

        # Check that output is valid image
        self.assertIsInstance(anonymized, Image.Image)
        self.assertEqual(anonymized.size, img.size)

    def test_strip_exif(self):
        """Test EXIF metadata removal"""
        img = self.create_test_image()
        # Note: Test image has no EXIF, but we test the function doesn't crash
        anonymized = self.anonymizer.anonymize_image(img, level="full")
        self.assertIsInstance(anonymized, Image.Image)

    def test_synthetic_variant(self):
        """Test synthetic augmentation"""
        img = self.create_test_image()
        augmented = self.anonymizer.generate_synthetic_variant(img)

        # Should be same size but different pixels
        self.assertEqual(augmented.size, img.size)
        # Images should be different (with high probability)
        self.assertFalse(np.array_equal(np.array(img), np.array(augmented)))

    def test_detect_sensitive_content(self):
        """Test sensitive content detection"""
        img = self.create_test_image()
        detection = self.anonymizer.detect_sensitive_content(img)

        # Should return valid detection results
        self.assertIn("faces_detected", detection)
        self.assertIn("text_detected", detection)
        self.assertIn("sensitivity_score", detection)
        self.assertGreaterEqual(detection["sensitivity_score"], 0.0)
        self.assertLessEqual(detection["sensitivity_score"], 1.0)


class TestUniversalAnonymization(unittest.TestCase):
    """Test universal anonymize_data function"""

    def test_text_anonymization(self):
        """Test anonymizing text data"""
        text = "Email: test@example.com"
        anonymized = anonymize_data(text, level="full", data_type="text")
        self.assertIn("[EMAIL]", anonymized)

    def test_image_anonymization(self):
        """Test anonymizing image data"""
        img = Image.fromarray(
            np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        )
        anonymized = anonymize_data(img, level="full", data_type="image")
        self.assertIsInstance(anonymized, Image.Image)

    def test_mixed_anonymization(self):
        """Test anonymizing mixed data"""
        data = {
            "instruction": "Contact admin@example.com",
            "image": Image.fromarray(
                np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            ),
            "metadata": {"task_id": "123"}
        }
        anonymized = anonymize_data(data, level="full", data_type="mixed")

        # Check text anonymized
        self.assertIn("[EMAIL]", anonymized["instruction"])
        # Check image anonymized
        self.assertIsInstance(anonymized["image"], Image.Image)
        # Check metadata preserved
        self.assertEqual(anonymized["metadata"]["task_id"], "123")

    def test_auto_detect_type(self):
        """Test automatic data type detection"""
        # Auto-detect text
        text = "Some text"
        result = anonymize_data(text, level="basic")
        self.assertIsInstance(result, str)

        # Auto-detect image
        img = Image.fromarray(
            np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        )
        result = anonymize_data(img, level="basic")
        self.assertIsInstance(result, Image.Image)


class TestSensitivityDetection(unittest.TestCase):
    """Test sensitivity detection"""

    def test_detect_text_sensitivity(self):
        """Test text sensitivity detection"""
        # High sensitivity text
        high_sensitive = "SSN: 123-45-6789, Email: test@example.com, Phone: 555-1234"
        detection = detect_sensitive_content(high_sensitive, data_type="text")
        self.assertGreater(detection["overall_sensitivity_score"], 0.5)
        self.assertEqual(detection["recommendation"], "full")

        # Low sensitivity text
        low_sensitive = "Pick up the red cup from the table"
        detection = detect_sensitive_content(low_sensitive, data_type="text")
        self.assertEqual(detection["overall_sensitivity_score"], 0.0)
        self.assertEqual(detection["recommendation"], "none")

    def test_privacy_levels(self):
        """Test privacy level configurations"""
        levels = ["none", "basic", "standard", "maximum"]
        for level in levels:
            config = get_privacy_level(level)
            self.assertIn("text", config)
            self.assertIn("image", config)
            self.assertIn("description", config)


class TestStorageIntegration(unittest.TestCase):
    """Test storage pipeline integration"""

    def setUp(self):
        self.pipeline = AnonymizationPipeline(
            default_level="standard",
            auto_detect=True,
            fail_on_detection=False
        )

    def test_process_before_storage(self):
        """Test processing data before storage"""
        data = {
            "instruction": "Email: test@example.com",
            "image": Image.fromarray(
                np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            ),
            "metadata": {"task_id": "123"}
        }

        anonymized = self.pipeline.process_before_storage(data)

        # Check anonymization applied
        self.assertIn("[EMAIL]", anonymized["instruction"])
        # Check metadata added
        self.assertIn("anonymization", anonymized["metadata"])
        self.assertTrue(anonymized["metadata"]["anonymization"]["applied"])

    def test_auto_detect_upgrade(self):
        """Test automatic level upgrade on detection"""
        # Create high-sensitivity data
        data = {
            "instruction": "SSN: 123-45-6789, Credit Card: 4532-1234-5678-9010"
        }

        # Process with basic level (should upgrade)
        anonymized = self.pipeline.process_before_storage(data, privacy_level="basic")

        # Check that level was upgraded
        applied_level = anonymized["metadata"]["anonymization"]["level"]
        self.assertIn(applied_level, ["full", "maximum"])

    def test_serialization(self):
        """Test S3 serialization"""
        data = {
            "instruction": "Test instruction",
            "image": Image.fromarray(
                np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            ),
            "metadata": {"task_id": "123"}
        }

        # Serialize
        serialized = self.pipeline.serialize_for_s3(data, include_image=True)

        # Check serialization
        self.assertIn("instruction", serialized)
        self.assertIn("image_bytes", serialized)
        self.assertIsInstance(serialized["image_bytes"], bytes)

        # Deserialize
        deserialized = self.pipeline.deserialize_from_s3(serialized)
        self.assertIsInstance(deserialized["image"], Image.Image)


if __name__ == "__main__":
    unittest.main()
