"""
Server setup and lifespan management for the DuckDuckGo search plugin.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

import httpx
from mcp.server.fastmcp import FastMCP

from .tools import register_search_tools

# Server logging will be configured by the main module
logger = logging.getLogger("mcp_duckduckgo.server")


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage application lifecycle with proper resource initialization and cleanup."""
    try:
        # Initialize resources on startup
        logger.info("Initializing DuckDuckGo search server")
        http_client = httpx.AsyncClient(
            timeout=15.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        yield {"http_client": http_client}
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down DuckDuckGo search server")
        await http_client.aclose()


def create_mcp_server() -> FastMCP:
    """Create and return a FastMCP server instance with proper tool registration."""
    server = FastMCP("DuckDuckGo Search", lifespan=app_lifespan)

    # Register tools directly with the server instance
    register_search_tools(server)

    return server


# Initialize FastMCP server instance for backward compatibility
mcp_server = create_mcp_server()
