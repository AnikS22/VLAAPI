# VLA API Testing Quick Start Guide

## Prerequisites

### 1. Install Test Dependencies

```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock faker factory-boy
```

### 2. Start Test Environment

```bash
# Start test database, Redis, and MinIO
docker-compose -f docker-compose.test.yml up -d

# Wait for services to be healthy (about 10 seconds)
sleep 10

# Check services are running
docker-compose -f docker-compose.test.yml ps
```

### 3. Set Environment Variables

```bash
# Load test environment variables
export $(cat .env.test | xargs)

# Or source it
source .env.test
```

---

## Quick Test Runs

### Run All Tests (Fast)

```bash
# Run all tests with coverage
pytest tests/ --cov=src --cov-report=html -v
```

### Run Specific Test Categories

```bash
# 1. Unit tests only (models, utils, middleware)
pytest tests/models/ tests/utils/ tests/middleware/ -v

# 2. API endpoint tests
pytest tests/api/ -v

# 3. Service layer tests
pytest tests/services/ -v

# 4. Integration tests
pytest tests/integration/ -v

# 5. Comprehensive system test
pytest tests/test_all_systems.py -v
```

### Run Tests by Marker

```bash
# Integration tests only
pytest -m integration -v

# Skip slow tests
pytest -m "not slow" -v

# Benchmark tests only
pytest -m benchmark -v
```

---

## Test Execution Examples

### Example 1: Complete User Flow Test

```bash
# Test user registration → login → API key → inference
pytest tests/integration/test_complete_user_flow.py -v -s
```

**Expected Output:**
```
=== Test 1: User Registration ===
✓ User registered successfully
  Email: test_user_1699472891@praxislabs.com
  User ID: user_123
  Token: eyJhbGciOiJIUzI1NiIs...

=== Test 2: User Login ===
✓ User logged in successfully
  Token: eyJhbGciOiJIUzI1NiIs...

=== Test 3: Create API Key ===
✓ API key created successfully
  Key: vla_live_abcd1234...
  Customer ID: cust_456

... [more tests]

RESULTS: 10 passed, 0 failed
```

### Example 2: Feedback API Tests

```bash
# Test all feedback endpoints
pytest tests/api/test_feedback_endpoints.py -v
```

**Expected Output:**
```
tests/api/test_feedback_endpoints.py::TestSuccessFeedback::test_success_feedback_valid PASSED
tests/api/test_feedback_endpoints.py::TestSuccessFeedback::test_success_feedback_rating_validation PASSED
tests/api/test_feedback_endpoints.py::TestSafetyRating::test_safety_rating_valid PASSED
tests/api/test_feedback_endpoints.py::TestActionCorrection::test_action_correction_valid PASSED
...

====== 35 passed in 4.23s ======
```

### Example 3: Monitoring Endpoints

```bash
# Test Prometheus metrics and health checks
pytest tests/api/test_monitoring_endpoints.py -v
```

### Example 4: Data Validation

```bash
# Test all 37+ Pydantic validators
pytest tests/test_all_systems.py::TestValidationContracts -v
```

---

## Coverage Reports

### Generate HTML Coverage Report

```bash
pytest tests/ --cov=src --cov-report=html

# Open in browser
open htmlcov/index.html
```

### Generate Terminal Coverage Report

```bash
pytest tests/ --cov=src --cov-report=term-missing
```

**Expected Output:**
```
Name                                   Stmts   Miss  Cover   Missing
--------------------------------------------------------------------
src/api/routers/auth.py                  156     12    92%   45-47, 89-91
src/api/routers/billing.py               234     34    85%   67-70, 123-145
src/api/routers/inference.py             189     8     96%   234-238
src/services/vla_inference.py            267     23    91%   145-150, 289-295
src/models/database.py                   123     3     98%   78, 156, 201
--------------------------------------------------------------------
TOTAL                                   3456    234    93%
```

### Set Minimum Coverage Threshold

```bash
# Fail if coverage < 80%
pytest tests/ --cov=src --cov-fail-under=80
```

---

## Test Configuration

### pytest.ini Configuration

Create `pytest.ini` in project root:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
markers =
    integration: Integration tests (slow)
    unit: Unit tests (fast)
    benchmark: Performance benchmarks
    slow: Slow tests (skip with -m "not slow")
asyncio_mode = auto
```

### conftest.py Fixtures

Create `tests/conftest.py` with shared fixtures:

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import app
from src.core.database import get_db_session


@pytest.fixture
async def async_client():
    """Async HTTP client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def db_session():
    """Database session for testing."""
    async for session in get_db_session():
        yield session


@pytest.fixture
def test_user():
    """Test user data."""
    return {
        "email": "test@example.com",
        "password": "SecurePass123!",
        "full_name": "Test User",
        "company_name": "Test Company"
    }
```

---

## Debugging Failed Tests

### Run Single Test with Detailed Output

```bash
# Run one test with full traceback
pytest tests/api/test_auth_endpoints.py::TestUserRegistration::test_register_valid_user -vv -s
```

