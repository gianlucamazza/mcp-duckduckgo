#!/bin/bash
set -e

# Install the package in development mode
echo "Installing package in development mode..."
pip install -e .

# Install development dependencies
echo "Installing development dependencies..."
pip install pytest pytest-cov black isort mypy flake8 build twine

echo "Development environment setup complete!"
