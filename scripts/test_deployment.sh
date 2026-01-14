#!/bin/bash
# Post-deployment test script
# Run this after deploying to verify the production site is working correctly.
#
# Usage:
#   ./scripts/test_deployment.sh              # Test production
#   ./scripts/test_deployment.sh --local      # Test local server

set -e

# Default to production
BASE_URL="https://training.ryanwillging.com"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            BASE_URL="http://localhost:8000"
            shift
            ;;
        --url)
            BASE_URL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--local] [--url URL]"
            exit 1
            ;;
    esac
done

echo "========================================"
echo "Post-Deployment Test Suite"
echo "========================================"
echo "Target: $BASE_URL"
echo ""

# Check if playwright is installed
if ! python3 -c "import playwright" 2>/dev/null; then
    echo "Installing Playwright..."
    pip install playwright pytest-playwright
    playwright install chromium
fi

# Run the tests
echo "Running tests..."
echo ""

pytest tests/e2e/ \
    --base-url "$BASE_URL" \
    -v \
    --tb=short \
    --no-header

TEST_EXIT_CODE=$?

echo ""
echo "========================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Some tests failed. Exit code: $TEST_EXIT_CODE"
fi
echo "========================================"

exit $TEST_EXIT_CODE
