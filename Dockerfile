# Multi-stage Dockerfile for production deployment
# Using Python 3.12 for optimal performance and security

# Build stage
FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency files
COPY pyproject.toml ./
COPY LICENSE ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install build && \
    pip install .

# Production stage
FROM python:3.12-slim AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    MCP_PORT=3000

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -r mcp && useradd -r -g mcp -m mcp

# Create application directory
WORKDIR /app

# Copy application code
COPY --chown=mcp:mcp mcp_duckduckgo/ ./mcp_duckduckgo/

# Switch to non-root user
USER mcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${MCP_PORT}/health || exit 1

# Expose port
EXPOSE 3000

# Run the application
CMD ["python", "-m", "mcp_duckduckgo.main"]

# Development stage
FROM builder AS development

# Install development dependencies
RUN pip install -e ".[test,dev]"

# Install pre-commit
RUN pip install pre-commit

# Set working directory
WORKDIR /app

# Copy all files for development
COPY . .

# Install pre-commit hooks
RUN pre-commit install

# Switch to non-root user
USER mcp

# Default command for development
CMD ["python", "-m", "mcp_duckduckgo.main"]