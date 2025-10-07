#!/bin/bash
set -e

# Run black for code formatting
echo "Running black code formatter..."
black mcp_duckduckgo tests

# Run isort for import sorting
echo "Running isort import sorter..."
isort mcp_duckduckgo tests

# Run mypy for type checking
echo "Running mypy type checker..."
mypy mcp_duckduckgo

# Run flake8 for linting
echo "Running flake8 linter..."
flake8 mcp_duckduckgo tests

echo "Linting and formatting completed!"
