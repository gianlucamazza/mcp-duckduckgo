"""
Server setup and lifespan management for the DuckDuckGo search plugin.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_duckduckgo.server")

# Global variable for HTTP client
http_client = None


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage application lifecycle with proper resource initialization and cleanup."""
    global http_client
    try:
        # Initialize resources on startup
        logger.info("Initializing DuckDuckGo search server")
        http_client = httpx.AsyncClient(
            timeout=10.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            },
        )
        yield {"http_client": http_client}
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down DuckDuckGo search server")
        if http_client:
            await http_client.aclose()


# Initialize FastMCP server with lifespan
mcp = FastMCP("DuckDuckGo Search", lifespan=app_lifespan)

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
