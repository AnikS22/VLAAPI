#!/bin/bash

# Complete flow test script for Praxis Labs

set -e

echo "=================================="
echo "Praxis Labs - Complete Flow Test"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend is running
echo "Checking if backend is running..."
if curl -s http://localhost:8000/ > /dev/null; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend is not running!${NC}"
    echo "Please start the backend with: python -m uvicorn src.api.main:app --reload"
    exit 1
fi

# Check if frontend is running (optional)
echo "Checking if frontend is running..."
if curl -s http://localhost:3000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is running${NC}"
else
    echo -e "${YELLOW}⚠ Frontend is not running (optional)${NC}"
    echo "To start frontend: cd frontend && npm run dev"
fi

echo ""
echo "Running integration tests..."
echo ""

# Install test dependencies if needed
pip install -q httpx pillow pytest pytest-asyncio

# Run the integration test
python tests/integration/test_complete_user_flow.py

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=================================="
    echo "All tests passed successfully!"
    echo -e "==================================${NC}"
else
    echo ""
    echo -e "${RED}=================================="
    echo "Some tests failed"
    echo -e "==================================${NC}"
fi

exit $exit_code
