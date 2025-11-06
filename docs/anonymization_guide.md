# Anonymization Pipeline Guide

## Overview

The VLA Inference API includes a comprehensive anonymization pipeline for protecting user privacy by removing personally identifiable information (PII) from both images and text data before storage or processing.

## Features

### Image Anonymization
- **Face Detection & Blurring**: Automatically detect and blur faces using Haar Cascade classifiers
- **Text Removal**: Detect and remove text from images using EasyOCR
- **EXIF Stripping**: Remove all metadata from images
- **Synthetic Augmentation**: Add noise and transformations for maximum privacy

### Text Anonymization
- **Email Removal**: Detect and remove email addresses
- **Phone Number Removal**: Support for US and international formats
- **SSN Detection**: Remove Social Security Numbers
- **Credit Card Detection**: Identify and remove credit card numbers with Luhn validation
- **Name Detection**: Use NER (Named Entity Recognition) to identify and remove person names
- **Address Removal**: Detect and remove physical addresses
- **IP Address Removal**: Remove IP addresses from text

## Privacy Levels

### None
- No anonymization applied
- Original data preserved

### Basic
- **Text**: Remove emails, phones, SSN, credit cards
- **Image**: Blur faces only

### Standard (Recommended)
- **Text**: Basic + remove names and addresses
- **Image**: Blur faces + remove text + strip EXIF

### Maximum
- **Text**: Aggressive PII removal with enhanced name matching
- **Image**: Full anonymization + synthetic augmentation

## Usage

### Basic Usage

```python
from src.utils.anonymization import anonymize_data

# Anonymize text
text = "Contact John Doe at john.doe@example.com or call 555-123-4567"
anonymized_text = anonymize_data(text, level="standard")
# Output: "Contact [NAME] at [EMAIL] or call [PHONE]"

# Anonymize image
from PIL import Image
img = Image.open("photo.jpg")
anonymized_img = anonymize_data(img, level="standard")

# Anonymize mixed data
data = {
    "instruction": "Email admin@company.com",
    "image": img,
    "metadata": {"task_id": "123"}
}
anonymized = anonymize_data(data, level="standard", data_type="mixed")
```

### Advanced Usage with Detection

```python
from src.utils.anonymization import detect_sensitive_content

# Detect sensitive content
detection = detect_sensitive_content(text)
print(f"Sensitivity Score: {detection['overall_sensitivity_score']}")
print(f"Recommended Level: {detection['recommendation']}")

# Details
print(f"Emails found: {detection['details']['emails']}")
print(f"Phones found: {detection['details']['phones']}")
```

### Storage Pipeline Integration

```python
from src.utils.anonymization.storage_integration import AnonymizationPipeline

# Create pipeline
pipeline = AnonymizationPipeline(
    default_level="standard",
    auto_detect=True,  # Automatically upgrade level based on sensitivity
    fail_on_detection=False  # Don't fail on high-sensitivity detection
)

# Process before storage
data = {
    "instruction": "Pick up the red cup",
    "image": img,
    "metadata": {"task_id": "123"}
}

anonymized = pipeline.process_before_storage(data)

# Serialize for S3
serialized = pipeline.serialize_for_s3(anonymized, include_image=True)

# Later: deserialize from S3
deserialized = pipeline.deserialize_from_s3(serialized)
```

## Storage Integration

### Before S3 Upload

```python
# In storage service
from src.utils.anonymization.storage_integration import create_anonymization_pipeline

# Initialize pipeline
anonymization_pipeline = create_anonymization_pipeline({
    "default_level": "standard",
    "auto_detect": True,
    "fail_on_detection": False
})

# Before storing
anonymized_data = anonymization_pipeline.process_before_storage(raw_data)

# Upload to S3
s3_client.put_object(
    Bucket=bucket_name,
    Key=object_key,
    Body=json.dumps(anonymized_data)
)
```

### Before Embedding Generation

```python
# Anonymize text before generating embeddings
# Note: Uses preserve_context=True to maintain structure
anonymized_text = anonymization_pipeline.process_before_embedding(
    text=instruction,
    privacy_level="standard"
)

# Generate embeddings
embeddings = embedding_model.encode(anonymized_text)
```

## Configuration

### Environment Variables

