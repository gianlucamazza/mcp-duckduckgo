#!/bin/bash
set -e

# Check if a test file was specified
if [ -z "$1" ]; then
    echo "Usage: $0 <test_file>"
    echo "Example: $0 tests/test_models.py"
    exit 1
fi

TEST_FILE="$1"

# Check if the file exists
if [ ! -f "$TEST_FILE" ]; then
    echo "Error: Test file $TEST_FILE not found."
    echo "Available test files:"
    find tests -name "test_*.py" | sort
    exit 1
fi

# Check if test dependencies are installed
python -c "import pytest" 2>/dev/null || {
    echo "pytest not found. Installing test dependencies..."
    python -m pip install -e ".[test]"
}

# Run the specified test with verbose output
echo "Running test: $TEST_FILE"
python -m pytest "$TEST_FILE" -v
