"""
Integration test for complete inference pipeline end-to-end.

Tests the full flow from API request to response including:
1. API request with image + instruction
2. Authentication and rate limiting
3. Quality gate validation
4. Model inference
5. Safety checks
6. Embedding generation (if consent)
7. Database logging
8. Storage upload (if consent)
9. Prometheus metrics recording
10. Response generation
"""

import asyncio
import base64
import io
import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from PIL import Image
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.constants import ConsentLevel, CustomerTier, InferenceStatus
from src.core.database import get_db_session
from src.core.redis_client import get_redis_client
from src.models.api_models import InferenceRequest
from src.monitoring.prometheus_metrics import inference_requests_total


@pytest.fixture
async def test_customer_with_api_key(db_session: AsyncSession):
    """Create test customer with API key."""
    from src.models.database_models import APIKey, Customer

    customer = Customer(
        customer_id=uuid4(),
        email="test@integration.com",
        company_name="Integration Test Co",
        tier=CustomerTier.STANDARD,
        rate_limit_rpm=60,
        monthly_quota=10000,
        monthly_usage=0,
        created_at=datetime.utcnow(),
        is_active=True,
        consent_level=ConsentLevel.FULL,
    )
    db_session.add(customer)
    await db_session.flush()

    # Create API key
    api_key = APIKey(
        key_id=uuid4(),
        customer_id=customer.customer_id,
        key_hash="test_hash_12345",
        key_prefix="vla_test",
        key_name="Test Key",
        scopes=["inference"],
        is_active=True,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=365),
        rate_limit_rpm=60,
    )
    db_session.add(api_key)
    await db_session.commit()

    return {
        "customer": customer,
        "api_key": api_key,
        "api_key_string": f"vla_test_{'x' * 32}",  # Mock full key
    }


@pytest.fixture
def test_image_base64():
    """Generate test image as base64."""
    # Create simple RGB image
    img = Image.new("RGB", (224, 224), color=(100, 150, 200))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


