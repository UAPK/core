#!/bin/bash
# Run tests for UAPK Gateway Python SDK

set -e

echo "================================"
echo "UAPK Gateway SDK Test Runner"
echo "================================"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "   Consider activating a venv first"
    echo ""
fi

# Install dependencies if needed
if ! python -c "import pytest" 2>/dev/null; then
    echo "📦 Installing test dependencies..."
    pip install -e ".[dev,langchain]" -q
    echo ""
fi

# Parse command line arguments
COVERAGE=false
VERBOSE=false
SPECIFIC_TEST=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --test|-t)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: ./run_tests.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -c, --coverage    Generate coverage report"
            echo "  -v, --verbose     Verbose output"
            echo "  -t, --test PATH   Run specific test file or function"
            echo "  -h, --help        Show this help"
            echo ""
            echo "Examples:"
            echo "  ./run_tests.sh                     # Run all tests"
            echo "  ./run_tests.sh --coverage          # Run with coverage"
            echo "  ./run_tests.sh -t tests/test_client.py  # Run specific file"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

if [ "$SPECIFIC_TEST" != "" ]; then
    PYTEST_CMD="$PYTEST_CMD $SPECIFIC_TEST"
fi

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=uapk_gateway --cov-report=term-missing --cov-report=html"
fi

# Run tests
echo "🧪 Running tests..."
echo "   Command: $PYTEST_CMD"
echo ""

$PYTEST_CMD

# Show coverage report location if generated
if [ "$COVERAGE" = true ]; then
    echo ""
    echo "📊 Coverage report generated:"
    echo "   HTML: htmlcov/index.html"
    echo "   Terminal: see above"
fi

echo ""
echo "✅ Tests completed!"
