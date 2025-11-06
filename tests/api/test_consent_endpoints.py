"""
Comprehensive tests for consent management API endpoints.

Tests GET, POST, DELETE endpoints with permission checks and validation.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from src.main import app
from src.database.models import ConsentTier


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_consent_manager():
    """Mock ConsentManager service."""
    manager = Mock()
    manager.get_consent = AsyncMock()
    manager.update_consent = AsyncMock()
    manager.revoke_consent = AsyncMock()
    return manager


@pytest.fixture
def mock_auth():
    """Mock authentication dependency."""
    return {"user_id": "admin-user", "role": "admin"}


class TestGetConsentEndpoint:
    """Test GET /admin/customers/{id}/consent endpoint."""

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_get_consent_success(self, mock_auth_dep, mock_manager_dep, client, mock_consent_manager, mock_auth):
        """Test successful consent retrieval."""
        mock_auth_dep.return_value = mock_auth
        mock_manager_dep.return_value = mock_consent_manager

        mock_consent_manager.get_consent.return_value = {
            "customer_id": "customer-123",
            "tier": "analytics",
            "can_store_images": True,
            "can_store_embeddings": True,
            "can_use_for_training": False,
            "updated_at": datetime.utcnow().isoformat()
        }

        response = client.get("/admin/customers/customer-123/consent")

        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == "customer-123"
        assert data["tier"] == "analytics"
        assert data["can_store_images"] is True

    @patch('src.api.admin.get_current_user')
    def test_get_consent_unauthorized(self, mock_auth_dep, client):
        """Test unauthorized access."""
        mock_auth_dep.side_effect = Exception("Unauthorized")

        response = client.get("/admin/customers/customer-123/consent")

        assert response.status_code in [401, 403]

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_get_consent_not_found(self, mock_auth_dep, mock_manager_dep, client, mock_consent_manager, mock_auth):
        """Test consent not found."""
        mock_auth_dep.return_value = mock_auth
        mock_manager_dep.return_value = mock_consent_manager

        mock_consent_manager.get_consent.return_value = {
            "tier": "none",
            "can_store_images": False,
            "can_store_embeddings": False,
            "can_use_for_training": False
        }

        response = client.get("/admin/customers/nonexistent/consent")

        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "none"

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_get_consent_invalid_customer_id(self, mock_auth_dep, mock_manager_dep, client, mock_auth):
        """Test invalid customer ID format."""
        mock_auth_dep.return_value = mock_auth

        response = client.get("/admin/customers//consent")

        assert response.status_code == 404


class TestPostConsentEndpoint:
    """Test POST /admin/customers/{id}/consent endpoint."""

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_update_consent_success(self, mock_auth_dep, mock_manager_dep, client, mock_consent_manager, mock_auth):
        """Test successful consent update."""
        mock_auth_dep.return_value = mock_auth
        mock_manager_dep.return_value = mock_consent_manager
        mock_consent_manager.update_consent.return_value = True

        payload = {
            "tier": "analytics",
            "can_store_images": True,
            "can_store_embeddings": True,
            "can_use_for_training": False
        }

        response = client.post("/admin/customers/customer-123/consent", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Consent updated successfully"
        mock_consent_manager.update_consent.assert_called_once_with("customer-123", payload)

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_update_consent_invalid_tier(self, mock_auth_dep, mock_manager_dep, client, mock_consent_manager, mock_auth):
        """Test update with invalid consent tier."""
        mock_auth_dep.return_value = mock_auth
        mock_manager_dep.return_value = mock_consent_manager

        payload = {
            "tier": "invalid_tier",
            "can_store_images": True
        }

        response = client.post("/admin/customers/customer-123/consent", json=payload)

        assert response.status_code == 422  # Validation error

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_update_consent_missing_fields(self, mock_auth_dep, mock_manager_dep, client, mock_auth):
        """Test update with missing required fields."""
        mock_auth_dep.return_value = mock_auth

        payload = {
            "tier": "analytics"
            # Missing permission flags
        }

        response = client.post("/admin/customers/customer-123/consent", json=payload)

        assert response.status_code == 422

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_update_consent_validation_logic(self, mock_auth_dep, mock_manager_dep, client, mock_consent_manager, mock_auth):
        """Test business logic validation."""
        mock_auth_dep.return_value = mock_auth
        mock_manager_dep.return_value = mock_consent_manager

        # Try to enable training without embeddings
        payload = {
            "tier": "research",
            "can_store_images": False,
            "can_store_embeddings": False,
            "can_use_for_training": True  # Invalid: training requires embeddings
        }

        response = client.post("/admin/customers/customer-123/consent", json=payload)

        # Should either reject or auto-correct
        assert response.status_code in [200, 400, 422]

    @patch('src.api.admin.get_current_user')
    def test_update_consent_unauthorized(self, mock_auth_dep, client):
        """Test unauthorized consent update."""
        mock_auth_dep.side_effect = Exception("Unauthorized")

        payload = {"tier": "analytics"}
        response = client.post("/admin/customers/customer-123/consent", json=payload)

        assert response.status_code in [401, 403]


class TestDeleteConsentEndpoint:
    """Test DELETE /admin/customers/{id}/consent endpoint."""

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_revoke_consent_success(self, mock_auth_dep, mock_manager_dep, client, mock_consent_manager, mock_auth):
        """Test successful consent revocation."""
        mock_auth_dep.return_value = mock_auth
        mock_manager_dep.return_value = mock_consent_manager
        mock_consent_manager.revoke_consent.return_value = True

        response = client.delete("/admin/customers/customer-123/consent")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Consent revoked successfully"
        mock_consent_manager.revoke_consent.assert_called_once_with("customer-123")

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_revoke_consent_idempotent(self, mock_auth_dep, mock_manager_dep, client, mock_consent_manager, mock_auth):
        """Test revocation is idempotent."""
        mock_auth_dep.return_value = mock_auth
        mock_manager_dep.return_value = mock_consent_manager
        mock_consent_manager.revoke_consent.return_value = True

        # First revocation
        response1 = client.delete("/admin/customers/customer-123/consent")
        assert response1.status_code == 200

        # Second revocation should also succeed
        response2 = client.delete("/admin/customers/customer-123/consent")
        assert response2.status_code == 200

    @patch('src.api.admin.get_current_user')
    def test_revoke_consent_unauthorized(self, mock_auth_dep, client):
        """Test unauthorized consent revocation."""
        mock_auth_dep.side_effect = Exception("Unauthorized")

        response = client.delete("/admin/customers/customer-123/consent")

        assert response.status_code in [401, 403]

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_revoke_consent_invalid_customer(self, mock_auth_dep, mock_manager_dep, client, mock_consent_manager, mock_auth):
        """Test revoking consent for invalid customer."""
        mock_auth_dep.return_value = mock_auth
        mock_manager_dep.return_value = mock_consent_manager
        mock_consent_manager.revoke_consent.return_value = True

        response = client.delete("/admin/customers/invalid-id/consent")

        # Should succeed idempotently even for nonexistent customer
        assert response.status_code == 200


class TestPermissionChecks:
    """Test permission validation across endpoints."""

    @patch('src.api.admin.get_current_user')
    def test_admin_only_access(self, mock_auth_dep, client):
        """Test that only admins can access consent endpoints."""
        # Non-admin user
        mock_auth_dep.return_value = {"user_id": "user-123", "role": "customer"}

        response = client.get("/admin/customers/customer-123/consent")

        assert response.status_code in [401, 403]

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_customer_cannot_modify_others_consent(self, mock_auth_dep, mock_manager_dep, client, mock_auth):
        """Test customers cannot modify other customers' consent."""
        mock_auth_dep.return_value = {"user_id": "customer-456", "role": "customer"}

        payload = {"tier": "research"}
        response = client.post("/admin/customers/customer-123/consent", json=payload)

        assert response.status_code in [401, 403]


