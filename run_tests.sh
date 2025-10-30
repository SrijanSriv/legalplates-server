#!/bin/bash
# Test runner script for LegalPlates API

set -e  # Exit on error

echo "========================================"
echo "LegalPlates API Test Suite"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not detected. Activating...${NC}"
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo -e "${RED}❌ Virtual environment not found. Please create one first:${NC}"
        echo "   python3 -m venv venv"
        echo "   source venv/bin/activate"
        echo "   pip install -r requirements.txt"
        exit 1
    fi
fi

# Check if pytest is installed
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${RED}❌ pytest not installed. Installing test dependencies...${NC}"
    pip install pytest pytest-asyncio httpx
fi

# Parse command line arguments
TEST_TYPE="all"
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --api)
            TEST_TYPE="api"
            shift
            ;;
        --performance)
            TEST_TYPE="performance"
            shift
            ;;
        --all)
            TEST_TYPE="all"
            shift
            ;;
        -v|--verbose)
            VERBOSE="-vv"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--api|--performance|--all] [-v|--verbose]"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}🚀 Starting tests...${NC}"
echo ""

# Run tests based on type
case $TEST_TYPE in
    api)
        echo "Running API tests only..."
        pytest tests/test_api.py $VERBOSE
        ;;
    performance)
        echo "Running performance tests only..."
        pytest tests/test_performance.py $VERBOSE
        ;;
    all)
        echo "Running all tests..."
        pytest tests/ $VERBOSE
        ;;
esac

# Capture exit code
TEST_EXIT_CODE=$?

echo ""
echo "========================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed. Exit code: $TEST_EXIT_CODE${NC}"
fi
echo "========================================"

exit $TEST_EXIT_CODE

