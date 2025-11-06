# Consent Management System

## Overview

The VLA Inference API includes a comprehensive consent management system for privacy compliance with regulations like GDPR, CCPA, and other data protection laws.

## Consent Tiers

The system supports four consent tiers, each with different data usage permissions:

### 1. NONE (Default)
- **Purpose**: Complete opt-out
- **Permissions**: No data storage or processing beyond operational necessity
- **Use Case**: Privacy-conscious users who want minimal data retention

### 2. BASIC
- **Purpose**: Operational data only
- **Permissions**: Store essential request metadata only
- **Restrictions**: No image storage, no embeddings, no training data
- **Use Case**: Users who need service but want minimal data collection

### 3. ANALYTICS
- **Purpose**: Service improvement
- **Permissions**: Store embeddings for analytics
- **Restrictions**: No raw image storage, no training data usage
- **Use Case**: Users who want to help improve the service without contributing to training

### 4. RESEARCH
- **Purpose**: Full data usage including ML training
- **Permissions**: Store images, embeddings, and use for model training
- **Requirements**: Explicit consent with clear explanation
- **Use Case**: Users who want to contribute to model improvement

## Anonymization Levels

Data can be anonymized at four different levels:

- **FULL**: Complete anonymization, no PII retained
- **PARTIAL**: Pseudonymization with reversible identifiers
- **MINIMAL**: Basic PII removal, trackable patterns remain
- **NONE**: No anonymization (only with explicit consent)

## API Endpoints

### Get Customer Consent

```http
GET /admin/customers/{customer_id}/consent
Authorization: Bearer <admin_api_key>
```

Response:
```json
{
  "customer_id": "123e4567-e89b-12d3-a456-426614174000",
  "consent_tier": "analytics",
  "can_store_images": false,
  "can_store_embeddings": true,
  "can_use_for_training": false,
  "anonymization_level": "full",
  "consent_granted_at": "2025-01-01T00:00:00Z",
  "consent_updated_at": "2025-01-15T10:30:00Z",
  "expires_at": null
}
```

### Update Customer Consent

```http
POST /admin/customers/{customer_id}/consent
Authorization: Bearer <admin_api_key>
Content-Type: application/json

{
  "consent_tier": "analytics",
  "can_store_images": false,
  "can_store_embeddings": true,
  "can_use_for_training": false,
  "anonymization_level": "full",
  "expires_at": null
}
```

### Check Specific Permissions

```http
GET /admin/customers/{customer_id}/consent/permissions?check=embeddings
Authorization: Bearer <admin_api_key>
```

Response:
```json
{
  "permission": "store_embeddings",
  "allowed": true
}
```

Available checks: `images`, `embeddings`, `training`, `anonymization`

### Revoke Consent

```http
DELETE /admin/customers/{customer_id}/consent
Authorization: Bearer <admin_api_key>
```

Sets consent to NONE tier and disables all permissions.

## Consent Validation Logic

The system enforces these validation rules:

1. **NONE tier**: Cannot have any data permissions enabled
2. **BASIC tier**: Cannot allow training or embeddings
3. **ANALYTICS tier**: Can store embeddings but not use for training
4. **RESEARCH tier**: Can use for training only if storing images or embeddings

## Integration with Inference Pipeline

The inference endpoint automatically checks consent before:

1. **Storing image metadata**: Only if `can_store_images` is true
2. **Storing embeddings**: Only if `can_store_embeddings` is true and tier is ANALYTICS or RESEARCH
3. **Using data for training**: Only if `can_use_for_training` is true and tier is RESEARCH

Example inference flow:

```python
# 1. Check consent (cached for 10 minutes)
can_store_images = await consent_manager.can_store_images(customer_id, db)
can_store_embeddings = await consent_manager.can_store_embeddings(customer_id, db)

# 2. Run inference
result = await inference_service.infer(...)

# 3. Log with respect to consent
log_entry = InferenceLog(
    # Only store image shape if consent allows
    image_shape=[h, w, c] if can_store_images else None,
    ...
)

# 4. Store embeddings if allowed
if can_store_embeddings:
    await store_embedding(customer_id, embedding)
```

