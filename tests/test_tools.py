"""
Tests for the DuckDuckGo search tools.

These tests verify that the MCP tools for DuckDuckGo search work correctly.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_duckduckgo.models import DetailedResult, SearchResponse
from mcp_duckduckgo.sandbox.snapshots import snapshot_store
from mcp_duckduckgo.search import DuckDuckGoSearchError

# Import the tools module containing the MCP tools
from mcp_duckduckgo.tools import (
    duckduckgo_get_details,
    duckduckgo_related_searches,
    duckduckgo_web_search,
    summarize_webpage,
)


@pytest.mark.asyncio
async def test_duckduckgo_web_search(mock_context, mock_search_function):
    """Test the duckduckgo_web_search tool."""
    # Mock the search function
    with patch("mcp_duckduckgo.tools.search.duckduckgo_search", mock_search_function):
        # Call the tool
        result = await duckduckgo_web_search(
            query="test query",
            count=5,
            page=1,
            site=None,
            time_period=None,
            ctx=mock_context,
        )

        # Verify the result
        assert isinstance(result, SearchResponse)
        assert len(result.results) == 2  # Based on the sample data in conftest.py
        assert result.total_results == 2
        assert result.page == 1
        assert result.intent == "general"
        assert result.intent_confidence == 0.0

        # Check the first result
        first_result = result.results[0]
        assert first_result.title == "Example Page 1"
        assert first_result.url == "https://example.com/page1"
        assert (
            first_result.description
            == "This is a policy announcement description for Example Page 1"
        )
        # Domain is included in result dict but not as a property in SearchResult model
        # assert first_result.domain == "example.com"


@pytest.mark.asyncio
async def test_duckduckgo_web_search_with_site_filter(
    mock_context, mock_search_function
):
    """Test the duckduckgo_web_search tool with site filter."""
    # Mock the search function to capture params
    mock_search_params = None

    async def capture_params(params, ctx):
        nonlocal mock_search_params
        mock_search_params = params
        return await mock_search_function(params, ctx)

    with patch("mcp_duckduckgo.tools.search.duckduckgo_search", capture_params):
        # Call the tool with site filter
        await duckduckgo_web_search(
            query="test query",
            count=5,
            page=1,
            site="example.com",
            time_period=None,
            ctx=mock_context,
        )

        # Verify that site filter was correctly applied to the query
        assert mock_search_params is not None
        assert mock_search_params["query"] == "test query site:example.com"
        assert mock_search_params["intent"] == "general"


@pytest.mark.asyncio
async def test_duckduckgo_web_search_with_time_filter(
    mock_context, mock_search_function
):
    """Test the duckduckgo_web_search tool with time filter."""
    # Mock the search function to capture params
    mock_search_params = None

    async def capture_params(params, ctx):
        nonlocal mock_search_params
        mock_search_params = params
        return await mock_search_function(params, ctx)

    with patch("mcp_duckduckgo.tools.search.duckduckgo_search", capture_params):
        # Call the tool with time filter
        await duckduckgo_web_search(
            query="test query",
            count=5,
            page=1,
            site=None,
            time_period="week",
            ctx=mock_context,
        )

        # Verify that time filter was correctly applied
        assert mock_search_params is not None
        assert "date:w" in mock_search_params["query"]
        assert mock_search_params["intent"] == "general"


@pytest.mark.asyncio
async def test_duckduckgo_web_search_pagination(mock_context, mock_search_function):
    """Test the duckduckgo_web_search tool with pagination."""
    # Mock the search function to capture params
    mock_search_params = None

    async def capture_params(params, ctx):
        nonlocal mock_search_params
        mock_search_params = params
        return await mock_search_function(params, ctx)

    with patch("mcp_duckduckgo.tools.search.duckduckgo_search", capture_params):
        # Call the tool with pagination
        await duckduckgo_web_search(
            query="test query",
            count=5,
            page=3,  # Page 3
            site=None,
            time_period=None,
            ctx=mock_context,
        )

        # Verify that pagination was correctly applied
        assert mock_search_params is not None
        assert mock_search_params["offset"] == 10  # (page-1) * count
        assert mock_search_params["intent"] == "general"


@pytest.mark.asyncio
async def test_duckduckgo_web_search_error_handling(mock_context):
    """Test error handling in the duckduckgo_web_search tool."""

    # Mock the search function to raise an exception
    async def mock_error(*args, **kwargs):
        raise ValueError("Test error")

    # Mock the error reporting method
    mock_context.error = AsyncMock()

    with patch("mcp_duckduckgo.tools.search.duckduckgo_search", mock_error):
        with pytest.raises(DuckDuckGoSearchError):
            await duckduckgo_web_search(
                query="test query",
                count=5,
                page=1,
                site=None,
                time_period=None,
                ctx=mock_context,
            )

    assert mock_context.error.called


@pytest.mark.asyncio
async def test_duckduckgo_get_details(mock_context, mock_http_client):
    """Test the duckduckgo_get_details tool."""

    with patch(
        "mcp_duckduckgo.tools.search.httpx.AsyncClient", return_value=mock_http_client
    ):
        url = "https://example.gov/page"
        mock_context.progress = AsyncMock()
        result = await duckduckgo_get_details(
            url=url,
            spider_depth=0,
            max_links_per_page=3,
            same_domain_only=True,
            ctx=mock_context,
        )

    assert isinstance(result, DetailedResult)
    assert result.url == url
    assert result.domain == "example.gov"
    assert result.is_official is True
    assert result.description == "An official announcement description."
    assert result.content_snippet and "policy change" in result.content_snippet
    assert result.headings and "Official Heading" in result.headings[0]
    assert result.related_links == [
        "https://example.gov/press-release",
        "https://example.gov/resources",
    ]
    assert (
        result.social_links
        and result.social_links.get("twitter") == "https://twitter.com/example"
    )
    assert result.structured_data and "json_ld" in result.structured_data
    assert result.entities and "Official" in result.entities
    assert result.knowledge_graph is not None
    assert result.knowledge_graph.nodes
    mock_context.progress.assert_awaited()


@pytest.mark.asyncio
async def test_duckduckgo_get_details_with_snapshot(mock_context, mock_http_client):
    """Ensure snapshots are captured when requested."""

    snapshot_store.clear()

    with patch(
        "mcp_duckduckgo.tools.search.httpx.AsyncClient", return_value=mock_http_client
    ):
        url = "https://example.gov/page"
        await duckduckgo_get_details(
            url=url,
            spider_depth=0,
            max_links_per_page=3,
            same_domain_only=True,
            ctx=mock_context,
            capture_snapshot=True,
        )

    snapshots = snapshot_store.list_snapshots()
    assert snapshots
    assert snapshots[0].url == url


@pytest.mark.asyncio
async def test_duckduckgo_related_searches(mock_context):
    """Test the duckduckgo_related_searches tool extracts related queries."""

    related_payload = {
        "results": [],
        "total_results": 0,
        "related_searches": ["Result One", "result one", "Result Two", "  "],
    }

    mock_search = AsyncMock(return_value=related_payload)

    with patch("mcp_duckduckgo.tools.search.duckduckgo_search", mock_search):
        result = await duckduckgo_related_searches(
            query="test query", count=3, ctx=mock_context
        )

    assert result == ["Result One", "Result Two"]
    assert mock_search.call_count == 1
    params = mock_search.call_args[0][0]
    assert params["get_related"] is True
    assert params["count"] == 3


@pytest.mark.asyncio
async def test_duckduckgo_related_searches_handles_missing_data(mock_context):
    """Related searches should return empty list when none are provided."""

    mock_search = AsyncMock(return_value={"results": [], "total_results": 0})

    with patch("mcp_duckduckgo.tools.search.duckduckgo_search", mock_search):
        result = await duckduckgo_related_searches(
            query="test query", count=5, ctx=mock_context
        )

    assert result == []


@pytest.mark.asyncio
async def test_summarize_webpage_streams_progress(mock_context):
    html = """
    <html>
        <head><title>Streaming Test</title></head>
        <body>
            <div id="content">
                <p>This is the first paragraph providing ample detail for streaming behaviour to engage properly.</p>
                <p>This is the second paragraph that continues the narrative and offers additional context for bullet creation.</p>
                <p>This is the third paragraph ensuring that multiple updates are dispatched to the client.</p>
            </div>
        </body>
    </html>
    """

    class Response:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    client = AsyncMock()
    client.get.return_value = Response(html)
    client.aclose = AsyncMock()

    mock_context.progress = AsyncMock()
    mock_context.report_progress = AsyncMock()

    with patch("mcp_duckduckgo.http.get_http_client", return_value=(client, True)):
        result = await summarize_webpage(
            url="https://example.com/stream", max_length=200, ctx=mock_context
        )

    assert mock_context.progress.await_count >= 3
    mock_context.report_progress.assert_awaited()
    assert result.get("summary")
