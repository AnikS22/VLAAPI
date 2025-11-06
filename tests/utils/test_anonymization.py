"""
Comprehensive tests for anonymization utilities.

Tests image processing (face blurring, OCR, EXIF stripping) and text PII removal.
"""

import pytest
import numpy as np
from PIL import Image
import io
from unittest.mock import Mock, patch, MagicMock
from src.utils.anonymization import (
    anonymize_image,
    blur_faces,
    remove_text_from_image,
    strip_exif,
    generate_synthetic_variant,
    anonymize_text,
    remove_pii_patterns,
    detect_and_remove_names,
    detect_and_remove_addresses,
    calculate_sensitivity_score,
    AnonymizationLevel
)


@pytest.fixture
def sample_image():
    """Create a sample PIL Image for testing."""
    img_array = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    return Image.fromarray(img_array)


@pytest.fixture
def sample_image_with_exif():
    """Create a sample image with EXIF data."""
    img = Image.new('RGB', (100, 100), color='red')
    exif_data = img.getexif()
    exif_data[0x010F] = "TestCamera"  # Manufacturer
    exif_data[0x8769] = {"GPS": "40.7128, -74.0060"}  # GPS data
    return img


class TestImageFaceBlurring:
    """Test face detection and blurring."""

    @patch('cv2.CascadeClassifier')
    def test_blur_faces_detected(self, mock_cascade, sample_image):
        """Test face blurring when faces are detected."""
        # Mock face detection to return one face
        mock_classifier = Mock()
        mock_classifier.detectMultiScale.return_value = [(100, 100, 50, 50)]
        mock_cascade.return_value = mock_classifier

        result = blur_faces(sample_image)

        assert isinstance(result, Image.Image)
        assert result.size == sample_image.size
        mock_classifier.detectMultiScale.assert_called_once()

    @patch('cv2.CascadeClassifier')
    def test_blur_faces_none_detected(self, mock_cascade, sample_image):
        """Test no blurring when no faces detected."""
        mock_classifier = Mock()
        mock_classifier.detectMultiScale.return_value = []
        mock_cascade.return_value = mock_classifier

        result = blur_faces(sample_image)

        assert isinstance(result, Image.Image)

    @patch('cv2.CascadeClassifier')
    def test_blur_faces_multiple_detected(self, mock_cascade, sample_image):
        """Test blurring multiple faces."""
        mock_classifier = Mock()
        mock_classifier.detectMultiScale.return_value = [
            (100, 100, 50, 50),
            (200, 200, 60, 60),
            (300, 150, 55, 55)
        ]
        mock_cascade.return_value = mock_classifier

        result = blur_faces(sample_image)

        assert isinstance(result, Image.Image)
        assert result.size == sample_image.size


class TestTextRemovalFromImages:
    """Test OCR-based text detection and removal."""

    @patch('pytesseract.image_to_data')
    def test_remove_text_detected(self, mock_ocr, sample_image):
        """Test text removal when text is detected."""
        # Mock OCR to return text regions
        mock_ocr.return_value = {
            'text': ['Hello', 'World', ''],
            'left': [50, 150, 0],
            'top': [50, 100, 0],
            'width': [100, 80, 0],
            'height': [30, 25, 0],
            'conf': [95, 90, -1]
        }

        result = remove_text_from_image(sample_image)

        assert isinstance(result, Image.Image)
        assert result.size == sample_image.size
        mock_ocr.assert_called_once()

    @patch('pytesseract.image_to_data')
    def test_remove_text_none_detected(self, mock_ocr, sample_image):
        """Test no changes when no text detected."""
        mock_ocr.return_value = {
            'text': [],
            'left': [],
            'top': [],
            'width': [],
            'height': [],
            'conf': []
        }

        result = remove_text_from_image(sample_image)

        assert isinstance(result, Image.Image)

    @patch('pytesseract.image_to_data')
    def test_remove_text_confidence_threshold(self, mock_ocr, sample_image):
        """Test text removal respects confidence threshold."""
        mock_ocr.return_value = {
            'text': ['HighConf', 'LowConf'],
            'left': [50, 150],
            'top': [50, 100],
            'width': [100, 80],
            'height': [30, 25],
            'conf': [95, 30]  # Second has low confidence
        }

        result = remove_text_from_image(sample_image, confidence_threshold=80)

        assert isinstance(result, Image.Image)


