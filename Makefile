# MCP DuckDuckGo - Development Makefile
.PHONY: help install install-dev test lint format type-check security clean build publish pre-commit setup-dev

help:  ## Show this help message
	@echo "MCP DuckDuckGo Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package
	pip install -e .

install-dev:  ## Install development dependencies
	pip install -e ".[test,dev]"

setup-dev: install-dev  ## Setup development environment
	pre-commit install
	@echo "Development environment setup complete!"

test:  ## Run tests with coverage
	pytest --cov=mcp_duckduckgo --cov-report=term-missing --cov-report=html

test-fast:  ## Run tests without coverage
	pytest -x -v

lint:  ## Run linting with ruff
	ruff check .

lint-fix:  ## Run linting with automatic fixes
	ruff check . --fix

format:  ## Format code with ruff
	ruff format .

format-check:  ## Check code formatting
	ruff format --check .

type-check:  ## Run type checking with mypy
	mypy mcp_duckduckgo/

security:  ## Run security checks
	bandit -r mcp_duckduckgo/ -c pyproject.toml
	safety check

quality: lint format-check type-check security  ## Run all quality checks

pre-commit:  ## Run pre-commit hooks
	pre-commit run --all-files

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean  ## Build the package
	python -m build

publish-test: build  ## Publish to test PyPI
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

publish: build  ## Publish to PyPI
	twine upload dist/*

dev-server:  ## Run development server
	python -m mcp_duckduckgo.main

# Docker commands
docker-build:  ## Build Docker image
	docker build -t mcp-duckduckgo .

docker-run:  ## Run Docker container
	docker run -p 3000:3000 mcp-duckduckgo

# CI simulation
ci-local: quality test  ## Run CI checks locally
	@echo "All CI checks passed! ✅"

# Performance testing
benchmark:  ## Run performance benchmarks
	pytest tests/test_property_based.py::TestPerformance --benchmark-only

profile-memory:  ## Profile memory usage
	python -m memory_profiler -c "import mcp_duckduckgo; from mcp_duckduckgo.search import extract_domain; [extract_domain(f'https://example{i}.com') for i in range(1000)]"

# Maintenance
maintenance:  ## Run maintenance tasks
	pre-commit autoupdate
	pip-check --not-required || true
	vulture mcp_duckduckgo/ --min-confidence 80 || true

# Update dependencies
update-deps:  ## Update development dependencies
	pip install --upgrade pip
	pip install --upgrade -e ".[test,dev]"

# Check for security vulnerabilities
audit:  ## Run comprehensive security audit
	pip-audit
	safety check
	bandit -r mcp_duckduckgo/ -c pyproject.toml
	semgrep --config=auto mcp_duckduckgo/

# Dead code analysis
dead-code:  ## Find unused code with vulture
	vulture mcp_duckduckgo/ --min-confidence 60

# Full static analysis
analyze: lint type-check security dead-code audit  ## Run complete static analysis

# Docker commands
docker-dev:  ## Start development environment with Docker
	docker-compose --profile dev up --build

docker-test:  ## Run tests in Docker
	docker-compose --profile test up --build

docker-prod:  ## Start production environment
	docker-compose up --build -d

docker-stop:  ## Stop all Docker services
	docker-compose down

docker-logs:  ## View Docker logs
	docker-compose logs -f

# Modern Python compliance check
modern-python-check:  ## Check modern Python compliance
	@echo "🔍 Running modern Python compliance checks..."
	@echo "✅ Python version: $(shell python --version)"
	@python -c "from __future__ import annotations; print('✅ Future annotations: Supported')"
	@python -c "exec('match 1:\\n    case 1:\\n        print(\\\"✅ Pattern matching: Supported\\\")')"
	@python -c "x: int | str = 1; print('✅ Union operator: Supported')"
	ruff check . --select UP
	mypy mcp_duckduckgo/ --ignore-missing-imports
	@echo "🎉 Modern Python compliance check completed!"