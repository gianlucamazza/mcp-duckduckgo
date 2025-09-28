"""
Health monitoring tools for MCP DuckDuckGo server.
Provides endpoints for health checks and performance metrics.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import Context

from ..monitoring import monitor_request, performance_monitor
from ..security import ResourceType, SecurityLevel, secure_operation
from ..server import tool

logger = logging.getLogger(__name__)


@tool()
@secure_operation(
    ResourceType.CACHE_READ,
    "health_check",
    SecurityLevel.PUBLIC,
    "Server health status check"
)
async def health_check(ctx: Context) -> dict:
    """
    Get the current health status of the MCP server.

    This endpoint provides comprehensive health information including:
    - Overall health status
    - Individual component health checks
    - Basic performance metrics
    - System resource usage

    Returns:
        dict: Health status information
    """
    try:
        health_status = await performance_monitor.get_health_status()
        return {
            "status": "success",
            "data": health_status,
            "message": "Health check completed successfully"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "data": {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": performance_monitor.start_time,
            },
            "message": f"Health check failed: {e}"
        }


@tool()
@secure_operation(
    ResourceType.CACHE_READ,
    "performance_metrics",
    SecurityLevel.LOW,
    "Server performance metrics"
)
async def get_performance_metrics(ctx: Context) -> dict:
    """
    Get detailed performance metrics for the MCP server.

    This endpoint provides comprehensive performance information including:
    - Request statistics (total, success rate, response times)
    - System resource usage (CPU, memory)
    - Cache performance metrics
    - Historical trends

    Returns:
        dict: Performance metrics and trends
    """
    try:
        # Update metrics history before returning
        performance_monitor.update_metrics_history()

        metrics_summary = performance_monitor.get_metrics_summary()
        return {
            "status": "success",
            "data": metrics_summary,
            "message": "Performance metrics retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        return {
            "status": "error",
            "data": {},
            "message": f"Failed to get performance metrics: {e}"
        }


@tool()
@secure_operation(
    ResourceType.CACHE_READ,
    "server_info",
    SecurityLevel.PUBLIC,
    "Basic server information"
)
async def get_server_info(ctx: Context) -> dict:
    """
    Get basic server information and status.

    Returns:
        dict: Server information including version, uptime, and configuration
    """
    try:
        import time

        from ..server import server_metrics

        uptime_seconds = time.time() - server_metrics["start_time"]

        server_info = {
            "server_name": "MCP DuckDuckGo Search (Enhanced Security)",
            "version": "0.1.1",
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": _format_uptime(uptime_seconds),
            "start_time": server_metrics["start_time"],
            "security_features": [
                "Resource Indicators (RFC 8707)",
                "Rate limiting",
                "Domain validation",
                "Input sanitization",
                "Distroless container support"
            ],
            "monitoring_features": [
                "Health checks",
                "Performance metrics",
                "Request tracking",
                "System resource monitoring",
                "Cache analytics"
            ]
        }

        return {
            "status": "success",
            "data": server_info,
            "message": "Server information retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Failed to get server info: {e}")
        return {
            "status": "error",
            "data": {},
            "message": f"Failed to get server info: {e}"
        }


def _format_uptime(uptime_seconds: float) -> str:
    """Format uptime in a human-readable format."""
    days = int(uptime_seconds // (24 * 3600))
    hours = int((uptime_seconds % (24 * 3600)) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


# Add performance monitoring to existing search tools
@monitor_request
async def monitored_search_wrapper(func: Callable, *args: Any, **kwargs: Any) -> Any:
    """Wrapper to add monitoring to search functions."""
    return await func(*args, **kwargs)

