"""Shared HTTP client helpers for MCP tools."""

from __future__ import annotations

import logging
from typing import Any, cast

import httpx
from mcp.server.fastmcp import Context

logger = logging.getLogger("mcp_duckduckgo.http")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    ),
}


def _get_lifespan_context(ctx: Context) -> Any:
    """Extract the lifespan context from MCP context.

    Args:
        ctx: The MCP context object

    Returns:
        The lifespan context dictionary or None if not available
    """
    direct = getattr(ctx, "lifespan_context", None)
    if isinstance(direct, dict):
        return direct

    try:
        request_context = ctx.request_context
    except (AttributeError, ValueError):
        return None

    return getattr(request_context, "lifespan_context", None)


def get_http_client(
    ctx: Context, timeout: float = 15.0
) -> tuple[httpx.AsyncClient, bool]:
    """Get or create an HTTP client from the MCP context.

    Args:
        ctx: The MCP context object
        timeout: HTTP timeout in seconds

    Returns:
        A tuple of (HTTP client, should_close) where should_close indicates
        whether the caller should close the client after use
    """
    lifespan_ctx = _get_lifespan_context(ctx)
    if isinstance(lifespan_ctx, dict):
        client = lifespan_ctx.get("http_client")
        client_type = getattr(httpx, "AsyncClient", None)
        is_real_type = isinstance(client_type, type)
        try:
            if (
                is_real_type and client_type and isinstance(client, client_type)
            ) or _looks_like_async_client(client):
                return cast(httpx.AsyncClient, client), False
        except TypeError:
            pass

        client = httpx.AsyncClient(
            timeout=timeout,
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
        )
        lifespan_ctx["http_client"] = client
        logger.debug("Provisioned HTTP client in lifespan context")
        return client, False

    logger.debug("Creating ephemeral HTTP client outside lifespan context")
    client = httpx.AsyncClient(
        timeout=timeout,
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
    )
    return client, True


def _looks_like_async_client(client: object) -> bool:
    """Check if an object looks like an async HTTP client.

    Args:
        client: The object to check

    Returns:
        True if the object has the expected HTTP client methods
    """
    if client is None:
        return False
    return (
        hasattr(client, "get") and hasattr(client, "post") and hasattr(client, "aclose")
    )