class TestEXIFStripping:
    """Test EXIF metadata removal."""

    def test_strip_exif_with_metadata(self, sample_image_with_exif):
        """Test EXIF stripping removes metadata."""
        result = strip_exif(sample_image_with_exif)

        assert isinstance(result, Image.Image)
        assert len(result.getexif()) == 0

    def test_strip_exif_without_metadata(self, sample_image):
        """Test EXIF stripping on image without metadata."""
        result = strip_exif(sample_image)

        assert isinstance(result, Image.Image)
        assert len(result.getexif()) == 0

    def test_strip_exif_preserves_image(self, sample_image_with_exif):
        """Test EXIF stripping preserves image data."""
        original_size = sample_image_with_exif.size
        result = strip_exif(sample_image_with_exif)

        assert result.size == original_size


class TestSyntheticVariantGeneration:
    """Test synthetic image variant generation."""

    def test_generate_synthetic_variant_basic(self, sample_image):
        """Test basic synthetic variant generation."""
        result = generate_synthetic_variant(sample_image)

        assert isinstance(result, Image.Image)
        assert result.size == sample_image.size

    def test_generate_synthetic_variant_different_from_original(self, sample_image):
        """Test synthetic variant differs from original."""
        result = generate_synthetic_variant(sample_image)

        # Convert to arrays for comparison
        original_array = np.array(sample_image)
        result_array = np.array(result)

        # Should be different but similar dimensions
        assert original_array.shape == result_array.shape
        # Should have some difference
        assert not np.array_equal(original_array, result_array)

    def test_generate_synthetic_variant_preserves_format(self, sample_image):
        """Test synthetic variant preserves image format."""
        result = generate_synthetic_variant(sample_image)

        assert result.mode == sample_image.mode


class TestTextPIIRemoval:
    """Test PII pattern detection and removal in text."""

    def test_remove_pii_email(self):
        """Test email address removal."""
        text = "Contact me at john.doe@example.com for details."
        result = remove_pii_patterns(text)

        assert "john.doe@example.com" not in result
        assert "[EMAIL_REDACTED]" in result

    def test_remove_pii_phone(self):
        """Test phone number removal."""
        text = "Call me at 555-123-4567 or (555) 987-6543"
        result = remove_pii_patterns(text)

        assert "555-123-4567" not in result
        assert "(555) 987-6543" not in result
        assert "[PHONE_REDACTED]" in result

    def test_remove_pii_ssn(self):
        """Test SSN removal."""
        text = "SSN: 123-45-6789"
        result = remove_pii_patterns(text)

        assert "123-45-6789" not in result
        assert "[SSN_REDACTED]" in result

    def test_remove_pii_credit_card(self):
        """Test credit card number removal."""
        text = "Card: 4532-1234-5678-9010"
        result = remove_pii_patterns(text)

        assert "4532-1234-5678-9010" not in result
        assert "[CREDIT_CARD_REDACTED]" in result

    def test_remove_pii_multiple_patterns(self):
        """Test removal of multiple PII patterns."""
        text = "Email: user@test.com Phone: 555-0123 SSN: 123-45-6789"
        result = remove_pii_patterns(text)

        assert "user@test.com" not in result
        assert "555-0123" not in result
        assert "123-45-6789" not in result
        assert "[EMAIL_REDACTED]" in result
        assert "[PHONE_REDACTED]" in result
        assert "[SSN_REDACTED]" in result

    def test_remove_pii_preserves_non_pii(self):
        """Test that non-PII text is preserved."""
        text = "The meeting is at 3pm tomorrow."
        result = remove_pii_patterns(text)

        assert result == text


class TestNameDetection:
    """Test name detection and removal."""

    @patch('spacy.load')
    def test_detect_and_remove_names(self, mock_spacy):
        """Test detection and removal of person names."""
        # Mock spaCy NER
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_entity = Mock()
        mock_entity.text = "John Doe"
        mock_entity.label_ = "PERSON"
        mock_doc.ents = [mock_entity]
        mock_nlp.return_value = mock_doc
        mock_spacy.return_value = mock_nlp

        text = "John Doe is attending the meeting."
        result = detect_and_remove_names(text)

        assert "John Doe" not in result
        assert "[NAME_REDACTED]" in result

    @patch('spacy.load')
    def test_detect_multiple_names(self, mock_spacy):
        """Test detection of multiple names."""
        mock_nlp = Mock()
        mock_doc = Mock()

        entity1 = Mock()
        entity1.text = "Alice Smith"
        entity1.label_ = "PERSON"

        entity2 = Mock()
        entity2.text = "Bob Johnson"
        entity2.label_ = "PERSON"

        mock_doc.ents = [entity1, entity2]
        mock_nlp.return_value = mock_doc
        mock_spacy.return_value = mock_nlp

        text = "Alice Smith and Bob Johnson are colleagues."
        result = detect_and_remove_names(text)

        assert "Alice Smith" not in result
        assert "Bob Johnson" not in result
        assert result.count("[NAME_REDACTED]") == 2


