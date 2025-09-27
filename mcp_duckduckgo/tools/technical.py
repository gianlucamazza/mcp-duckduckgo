"""
Technical search tools for the DuckDuckGo search plugin.
"""

import logging
import traceback

from mcp.server.fastmcp import Context
from pydantic import Field

from ..models import SearchResponse, SearchResult
from ..search import duckduckgo_search
from ..server import mcp

# Configure logging
logger = logging.getLogger("mcp_duckduckgo.tools.technical")


@mcp.tool()  # pragma: no cover
async def dev_search(
    query: str = Field(
        ...,
        description="Search query for technical documentation",
        max_length=400,
    ),
    language: str | None = Field(
        default=None,
        description="Programming language to filter results (e.g., 'python', 'javascript')",
    ),
    framework: str | None = Field(
        default=None,
        description="Framework to filter results (e.g., 'react', 'django')",
    ),
    site: str | None = Field(
        default=None,
        description="Filter results to specific site (e.g., 'stackoverflow.com', 'github.com')",
    ),
    count: int = Field(
        default=10,
        description="Number of results (1-20)",
        ge=1,
        le=20,
    ),
    *,
    ctx: Context,  # Context is automatically injected by MCP
) -> SearchResponse:
    """
    Search for technical documentation, code examples, and developer resources.

    This tool is specialized for finding programming-related content such as
    documentation, APIs, libraries, tutorials, and code examples.

    Args:
        query: Search query for technical documentation
        language: Programming language to filter results (e.g., 'python', 'javascript')
        framework: Framework to filter results (e.g., 'react', 'django')
        site: Filter results to specific site (e.g., 'stackoverflow.com', 'github.com')
        count: Number of results (1-20)
        ctx: MCP context object (automatically injected)

    Returns:
        A SearchResponse object containing search results

    Example:
        dev_search(query="async file handling", language="python", count=5)
    """
    try:
        logger.info(
            f"dev_search called with query: {query}, language: {language}, framework: {framework}"
        )

        # Log the context to help with debugging
        if ctx:
            logger.info(f"Context available: {ctx}")
        else:
            logger.warning("Context is None!")

        # Enhance the query with technical filters
        enhanced_query = query

        # Add programming language if provided
        if language:
            enhanced_query = f"{enhanced_query} {language}"

        # Add framework if provided
        if framework:
            enhanced_query = f"{enhanced_query} {framework}"

        # Build a list of technical sites to prioritize
        tech_sites = [
            "stackoverflow.com",
            "github.com",
            "docs.python.org",
            "developer.mozilla.org",
            "docs.microsoft.com",
            "reactjs.org",
            "vuejs.org",
            "angular.io",
            "djangoproject.com",
            "laravel.com",
            "nodejs.org",
            "npmjs.com",
            "pypi.org",
        ]

        # Add site filter if provided or use a generic tech sites filter
        site_filter = ""
        if site:
            site_filter = f"site:{site}"
            enhanced_query = f"{enhanced_query} {site_filter}"

        if hasattr(ctx, "progress"):
            await ctx.progress(f"Searching for technical content: {enhanced_query}")

        # Perform the search with enhanced query
        result = await duckduckgo_search({"query": enhanced_query, "count": count}, ctx)

        # Process results to prioritize technical sites
        search_results = []
        prioritized_results = []
        other_results = []

        for item in result["results"]:
            # Create a search result
            search_result = SearchResult(
                title=item["title"],
                url=item["url"],
                description=item["description"],
                published_date=item.get("published_date"),
            )

            # Check if this is from a technical site
            is_tech_site = any(tech_site in item["url"] for tech_site in tech_sites)

            # Prioritize results from technical sites
            if is_tech_site:
                prioritized_results.append(search_result)
            else:
                other_results.append(search_result)

        # Combine prioritized and other results, up to count
        search_results = prioritized_results + other_results
        search_results = search_results[:count]

        # Create the response
        response = SearchResponse(
            results=search_results,
            total_results=result["total_results"],
            page=1,
            total_pages=1,
            has_next=False,
            has_previous=False,
        )

        logger.info(
            f"Returning SearchResponse with {len(search_results)} technical results"
        )
        return response

    except Exception as e:
        error_msg = f"Error in dev_search: {e!s}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        if hasattr(ctx, "error"):
            await ctx.error(error_msg)
        raise
