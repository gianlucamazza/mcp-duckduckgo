# MCP DuckDuckGo Search Plugin

A modern, feature-rich DuckDuckGo search plugin for Model Context Protocol (MCP), built with current Python best practices. Compatible with Claude Code and any MCP-supporting client.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: Ruff](https://img.shields.io/badge/Code%20style-Ruff-black.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/Type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
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
- **Enhanced Content Extraction**: Extract rich content from webpages including metadata, structure, and snippets
- **Basic Web Spidering**: Follow links from search results to explore related content (configurable depth)
- **Metadata Extraction**: Extract titles, authors, keywords, publication dates, and more
- **Social Media Detection**: Identify and extract social media links from webpages
- **Content Structure Analysis**: Extract headings and sections to understand webpage structure
- **Search Documentation**: Access comprehensive documentation about the search functionality
- **Search Assistant**: Get help formulating effective search queries
- **Parameterized Resource**: Retrieve formatted search results for specific queries
- **Semantic Cache**: Freshness-aware caching with automatic invalidation heuristics per query intent
- **Knowledge Graph Enrichment**: Link extracted entities to lightweight knowledge graphs for richer reasoning
- **Sandbox Snapshots**: Capture reproducible HTML snapshots for auditing and differential analysis
- **Multi-hop Research**: Orchestrate search, detail enrichment, and summarization with a single tool call

## 2025 Best Practices Implementation

This project implements cutting-edge 2025 best practices for both Docker and MCP:

### **🔐 Enhanced Security (2025)**
- **Distroless Production Images**: Ultra-secure `gcr.io/distroless/python3` containers
- **Resource Indicators (RFC 8707)**: MCP token mis-redemption prevention
- **Docker Scout Integration**: Automated vulnerability scanning and SBOM generation
- **Multi-layer Security Scanning**: Trivy + Docker Scout + comprehensive static analysis
- **Rate Limiting & Domain Validation**: Advanced protection against abuse

### **⚡ Performance & Monitoring (2025)**
- **Real-time Health Checks**: `/health`, `/metrics`, `/info` endpoints
- **Performance Metrics**: CPU, memory, response time, cache hit ratio tracking
- **BuildKit Cache Optimization**: `--mount=type=cache` for faster builds
- **Multi-platform Support**: Native ARM64 and AMD64 builds
- **System Resource Monitoring**: psutil-based comprehensive monitoring

### **🚀 Modern Development Practices**
- **Modern Python Syntax**: Union types (`|`), pattern matching, enhanced error messages
- **Ultra-fast Tooling**: Ruff for lightning-fast linting and formatting
- **Comprehensive Type Safety**: Full type hints with future annotations
- **Advanced Security Scanning**: bandit, safety, semgrep, pip-audit integration
- **Property-based Testing**: Hypothesis for edge case discovery
- **OCI Compliance**: Full metadata labels and image signing support

## Requirements

- Python 3.10 or higher (latest version recommended)
- Package manager: `uv` (recommended) or `pip`
- Python packages listed in `pyproject.toml`

## Installation

### From PyPI

*Note: This package is not yet published to PyPI. Please install from source below.*

In the future, once published, you'll be able to install with:

```bash
pip install mcp-duckduckgo
```

### From Source

#### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager that provides better dependency resolution and faster installs.

1. Install uv if you haven't already:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Clone and install as a tool:
   ```bash
   git clone https://github.com/gianlucamazza/mcp-duckduckgo.git
   cd mcp-duckduckgo
   uv tool install .
   ```

   Or install directly from the repository:
   ```bash
   uv tool install git+https://github.com/gianlucamazza/mcp-duckduckgo.git
   ```

#### Using pip

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
mcp-duckduckgo --port 8000
```

Or use the provided script for development:

```bash
./scripts/run.sh
```

Or use Make:

```bash
make run
```

### Environment Variables

The MCP server can be configured using environment variables:

- `MCP_PORT`: Set the port number for the server (default: 3000)

Example usage:

```bash
# Set port via environment variable
export MCP_PORT=8080
mcp-duckduckgo

# Or set it inline
MCP_PORT=8080 mcp-duckduckgo
```

Note: The `--port` command-line argument takes precedence over the `MCP_PORT` environment variable.

### Using with Claude Code

1. Install the package from source as described above.

2. Configure Claude Code to use the plugin:

   ```bash
   claude mcp add duckduckgo-search -- mcp-duckduckgo
   ```

3. For global configuration (available in all projects):

   ```bash
   claude mcp add duckduckgo-search --scope user -- mcp-duckduckgo
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

### Tool: `duckduckgo_multi_hop_research`

Runs an orchestrated research workflow that chains search, detail fetching, and summarization:

- `query` (required): Research topic to investigate (max 400 characters)
- `count` (optional, default: 6): Number of initial search results to retrieve (1-15)
- `detail_count` (optional, default: 3): How many results to enrich with detailed scraping (1-6)
- `summary_length` (optional, default: 300): Maximum length of each generated summary (120-600 characters)
- `capture_snapshots` (optional, default: false): Persist HTML snapshots to the local sandbox for reproducible audits

Example usage in Claude Code:

```text
Run a multi-hop research workflow about "quantum networking" with 4 results and summaries up to 250 characters
```

## **🔥 New 2025 Features**

### Enhanced Security & Monitoring Tools

#### Tool: `health_check`

Get comprehensive server health status with enhanced security validation:

```text
Check server health status
```

Returns:
- Overall health status (healthy/degraded/unhealthy)
- Component-level health checks
- Resource usage indicators
- Security validation status

#### Tool: `get_performance_metrics`

Access detailed performance analytics:

```text
Show performance metrics and trends
```

Returns:
- Request statistics and success rates
- System resource usage (CPU, memory)
- Cache performance analytics
- Historical trend analysis

#### Tool: `get_server_info`

Get enhanced server information with security features:

```text
Show server information and capabilities
```

Returns:
- Server version and security features
- Uptime and configuration details
- Enabled monitoring capabilities
- 2025 compliance status

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

### Repository Layout

- `mcp_duckduckgo/search.py` – Core search flow, semantic cache integration, and reranking
- `mcp_duckduckgo/tools/` – Individual MCP tools including the new `research.py` orchestrator
- `mcp_duckduckgo/semantic_cache.py` – Freshness-aware caching layer with intent-specific TTLs
- `mcp_duckduckgo/knowledge_graph.py` & `enrichment.py` – Entity linking and graph construction utilities
- `mcp_duckduckgo/sandbox/` – Snapshot storage utilities for reproducible audits
- `mcp_duckduckgo/orchestration/` – Declarative multi-hop planning and execution engine
- `tests/` – Extensive unit, integration, and workflow coverage mirroring the modules above

## Enhanced Content Extraction

The DuckDuckGo plugin includes advanced content extraction capabilities that go beyond simple search results:

### Content Extraction Features

- **Full Webpage Analysis**: Extract and parse HTML content from search result URLs
- **Intelligent Content Targeting**: Identify and extract main content areas from different types of websites
- **Rich Metadata Extraction**: Extract titles, descriptions, authors, keywords, and publication dates
- **Image Detection**: Identify and extract main images and media from webpages
- **Social Media Integration**: Detect and extract links to social media profiles
- **Content Structure Analysis**: Extract headings and sections to understand webpage organization
- **Official Source Detection**: Identify whether a source is official based on domain and content signals

### Web Spidering Capabilities

The plugin includes basic web spidering functionality:

- **Configurable Depth**: Follow links from 0 to 3 levels deep from the original URL
- **Link Limitation**: Control the maximum number of links to follow per page (1-5)
- **Domain Restriction**: Option to only follow links within the same domain
- **Related Content Discovery**: Find and analyze content related to the original search

### Using Enhanced Content Extraction

To use the enhanced content extraction features:

```text
Get details for "https://example.com/article" with spider depth 1
```

To control spidering behavior:

```text
Get details for "https://example.com/article" with spider depth 2, max links 3, same domain only
```

## Knowledge Graph Enrichment

Detailed results now include a lightweight knowledge graph composed of the source domain and salient entities referenced in the page. Entity linking is performed locally with deterministic fallbacks, enabling downstream reasoning about relationships without relying on external APIs.

- Graphs are returned in the `knowledge_graph` field of `DetailedResult`
- Nodes include provenance metadata and confidence scores
- Edges express the relationship between the crawled domain and linked entities

Example:

```text
Get details for "https://example.gov/policy" with spider depth 0
```

You will receive a knowledge graph alongside the usual structured metadata, which can be fed into follow-up tools or external reasoning engines.

## Semantic Cache & Freshness Management

Search requests are served through an intent-aware semantic cache that accelerates repeated queries while respecting topical freshness:

- Cache keys blend query embeddings, pagination, filters, and related-search options
- Per-intent TTLs (e.g., 15 minutes for news, 24 hours for technical queries) automatically refresh stale entries
- Partial hits seamlessly merge with newly fetched results, preserving relevance while updating content
- Domain-level invalidation lets downstream workflows force-refresh when a site is known to have changed

Cache diagnostics are exposed in the `cache_metadata` field of search responses. To invalidate cache entries programmatically, call `semantic_cache.mark_domain_stale("example.com")` from custom extensions.

## Sandbox Snapshots & Auditing

Setting `capture_snapshots=true` in `duckduckgo_multi_hop_research` or `duckduckgo_get_details` stores HTML snapshots in a local sandbox ledger:

- Snapshots capture canonicalized previews and metadata for reproducibility
- Deterministic IDs allow diffing between runs via the `snapshot_store.diff()` helper
- The store is automatically pruned to maintain a bounded footprint

This is particularly useful when generating compliance reports or running long-lived research tasks that require auditable trails.

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

### Testing

The project includes a comprehensive test suite covering all major functionality. Tests are located in the `tests/` directory.

#### Installing Test Dependencies

Before running the tests, install the test dependencies:

```bash
pip install -e ".[test]"
```

#### Running Tests

You can run all tests with:

```bash
pytest
```

To run tests with coverage reporting:

```bash
pytest --cov=mcp_duckduckgo
```

To run a specific test file:

```bash
pytest tests/test_models.py
```

To run tests with verbose output:

```bash
pytest -v
```

Or use the provided script:

```bash
./scripts/test.sh
```

Or use Make:

```bash
make test
```

#### Test Structure

The test suite is organized as follows:

- `conftest.py` – Shared fixtures and cache/snapshot reset hooks
- `test_search.py` – Core search behavior and caching scenarios
- `test_tools.py` – Traditional MCP tool coverage
- `test_research_tool.py` – Multi-hop orchestration workflow
- `test_enrichment.py` – Knowledge graph enrichment pipeline
- `test_semantic_cache.py` – Semantic cache heuristics and eviction
- `test_knowledge_graph.py` – Entity linking behavior and graph structure
- `test_sandbox.py` – Snapshot store management and diffing
- `test_orchestration.py` – Orchestrator dependency resolution
- `test_integration.py` – End-to-end integration tests
- `test_utils_module.py` – Utilities and HTML extraction helpers

For more details about testing, see the [tests/README.md](tests/README.md) file.

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

[GitHub Repository](https://github.com/gianlucamazza/mcp-duckduckgo)
