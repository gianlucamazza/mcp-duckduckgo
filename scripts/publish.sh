#!/bin/bash
set -e

# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Build the package
echo "Building package..."
python -m build

# Check the package
echo "Checking package..."
twine check dist/*

# Publish to PyPI
echo "Do you want to publish to PyPI? (y/n)"
read answer

if [ "$answer" == "y" ]; then
    echo "Publishing to PyPI..."
    twine upload dist/*
    echo "Package published successfully!"
else
    echo "Publishing skipped."
fi
