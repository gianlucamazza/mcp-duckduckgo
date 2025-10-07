#!/bin/bash
set -e

echo "=== MCP DuckDuckGo Test Suite ==="

# Check if test dependencies are installed
echo "Checking for test dependencies..."
python -c "import pytest" 2>/dev/null || {
    echo "pytest not found. Installing test dependencies..."
    pip install -e ".[test]"
}

# Create tests directory if it doesn't exist
if [ ! -d "tests" ]; then
    echo "Creating tests directory..."
    mkdir -p tests
fi

# Run tests with coverage
echo "Running tests with coverage..."
python -m pytest --cov=mcp_duckduckgo tests/ --cov-report=term-missing

# Generate HTML coverage report
echo "Generating HTML coverage report..."
python -m pytest --cov=mcp_duckduckgo tests/ --cov-report=html

# Check for mypy errors
echo "Running type checking with mypy..."
python -m mypy mcp_duckduckgo tests

echo "=== Test Summary ==="
echo "Tests completed. HTML coverage report available in htmlcov/"
echo
echo "You can also run specific test commands:"
echo "  - pytest tests/              # Run all tests"
echo "  - pytest tests/test_models.py  # Run specific test file"
echo "  - pytest -v                  # Run with verbose output"
echo "  - pytest --cov=mcp_duckduckgo  # Run with coverage"
echo "======================="
