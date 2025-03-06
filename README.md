# MCP DuckDuckGo Search Plugin

A DuckDuckGo search plugin for Model Context Protocol (MCP), compatible with Claude Code. Provides web search functionality with advanced navigation and content exploration features.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/github/stars/gianlucamazza/mcp-duckduckgo?style=social)](https://github.com/gianlucamazza/mcp-duckduckgo)

## Description

This project implements a Model Context Protocol (MCP) server that provides web search functionality using DuckDuckGo. The plugin is designed to work seamlessly with Claude Code or any other client that supports MCP, offering not just basic search capabilities but also advanced navigation and result exploration features.

## Features

- **Web Search Tool**: Perform web searches using DuckDuckGo
- **Detailed Results**: Get detailed information about specific search results
- **Related Searches**: Discover related search queries based on your original search
- **Pagination Support**: Navigate through multiple pages of search results
- **Domain Extraction**: View domain information for each search result
- **Advanced Filtering**: Filter results by site and time period
- **Search Documentation**: Access comprehensive documentation about the search functionality
- **Search Assistant**: Get help formulating effective search queries
- **Parameterized Resource**: Retrieve formatted search results for specific queries

## Requirements

- Python 3.9 or higher
- pip (Python package manager)
- Python packages listed in `pyproject.toml`

## Installation

### From PyPI

*Note: This package is not yet published to PyPI. Please install from source below.*

In the future, once published, you'll be able to install with:

```bash
pip install mcp-duckduckgo
```

### From Source

1. Clone this repository:

   ```bash
   git clone https://github.com/gianlucamazza/mcp-duckduckgo.git
   cd mcp-duckduckgo
   ```

2. Install the package in development mode:

   ```bash
   pip install -e .
   ```

   Or use the provided script:

   ```bash
   ./scripts/install_dev.sh
   ```

   Or use Make:

   ```bash
   make install
   ```

## Usage

### Starting the Server Manually

To start the MCP server:

```bash
mcp-duckduckgo
```

Or with custom parameters:

```bash
mcp-duckduckgo --host 127.0.0.1 --port 8000
```

Or use the provided script for development:

```bash
./scripts/run.sh
```

Or use Make:

```bash
make run
```

### Using with Claude Code

1. Install the package from source as described above.

2. Configure Claude Code to use the plugin:

   ```bash
   claude mcp add duckduckgo-search -- mcp-duckduckgo
   ```

3. For global configuration (available in all projects):

   ```bash
   claude mcp add duckduckgo-search --scope global -- mcp-duckduckgo
   ```

4. Start Claude Code:

   ```bash
   claude
   ```

5. Now you can use the DuckDuckGo search functionality within Claude Code.

## Available Endpoints

The plugin provides the following endpoints:

### Tool: `duckduckgo_web_search`

Performs a web search using DuckDuckGo with the following parameters:

- `query` (required): The search query (max 400 characters, 50 words)
- `count` (optional, default: 10): Number of results per page (1-20)
- `page` (optional, default: 1): Page number for pagination
- `site` (optional): Limit results to a specific site (e.g., 'example.com')
- `time_period` (optional): Filter results by time period ('day', 'week', 'month', 'year')

Example usage in Claude Code:

```text
Search for "artificial intelligence latest developments"
```

### Tool: `duckduckgo_get_details`

Retrieves detailed information about a specific search result:

- `url` (required): URL of the result to get details for

Example usage in Claude Code:

```text
Get details for "https://example.com/article"
```

### Tool: `duckduckgo_related_searches`

Suggests related search queries based on the original query:

- `query` (required): Original search query (max 400 characters)
- `count` (optional, default: 5): Number of related searches to return (1-10)

Example usage in Claude Code:

```text
Find related searches for "renewable energy"
```

### Resource: `docs://search`

Provides comprehensive documentation about the search functionality.

Example usage in Claude Code:

```text
Show me the documentation for the DuckDuckGo search
```

### Prompt: `search_assistant`

Helps formulate effective search queries.

Example usage in Claude Code:

```text
Help me formulate a search query about climate change solutions
```

### Resource: `search://{query}`

Retrieves formatted search results for a specific query.

Example usage in Claude Code:

```text
Get search results for "quantum computing breakthroughs"
```

## Using the Navigation Features

The plugin provides several features to help navigate and explore search results:

### Pagination

To navigate through multiple pages of search results:

```text
Search for "climate change solutions" with 5 results per page, page 2
```

### Filtering Results

To filter results by specific site:

```text
Search for "machine learning tutorials" on "tensorflow.org"
```

To filter results by time period:

```text
Search for "latest news" from the past week
```

### Exploring Result Details

To get more information about a specific search result:

```text
Get details for "https://example.com/article-found-in-search"
```

### Finding Related Searches

To discover related search queries:

```text
Find related searches for "electric vehicles"
```

These navigation features can be combined with Claude's natural language capabilities to create a powerful search and exploration experience. For example:

```text
Search for "python machine learning libraries", then get details on the top result, and finally show me related search terms
```

## Implementation Notes

This implementation uses DuckDuckGo's public web interface and parses the HTML response to extract results. This approach is used for demonstration purposes, as DuckDuckGo does not offer an official search API. In a production environment, it's recommended to use a search service with an official API.

## Development

The project includes several utility scripts in the `scripts` directory to help with development:

- `install_dev.sh`: Sets up the development environment
- `run.sh`: Runs the MCP server with development settings
- `test.sh`: Runs tests with coverage reporting
- `lint.sh`: Runs linting and code formatting
- `publish.sh`: Builds and publishes the package to PyPI

For convenience, a Makefile is also provided with the following targets:

```bash
make install  # Install the package in development mode
make test     # Run tests with coverage
make lint     # Run linting and code formatting
make run      # Run the MCP server
make publish  # Build and publish the package to PyPI
make clean    # Clean build artifacts
make all      # Run install, lint, and test (default)
make help     # Show help message
```

### Running Tests

```bash
pytest
```

Or use the provided script:

```bash
./scripts/test.sh
```

Or use Make:

```bash
make test
```

### Code Formatting and Linting

```bash
black mcp_duckduckgo
isort mcp_duckduckgo
mypy mcp_duckduckgo
```

Or use the provided script:

```bash
./scripts/lint.sh
```

Or use Make:

```bash
make lint
```

### Publishing to PyPI

If you want to publish the package to PyPI:

1. Update the version in `pyproject.toml`
2. Ensure you have the necessary credentials and tools:
   ```bash
   pip install build twine
   ```
3. Build and publish:
   ```bash
   python -m build
   twine upload dist/*
   ```

Or use the provided script if available:

```bash
./scripts/publish.sh
```

Or use Make:

```bash
make publish
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[MIT](LICENSE)

## Repository

https://github.com/gianlucamazza/mcp-duckduckgo
