"""
DuckDuckGo search plugin for Model Context Protocol.
This module implements a web search function using the DuckDuckGo API.
"""

import argparse
import logging
import importlib
import os
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_duckduckgo")

def initialize_mcp() -> Any:
    """Initialize MCP server and register components."""
    # Import server module and create server instance
    server_module = importlib.import_module(".server", package="mcp_duckduckgo")
    mcp = server_module.create_mcp_server()

    # Import all MCP components to register them
    importlib.import_module(".tools", package="mcp_duckduckgo")
    importlib.import_module(".resources", package="mcp_duckduckgo")
    importlib.import_module(".prompts", package="mcp_duckduckgo")

    return mcp

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DuckDuckGo search plugin for Model Context Protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port number for the MCP server (default: 3000)"
    )
    return parser.parse_args()

def main() -> None:
    """Run the MCP server."""
    try:
        # Parse command line arguments
        args = parse_args()

        # Set port via environment variable for FastMCP
        os.environ["MCP_PORT"] = str(args.port)

        # Initialize MCP server
        mcp = initialize_mcp()

        logger.info("Starting DuckDuckGo Search MCP server on port %s", args.port)
        logger.info("Available endpoints:")
        logger.info("- Tool: duckduckgo_web_search")
        logger.info("- Tool: duckduckgo_get_details")
        logger.info("- Tool: duckduckgo_related_searches")
        logger.info("- Resource: docs://search")
        logger.info("- Resource: search://{query}")
        logger.info("- Prompt: search_assistant")

        # Run the MCP server
        # FastMCP reads port from MCP_PORT environment variable
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error("Error starting server: %s", e, exc_info=True)
        raise

if __name__ == "__main__":
    main()
