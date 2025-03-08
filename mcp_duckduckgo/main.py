"""
DuckDuckGo search plugin for Model Context Protocol.
This module implements a web search function using the DuckDuckGo API.
"""

import logging
import importlib
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_duckduckgo")

def initialize_mcp() -> Any:
    """Initialize MCP server and register components."""
    # Import server to initialize MCP
    server_module = importlib.import_module(".server", package="mcp_duckduckgo")
    mcp = server_module.mcp
    
    # Import all MCP components to register them
    importlib.import_module(".tools", package="mcp_duckduckgo")
    importlib.import_module(".resources", package="mcp_duckduckgo")
    importlib.import_module(".prompts", package="mcp_duckduckgo")
    
    return mcp

def main() -> None:
    """Run the MCP server."""
    try:
        # Initialize MCP
        mcp = initialize_mcp()
        
        logger.info("Starting DuckDuckGo Search MCP server on port 3000")
        logger.info("Available endpoints:")
        logger.info("- Tool: duckduckgo_web_search")
        logger.info("- Tool: duckduckgo_get_details")
        logger.info("- Tool: duckduckgo_related_searches")
        logger.info("- Resource: docs://search")
        logger.info("- Resource: search://{query}")
        logger.info("- Prompt: search_assistant")
        
        # Run the MCP server
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 