### Run Tests with PDB on Failure

```bash
# Drop into debugger on first failure
pytest tests/ --pdb -x
```

### Increase Logging Verbosity

```bash
# See all logs including DEBUG level
pytest tests/ -v -s --log-cli-level=DEBUG
```

### Run Tests in Parallel (Faster)

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run with 4 workers
pytest tests/ -n 4
```

---

## Mock VLA Inference

Since we don't have GPU/VLA models, use mock inference:

```python
# tests/mocks/mock_vla_inference.py

class MockVLAInferenceService:
    """Mock VLA inference for testing without GPU."""

    async def infer(self, image, instruction, robot_type):
        return {
            "action": {
                "vector": [0.1, 0.0, 0.2, 0.0, 0.15, 0.0, 1.0],
                "dimensions": 7,
                "robot_type": robot_type
            },
            "safety": {
                "score": 0.95,
                "checks_passed": ["bounds", "collision", "workspace"],
                "warnings": []
            },
            "latency_ms": 45.2
        }
```

### Use Mock in Tests

```python
import pytest
from tests.mocks.mock_vla_inference import MockVLAInferenceService

@pytest.fixture
def mock_vla_service(monkeypatch):
    """Replace real VLA service with mock."""
    mock = MockVLAInferenceService()
    monkeypatch.setattr("src.services.vla_inference.vla_service", mock)
    return mock
```

---

## Common Test Patterns

### Test API Endpoint

```python
import pytest

@pytest.mark.asyncio
async def test_create_user(async_client):
    """Test user registration endpoint."""
    response = await async_client.post(
        "/auth/register",
        json={
            "email": "new@example.com",
            "password": "SecurePass123!",
            "full_name": "New User"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert "access_token" in data
```

### Test Database Operations

```python
import pytest
from src.models.database import Customer

@pytest.mark.asyncio
async def test_create_customer(db_session):
    """Test customer creation."""
    customer = Customer(
        email="test@example.com",
        company_name="Test Co",
        tier="standard"
    )

    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)

    assert customer.customer_id is not None
    assert customer.email == "test@example.com"
```

### Test Validation

```python
import pytest
from pydantic import ValidationError
from src.models.contracts.inference_log import InferenceLogContract

def test_action_vector_must_be_7dof():
    """Test action vector validation."""
    with pytest.raises(ValidationError):
        InferenceLogContract(
            request_id="req-123",
            customer_id="cust-123",
            timestamp=datetime.utcnow(),
            model_name="openvla-7b",
            instruction="pick up cube",
            robot_type="franka_panda",
            action_vector=[0.1, 0.0, 0.2],  # Only 3 DoF - SHOULD FAIL
            status="success"
        )
```

---

## Troubleshooting

### Problem: Database Connection Errors

```bash
# Check if test database is running
docker-compose -f docker-compose.test.yml ps test-db

# Restart if needed
docker-compose -f docker-compose.test.yml restart test-db

# Check logs
docker-compose -f docker-compose.test.yml logs test-db
```

### Problem: Redis Connection Errors

```bash
# Check Redis
docker-compose -f docker-compose.test.yml ps test-redis

# Test connection
redis-cli -p 6380 ping
# Should return: PONG
```

### Problem: Import Errors

```bash
# Install missing dependencies
pip install -r requirements.txt

# Ensure src/ is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Problem: Async Tests Not Working

```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Ensure asyncio_mode is set in pytest.ini
echo "asyncio_mode = auto" >> pytest.ini
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/tests.yml

name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: vla_test
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        ports:
          - 5433:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6380:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost:5433/vla_test
          REDIS_URL: redis://localhost:6380/0
          MOCK_VLA_INFERENCE: true
        run: |
          pytest tests/ --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Test Metrics & Goals

### Current Status
- **Total Test Files:** 23
- **Test Classes:** ~44
- **Estimated Tests:** ~200+
- **Coverage Target:** >85%

### Success Criteria
- ✅ All critical paths tested
- ✅ >85% code coverage
- ✅ <20 minute full test suite
- ✅ Zero flaky tests
- ✅ All P0 scenarios covered

---

## Next Steps

1. **Run baseline tests:**
   ```bash
   pytest tests/ --cov=src --cov-report=html -v
   ```

2. **Review coverage report:**
   ```bash
   open htmlcov/index.html
   ```

3. **Implement missing tests** (see TEST_ANALYSIS_AND_PLAN.md)

4. **Set up CI/CD** for automated testing

5. **Achieve >85% coverage** on critical paths

---

## Resources

- **Test Plan:** `docs/TEST_ANALYSIS_AND_PLAN.md`
- **Test Scripts:** `scripts/run_tests.sh`
- **Docker Compose:** `docker-compose.test.yml`
- **Test Environment:** `.env.test`
- **Coverage Report:** `htmlcov/index.html` (after running tests)

---

**Ready to test!** 🚀

Start with:
```bash
docker-compose -f docker-compose.test.yml up -d
pytest tests/test_all_systems.py -v
```
