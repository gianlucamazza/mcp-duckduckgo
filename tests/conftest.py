"""
Shared test fixtures and configurations for MCP DuckDuckGo plugin tests.
"""

from typing import Any, Callable, Dict, List
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from bs4 import BeautifulSoup
from mcp.server.fastmcp import Context

# Sample HTML response for mocking DuckDuckGo search results
SAMPLE_HTML = """
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
</body>
</html>
"""

# Sample search results for testing
SAMPLE_SEARCH_RESULTS = [
    {
        "title": "Example Page 1",
        "url": "https://example.com/page1",
        "description": "This is a description for Example Page 1",
        "published_date": None,
        "domain": "example.com",
    },
    {
        "title": "Example Page 2",
        "url": "https://example.com/page2",
        "description": "This is a description for Example Page 2",
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
                response=self,  # type: ignore[arg-type]
            )


class MockContext(MagicMock):
    """Mock for MCP Context"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.lifespan_context = {"http_client": AsyncMock()}

    async def report_progress(self, current: int, total: int) -> None:
        """Mock for report_progress method"""
        pass

    async def error(self, message: str) -> None:
        """Mock for error method"""
        pass

    async def info(self, message: str) -> None:
        """Mock for info method"""
        pass


@pytest.fixture
def mock_context() -> MockContext:
    """Return a mock Context object"""
    return MockContext()


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Return a mock AsyncClient"""
    client = AsyncMock()
    client.post = AsyncMock(return_value=MockResponse(SAMPLE_HTML))
    client.get = AsyncMock(return_value=MockResponse(SAMPLE_HTML))
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def sample_search_params() -> Dict[str, Any]:
    """Return sample search parameters"""
    return {
        "query": "test query",
        "count": 2,
        "page": 1,
        "site": None,
        "time_period": None,
    }


@pytest.fixture
def sample_search_results() -> List[Dict[str, Any]]:
    """Return sample search results"""
    return SAMPLE_SEARCH_RESULTS


@pytest.fixture
def sample_soup() -> BeautifulSoup:
    """Return a BeautifulSoup object with sample HTML"""
    return BeautifulSoup(SAMPLE_HTML, "html.parser")


@pytest.fixture
def mock_search_function() -> Callable[[Dict[str, Any], Context], Dict[str, Any]]:
    """Mock for the duckduckgo_search function"""

    async def mock_search(params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
        return {
            "results": SAMPLE_SEARCH_RESULTS,
            "total_results": len(SAMPLE_SEARCH_RESULTS),
        }

    return mock_search  # type: ignore[return-value]
