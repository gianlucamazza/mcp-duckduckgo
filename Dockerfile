# Multi-stage Dockerfile for production deployment - 2025 Best Practices
# Using Python 3.12 for optimal performance and security

# Build stage
FROM python:3.12-slim AS builder

# OCI labels for metadata and compliance
LABEL org.opencontainers.image.title="MCP DuckDuckGo Search"
LABEL org.opencontainers.image.description="DuckDuckGo search plugin for Model Context Protocol"
LABEL org.opencontainers.image.version="0.1.1"
LABEL org.opencontainers.image.authors="Gianluca Mazza <info@gianlucamazza.it>"
LABEL org.opencontainers.image.source="https://github.com/gianlucamazza/mcp-duckduckgo"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.vendor="Gianluca Mazza"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building with cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency files
COPY pyproject.toml ./
COPY LICENSE ./

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install build && \
    pip install .

# Distroless production stage for maximum security
FROM gcr.io/distroless/python3-debian12:latest AS production

# OCI labels for production image
LABEL org.opencontainers.image.title="MCP DuckDuckGo Search"
LABEL org.opencontainers.image.description="DuckDuckGo search plugin for Model Context Protocol"
LABEL org.opencontainers.image.version="0.1.1"
LABEL org.opencontainers.image.authors="Gianluca Mazza <info@gianlucamazza.it>"
LABEL org.opencontainers.image.source="https://github.com/gianlucamazza/mcp-duckduckgo"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.vendor="Gianluca Mazza"
LABEL org.opencontainers.image.documentation="https://github.com/gianlucamazza/mcp-duckduckgo#readme"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    MCP_PORT=3000

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create application directory and copy code
WORKDIR /app
COPY --chown=nonroot:nonroot mcp_duckduckgo/ ./mcp_duckduckgo/

# Switch to non-root user (distroless provides nonroot user)
USER nonroot

# Expose port
EXPOSE 3000

# Run the application
ENTRYPOINT ["python", "-m", "mcp_duckduckgo.main"]

# Slim production stage (alternative to distroless for compatibility)
FROM python:3.12-slim AS production-slim

# OCI labels for slim production image
LABEL org.opencontainers.image.title="MCP DuckDuckGo Search (Slim)"
LABEL org.opencontainers.image.description="DuckDuckGo search plugin for Model Context Protocol - Slim variant"
LABEL org.opencontainers.image.version="0.1.1"
LABEL org.opencontainers.image.authors="Gianluca Mazza <info@gianlucamazza.it>"
LABEL org.opencontainers.image.source="https://github.com/gianlucamazza/mcp-duckduckgo"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.vendor="Gianluca Mazza"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    MCP_PORT=3000

# Install minimal runtime dependencies with cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    curl \
    ca-certificates \
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