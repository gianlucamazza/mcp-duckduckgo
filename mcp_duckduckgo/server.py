"""
Server setup and lifespan management for the DuckDuckGo search plugin.
Enhanced with 2025 security best practices and Resource Indicators (RFC 8707).
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from .security import security_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_duckduckgo.server")

# Global variables
http_client = None
server_metrics = {
    "start_time": time.time(),
    "requests_processed": 0,
    "errors_count": 0,
    "cache_hits": 0,
    "cache_misses": 0,
}


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage application lifecycle with proper resource initialization and cleanup."""
    global http_client
    try:
        # Initialize resources on startup
        logger.info("Initializing DuckDuckGo search server with enhanced security")

        # Initialize HTTP client with security headers
        http_client = httpx.AsyncClient(
            timeout=30.0,  # Increased timeout for better reliability
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            follow_redirects=True,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30,
            ),
        )

        # Initialize security manager
        logger.info("Security manager initialized with RFC 8707 Resource Indicators")

        yield {
            "http_client": http_client,
            "security_manager": security_manager,
            "metrics": server_metrics,
        }
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down DuckDuckGo search server")
        if http_client:
            await http_client.aclose()

        # Log final metrics
        uptime = time.time() - server_metrics["start_time"]
        logger.info(f"Server uptime: {uptime:.2f}s")
        logger.info(f"Total requests processed: {server_metrics['requests_processed']}")
        logger.info(f"Total errors: {server_metrics['errors_count']}")
        logger.info(f"Cache hit ratio: {_calculate_cache_hit_ratio():.2%}")


def _calculate_cache_hit_ratio() -> float:
    """Calculate cache hit ratio for metrics."""
    total_cache_requests = server_metrics["cache_hits"] + server_metrics["cache_misses"]
    if total_cache_requests == 0:
        return 0.0
    return server_metrics["cache_hits"] / total_cache_requests


# Initialize FastMCP server with enhanced lifespan
mcp = FastMCP(
    "DuckDuckGo Search (Enhanced Security)",
    lifespan=app_lifespan
)

# Export the tool decorator for use in tools modules
tool = mcp.tool


# Function to cleanly close the HTTP client
async def close_http_client() -> None:
    """Cleanly close the HTTP client."""
    global http_client
    if http_client:
        logger.info("Closing HTTP client")
        await http_client.aclose()
        http_client = None

