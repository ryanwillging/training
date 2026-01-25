#!/bin/bash

# Phase A Frontend Integration Test Runner
# Created: 2026-01-25

set -e

cd "$(dirname "$0")"

echo "========================================"
echo "Phase A Frontend Integration Tests"
echo "========================================"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if playwright is installed
if ! python -c "import playwright" 2>/dev/null; then
    echo "❌ Playwright not installed. Run: pip install pytest-playwright && playwright install"
    exit 1
fi

# Parse arguments
VERBOSE=""
TEST_FILTER=""
SAVE_RESULTS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -k|--filter)
            TEST_FILTER="-k $2"
            shift 2
            ;;
        -s|--save)
            SAVE_RESULTS="| tee test_results_$(date +%Y%m%d_%H%M%S).txt"
            shift
            ;;
        --dashboard)
            TEST_FILTER="-k TestDashboardWidgets"
            shift
            ;;
        --goals)
            TEST_FILTER="-k TestGoalsPage"
            shift
            ;;
        --plan)
            TEST_FILTER="-k TestPlanAdjustmentsPage"
            shift
            ;;
        --explore)
            TEST_FILTER="-k TestExplorePage"
            shift
            ;;
        --upcoming)
            TEST_FILTER="-k TestUpcomingPage"
            shift
            ;;
        --help)
            echo "Usage: ./run_phase_a_tests.sh [options]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose         Verbose output"
            echo "  -k, --filter <name>   Filter tests by name"
            echo "  -s, --save            Save results to timestamped file"
            echo "  --dashboard           Run only dashboard tests"
            echo "  --goals               Run only goals page tests"
            echo "  --plan                Run only plan adjustments tests"
            echo "  --explore             Run only explore page tests"
            echo "  --upcoming            Run only upcoming page tests"
            echo "  --help                Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run_phase_a_tests.sh                    # Run all tests"
            echo "  ./run_phase_a_tests.sh -v                 # Run all tests with verbose output"
            echo "  ./run_phase_a_tests.sh --dashboard        # Run only dashboard tests"
            echo "  ./run_phase_a_tests.sh -k test_loads      # Run tests matching 'test_loads'"
            echo "  ./run_phase_a_tests.sh -v -s              # Verbose output and save results"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run with --help to see available options"
            exit 1
            ;;
    esac
done

echo "Running Phase A tests..."
echo "Frontend URL: https://frontend-ryanwillgings-projects.vercel.app"
echo ""

# Run tests
eval "pytest tests/e2e/test_phase_a_frontend.py $VERBOSE $TEST_FILTER --tb=short $SAVE_RESULTS"

echo ""
echo "========================================"
echo "Tests complete!"
echo "========================================"
echo ""
echo "View detailed results: docs/PHASE_A_TEST_RESULTS.md"
echo "Next steps: docs/PHASE_A_NEXT_STEPS.md"
