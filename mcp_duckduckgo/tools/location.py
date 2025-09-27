"""
Location-based search tools for the DuckDuckGo search plugin.
"""

import logging
import traceback

from mcp.server.fastmcp import Context
from pydantic import Field

from ..models import SearchResponse, SearchResult
from ..search import duckduckgo_search
from ..server import mcp

# Configure logging
logger = logging.getLogger("mcp_duckduckgo.tools.location")


@mcp.tool()  # pragma: no cover
async def location_search(
    query: str = Field(
        ...,
        description="Search query for location-based information",
        max_length=400,
    ),
    location: str = Field(
        ...,
        description="Location name (city, country, region, etc.)",
    ),
    service_type: str | None = Field(
        default=None,
        description="Type of service to search for (e.g., 'restaurants', 'hotels', 'parks')",
    ),
    radius_km: int | None = Field(
        default=None,
        description="Search radius in kilometers (approximate)",
        ge=1,
        le=50,
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
    Search for information or services at a specific location.

    This tool is designed to find location-based information such as
    local businesses, landmarks, services, or events in a specific area.

    Args:
        query: Search query for location-based information
        location: Location name (city, country, region, etc.)
        service_type: Type of service to search for (e.g., 'restaurants', 'hotels', 'parks')
        radius_km: Search radius in kilometers (approximate)
        count: Number of results (1-20)
        ctx: MCP context object (automatically injected)

    Returns:
        A SearchResponse object containing location-based search results

    Example:
        location_search(query="coffee shops", location="San Francisco", service_type="cafe", count=5)
    """
    try:
        logger.info(
            f"location_search called with query: {query}, location: {location}, service_type: {service_type}"
        )

        # Log the context to help with debugging
        if ctx:
            logger.info(f"Context available: {ctx}")
        else:
            logger.warning("Context is None!")

        # Construct a location-based search query
        geo_query = f"{query} in {location}"

        # Add service type if provided
        if service_type:
            geo_query = f"{service_type} {geo_query}"

        # Add radius if provided (as a hint in the query)
        if radius_km:
            geo_query = f"{geo_query} within {radius_km} km"

        if hasattr(ctx, "progress"):
            await ctx.progress(f"Searching for: {geo_query}")

        # Perform the search
        result = await duckduckgo_search({"query": geo_query, "count": count}, ctx)

        # Filter and process results
        search_results = []

        for item in result["results"]:
            # Check if the result contains location-relevant information
            # This is a simple check - in a production system you would use
            # proper geocoding and location data
            result_text = f"{item['title']} {item['description']}".lower()
            location_terms = location.lower().split()

            # Skip result if it doesn't mention the location terms
            # (helps filter out irrelevant results)
            if not any(term in result_text for term in location_terms if len(term) > 3):
                continue

            # Create the search result
            search_result = SearchResult(
                title=item["title"],
                url=item["url"],
                description=item["description"],
                published_date=item.get("published_date"),
            )

            search_results.append(search_result)

            # Stop once we have enough results
            if len(search_results) >= count:
                break

        # Create the response
        response = SearchResponse(
            results=search_results,
            total_results=len(search_results),
            page=1,
            total_pages=1,
            has_next=False,
            has_previous=False,
        )

        logger.info(
            f"Returning SearchResponse with {len(search_results)} location-based results"
        )
        return response

    except Exception as e:
        error_msg = f"Error in location_search: {e!s}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        if hasattr(ctx, "error"):
            await ctx.error(error_msg)
        raise