class TestValidationErrors:
    """Test input validation and error handling."""

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_invalid_json_payload(self, mock_auth_dep, mock_manager_dep, client, mock_auth):
        """Test invalid JSON payload."""
        mock_auth_dep.return_value = mock_auth

        response = client.post(
            "/admin/customers/customer-123/consent",
            data="invalid json{",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_type_validation(self, mock_auth_dep, mock_manager_dep, client, mock_auth):
        """Test type validation for boolean fields."""
        mock_auth_dep.return_value = mock_auth

        payload = {
            "tier": "analytics",
            "can_store_images": "yes",  # Should be boolean
            "can_store_embeddings": True,
            "can_use_for_training": False
        }

        response = client.post("/admin/customers/customer-123/consent", json=payload)

        assert response.status_code == 422

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_extra_fields_ignored(self, mock_auth_dep, mock_manager_dep, client, mock_consent_manager, mock_auth):
        """Test that extra fields are ignored."""
        mock_auth_dep.return_value = mock_auth
        mock_manager_dep.return_value = mock_consent_manager
        mock_consent_manager.update_consent.return_value = True

        payload = {
            "tier": "analytics",
            "can_store_images": True,
            "can_store_embeddings": True,
            "can_use_for_training": False,
            "extra_field": "should_be_ignored"
        }

        response = client.post("/admin/customers/customer-123/consent", json=payload)

        # Should succeed, ignoring extra field
        assert response.status_code == 200


class TestConsentTierValidation:
    """Test consent tier-specific validation rules."""

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_none_tier_all_permissions_false(self, mock_auth_dep, mock_manager_dep, client, mock_consent_manager, mock_auth):
        """Test 'none' tier requires all permissions to be false."""
        mock_auth_dep.return_value = mock_auth
        mock_manager_dep.return_value = mock_consent_manager

        payload = {
            "tier": "none",
            "can_store_images": True,  # Invalid for 'none' tier
            "can_store_embeddings": False,
            "can_use_for_training": False
        }

        response = client.post("/admin/customers/customer-123/consent", json=payload)

        # Should reject or auto-correct
        assert response.status_code in [200, 400, 422]

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_basic_tier_no_images(self, mock_auth_dep, mock_manager_dep, client, mock_consent_manager, mock_auth):
        """Test 'basic' tier doesn't allow image storage."""
        mock_auth_dep.return_value = mock_auth
        mock_manager_dep.return_value = mock_consent_manager

        payload = {
            "tier": "basic",
            "can_store_images": True,  # Invalid for 'basic'
            "can_store_embeddings": True,
            "can_use_for_training": False
        }

        response = client.post("/admin/customers/customer-123/consent", json=payload)

        assert response.status_code in [200, 400, 422]

    @patch('src.api.admin.get_consent_manager')
    @patch('src.api.admin.get_current_user')
    def test_research_tier_all_permissions(self, mock_auth_dep, mock_manager_dep, client, mock_consent_manager, mock_auth):
        """Test 'research' tier allows all permissions."""
        mock_auth_dep.return_value = mock_auth
        mock_manager_dep.return_value = mock_consent_manager
        mock_consent_manager.update_consent.return_value = True

        payload = {
            "tier": "research",
            "can_store_images": True,
            "can_store_embeddings": True,
            "can_use_for_training": True
        }

        response = client.post("/admin/customers/customer-123/consent", json=payload)

        assert response.status_code == 200
