# MCP DuckDuckGo

A Model Context Protocol (MCP) server that provides web search capabilities using [DuckDuckGo](https://duckduckgo.com). This server enables LLMs to search the web and retrieve detailed content from websites through structured data extraction.

## Key Features
- **Fast and reliable**. Uses DuckDuckGo's web interface with robust HTML parsing
- **LLM-friendly**. Returns structured data optimized for AI consumption
- **Content extraction**. Intelligently extracts and summarizes webpage content
- **Related searches**. Generates contextual search suggestions

## Requirements
- Python 3.10 or newer
- VS Code, Cursor, Windsurf, Claude Desktop, Goose or any other MCP client

## Getting started

First, install the DuckDuckGo MCP server with your client.

**Standard config** works in most of the tools:

```json
{
  "mcpServers": {
    "duckduckgo-search": {
      "command": "mcp-duckduckgo"
    }
  }
}
```

### Claude Code

Use the Claude Code CLI to add the DuckDuckGo MCP server:
```bash
claude mcp add duckduckgo-search mcp-duckduckgo
```

For global configuration (available in all projects):
```bash
claude mcp add duckduckgo-search --scope user mcp-duckduckgo
```

### Claude Desktop

Follow the MCP install [guide](https://modelcontextprotocol.io/quickstart/user), use the standard config above.

### Cursor

Go to `Cursor Settings` -> `MCP` .

#### Click the button to install:
[Install in Cursor](https://cursor.com/en/install-mcp?name=DuckDuckGo&config=eyJjb21tYW5kIjoibWNwLWR1Y2tkdWNrZ28ifQ%3D%3D)

#### Or install manually:
Go to `Cursor Settings` -> `MCP` -> `Add new MCP Server`. Name to your liking, use `command` type with the command `mcp-duckduckgo`.

### VS Code

#### Click the button to install:
[Install in VS Code](https://insiders.vscode.dev/redirect?url=vscode%3Amcp%2Finstall%3F%257B%2522name%2522%253A%2522duckduckgo-search%2522%252C%2522command%2522%253A%2522mcp-duckduckgo%2522%257D)

#### Or install manually:
Follow the MCP install [guide](https://code.visualstudio.com/docs/copilot/chat/mcp-servers#_add-an-mcp-server), use the standard config above.

You can also install the DuckDuckGo MCP server using the VS Code CLI:
```bash
code --add-mcp '{"name":"duckduckgo-search","command":"mcp-duckduckgo"}'
```

After installation, the DuckDuckGo MCP server will be available for use with your GitHub Copilot agent in VS Code.

### Windsurf

Follow Windsurf MCP [documentation](https://docs.windsurf.com/windsurf/cascade/mcp). Use the standard config above.

### Goose

#### Click the button to install:
[![Install in Goose](https://block.github.io/goose/img/extension-install-dark.svg)](https://block.github.io/goose/extension?cmd=mcp-duckduckgo&id=duckduckgo&name=DuckDuckGo&description=Search%20the%20web%20and%20extract%20content%20using%20DuckDuckGo)

#### Or install manually:
Go to `Advanced settings` -> `Extensions` -> `Add custom extension`. Name to your liking, use type `STDIO`, and set the `command` to `mcp-duckduckgo`. Click "Add Extension".

### LM Studio

#### Click the button to install:
[![Add MCP Server duckduckgo to LM Studio](https://files.lmstudio.ai/deeplink/mcp-install-light.svg)](https://lmstudio.ai/install-mcp?name=duckduckgo&config=eyJjb21tYW5kIjoibWNwLWR1Y2tkdWNrZ28ifQ%3D%3D)

#### Or install manually:
Go to `Program` in the right sidebar -> `Install` -> `Edit mcp.json`. Use the standard config above.

## Configuration

DuckDuckGo MCP server supports following arguments:

```bash
mcp-duckduckgo --help
```

Available options:
```bash
--port PORT        Port number for the MCP server (default: 3000)
--version          Show program's version number and exit
--help             Show help message and exit
```

### Environment Variables

- `MCP_PORT`: Set the port number for the server (default: 3000)

Example usage:
```bash
# Set port via environment variable
export MCP_PORT=8080
mcp-duckduckgo

# Or set it inline
MCP_PORT=8080 mcp-duckduckgo
```

## Available Tools

### **web_search**
- Title: Web Search
- Description: Search the web using DuckDuckGo
- Parameters:
  - `query` (string): Search query (max 400 characters)
  - `max_results` (number, optional): Maximum number of results to return (1-20, default 10)
- Read-only: **false**

### **get_page_content**
- Title: Get Page Content
- Description: Retrieve and extract content from a web page
- Parameters:
  - `url` (string): URL to fetch content from
- Read-only: **false**

### **suggest_related_searches**
- Title: Suggest Related Searches
- Description: Generate contextual search suggestions based on a query
- Parameters:
  - `query` (string): Original search query
  - `max_suggestions` (number, optional): Maximum suggestions to return (1-10, default 5)
- Read-only: **true**

## Installation from Source

If you need to install from source or development:

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install from GitHub
uv tool install git+https://github.com/gianlucamazza/mcp-duckduckgo.git
```

### Using pip

```bash
# Clone and install
git clone https://github.com/gianlucamazza/mcp-duckduckgo.git
cd mcp-duckduckgo
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/gianlucamazza/mcp-duckduckgo.git
cd mcp-duckduckgo

# Install in development mode
pip install -e .

# Run tests
pip install -e ".[test]"
pytest
```

## License

[MIT](LICENSE)

## Repository

[GitHub Repository](https://github.com/gianlucamazza/mcp-duckduckgo)
