#!/bin/bash
set -e

# Run the MCP server with development settings
echo "Starting MCP DuckDuckGo server in development mode..."
python -m mcp_duckduckgo.main --host 127.0.0.1 --port 3000 --log-level debug

# Note: This script will run until interrupted with Ctrl+C
