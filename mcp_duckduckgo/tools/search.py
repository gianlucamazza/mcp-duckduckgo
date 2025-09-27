"""
Search tools for the DuckDuckGo search plugin.
"""

import logging
import traceback
from typing import cast, Optional, List

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field

from ..enrichment import build_knowledge_graph
from ..intent import detect_query_intent
from ..models import DetailedResult, SearchResponse, SearchResult
from ..sandbox.snapshots import snapshot_store
from ..search import DuckDuckGoSearchError, duckduckgo_search, extract_domain
from ..server import mcp

# Import helper functions from the utils module
from .utils import (
    extract_author,
    extract_entities,
    extract_keywords,
    extract_main_image,
    extract_metadata,
    extract_related_links,
    extract_social_links,
    extract_structured_data,
    extract_targeted_content,
    spider_links,
)

# Configure logging
logger = logging.getLogger("mcp_duckduckgo.tools.search")


@mcp.tool()  # pragma: no cover
async def duckduckgo_web_search(  # vulture: ignore
    query: str = Field(
        ...,
        description="Search query (max 400 chars, 50 words)",
        max_length=400,
    ),
    count: int = Field(
        default=10,
        description="Number of results per page (1-20, default 10)",
        ge=1,
        le=20,
    ),
    page: int = Field(
        default=1,
        description="Page number (default 1)",
        ge=1,
    ),
    site: str | None = Field(
        default=None,
        description="Limit results to a specific site (e.g., 'site:example.com')",
    ),
    time_period: str | None = Field(
        default=None,
        description="Time period for results ('day', 'week', 'month', 'year')",
    ),
    *,
    ctx: Context,  # Context is automatically injected by MCP
) -> SearchResponse:
    """
    Perform a web search using the DuckDuckGo search engine.

    This tool searches the web using DuckDuckGo and returns relevant results.
    It's ideal for finding current information, news, articles, and general web content.

    Args:
        query: The search query (max 400 chars, 50 words)
        count: Number of results per page (1-20, default 10)
        page: Page number for pagination (default 1)
        site: Limit results to a specific site (e.g., 'site:example.com')
        time_period: Filter results by time period ('day', 'week', 'month', 'year')
        ctx: MCP context object (automatically injected)

    Returns:
        A SearchResponse object containing search results and pagination metadata

    Example:
        duckduckgo_web_search(query="latest AI developments", count=5, page=1)
    """
    try:
        logger.info(
            f"duckduckgo_web_search called with query: {query}, count: {count}, page: {page}"
        )

        # Enhance query with site limitation if provided
        if site:
            # Check if site is a string before using it
            if isinstance(site, str) and "site:" not in query:
                query = f"{query} site:{site}"

        # Enhance query with time period if provided
        if time_period:
            # Map time_period to DuckDuckGo format
            time_map = {"day": "d", "week": "w", "month": "m", "year": "y"}
            # Check if time_period is a string before calling lower()
            if isinstance(time_period, str) and time_period.lower() in time_map:
                query = f"{query} date:{time_map[time_period.lower()]}"

        # Log the context to help with debugging
        if ctx:
            logger.debug(f"Context available: {ctx}")
        else:
            logger.error("Context is None!")

            # Create a minimal context if none is provided
            class MinimalContext(BaseModel):
                pass

            ctx = MinimalContext()

        # Calculate offset from page number
        offset = (page - 1) * count

        intent, intent_confidence = detect_query_intent(query)

        result = await duckduckgo_search(
            {
                "query": query,
                "count": count,
                "offset": offset,
                "page": page,
                "intent": intent,
            },
            ctx,
        )

        logger.debug(f"duckduckgo_search returned: {result}")

        # Convert the result to a SearchResponse object
        search_results = []
        for item in result["results"]:
            try:
                search_result = SearchResult(
                    title=item["title"],
                    url=item["url"],
                    description=item["description"],
                    published_date=item.get("published_date"),
                )
                search_results.append(search_result)
            except Exception as e:
                logger.error(f"Error creating SearchResult: {e}, item: {item}")
                if hasattr(ctx, "error"):
                    await ctx.error(f"Error creating SearchResult: {e}, item: {item}")

        # Calculate pagination metadata
        total_results = result["total_results"]
        total_pages = (total_results + count - 1) // count if total_results > 0 else 1
        has_next = page < total_pages
        has_previous = page > 1

        response = SearchResponse(
            results=search_results,
            total_results=total_results,
            page=page,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous,
            intent=intent,
            intent_confidence=intent_confidence,
        )

        logger.debug(f"Returning SearchResponse: {response}")
        return response

    except DuckDuckGoSearchError:
        raise
    except Exception as e:
        error_msg = f"Error in duckduckgo_web_search: {e!s}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        if hasattr(ctx, "error"):
            await ctx.error(error_msg)
        raise DuckDuckGoSearchError(error_msg) from e