class TestAddressDetection:
    """Test address detection and removal."""

    @patch('spacy.load')
    def test_detect_and_remove_addresses(self, mock_spacy):
        """Test detection and removal of addresses."""
        mock_nlp = Mock()
        mock_doc = Mock()

        entity = Mock()
        entity.text = "123 Main Street"
        entity.label_ = "GPE"

        mock_doc.ents = [entity]
        mock_nlp.return_value = mock_doc
        mock_spacy.return_value = mock_nlp

        text = "Located at 123 Main Street, Springfield."
        result = detect_and_remove_addresses(text)

        assert "123 Main Street" not in result
        assert "[ADDRESS_REDACTED]" in result


class TestAnonymizationLevels:
    """Test different anonymization levels."""

    def test_anonymize_text_basic_level(self):
        """Test basic anonymization (emails and phones only)."""
        text = "Email: user@test.com Phone: 555-0123 Name: John Doe"
        result = anonymize_text(text, level=AnonymizationLevel.BASIC)

        assert "user@test.com" not in result
        assert "555-0123" not in result
        # Name should still be present in basic level
        assert "John Doe" in result

    @patch('spacy.load')
    def test_anonymize_text_standard_level(self, mock_spacy):
        """Test standard anonymization (emails, phones, names)."""
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_entity = Mock()
        mock_entity.text = "John Doe"
        mock_entity.label_ = "PERSON"
        mock_doc.ents = [mock_entity]
        mock_nlp.return_value = mock_doc
        mock_spacy.return_value = mock_nlp

        text = "Email: user@test.com Name: John Doe"
        result = anonymize_text(text, level=AnonymizationLevel.STANDARD)

        assert "user@test.com" not in result
        assert "John Doe" not in result

    def test_anonymize_image_basic_level(self, sample_image):
        """Test basic image anonymization (EXIF only)."""
        result = anonymize_image(sample_image, level=AnonymizationLevel.BASIC)

        assert isinstance(result, Image.Image)
        assert len(result.getexif()) == 0

    @patch('cv2.CascadeClassifier')
    def test_anonymize_image_standard_level(self, mock_cascade, sample_image):
        """Test standard image anonymization (EXIF + faces)."""
        mock_classifier = Mock()
        mock_classifier.detectMultiScale.return_value = [(100, 100, 50, 50)]
        mock_cascade.return_value = mock_classifier

        result = anonymize_image(sample_image, level=AnonymizationLevel.STANDARD)

        assert isinstance(result, Image.Image)
        assert len(result.getexif()) == 0

    @patch('cv2.CascadeClassifier')
    @patch('pytesseract.image_to_data')
    def test_anonymize_image_maximum_level(self, mock_ocr, mock_cascade, sample_image):
        """Test maximum image anonymization (all techniques)."""
        mock_classifier = Mock()
        mock_classifier.detectMultiScale.return_value = []
        mock_cascade.return_value = mock_classifier

        mock_ocr.return_value = {'text': [], 'left': [], 'top': [], 'width': [], 'height': [], 'conf': []}

        result = anonymize_image(sample_image, level=AnonymizationLevel.MAXIMUM)

        assert isinstance(result, Image.Image)
        assert len(result.getexif()) == 0


class TestSensitivityDetection:
    """Test sensitivity score calculation."""

    def test_calculate_sensitivity_low(self):
        """Test low sensitivity score."""
        text = "The weather is nice today."
        score = calculate_sensitivity_score(text)

        assert 0.0 <= score < 0.3

    def test_calculate_sensitivity_medium(self):
        """Test medium sensitivity score."""
        text = "My email is user@example.com"
        score = calculate_sensitivity_score(text)

        assert 0.3 <= score < 0.7

    def test_calculate_sensitivity_high(self):
        """Test high sensitivity score."""
        text = "SSN: 123-45-6789 Credit Card: 4532-1234-5678-9010"
        score = calculate_sensitivity_score(text)

        assert 0.7 <= score <= 1.0

    def test_calculate_sensitivity_multiple_indicators(self):
        """Test sensitivity with multiple PII types."""
        text = "Name: John Doe, Email: john@test.com, Phone: 555-1234, SSN: 123-45-6789"
        score = calculate_sensitivity_score(text)

        assert score > 0.7  # Should be high with multiple PII types

    def test_calculate_sensitivity_empty_text(self):
        """Test sensitivity score for empty text."""
        score = calculate_sensitivity_score("")

        assert score == 0.0
