#!/bin/bash

# VLA API Test Execution Script
# Run comprehensive tests with coverage reporting

set -e  # Exit on error

echo "=================================================="
echo "VLA API Platform - Test Execution"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: Must run from project root directory${NC}"
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Install/upgrade test dependencies
echo ""
echo "Installing test dependencies..."
pip install -q pytest pytest-asyncio pytest-cov pytest-mock faker factory-boy httpx pillow

# Set test environment variables
export ENVIRONMENT=test
export DEBUG=true
export LOG_LEVEL=WARNING  # Reduce log noise during tests
export MOCK_VLA_INFERENCE=true
export ENABLE_GPU_MONITORING=false
export ENABLE_EMBEDDINGS=false

# Database and Redis should be running (Docker Compose)
export DATABASE_URL=${DATABASE_URL:-"postgresql+asyncpg://test_user:test_pass@localhost:5433/vla_test"}
export REDIS_URL=${REDIS_URL:-"redis://localhost:6380/0"}

echo ""
echo "Test Environment:"
echo "  - ENVIRONMENT: $ENVIRONMENT"
echo "  - MOCK_VLA_INFERENCE: $MOCK_VLA_INFERENCE"
echo "  - DATABASE_URL: $DATABASE_URL"
echo "  - REDIS_URL: $REDIS_URL"
echo ""

# Test execution options
TEST_PATH="${1:-tests/}"
COVERAGE_MIN="${2:-70}"
MARKERS="${3:-}"

echo "Test Configuration:"
echo "  - Test path: $TEST_PATH"
echo "  - Coverage minimum: ${COVERAGE_MIN}%"
echo "  - Markers: ${MARKERS:-all}"
echo ""

# Create coverage directory
mkdir -p htmlcov

# Run tests with coverage
echo "=================================================="
echo "Running Tests..."
echo "=================================================="
echo ""

if [ -n "$MARKERS" ]; then
    pytest "$TEST_PATH" \
        -m "$MARKERS" \
        --cov=src \
        --cov-report=html \
        --cov-report=term-missing \
        --cov-report=xml \
        --cov-fail-under="$COVERAGE_MIN" \
        -v \
        --tb=short \
        --maxfail=5 \
        -x  # Stop on first failure for quick feedback
else
    pytest "$TEST_PATH" \
        --cov=src \
        --cov-report=html \
        --cov-report=term-missing \
        --cov-report=xml \
        --cov-fail-under="$COVERAGE_MIN" \
        -v \
        --tb=short \
        --maxfail=5
fi

test_exit_code=$?

echo ""
echo "=================================================="
echo "Test Execution Complete"
echo "=================================================="
echo ""

if [ $test_exit_code -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Coverage report generated:"
    echo "  - HTML: htmlcov/index.html"
    echo "  - XML: coverage.xml"
    echo ""
    echo "View HTML report:"
    echo "  open htmlcov/index.html"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Review failures above or check detailed report:"
    echo "  open htmlcov/index.html"
fi

exit $test_exit_code
