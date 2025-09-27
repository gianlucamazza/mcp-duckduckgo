"""
Shared test fixtures and configurations for MCP DuckDuckGo plugin tests.
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from bs4 import BeautifulSoup
from mcp.server.fastmcp import Context

from mcp_duckduckgo.sandbox.snapshots import snapshot_store
from mcp_duckduckgo.semantic_cache import semantic_cache

# Sample HTML response for mocking DuckDuckGo search results
SAMPLE_SEARCH_HTML = """
<html>
<body>
    <table>
        <tr class="result-link">
            <td>
                <a href="https://example.com/page1">Example Page 1</a>
            </td>
        </tr>
        <tr class="result-snippet">
            <td>This is a description for Example Page 1</td>
        </tr>
        <tr class="result-link">
            <td>
                <a href="https://example.com/page2">Example Page 2</a>
            </td>
        </tr>
        <tr class="result-snippet">
            <td>This is a description for Example Page 2</td>
        </tr>
    </table>
    <table class="related-searches">
        <tr class="result-link--related">
            <td>
                <a href="https://duckduckgo.com/?q=Example+Topic+One">Example Topic One</a>
            </td>
        </tr>
        <tr class="result-link--related">
            <td>
                <a href="https://duckduckgo.com/?q=Example+Topic+Two">Example Topic Two</a>
            </td>
        </tr>
    </table>
</body>
</html>
"""

DETAIL_PAGE_HTML = """
<html>
<head>
    <title>Official Announcement</title>
    <meta name="description" content="An official announcement description.">
    <meta property="article:published_time" content="2024-01-01">
    <meta name="author" content="Agency">
    <meta name="keywords" content="policy, announcement, update">
    <meta property="og:image" content="https://example.gov/hero.png">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": "Official Announcement",
        "datePublished": "2024-01-01",
        "author": {
            "@type": "Organization",
            "name": "Agency"
        }
    }
    </script>
</head>
<body>
    <div id="content">
        <h1>Official Heading</h1>
        <h2>Supporting Heading</h2>
        <p>
            This announcement provides detailed information about a significant policy change.
            It includes relevant context and supporting statements to ensure clarity.
        </p>
        <a href="/press-release">Press Release</a>
        <a href="https://example.gov/resources">Additional Resources</a>
        <a href="https://twitter.com/example">Twitter</a>
    </div>
</body>
</html>
"""

UTILS_HTML = """
<html>
<head>
    <title>Official Documentation</title>
    <meta name="description" content="This page describes official procedures.">
    <meta name="author" content="Documentation Team">
    <meta name="keywords" content="alpha, beta, gamma">
    <meta property="article:published_time" content="2023-12-12">
    <meta property="og:description" content="Fallback description">
    <meta property="og:image" content="https://docs.example.com/main.png">
</head>
<body>
    <main class="content documentation">
        <h1>Main Doc Heading</h1>
        <h2>Subheading</h2>
        <article class="article">
            <p>This documentation paragraph contains sufficient detail to be captured by extractors.</p>
            <pre>print('hello world')</pre>
        </article>
        <div class="post">
            <p>Additional content paragraph that is also long enough to count as meaningful text.</p>
        </div>
        <a href="/internal">Internal Path</a>
        <a href="https://docs.example.com/guide">Docs Guide</a>
        <a href="https://twitter.com/docs">Twitter</a>
        <a href="javascript:void(0)">Skip</a>
    </main>
</body>
</html>
"""

# Sample search results for testing
SAMPLE_SEARCH_RESULTS = [
    {
        "title": "Example Page 1",
        "url": "https://example.com/page1",
        "description": "This is a policy announcement description for Example Page 1",
        "published_date": None,
        "domain": "example.com",
    },
    {
        "title": "Example Page 2",
        "url": "https://example.com/page2",
        "description": "This is a general description for Example Page 2",
        "published_date": None,
        "domain": "example.com",
    },
]


class MockResponse:
    """Mock for httpx.Response"""

    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Mock the raise_for_status method"""
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                message=f"HTTP Error {self.status_code}",
                request=httpx.Request("POST", "https://lite.duckduckgo.com/lite/"),
                response=self,
            )


class MockContext(MagicMock):
    """Mock for MCP Context"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.lifespan_context = {"http_client": AsyncMock()}

    async def report_progress(self, current: int, total: int) -> None:
        """Mock for report_progress method"""
        pass

    async def progress(self, message: str) -> None:
        """Mock for progress method"""
        pass

    async def error(self, message: str) -> None:
        """Mock for error method"""
        pass

    async def info(self, message: str) -> None:
        """Mock for info method"""
        pass


@pytest.fixture
def mock_context(mock_http_client: AsyncMock) -> MockContext:
    """Return a mock Context object with a prepared HTTP client."""
    context = MockContext()
    context.lifespan_context = {"http_client": mock_http_client}
    return context


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Return a mock AsyncClient"""
    client = AsyncMock()
    client.post = AsyncMock(return_value=MockResponse(SAMPLE_SEARCH_HTML))
    client.get = AsyncMock(return_value=MockResponse(DETAIL_PAGE_HTML))
    client.aclose = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    return client


@pytest.fixture(autouse=True)
def reset_semantic_cache() -> None:
    """Ensure the semantic cache is cleared between tests."""

    semantic_cache.clear()
    yield
    semantic_cache.clear()


@pytest.fixture(autouse=True)
def reset_snapshot_store() -> None:
    """Ensure snapshot store does not leak between tests."""

    snapshot_store.clear()
    yield
    snapshot_store.clear()


@pytest.fixture
def sample_search_params() -> dict[str, Any]:
    """Return sample search parameters"""
    return {
        "query": "test query",
        "count": 2,
        "page": 1,
        "site": None,
        "time_period": None,
    }


@pytest.fixture
def sample_search_results() -> list[dict[str, Any]]:
    """Return sample search results"""
    return SAMPLE_SEARCH_RESULTS


@pytest.fixture
def sample_soup() -> BeautifulSoup:
    """Return a BeautifulSoup object with sample HTML"""
    return BeautifulSoup(SAMPLE_SEARCH_HTML, "html.parser")


@pytest.fixture
def utils_soup() -> BeautifulSoup:
    """Return a BeautifulSoup object with utility-focused HTML."""
    return BeautifulSoup(UTILS_HTML, "html.parser")


@pytest.fixture
def mock_search_function() -> Callable[[dict[str, Any], Context], dict[str, Any]]:
    """Mock for the duckduckgo_search function"""

    async def mock_search(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
        return {
            "results": SAMPLE_SEARCH_RESULTS,
            "total_results": len(SAMPLE_SEARCH_RESULTS),
            "related_searches": ["Example Topic One", "Example Topic Two"],
        }

    return mock_search


@pytest.fixture
def detail_soup() -> BeautifulSoup:
    """Return a BeautifulSoup object with detail HTML."""
    return BeautifulSoup(DETAIL_PAGE_HTML, "html.parser")
