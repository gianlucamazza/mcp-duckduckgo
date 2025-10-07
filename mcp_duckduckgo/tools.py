"""
Working MCP tools implementation for DuckDuckGo search.
"""

import logging
from typing import Any, Dict, List

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from .search import extract_domain, search_web

logger = logging.getLogger(__name__)


async def get_autocomplete_suggestions(
    query: str, http_client: httpx.AsyncClient
) -> List[str]:
    """Get search suggestions from DuckDuckGo autocomplete API."""
    try:
        url = "https://duckduckgo.com/ac/"
        params = {"q": query, "type": "list"}

        response = await http_client.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        # Response format: ["query", ["suggestion1", "suggestion2", ...]]
        suggestions = data[1] if len(data) > 1 and isinstance(data[1], list) else []

        logger.info("Found %d autocomplete suggestions", len(suggestions))
        return suggestions

    except (httpx.RequestError, httpx.HTTPError, ValueError) as e:
        logger.error("Failed to get autocomplete suggestions: %s", e)
        return []


def register_search_tools(mcp_server: FastMCP) -> None:
    """Register all search tools with the MCP server."""

    @mcp_server.tool()
    async def web_search(
        query: str = Field(..., description="Search query", max_length=400),
        max_results: int = Field(
            10, description="Maximum number of results to return (1-20)", ge=1, le=20
        ),
        ctx: Context = Field(default_factory=Context),
    ) -> Dict[str, Any]:
        """
        Search the web using DuckDuckGo.

        Returns a list of search results with titles, URLs, descriptions, and domains.
        """
        logger.info("Searching for: '%s' (max %d results)", query, max_results)

        try:
            # Get HTTP client from context
            http_client = None
            close_client = False

            # Try to get HTTP client from lifespan context
            if (
                hasattr(ctx, "lifespan_context")
                and ctx.lifespan_context
                and "http_client" in ctx.lifespan_context
            ):
                logger.info("Using HTTP client from lifespan context")
                http_client = ctx.lifespan_context["http_client"]
            else:
                # Create a new HTTP client
                logger.info("Creating new HTTP client")
                http_client = httpx.AsyncClient(timeout=10.0)
                close_client = True

            try:
                # Perform the search
                results = await search_web(query, http_client, max_results)

                # Convert to dict format
                search_results = [
                    {
                        "title": result.title,
                        "url": result.url,
                        "description": result.description,
                        "domain": result.domain,
                    }
                    for result in results
                ]

                return {
                    "query": query,
                    "results": search_results,
                    "total_results": len(search_results),
                    "status": "success",
                }

            finally:
                if close_client:
                    await http_client.aclose()

        except (httpx.RequestError, httpx.HTTPError, ValueError) as e:
            logger.error("Search failed: %s", e)
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "status": "error",
                "error": str(e),
            }

    @mcp_server.tool()
    async def get_page_content(
        url: str = Field(..., description="URL to fetch content from"),
        ctx: Context = Field(default_factory=Context),
    ) -> Dict[str, Any]:
        """
        Fetch and extract content from a web page.

        Returns the page title, description, and main content.
        """
        logger.info("Fetching content from: %s", url)

        try:
            # Get HTTP client from context
            http_client = getattr(ctx, "http_client", None)
            if not http_client:
                http_client = httpx.AsyncClient(timeout=15.0)
                close_client = True
            else:
                close_client = False

            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }

                response = await http_client.get(url, headers=headers, timeout=15)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Extract title
                title = ""
                title_tag = soup.find("title")
                if title_tag:
                    title = title_tag.get_text().strip()

                # Extract description from meta tags
                description = ""
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc:
                    description = meta_desc.get("content", "").strip()  # type: ignore[union-attr]

                # Extract main content (try common content selectors)
                content_text = ""
                content_selectors = [
                    "main article",
                    "article",
                    '[role="main"]',
                    ".content",
                    ".article-content",
                    ".post-content",
                    "#content",
                    "#article",
                    ".entry-content",
                ]

                for selector in content_selectors:
                    main_content = soup.select_one(selector)
                    if main_content:
                        content_text = main_content.get_text().strip()
                        break

                # If no content found, get all paragraphs
                if not content_text:
                    paragraphs = soup.find_all("p")[:5]  # First 5 paragraphs
                    content_text = "\n\n".join(p.get_text().strip() for p in paragraphs)

                # Clean up content (first 500 chars for preview)
                content_preview = (
                    content_text[:500] + "..."
                    if len(content_text) > 500
                    else content_text
                )

                return {
                    "url": url,
                    "title": title,
                    "description": description,
                    "content": content_text,
                    "content_preview": content_preview,
                    "domain": extract_domain(url),
                    "status": "success",
                }

            finally:
                if close_client:
                    await http_client.aclose()

        except Exception as e:
            logger.error("Failed to fetch content from %s: %s", url, e)
            return {
                "url": url,
                "title": "",
                "description": "",
                "content": "",
                "content_preview": f"Error: {str(e)}",
                "domain": extract_domain(url),
                "status": "error",
                "error": str(e),
            }

    @mcp_server.tool()
    async def suggest_related_searches(
        query: str = Field(..., description="Original search query"),
        max_suggestions: int = Field(
            5,
            ge=1,
            le=10,
            description="Maximum number of related suggestions to return",
        ),
        ctx: Context = Field(default_factory=Context),
    ) -> Dict[str, Any]:
        """
        Get search suggestions from DuckDuckGo autocomplete API.

        Returns suggestions based on what people actually search for.
        """
        logger.info(
            "Getting autocomplete suggestions for: '%s' (max %d suggestions)",
            query,
            max_suggestions,
        )

        # Get HTTP client from context
        http_client = None
        close_client = False

        try:
            if (
                hasattr(ctx, "lifespan_context")
                and ctx.lifespan_context
                and "http_client" in ctx.lifespan_context
            ):
                logger.info("Using HTTP client from lifespan context")
                http_client = ctx.lifespan_context["http_client"]
            else:
                logger.info("Creating new HTTP client")
                http_client = httpx.AsyncClient(timeout=10.0)
                close_client = True

            # Get autocomplete suggestions from DuckDuckGo
            suggestions = await get_autocomplete_suggestions(query, http_client)

            return {
                "original_query": query,
                "related_searches": suggestions[:max_suggestions],
                "count": len(suggestions[:max_suggestions]),
            }

        except (httpx.RequestError, httpx.HTTPError, ValueError) as e:
            logger.error("Failed to get autocomplete suggestions: %s", e)
            return {
                "original_query": query,
                "related_searches": [],
                "count": 0,
                "error": str(e),
            }
        finally:
            if close_client and http_client:
                await http_client.aclose()
