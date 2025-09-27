"""
Tests for the DuckDuckGo search functionality.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
from bs4 import BeautifulSoup

from mcp_duckduckgo import search as search_module
from mcp_duckduckgo.http import get_http_client
from mcp_duckduckgo.intent import detect_query_intent
from mcp_duckduckgo.search import DuckDuckGoSearchError, duckduckgo_search, extract_domain


class TestExtractDomain:
    """Tests for the extract_domain function."""

    def test_extract_domain_valid_url(self):
        """Test that extract_domain works with valid URLs."""
        url = "https://example.com/page?query=test"
        domain = extract_domain(url)
        assert domain == "example.com"

    def test_extract_domain_with_subdomain(self):
        """Test extract_domain with subdomains."""
        url = "https://blog.example.com/article"
        domain = extract_domain(url)
        assert domain == "blog.example.com"

    def test_extract_domain_invalid_url(self):
        """Test extract_domain with invalid URLs."""
        url = "not a url"
        domain = extract_domain(url)
        assert domain == ""

    def test_extract_domain_empty_string(self):
        """Test extract_domain with empty string."""
        url = ""
        domain = extract_domain(url)
        assert domain == ""


class TestDuckDuckGoSearch:
    """Tests for the duckduckgo_search function."""

    @pytest.mark.asyncio
    async def test_basic_search(
        self, mock_context, mock_http_client, sample_search_params
    ):
        """Test a basic search with mocked response."""
        # Set up the mock client in the context
        mock_context.lifespan_context["http_client"] = mock_http_client

        # Run the search function
        result = await duckduckgo_search(sample_search_params, mock_context)

        # Verify the result structure
        assert "results" in result
        assert "total_results" in result
        assert isinstance(result["results"], list)
        assert isinstance(result["total_results"], int)

        # Verify that the HTTP client was called correctly
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert call_args[0][0] == "https://lite.duckduckgo.com/lite/"
        assert "data" in call_args[1]
        assert call_args[1]["data"]["q"] == sample_search_params["query"]

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, mock_context, mock_http_client):
        """Test search with pagination parameters."""
        # Set up the mock client in the context
        mock_context.lifespan_context["http_client"] = mock_http_client

        # Set up the search parameters with pagination
        search_params = {"query": "test query", "count": 5, "offset": 10, "page": 3}

        # Run the search function
        await duckduckgo_search(search_params, mock_context)

        # Verify that the HTTP client was called with the right offset
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert call_args[1]["data"]["s"] == 10  # Check the offset was passed

    @pytest.mark.asyncio
    async def test_search_without_context_client(self, mock_context):
        """Test search without a client in the context."""
        # Set up context without http_client
        mock_context.lifespan_context = {}

        # Set up a mock for httpx.AsyncClient to be used in the function
        mock_client = AsyncMock()
        mock_client.post.return_value = MagicMock(
            text="""
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
                </table>
            </body>
            </html>
            """,
            status_code=200,
            raise_for_status=MagicMock(),
        )

        # Mock the AsyncClient constructor
        with patch("httpx.AsyncClient", return_value=mock_client):
            # Run the search function
            search_params = {"query": "test query"}
            result = await duckduckgo_search(search_params, mock_context)

            # Verify the client was created and used
            mock_client.post.assert_called_once()
            assert mock_context.lifespan_context["http_client"] is mock_client
            mock_client.aclose.assert_not_called()

            # Verify results
            assert "results" in result
            assert len(result["results"]) > 0

    @pytest.mark.asyncio
    async def test_search_with_no_results(self, mock_context, mock_http_client):
        """Test search with no results."""
        # Set up the mock client to return a response with no results
        empty_html = "<html><body><table></table></body></html>"
        mock_http_client.post.return_value = MagicMock(
            text=empty_html, status_code=200, raise_for_status=MagicMock()
        )
        mock_context.lifespan_context["http_client"] = mock_http_client

        # Run the search function
        search_params = {"query": "nonexistent query"}
        result = await duckduckgo_search(search_params, mock_context)

        # Verify empty results
        assert "results" in result
        assert len(result["results"]) == 0

    @pytest.mark.asyncio
    async def test_search_with_http_error(self, mock_context, mock_http_client):
        """Test search with HTTP error."""
        # Set up the mock client to raise an HTTP error
        mock_http_client.post.return_value = MagicMock(
            status_code=404,
            raise_for_status=MagicMock(
                side_effect=httpx.HTTPStatusError(
                    message="404 Not Found",
                    request=MagicMock(),
                    response=MagicMock(status_code=404),
                )
            ),
        )
        mock_context.lifespan_context["http_client"] = mock_http_client

        # Run the search function and expect an exception
        search_params = {"query": "test query"}
        with pytest.raises(DuckDuckGoSearchError) as excinfo:
            await duckduckgo_search(search_params, mock_context)

        assert "DuckDuckGo returned HTTP status" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_search_with_request_error(self, mock_context, mock_http_client):
        """Test search with request error."""
        # Set up the mock client to raise a request error
        mock_http_client.post.side_effect = httpx.RequestError(
            "Connection error", request=MagicMock()
        )
        mock_context.lifespan_context["http_client"] = mock_http_client

        # Run the search function and expect an exception
        search_params = {"query": "test query"}
        with pytest.raises(DuckDuckGoSearchError) as excinfo:
            await duckduckgo_search(search_params, mock_context)

        assert "Failed to reach DuckDuckGo" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_search_with_fallback_parsing(self, mock_context, mock_http_client):
        """Test search with fallback HTML parsing approach."""
        # HTML without the expected structure but with links
        fallback_html = """
        <html>
        <body>
            <div>
                <a href="https://example.com/fallback">Fallback Result</a>
                <p>This is a fallback description</p>
            </div>
        </body>
        </html>
        """
        mock_http_client.post.return_value = MagicMock(
            text=fallback_html, status_code=200, raise_for_status=MagicMock()
        )
        mock_context.lifespan_context["http_client"] = mock_http_client

        # Run the search function
        search_params = {"query": "test query"}
        result = await duckduckgo_search(search_params, mock_context)

        # Verify results using fallback mechanism
        assert "results" in result
        assert len(result["results"]) > 0
        # The fallback should have found the link
        found_url = False
        for item in result["results"]:
            if item["url"] == "https://example.com/fallback":
                found_url = True
                break
        assert found_url, "Fallback parsing didn't find the expected URL"

    @pytest.mark.asyncio
    async def test_missing_query_parameter(self, mock_context):
        """Test that an error is raised when query parameter is missing."""
        # Run the search function without a query
        search_params = {}
        with pytest.raises(ValueError) as excinfo:
            await duckduckgo_search(search_params, mock_context)

        assert "Query parameter is required" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_progress_reporting(
        self, mock_context, mock_http_client, sample_search_params
    ):
        """Test that progress is reported correctly."""
        # Set up the context with report_progress method
        mock_context.report_progress = AsyncMock()
        mock_context.lifespan_context["http_client"] = mock_http_client

        # Run the search function
        await duckduckgo_search(sample_search_params, mock_context)

        # Verify that report_progress was called at least once
        assert mock_context.report_progress.called

    @pytest.mark.asyncio
    async def test_info_reporting(
        self, mock_context, mock_http_client, sample_search_params
    ):
        """Test that info is reported correctly."""
        # Set up the context with info method
        mock_context.info = AsyncMock()
        mock_context.lifespan_context["http_client"] = mock_http_client

        # Run the search function
        await duckduckgo_search(sample_search_params, mock_context)

        # Verify that info was called at least once
        assert mock_context.info.called

    @pytest.mark.asyncio
    async def test_search_extracts_related_queries(
        self, mock_context, mock_http_client
    ):
        """Ensure related searches are captured when requested."""

        mock_context.lifespan_context["http_client"] = mock_http_client

        search_params = {"query": "test query", "count": 5, "get_related": True}
        result = await duckduckgo_search(search_params, mock_context)

        assert result.get("related_searches") == [
            "Example Topic One",
            "Example Topic Two",
        ]

    @pytest.mark.asyncio
    async def test_unexpected_error_wraps_in_duckduckgo_error(
        self, mock_context, mock_http_client
    ):
        mock_context.lifespan_context["http_client"] = mock_http_client

        with patch("mcp_duckduckgo.search.BeautifulSoup", side_effect=RuntimeError("parse")):
            with pytest.raises(search_module.DuckDuckGoSearchError):
                await duckduckgo_search({"query": "trigger"}, mock_context)


    def test_internal_helper_functions(self, mock_context):
        node = Mock()
        node.text = "  helper  "
        other = Mock()
        other.text = "   "
        values = search_module._ensure_iterable_text([node, other])
        assert values == ["helper"]

        soup = BeautifulSoup(
            """
            <table class="related-searches">
                <tr><td><a>Alpha Topic</a></td></tr>
            </table>
            """,
            "html.parser",
        )
        extracted = search_module._extract_related_queries(soup)
        assert extracted == ["Alpha Topic"]

        client, should_close = get_http_client(mock_context, timeout=10.0)
        assert client is mock_context.lifespan_context["http_client"]
        assert should_close is False

        class DummyContext:
            pass

        new_client = AsyncMock()
        with patch("httpx.AsyncClient", return_value=new_client):
            client2, should_close2 = get_http_client(DummyContext(), timeout=10.0)
        assert client2 is new_client
        assert should_close2 is True

    def test_detect_query_intent_news(self):
        intent, confidence = detect_query_intent("latest breaking news on ai")
        assert intent == "news"
        assert confidence > 0

    def test_detect_query_intent_technical(self):
        intent, confidence = detect_query_intent("python api documentation errors")
        assert intent == "technical"
        assert confidence > 0

    @pytest.mark.asyncio
    async def test_rerank_results_prioritises_overlap(self, mock_context, mock_http_client):
        mock_context.lifespan_context["http_client"] = mock_http_client

        search_params = {"query": "policy announcement", "count": 5}
        payload = await duckduckgo_search(search_params, mock_context)

        titles = [item["title"] for item in payload["results"]]
        assert titles[0] == "Example Page 1"

    @pytest.mark.asyncio
    async def test_semantic_cache_hit_returns_without_http_call(
        self, mock_context, mock_http_client
    ):
        mock_context.lifespan_context["http_client"] = mock_http_client

        params = {"query": "cached query", "count": 5}
        await duckduckgo_search(params, mock_context)
        assert mock_http_client.post.call_count == 1

        payload = await duckduckgo_search(params, mock_context)
        assert mock_http_client.post.call_count == 1
        assert payload["cache_metadata"]["status"] == "hit"
        assert "age_seconds" in payload["cache_metadata"]
