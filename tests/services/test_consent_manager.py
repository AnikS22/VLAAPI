"""
Comprehensive tests for ConsentManager service.

Tests Redis caching, database fallback, tier validation, and permission checks.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from src.services.consent import ConsentManager
from src.database.models import ConsentTier


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = Mock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock()
    return db


@pytest.fixture
def consent_manager(mock_redis, mock_db):
    """Create ConsentManager instance with mocked dependencies."""
    return ConsentManager(redis_client=mock_redis, db_session=mock_db)


class TestGetConsent:
    """Test consent retrieval with Redis cache and DB fallback."""

    @pytest.mark.asyncio
    async def test_get_consent_from_cache(self, consent_manager, mock_redis):
        """Test retrieving consent from Redis cache."""
        customer_id = "test-customer"
        cached_data = '{"tier": "analytics", "can_store_images": true}'
        mock_redis.get.return_value = cached_data

        result = await consent_manager.get_consent(customer_id)

        assert result["tier"] == "analytics"
        assert result["can_store_images"] is True
        mock_redis.get.assert_called_once_with(f"consent:{customer_id}")

    @pytest.mark.asyncio
    async def test_get_consent_from_db_fallback(self, consent_manager, mock_redis, mock_db):
        """Test retrieving consent from database when cache misses."""
        customer_id = "test-customer"
        mock_redis.get.return_value = None

        # Mock database query
        mock_consent = Mock()
        mock_consent.tier = ConsentTier.ANALYTICS
        mock_consent.can_store_images = True
        mock_consent.can_store_embeddings = True
        mock_consent.can_use_for_training = False
        mock_consent.updated_at = datetime.utcnow()

        mock_db.query.return_value.filter.return_value.first.return_value = mock_consent

        result = await consent_manager.get_consent(customer_id)

        assert result["tier"] == "analytics"
        assert result["can_store_images"] is True
        assert result["can_store_embeddings"] is True
        assert result["can_use_for_training"] is False

        # Verify cache was populated
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_consent_default_none(self, consent_manager, mock_redis, mock_db):
        """Test default consent when no record exists."""
        customer_id = "new-customer"
        mock_redis.get.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await consent_manager.get_consent(customer_id)

        assert result["tier"] == "none"
        assert result["can_store_images"] is False
        assert result["can_store_embeddings"] is False
        assert result["can_use_for_training"] is False


class TestPermissionChecks:
    """Test individual permission check methods."""

    @pytest.mark.asyncio
    async def test_can_store_images_true(self, consent_manager):
        """Test can_store_images returns True for analytics tier."""
        with patch.object(consent_manager, 'get_consent', AsyncMock(return_value={
            "tier": "analytics",
            "can_store_images": True
        })):
            result = await consent_manager.can_store_images("customer-1")
            assert result is True

    @pytest.mark.asyncio
    async def test_can_store_images_false(self, consent_manager):
        """Test can_store_images returns False for basic tier."""
        with patch.object(consent_manager, 'get_consent', AsyncMock(return_value={
            "tier": "basic",
            "can_store_images": False
        })):
            result = await consent_manager.can_store_images("customer-1")
            assert result is False

    @pytest.mark.asyncio
    async def test_can_store_embeddings_true(self, consent_manager):
        """Test can_store_embeddings returns True for research tier."""
        with patch.object(consent_manager, 'get_consent', AsyncMock(return_value={
            "tier": "research",
            "can_store_embeddings": True
        })):
            result = await consent_manager.can_store_embeddings("customer-1")
            assert result is True

    @pytest.mark.asyncio
    async def test_can_use_for_training_true(self, consent_manager):
        """Test can_use_for_training returns True for research tier."""
        with patch.object(consent_manager, 'get_consent', AsyncMock(return_value={
            "tier": "research",
            "can_use_for_training": True
        })):
            result = await consent_manager.can_use_for_training("customer-1")
            assert result is True


class TestUpdateConsent:
    """Test consent updates with tier validation."""

    @pytest.mark.asyncio
    async def test_update_consent_valid_tier(self, consent_manager, mock_redis, mock_db):
        """Test updating consent with valid tier."""
        customer_id = "test-customer"
        new_consent = {
            "tier": "analytics",
            "can_store_images": True,
            "can_store_embeddings": True,
            "can_use_for_training": False
        }

        mock_consent_record = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_consent_record

        result = await consent_manager.update_consent(customer_id, new_consent)

        assert result is True
        assert mock_consent_record.tier == ConsentTier.ANALYTICS
        assert mock_consent_record.can_store_images is True
        mock_db.commit.assert_called_once()
        mock_redis.delete.assert_called_once_with(f"consent:{customer_id}")

    @pytest.mark.asyncio
    async def test_update_consent_invalid_tier(self, consent_manager):
        """Test updating consent with invalid tier raises ValueError."""
        customer_id = "test-customer"
        invalid_consent = {
            "tier": "invalid_tier",
            "can_store_images": True
        }

        with pytest.raises(ValueError, match="Invalid consent tier"):
            await consent_manager.update_consent(customer_id, invalid_consent)

    @pytest.mark.asyncio
    async def test_update_consent_creates_new_record(self, consent_manager, mock_redis, mock_db):
        """Test creating new consent record when none exists."""
        customer_id = "new-customer"
        mock_db.query.return_value.filter.return_value.first.return_value = None

        new_consent = {
            "tier": "basic",
            "can_store_images": False
        }

        result = await consent_manager.update_consent(customer_id, new_consent)

        assert result is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestRevokeConsent:
    """Test consent revocation."""

    @pytest.mark.asyncio
    async def test_revoke_consent_success(self, consent_manager, mock_redis, mock_db):
        """Test successful consent revocation."""
        customer_id = "test-customer"
        mock_consent_record = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_consent_record

        result = await consent_manager.revoke_consent(customer_id)

        assert result is True
        assert mock_consent_record.tier == ConsentTier.NONE
        assert mock_consent_record.can_store_images is False
        assert mock_consent_record.can_store_embeddings is False
        assert mock_consent_record.can_use_for_training is False
        mock_redis.delete.assert_called_once_with(f"consent:{customer_id}")

    @pytest.mark.asyncio
    async def test_revoke_consent_no_record(self, consent_manager, mock_db):
        """Test revoking consent when no record exists."""
        customer_id = "nonexistent-customer"
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await consent_manager.revoke_consent(customer_id)

        assert result is True  # Should succeed idempotently


class TestConsentTierLogic:
    """Test consent tier hierarchies and logic."""

    @pytest.mark.asyncio
    async def test_none_tier_permissions(self, consent_manager):
        """Test that 'none' tier has no permissions."""
        with patch.object(consent_manager, 'get_consent', AsyncMock(return_value={
            "tier": "none",
            "can_store_images": False,
            "can_store_embeddings": False,
            "can_use_for_training": False
        })):
            assert await consent_manager.can_store_images("customer") is False
            assert await consent_manager.can_store_embeddings("customer") is False
            assert await consent_manager.can_use_for_training("customer") is False

    @pytest.mark.asyncio
    async def test_basic_tier_permissions(self, consent_manager):
        """Test 'basic' tier allows temporary storage only."""
        with patch.object(consent_manager, 'get_consent', AsyncMock(return_value={
            "tier": "basic",
            "can_store_images": False,
            "can_store_embeddings": True,
            "can_use_for_training": False
        })):
            assert await consent_manager.can_store_images("customer") is False
            assert await consent_manager.can_store_embeddings("customer") is True
            assert await consent_manager.can_use_for_training("customer") is False

    @pytest.mark.asyncio
    async def test_analytics_tier_permissions(self, consent_manager):
        """Test 'analytics' tier allows storage but not training."""
        with patch.object(consent_manager, 'get_consent', AsyncMock(return_value={
            "tier": "analytics",
            "can_store_images": True,
            "can_store_embeddings": True,
            "can_use_for_training": False
        })):
            assert await consent_manager.can_store_images("customer") is True
            assert await consent_manager.can_store_embeddings("customer") is True
            assert await consent_manager.can_use_for_training("customer") is False

    @pytest.mark.asyncio
    async def test_research_tier_permissions(self, consent_manager):
        """Test 'research' tier allows all operations."""
        with patch.object(consent_manager, 'get_consent', AsyncMock(return_value={
            "tier": "research",
            "can_store_images": True,
            "can_store_embeddings": True,
            "can_use_for_training": True
        })):
            assert await consent_manager.can_store_images("customer") is True
            assert await consent_manager.can_store_embeddings("customer") is True
            assert await consent_manager.can_use_for_training("customer") is True


class TestCacheInvalidation:
    """Test cache invalidation on updates."""

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_update(self, consent_manager, mock_redis, mock_db):
        """Test that cache is invalidated when consent is updated."""
        customer_id = "test-customer"
        mock_consent_record = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_consent_record

        await consent_manager.update_consent(customer_id, {
            "tier": "analytics",
            "can_store_images": True
        })

        mock_redis.delete.assert_called_once_with(f"consent:{customer_id}")

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_revoke(self, consent_manager, mock_redis, mock_db):
        """Test that cache is invalidated when consent is revoked."""
        customer_id = "test-customer"
        mock_consent_record = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_consent_record

        await consent_manager.revoke_consent(customer_id)

        mock_redis.delete.assert_called_once_with(f"consent:{customer_id}")
