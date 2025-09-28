"""
DuckDuckGo search plugin for Model Context Protocol.
This module implements a web search function using the DuckDuckGo API.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import logging
import os
import signal
import threading
import time
from types import FrameType
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_duckduckgo")

# Global variables to track MCP instance
mcp_instance = None
server_module = None
# Flag to track if the server is shutting down
is_shutting_down = False
# Timestamp of the last interrupt signal
last_interrupt_time: float = 0.0


def signal_handler(sig: int, _frame: FrameType | None) -> None:
    """Handle process interruption signals like SIGINT (Ctrl+C)."""
    global is_shutting_down, last_interrupt_time

    current_time = time.time()

    # Use modern pattern matching for signal handling
    match sig:
        case signal.SIGINT:
            # Handle Ctrl+C with double-tap detection
            if is_shutting_down or (
                current_time - last_interrupt_time < 1.0 and last_interrupt_time > 0
            ):
                logger.info("Forced server shutdown (double Ctrl+C)")
                os._exit(1)
            else:
                logger.info("Graceful shutdown initiated (Ctrl+C)")
        case signal.SIGTERM:
            logger.info("Termination signal received")
        case _:
            logger.info(f"Unhandled signal: {sig}")

    is_shutting_down = True
    last_interrupt_time = current_time
    logger.info("Server shutdown requested by user")

    # Close the HTTP client cleanly if possible
    if server_module and hasattr(server_module, "close_http_client"):
        try:
            # Check if there's an active event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If the loop is running, schedule the closure
                    asyncio.create_task(server_module.close_http_client())  # noqa: RUF006
                else:
                    # If the loop is not running, run the function synchronously
                    loop.run_until_complete(server_module.close_http_client())
            except RuntimeError:
                # If there's no active event loop, don't try to close the HTTP client
                logger.info("No active event loop, cannot close HTTP client cleanly")
        except Exception as e:
            logger.error(f"Error closing HTTP client: {e}")

    # Terminate the process after a short delay
    # This gives the server some time to shut down cleanly
    def delayed_exit() -> None:
        time.sleep(0.5)  # Wait 0.5 seconds
        logger.info("Terminating process")
        os._exit(0)

    # Start a new thread to terminate the process after a short delay
    threading.Thread(target=delayed_exit, daemon=True).start()


def initialize_mcp() -> Any:
    """Initialize MCP server and register components."""
    global server_module
    # Import server module and get MCP instance
    server_module = importlib.import_module(".server", package="mcp_duckduckgo")
    mcp = server_module.mcp

    # Import all MCP components to register them
    importlib.import_module(".tools", package="mcp_duckduckgo")
    importlib.import_module(".resources", package="mcp_duckduckgo")
    importlib.import_module(".prompts", package="mcp_duckduckgo")

    return mcp


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DuckDuckGo search plugin for Model Context Protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port number for the MCP server (default: 3000)",
    )
    return parser.parse_args()


def main() -> None:
    """Run the MCP server."""
    global mcp_instance, is_shutting_down

    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Parse command line arguments
        args = parse_args()

        # Set port via environment variable for FastMCP
        os.environ["MCP_PORT"] = str(args.port)

        # Initialize MCP server
        mcp_instance = initialize_mcp()

        logger.info("Starting DuckDuckGo Search MCP server with 2025 enhancements on port %s", args.port)
        logger.info("🔍 Search Tools:")
        logger.info("- Tool: duckduckgo_web_search")
        logger.info("- Tool: duckduckgo_get_details")
        logger.info("- Tool: duckduckgo_related_searches")
        logger.info("- Tool: duckduckgo_multi_hop_research")
        logger.info("🤖 AI Tools:")
        logger.info("- Tool: summarize_webpage")
        logger.info("- Tool: fact_check")
        logger.info("- Tool: dev_search")
        logger.info("- Tool: location_search")
        logger.info("🔧 2025 Monitoring Tools:")
        logger.info("- Tool: health_check")
        logger.info("- Tool: get_performance_metrics")
        logger.info("- Tool: get_server_info")
        logger.info("📚 Resources:")
        logger.info("- Resource: docs://search")
        logger.info("- Resource: search://{query}")
        logger.info("🎯 AI Assistants:")
        logger.info("- Prompt: search_assistant")
        logger.info("- Prompt: fact_check_assistant")
        logger.info("- Prompt: technical_search_assistant")
        logger.info("- Prompt: location_search_assistant")
        logger.info("- Prompt: summary_assistant")
        logger.info("🔐 Security: Enhanced with RFC 8707 Resource Indicators")
        logger.info("📊 Monitoring: Real-time health checks and performance metrics")
        logger.info("🐳 Container: Distroless production image available")

        # Run the MCP server
        # FastMCP reads port from MCP_PORT environment variable
        mcp_instance.run()
    except KeyboardInterrupt:
        # Set the shutdown flag
        is_shutting_down = True
        logger.info("Server shutdown requested by user")

        # Close the HTTP client cleanly
        if server_module and hasattr(server_module, "close_http_client"):
            try:
                # Check if there's an active event loop
                try:
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(server_module.close_http_client())
                except RuntimeError:
                    # If there's no active event loop, don't try to close the HTTP client
                    logger.info(
                        "No active event loop, cannot close HTTP client cleanly"
                    )
            except Exception as e:
                logger.error(f"Error closing HTTP client: {e}")
    except Exception as e:
        logger.error("Error starting server: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    main()