```bash
# Enable/disable anonymization
ANONYMIZATION_ENABLED=true

# Default privacy level
ANONYMIZATION_DEFAULT_LEVEL=standard

# Auto-detect and upgrade level
ANONYMIZATION_AUTO_DETECT=true

# Fail on high-sensitivity detection
ANONYMIZATION_FAIL_ON_HIGH_SENSITIVITY=false

# Use GPU for image processing (requires CUDA)
ANONYMIZATION_USE_GPU=false
```

### Application Config

```python
ANONYMIZATION_CONFIG = {
    "enabled": True,
    "default_level": "standard",
    "auto_detect": True,
    "fail_on_detection": False,
    "use_gpu": False,
    "preserve_context_for_embeddings": True
}
```

## Dependencies

### Required
```bash
pip install Pillow opencv-python numpy
```

### Optional (Enhanced Features)
```bash
# For text detection in images
pip install easyocr

# For name detection using NER
pip install spacy
python -m spacy download en_core_web_sm
```

## API Integration

### REST API Endpoint

```python
# POST /api/v1/data/anonymize
{
    "data": {
        "instruction": "Contact john@example.com",
        "image_url": "https://..."
    },
    "level": "standard",
    "detect_only": false
}

# Response
{
    "anonymized_data": {
        "instruction": "Contact [EMAIL]",
        "image_url": "s3://anonymized/..."
    },
    "metadata": {
        "sensitivity_score": 0.4,
        "applied_level": "standard",
        "pii_removed": {
            "emails": 1,
            "faces": 0,
            "text_regions": 0
        }
    }
}
```

### Detection Only

```python
# POST /api/v1/data/detect-sensitivity
{
    "data": {
        "instruction": "SSN: 123-45-6789"
    }
}

# Response
{
    "sensitivity_score": 0.8,
    "recommendation": "maximum",
    "details": {
        "emails": 0,
        "phones": 0,
        "ssn": 1,
        "credit_cards": 0
    }
}
```

## Performance Considerations

### Image Processing
- Face detection: ~50-200ms per image (CPU)
- Text detection with EasyOCR: ~500-2000ms per image (CPU)
- GPU acceleration available for OCR operations

### Text Processing
- Basic PII removal: ~10-50ms per text
- NER-based name detection: ~50-200ms per text

### Recommendations
- Enable GPU for high-throughput image processing
- Use basic level for real-time applications
- Use standard/maximum for batch processing and storage

## Testing

```bash
# Run anonymization tests
python -m pytest tests/test_anonymization.py -v

# Run specific test class
python -m pytest tests/test_anonymization.py::TestTextAnonymization -v

# Check coverage
python -m pytest tests/test_anonymization.py --cov=src/utils/anonymization
```

## Best Practices

1. **Always anonymize before storage**: Apply anonymization before uploading to S3 or storing in databases
2. **Use auto-detection**: Enable automatic sensitivity detection to ensure appropriate privacy levels
3. **Preserve context for ML**: Use `preserve_context=True` when anonymizing text for embeddings
4. **Log anonymization events**: Track what was anonymized for audit purposes
5. **Test with real data**: Validate anonymization with representative samples
6. **Review privacy levels**: Regularly review and adjust privacy levels based on use case

## Security Considerations

- Anonymization is **irreversible** - original data cannot be recovered
- EXIF metadata removal prevents location tracking
- Face blurring protects individual identity
- PII removal complies with GDPR and privacy regulations
- Consider legal requirements for your jurisdiction

## Troubleshooting

### EasyOCR Not Available
- Install: `pip install easyocr`
- Text detection in images will be disabled without it

### spaCy Model Missing
- Install model: `python -m spacy download en_core_web_sm`
- Name detection will use basic patterns as fallback

### GPU Not Available
- Set `use_gpu=False` in configuration
- CPU processing will be used (slower but functional)

## Future Enhancements

- [ ] Support for additional languages (EasyOCR multi-language)
- [ ] Deep learning-based face detection (MTCNN, RetinaFace)
- [ ] Custom PII patterns via configuration
- [ ] Differential privacy for numerical data
- [ ] Reversible anonymization with secure key storage
- [ ] Real-time video anonymization
- [ ] Federated learning integration

## License

This anonymization pipeline is part of the VLA Inference API Platform.
See LICENSE file for details.