@mcp.tool()  # pragma: no cover
async def duckduckgo_get_details(
    url: str,
    spider_depth: int = Field(
        0,
        ge=0,
        le=3,
        description="Number of links to follow from the page (0-3, default 0)",
    ),
    max_links_per_page: int = Field(
        3,
        ge=1,
        le=5,
        description="Maximum number of links to follow per page (1-5, default 3)",
    ),
    same_domain_only: bool = Field(
        True, description="Only follow links to the same domain"
    ),
    capture_snapshot: bool = Field(
        False,
        description="Persist a sandbox snapshot of the fetched page",
    ),
    *,
    ctx: Context,
) -> DetailedResult:
    """
    Get detailed information about a search result.

    This tool retrieves additional details about a search result,
    such as the domain, title, description, and content snippet
    by fetching and parsing the actual web page. It can also
    follow links to gather more comprehensive content.

    Args:
        url: The URL of the result to get details for
        spider_depth: Number of links to follow (0-3, default 0)
        max_links_per_page: Maximum number of links to follow per page (1-5, default 3)
        same_domain_only: Only follow links to the same domain
        ctx: MCP context object (automatically injected)

    Returns:
        A DetailedResult object with additional information

    Example:
        duckduckgo_get_details(url="https://example.com/article", spider_depth=1)
    """
    logger.info(
        f"duckduckgo_get_details called with URL: {url}, spider_depth: {spider_depth}"
    )

    # Extract domain from the URL
    domain = extract_domain(url)

    try:
        # Create an HTTP client for fetching pages
        async with httpx.AsyncClient(
            timeout=10.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            },
            follow_redirects=True,
        ) as client:
            # Fetch the requested URL
            if hasattr(ctx, "progress"):
                await ctx.progress(f"Fetching URL: {url}")

            response = await client.get(url, timeout=10.0)
            response.raise_for_status()

            # Parse the HTML content
            html_text = response.text
            soup = BeautifulSoup(html_text, "html.parser")

            # Extract title
            title = soup.title.string.strip() if soup.title else "No title"

            # Extract metadata
            metadata = extract_metadata(soup, domain, url)

            # Extract author information
            author = extract_author(soup)

            # Extract keywords/tags
            keywords = extract_keywords(soup)

            # Extract main image
            main_image = extract_main_image(soup, url)

            # Extract social links
            social_links = extract_social_links(soup)

            # Extract targeted content based on domain/type
            content_snippet, headings = extract_targeted_content(soup, domain)

            structured_data = extract_structured_data(soup)
            entities = extract_entities(headings, content_snippet)
            knowledge_graph = await build_knowledge_graph(entities, domain)

            if capture_snapshot:
                snapshot_store.record(
                    url=url,
                    content=html_text,
                    metadata={
                        "title": title,
                        "domain": domain,
                        "source": "duckduckgo_get_details",
                    },
                )

            # Extract related links
            related_links = extract_related_links(soup, url, domain, same_domain_only)

            # Spider links if requested
            linked_content = []
            if spider_depth > 0 and related_links:
                linked_content = await spider_links(
                    related_links[:max_links_per_page],
                    client,
                    domain,
                    spider_depth,
                    max_links_per_page,
                    same_domain_only,
                    ctx,
                )

            # Create and return the detailed result
            result = DetailedResult(
                url=url,
                domain=domain,
                title=title,
                description=metadata["description"],
                content_snippet=content_snippet,
                headings=headings,
                published_date=metadata["published_date"],
                author=author,
                keywords=keywords,
                main_image=main_image,
                is_official=metadata["is_official"],
                social_links=social_links,
                related_links=related_links,
                linked_content=linked_content,
                structured_data=structured_data or None,
                entities=entities or None,
                knowledge_graph=knowledge_graph,
            )

            logger.info(f"Returning DetailedResult for URL: {url}")
            return result

    except Exception as e:
        error_msg = f"Error in duckduckgo_get_details: {e!s}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        if hasattr(ctx, "error"):
            await ctx.error(error_msg)
        raise


@mcp.tool()  # pragma: no cover
async def duckduckgo_related_searches(  # vulture: ignore
    query: str = Field(
        ...,
        description="Original search query",
        max_length=400,
    ),
    count: int = Field(
        default=5,
        description="Number of related searches to return (1-10, default 5)",
        ge=1,
        le=10,
    ),
    *,
    ctx: Context,  # Context is automatically injected by MCP
) -> list[str]:
    """
    Get related search queries for a given query.

    This tool suggests alternative search queries related to
    the original query, which can help explore a topic more broadly.

    Args:
        query: The original search query
        count: Number of related searches to return (1-10, default 5)
        ctx: MCP context object (automatically injected)

    Returns:
        A list of related search queries

    Example:
        duckduckgo_related_searches(query="artificial intelligence", count=5)
    """
    try:
        logger.info(
            f"duckduckgo_related_searches called with query: {query}, count: {count}"
        )

        # Log the context to help with debugging
        if ctx:
            logger.info(f"Context available: {ctx}")
        else:
            logger.error("Context is None!")

            # Create a minimal context if none is provided
            class MinimalContext(BaseModel):
                pass

            ctx = MinimalContext()

        # Use the main search function with a special flag for related searches
        result = await duckduckgo_search(
            {"query": query, "count": count, "get_related": True}, ctx
        )

        # Extract related searches and ensure they're strings
        raw_searches = result.get("related_searches", [])

        # Create a properly typed list, deduplicated and limited to requested count
        related_searches: list[str] = []
        seen: set[str] = set()
        for item in raw_searches:
            text = str(item).strip()
            if not text or text.lower() in seen:
                continue
            seen.add(text.lower())
            related_searches.append(text)
            if len(related_searches) >= count:
                break

        logger.info(f"Found {len(related_searches)} related searches")
        # Cast explicitly to satisfy type checker
        return cast(list[str], related_searches)

    except Exception as e:
        error_msg = f"Error in duckduckgo_related_searches: {e!s}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        if hasattr(ctx, "error"):
            await ctx.error(error_msg)

        # Return an empty list instead of raising an exception
        return cast(list[str], [])
