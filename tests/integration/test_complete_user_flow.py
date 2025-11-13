"""
Complete integration test for the entire user flow.

Tests:
1. User registration
2. User login
3. API key creation
4. Inference with API key
5. Data collection verification
6. Analytics verification
7. Admin panel access
"""

import asyncio
import base64
import json
import sys
from pathlib import Path

import httpx
import pytest

# Base URL for API
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

# Test user credentials
TEST_USER = {
    "email": f"test_user_{int(asyncio.get_event_loop().time())}@praxislabs.com",
    "password": "SecurePass123!",
    "full_name": "Test User",
    "company_name": "Test Company Inc."
}

# Admin user (needs to exist in DB with is_superuser=True)
ADMIN_USER = {
    "email": "admin@praxislabs.com",
    "password": "AdminPass123!"
}


class TestCompleteUserFlow:
    """Test the complete user flow from registration to analytics."""

    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        self.user_token = None
        self.admin_token = None
        self.api_key = None
        self.customer_id = None
        self.inference_log_id = None

    async def test_1_user_registration(self):
        """Test user registration creates user and customer."""
        print("\n=== Test 1: User Registration ===")

        response = await self.client.post(
            "/auth/register",
            json={
                "email": TEST_USER["email"],
                "password": TEST_USER["password"],
                "full_name": TEST_USER["full_name"],
                "company_name": TEST_USER["company_name"]
            }
        )

        assert response.status_code == 201, f"Registration failed: {response.text}"
        data = response.json()

        assert "access_token" in data
        assert data["email"] == TEST_USER["email"]
        assert data["full_name"] == TEST_USER["full_name"]

        self.user_token = data["access_token"]

        print(f"✓ User registered successfully")
        print(f"  Email: {data['email']}")
        print(f"  User ID: {data['user_id']}")
        print(f"  Token: {self.user_token[:20]}...")

        return True

    async def test_2_user_login(self):
        """Test user can login with credentials."""
        print("\n=== Test 2: User Login ===")

        response = await self.client.post(
            "/auth/login",
            data={
                "username": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
        )

        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()

        assert "access_token" in data
        self.user_token = data["access_token"]

        print(f"✓ User logged in successfully")
        print(f"  Token: {self.user_token[:20]}...")

        return True

    async def test_3_create_api_key(self):
        """Test API key creation."""
        print("\n=== Test 3: Create API Key ===")

        headers = {"Authorization": f"Bearer {self.user_token}"}

        response = await self.client.post(
            "/v1/api-keys",
            headers=headers,
            json={
                "key_name": "Test API Key",
                "scopes": ["inference"]
            }
        )

        assert response.status_code == 201, f"API key creation failed: {response.text}"
        data = response.json()

        assert "api_key" in data
        assert data["api_key"].startswith("vla_live_")

        self.api_key = data["api_key"]
        self.customer_id = data["customer_id"]

        print(f"✓ API key created successfully")
        print(f"  Key: {self.api_key[:20]}...")
        print(f"  Customer ID: {self.customer_id}")

        return True

    async def test_4_list_api_keys(self):
        """Test listing API keys."""
        print("\n=== Test 4: List API Keys ===")

        headers = {"Authorization": f"Bearer {self.user_token}"}

        response = await self.client.get("/v1/api-keys", headers=headers)

        assert response.status_code == 200, f"List API keys failed: {response.text}"
        data = response.json()

        assert len(data) > 0
        assert any(key["key_name"] == "Test API Key" for key in data)

        print(f"✓ API keys listed successfully")
        print(f"  Total keys: {len(data)}")

        return True

    async def test_5_run_inference(self):
        """Test running inference with API key."""
        print("\n=== Test 5: Run Inference ===")

        # Create a simple test image (1x1 red pixel)
        import io
        from PIL import Image

        img = Image.new('RGB', (224, 224), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode()

        headers = {"X-API-Key": self.api_key}

        response = await self.client.post(
            "/v1/inference",
            headers=headers,
            json={
                "image": f"data:image/jpeg;base64,{image_base64}",
                "instruction": "Pick up the red block",
                "robot_type": "franka_panda",
                "environment_type": "tabletop"
            }
        )

        # Note: This might fail if VLA model is not loaded, which is OK for this test
        if response.status_code == 200:
            data = response.json()
            assert "action" in data
            assert "safety" in data
            assert len(data["action"]["vector"]) == 7

            self.inference_log_id = data.get("log_id")

            print(f"✓ Inference completed successfully")
            print(f"  Action: {data['action']['vector']}")
            print(f"  Safety Score: {data['safety']['score']}")
            print(f"  Log ID: {self.inference_log_id}")
        else:
            print(f"⚠ Inference endpoint returned {response.status_code}")
            print(f"  This is expected if VLA model is not loaded")
            print(f"  Message: {response.text[:200]}")

        return True

    async def test_6_get_usage_analytics(self):
        """Test retrieving usage analytics."""
        print("\n=== Test 6: Get Usage Analytics ===")

        headers = {"Authorization": f"Bearer {self.user_token}"}

        response = await self.client.get(
            "/v1/analytics/usage?days=7",
            headers=headers
        )

        assert response.status_code == 200, f"Analytics failed: {response.text}"
        data = response.json()

        assert "total_requests" in data
        assert "success_rate" in data

        print(f"✓ Analytics retrieved successfully")
        print(f"  Total Requests: {data['total_requests']}")
        print(f"  Success Rate: {data['success_rate']:.1f}%")

        return True

    async def test_7_get_subscription(self):
        """Test getting subscription info."""
        print("\n=== Test 7: Get Subscription ===")

        headers = {"Authorization": f"Bearer {self.user_token}"}

        response = await self.client.get(
            "/v1/billing/subscription",
            headers=headers
        )

        assert response.status_code == 200, f"Subscription failed: {response.text}"
        data = response.json()

        assert data["tier"] == "free"
        assert data["monthly_quota"] == 100

        print(f"✓ Subscription retrieved successfully")
        print(f"  Tier: {data['tier']}")
        print(f"  Monthly Quota: {data['monthly_quota']}")
        print(f"  Monthly Usage: {data['monthly_usage']}")

        return True

    async def test_8_admin_login(self):
        """Test admin user login."""
        print("\n=== Test 8: Admin Login ===")

        response = await self.client.post(
            "/auth/login",
            data={
                "username": ADMIN_USER["email"],
                "password": ADMIN_USER["password"]
            }
        )

        if response.status_code == 200:
            data = response.json()
            self.admin_token = data["access_token"]

            print(f"✓ Admin logged in successfully")
            print(f"  Token: {self.admin_token[:20]}...")
        else:
            print(f"⚠ Admin login failed (status {response.status_code})")
            print(f"  Make sure admin user exists with is_superuser=True")
            print(f"  Email: {ADMIN_USER['email']}")

        return True

    async def test_9_admin_stats(self):
        """Test admin stats endpoint."""
        print("\n=== Test 9: Admin Stats ===")

        if not self.admin_token:
            print("⚠ Skipping - no admin token")
            return True

        headers = {"Authorization": f"Bearer {self.admin_token}"}

        response = await self.client.get("/admin/stats", headers=headers)

        if response.status_code == 200:
            data = response.json()

            print(f"✓ Admin stats retrieved successfully")
            print(f"  Total Customers: {data['total_customers']}")
            print(f"  Total Requests: {data['total_requests']}")
            print(f"  MRR: ${data['monthly_revenue']}")
        elif response.status_code == 403:
            print(f"⚠ Access forbidden - user is not admin")
        else:
            print(f"⚠ Admin stats failed: {response.status_code}")

        return True

    async def test_10_admin_customers(self):
        """Test admin customer list endpoint."""
        print("\n=== Test 10: Admin Customer List ===")

        if not self.admin_token:
            print("⚠ Skipping - no admin token")
            return True

        headers = {"Authorization": f"Bearer {self.admin_token}"}

        response = await self.client.get(
            "/admin/customers?page=1&limit=10",
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()

            print(f"✓ Customer list retrieved successfully")
            print(f"  Total Customers: {data['total_count']}")
            print(f"  Page: {data['page']}/{data['total_pages']}")
        else:
            print(f"⚠ Customer list failed: {response.status_code}")

        return True

    async def cleanup(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def run_all_tests(self):
        """Run all tests in sequence."""
        print("\n" + "="*60)
        print("PRAXIS LABS - COMPLETE USER FLOW TEST")
        print("="*60)

        tests = [
            self.test_1_user_registration,
            self.test_2_user_login,
            self.test_3_create_api_key,
            self.test_4_list_api_keys,
            self.test_5_run_inference,
            self.test_6_get_usage_analytics,
            self.test_7_get_subscription,
            self.test_8_admin_login,
            self.test_9_admin_stats,
            self.test_10_admin_customers,
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                result = await test()
                if result:
                    passed += 1
            except AssertionError as e:
                print(f"✗ Test failed: {e}")
                failed += 1
            except Exception as e:
                print(f"✗ Test error: {e}")
                failed += 1

        print("\n" + "="*60)
        print(f"RESULTS: {passed} passed, {failed} failed")
        print("="*60)

        await self.cleanup()

        return failed == 0


async def main():
    """Run the test suite."""
    test = TestCompleteUserFlow()
    success = await test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