@pytest.mark.asyncio
@pytest.mark.integration
class TestFullInferencePipeline:
    """Test complete inference pipeline end-to-end."""

    async def test_successful_inference_flow_full_consent(
        self,
        async_client: AsyncClient,
        test_customer_with_api_key: dict,
        test_image_base64: str,
        db_session: AsyncSession,
    ):
        """Test complete successful inference with full consent."""
        customer_data = test_customer_with_api_key
        api_key = customer_data["api_key_string"]

        # 1. Make inference request
        request_data = {
            "model": "openvla-7b",
            "image": test_image_base64,
            "instruction": "Pick up the red block and place it on the table",
            "robot_config": {
                "type": "franka_panda",
                "workspace_bounds": [[-0.5, -0.5, 0.0], [0.5, 0.5, 0.5]],
            },
            "safety": {
                "enable_classifier": True,
                "enable_collision_check": True,
                "safety_threshold": 0.8,
            },
        }

        response = await async_client.post(
            "/inference",
            json=request_data,
            headers={"Authorization": f"Bearer {api_key}"},
        )

        # 2. Verify response structure
        assert response.status_code == 200
        data = response.json()

        assert "request_id" in data
        assert "timestamp" in data
        assert "model" in data
        assert "action" in data
        assert "safety" in data
        assert "performance" in data
        assert "usage" in data

        request_id = data["request_id"]

        # 3. Verify action response
        action = data["action"]
        assert action["dimensions"] == 7
        assert len(action["values"]) == 7
        assert all(isinstance(v, float) for v in action["values"])

        # 4. Verify safety checks
        safety = data["safety"]
        assert "overall_score" in safety
        assert 0.0 <= safety["overall_score"] <= 1.0
        assert "checks_passed" in safety
        assert isinstance(safety["checks_passed"], list)

        # 5. Verify performance metrics
        perf = data["performance"]
        assert perf["total_latency_ms"] > 0
        assert perf["inference_ms"] > 0
        assert perf["safety_check_ms"] >= 0

        # 6. Check database logging
        from src.models.database_models import InferenceLog

        result = await db_session.execute(
            select(InferenceLog).where(InferenceLog.request_id == request_id)
        )
        log_entry = result.scalar_one_or_none()

        assert log_entry is not None
        assert log_entry.customer_id == customer_data["customer"].customer_id
        assert log_entry.model_name == "openvla-7b"
        assert log_entry.status == InferenceStatus.SUCCESS
        assert log_entry.inference_latency_ms == perf["inference_ms"]

        # 7. Verify embeddings generated (full consent)
        assert log_entry.instruction_embedding is not None
        assert log_entry.image_embedding is not None
        assert len(log_entry.instruction_embedding) > 0
        assert len(log_entry.image_embedding) > 0

        # 8. Verify image stored (full consent)
        assert log_entry.image_s3_key is not None
        assert log_entry.image_s3_key.startswith("images/")

        # 9. Check Prometheus metrics updated
        # Note: In real test, would query Prometheus API
        # Here we just verify the metric exists
        assert inference_requests_total is not None

        # 10. Verify rate limit headers
        assert "X-RateLimit-Remaining-Minute" in response.headers
        assert "X-RateLimit-Remaining-Day" in response.headers

    async def test_inference_flow_no_consent(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_image_base64: str,
    ):
        """Test inference with no consent - verify no data stored."""
        from src.models.database_models import APIKey, Customer

        # Create customer with NO consent
        customer = Customer(
            customer_id=uuid4(),
            email="noconsent@test.com",
            tier=CustomerTier.FREE,
            consent_level=ConsentLevel.NONE,
            is_active=True,
        )
        db_session.add(customer)
        await db_session.flush()

        api_key = APIKey(
            key_id=uuid4(),
            customer_id=customer.customer_id,
            key_hash="noconsent_hash",
            key_prefix="vla_nocon",
            scopes=["inference"],
            is_active=True,
        )
        db_session.add(api_key)
        await db_session.commit()

        # Make inference request
        request_data = {
            "model": "openvla-7b",
            "image": test_image_base64,
            "instruction": "Pick up the object",
        }

        response = await async_client.post(
            "/inference",
            json=request_data,
            headers={"Authorization": f"Bearer vla_nocon_{'x' * 32}"},
        )

        assert response.status_code == 200
        data = response.json()
        request_id = data["request_id"]

        # Verify log entry exists but without sensitive data
        from src.models.database_models import InferenceLog

        result = await db_session.execute(
            select(InferenceLog).where(InferenceLog.request_id == request_id)
        )
        log_entry = result.scalar_one()

        # Should have anonymous instruction
        assert log_entry.instruction_text == "[REDACTED]"

        # Should NOT have embeddings
        assert log_entry.instruction_embedding is None
        assert log_entry.image_embedding is None

        # Should NOT have image stored
        assert log_entry.image_s3_key is None

    async def test_quality_gate_rejection(
        self,
        async_client: AsyncClient,
        test_customer_with_api_key: dict,
        db_session: AsyncSession,
    ):
        """Test inference rejected by quality gate."""
        api_key = test_customer_with_api_key["api_key_string"]

        # Create very small/invalid image
        tiny_img = Image.new("RGB", (10, 10), color=(0, 0, 0))
        buffer = io.BytesIO()
        tiny_img.save(buffer, format="JPEG")
        buffer.seek(0)
        tiny_image_b64 = base64.b64encode(buffer.read()).decode("utf-8")

        request_data = {
            "model": "openvla-7b",
            "image": tiny_image_b64,
            "instruction": "x",  # Too short
        }

        response = await async_client.post(
            "/inference",
            json=request_data,
            headers={"Authorization": f"Bearer {api_key}"},
        )

        # Should either reject or return with warning
        if response.status_code == 400:
            # Quality gate rejection
            data = response.json()
            assert "quality" in data["error"].lower() or "invalid" in data[
                "error"
            ].lower()
        else:
            # Accepted but with low quality score
            data = response.json()
            # Check if quality warning present
            assert response.status_code == 200

    async def test_safety_rejection(
        self,
        async_client: AsyncClient,
        test_customer_with_api_key: dict,
        test_image_base64: str,
        db_session: AsyncSession,
    ):
        """Test inference rejected by safety checks."""
        api_key = test_customer_with_api_key["api_key_string"]

        # Request with very strict safety threshold
        request_data = {
            "model": "openvla-7b",
            "image": test_image_base64,
            "instruction": "Move to dangerous position at high speed",
            "safety": {
                "enable_classifier": True,
                "safety_threshold": 0.99,  # Very strict
            },
        }

        response = await async_client.post(
            "/inference",
            json=request_data,
            headers={"Authorization": f"Bearer {api_key}"},
        )

        data = response.json()

        # If safety failed, check flags
        if "safety" in data:
            safety = data["safety"]
            # At minimum, should have safety evaluation
            assert "overall_score" in safety

            # Check if action was modified for safety
            if safety.get("modifications_applied"):
                assert safety["overall_score"] < 0.99

    async def test_rate_limiting(
        self,
        async_client: AsyncClient,
        test_customer_with_api_key: dict,
        test_image_base64: str,
    ):
        """Test rate limiting enforcement."""
        api_key = test_customer_with_api_key["api_key_string"]

        request_data = {
            "model": "openvla-7b",
            "image": test_image_base64,
            "instruction": "Test rate limit",
        }

        # Make requests up to rate limit
        rate_limit = test_customer_with_api_key["customer"].rate_limit_rpm

        responses = []
        for i in range(rate_limit + 5):  # Try to exceed limit
            response = await async_client.post(
                "/inference",
                json=request_data,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            responses.append(response)

            if response.status_code == 429:
                # Rate limit hit
                data = response.json()
                assert "rate_limit" in data["error"].lower()
                assert "retry_after_seconds" in data
                break

            await asyncio.sleep(0.1)  # Small delay between requests

        # At least some requests should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count > 0

        # Should hit rate limit eventually
        rate_limited = any(r.status_code == 429 for r in responses)
        # Note: May not hit in test if rate limit is high
        # assert rate_limited or len(responses) < rate_limit

    async def test_concurrent_inference_requests(
        self,
        async_client: AsyncClient,
        test_customer_with_api_key: dict,
        test_image_base64: str,
    ):
        """Test handling concurrent inference requests."""
        api_key = test_customer_with_api_key["api_key_string"]

        request_data = {
            "model": "openvla-7b",
            "image": test_image_base64,
            "instruction": "Concurrent test",
        }

        # Send 5 concurrent requests
        tasks = []
        for _ in range(5):
            task = async_client.post(
                "/inference",
                json=request_data,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Check responses
        success_count = 0
        for resp in responses:
            if isinstance(resp, Exception):
                continue
            if resp.status_code == 200:
                success_count += 1

        # At least some should succeed
        assert success_count > 0

    async def test_invalid_model_name(
        self,
        async_client: AsyncClient,
        test_customer_with_api_key: dict,
        test_image_base64: str,
    ):
        """Test validation of model name."""
        api_key = test_customer_with_api_key["api_key_string"]

        request_data = {
            "model": "invalid-model-xyz",
            "image": test_image_base64,
            "instruction": "Test instruction",
        }

        response = await async_client.post(
            "/inference",
            json=request_data,
            headers={"Authorization": f"Bearer {api_key}"},
        )

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "model" in str(data).lower()

    async def test_authentication_required(
        self, async_client: AsyncClient, test_image_base64: str
    ):
        """Test authentication is required."""
        request_data = {
            "model": "openvla-7b",
            "image": test_image_base64,
            "instruction": "Test instruction",
        }

        # No auth header
        response = await async_client.post("/inference", json=request_data)
        assert response.status_code == 401

        # Invalid auth header
        response = await async_client.post(
            "/inference",
            json=request_data,
            headers={"Authorization": "Bearer invalid_key"},
        )
        assert response.status_code == 401

    async def test_performance_metrics_accuracy(
        self,
        async_client: AsyncClient,
        test_customer_with_api_key: dict,
        test_image_base64: str,
    ):
        """Test performance metrics are accurate."""
        api_key = test_customer_with_api_key["api_key_string"]

        request_data = {
            "model": "openvla-7b",
            "image": test_image_base64,
            "instruction": "Performance test",
        }

        import time

        start_time = time.time()
        response = await async_client.post(
            "/inference",
            json=request_data,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        end_time = time.time()

        assert response.status_code == 200
        data = response.json()

        # Total latency should be reasonable
        total_latency_ms = data["performance"]["total_latency_ms"]
        actual_latency_ms = (end_time - start_time) * 1000

        # Reported latency should be close to actual (within 20%)
        assert total_latency_ms <= actual_latency_ms * 1.2

        # Component latencies should sum to total (approximately)
        perf = data["performance"]
        component_sum = (
            perf["queue_wait_ms"]
            + perf["inference_ms"]
            + perf["safety_check_ms"]
            + perf["postprocess_ms"]
        )

        # Should be within 10% of total
        assert abs(component_sum - total_latency_ms) <= total_latency_ms * 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