## Caching

Consent preferences are cached in Redis for 10 minutes to reduce database load:

- **Cache key format**: `consent:{customer_id}`
- **TTL**: 600 seconds (10 minutes)
- **Invalidation**: Automatic on consent updates

## Audit Trail

All consent changes are logged in the `customer_consent_audit` table:

```sql
SELECT * FROM vlaapi.customer_consent_audit
WHERE customer_id = 'customer-uuid'
ORDER BY timestamp DESC;
```

Audit logs include:
- Previous and new consent tier
- Who made the change (user/admin)
- Timestamp and IP address
- Optional reason for change

## Python Usage Examples

### Check Consent in Service

```python
from src.services.consent import get_consent_manager

# Initialize consent manager
consent_manager = get_consent_manager(redis_client)

# Check if customer allows image storage
can_store = await consent_manager.can_store_images(customer_id, db)

if can_store:
    # Store image data
    await store_image(...)
```

### Update Consent Programmatically

```python
from src.models.contracts.consent import ConsentTier, AnonymizationLevel

# Update customer consent
await consent_manager.update_consent(
    customer_id=customer_id,
    db=db,
    tier=ConsentTier.ANALYTICS,
    can_store_images=False,
    can_store_embeddings=True,
    can_use_for_training=False,
    anonymization_level=AnonymizationLevel.FULL,
)
```

### Get Anonymization Level

```python
# Get anonymization level for customer
level = await consent_manager.get_anonymization_level(customer_id, db)

if level == AnonymizationLevel.FULL:
    # Apply full anonymization
    data = anonymize_fully(data)
```

## Compliance Notes

### GDPR Compliance

- ✅ Right to access: `/admin/customers/{id}/consent` endpoint
- ✅ Right to rectification: Update consent via POST endpoint
- ✅ Right to erasure: Revoke consent via DELETE endpoint
- ✅ Data minimization: Consent-based data storage
- ✅ Purpose limitation: Tier-based usage restrictions
- ✅ Accountability: Full audit trail

### CCPA Compliance

- ✅ Right to know: Transparent consent tiers
- ✅ Right to delete: Consent revocation
- ✅ Right to opt-out: NONE tier
- ✅ Non-discrimination: Service works with all tiers

## Best Practices

1. **Default to NONE**: New customers start with no data collection
2. **Explicit consent**: Require user action to upgrade consent tier
3. **Clear explanations**: Explain what each tier means in UI
4. **Easy revocation**: Make it simple to downgrade or revoke consent
5. **Regular review**: Remind users to review consent preferences
6. **Expiration dates**: Set expiration for time-limited consent
7. **Audit everything**: Log all consent changes with reasons

## Testing

### Test Consent Validation

```python
import pytest
from src.services.consent import ConsentManager
from src.models.contracts.consent import ConsentTier

async def test_consent_validation():
    manager = ConsentManager(redis_client)

    # Should raise ValueError: NONE tier cannot have permissions
    with pytest.raises(ValueError):
        await manager.update_consent(
            customer_id="test-id",
            db=db,
            tier=ConsentTier.NONE,
            can_store_images=True,  # Invalid!
        )

    # Should succeed: ANALYTICS tier can store embeddings
    await manager.update_consent(
        customer_id="test-id",
        db=db,
        tier=ConsentTier.ANALYTICS,
        can_store_embeddings=True,
    )
```

## Future Enhancements

- [ ] Customer self-service consent portal
- [ ] Consent request workflows
- [ ] Automated consent expiration handling
- [ ] Integration with data deletion workflows
- [ ] Multi-language consent forms
- [ ] Consent preferences export (JSON/PDF)
