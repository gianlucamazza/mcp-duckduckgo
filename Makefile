.PHONY: install test lint run publish clean vulture

# Default target
all: install lint test

# Install the package in development mode
install:
	./scripts/install_dev.sh

# Run tests with coverage
test:
	./scripts/test.sh

# Run linting and code formatting
lint:
	./scripts/lint.sh

# Run the MCP server
run:
	./scripts/run.sh

# Build and publish the package to PyPI
publish:
	./scripts/publish.sh

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/ .coverage htmlcov/ .pytest_cache/ __pycache__/ mcp_duckduckgo/__pycache__/ tests/__pycache__/

# Run Vulture to check for unused code
vulture:
	./scripts/vulture.sh

# Help target
help:
	@echo "Available targets:"
	@echo "  make install  - Install the package in development mode"
	@echo "  make test     - Run tests with coverage"
	@echo "  make lint     - Run linting and code formatting"
	@echo "  make run      - Run the MCP server"
	@echo "  make publish  - Build and publish the package to PyPI"
	@echo "  make clean    - Clean build artifacts"
	@echo "  make vulture  - Check for unused code with Vulture"
	@echo "  make all      - Run install, lint, and test (default)"
	@echo "  make help     - Show this help message"
