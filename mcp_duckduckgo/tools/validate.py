"""
Validation tools for the DuckDuckGo search plugin.
"""

import logging
import traceback
from typing import Any

from mcp.server.fastmcp import Context
from pydantic import Field

from ..search import duckduckgo_search
from ..server import mcp

# Configure logging
logger = logging.getLogger("mcp_duckduckgo.tools.validate")


@mcp.tool()  # pragma: no cover
async def fact_check(
    statement: str = Field(
        ...,
        description="The statement to fact check",
        max_length=500,
    ),
    min_sources: int = Field(
        default=3,
        description="Minimum number of sources to check (1-10)",
        ge=1,
        le=10,
    ),
    *,
    ctx: Context,  # Context is automatically injected by MCP
) -> dict[str, Any]:
    """
    Validate a statement by searching for supporting or contradicting information.

    This tool performs a search to find sources that support or contradict
    the given statement, helping to assess its accuracy.

    Args:
        statement: The statement to fact check
        min_sources: Minimum number of sources to check (1-10)
        ctx: MCP context object (automatically injected)

    Returns:
        A dictionary containing validation results, sources, and confidence score

    Example:
        fact_check(statement="The Earth is flat", min_sources=5)
    """
    try:
        logger.info(
            f"fact_check called with statement: {statement}, min_sources: {min_sources}"
        )

        # Log the context to help with debugging
        if ctx:
            logger.info(f"Context available: {ctx}")
        else:
            logger.warning("Context is None!")

        # Create search queries to find supporting and contradicting information
        search_queries = [
            f"{statement} fact check",
            f"is it true that {statement}",
            f"{statement} debunked",
            f"{statement} evidence",
            f"is {statement} accurate",
        ]

        # Process the first query to see if it's mentioned in fact-checking sites
        if hasattr(ctx, "progress"):
            await ctx.progress(f"Searching for fact checks on: {statement}")

        # Track sources and validation results
        sources: list[dict[str, Any]] = []
        supporting_sources = 0
        contradicting_sources = 0
        neutral_sources = 0

        # Check multiple search queries
        for query in search_queries:
            # Skip additional queries if we have enough sources
            if len(sources) >= min_sources * 2:
                break

            result = await duckduckgo_search(
                {
                    "query": query,
                    "count": 5,
                },
                ctx,
            )

            # Process search results
            for item in result["results"]:
                # Skip if we already have this source
                if any(s["url"] == item["url"] for s in sources):
                    continue

                title = item["title"].lower()
                description = item["description"].lower()

                # Analyze the sentiment of the source towards the statement
                sentiment = "neutral"

                # Check for supporting terms
                supporting_terms = [
                    "confirm",
                    "true",
                    "verified",
                    "evidence supports",
                    "proven",
                    "accurate",
                    "correct",
                ]
                contradicting_terms = [
                    "false",
                    "fake",
                    "hoax",
                    "debunk",
                    "myth",
                    "incorrect",
                    "no evidence",
                    "wrong",
                ]

                # Simple sentiment analysis based on keywords
                supporting_count = sum(
                    1
                    for term in supporting_terms
                    if term in title or term in description
                )
                contradicting_count = sum(
                    1
                    for term in contradicting_terms
                    if term in title or term in description
                )

                # Determine sentiment based on keyword count
                if supporting_count > contradicting_count:
                    sentiment = "supporting"
                    supporting_sources += 1
                elif contradicting_count > supporting_count:
                    sentiment = "contradicting"
                    contradicting_sources += 1
                else:
                    sentiment = "neutral"
                    neutral_sources += 1

                # Add to sources
                sources.append(
                    {
                        "url": item["url"],
                        "title": item["title"],
                        "description": item["description"],
                        "sentiment": sentiment,
                    }
                )

                # Check if we have enough sources
                if len(sources) >= min_sources * 2:
                    break

        # Calculate confidence score (-100 to 100)
        # Positive means supporting, negative means contradicting
        total_sources = (
            supporting_sources + contradicting_sources + (neutral_sources * 0.5)
        )
        confidence_score = 0

        if total_sources > 0:
            # Calculate weighted score
            confidence_score = int(
                ((supporting_sources - contradicting_sources) / total_sources) * 100
            )
            # Ensure within bounds
            confidence_score = max(-100, min(100, confidence_score))

        # Determine validation result
        validation_result = "Inconclusive"
        if confidence_score >= 70:
            validation_result = "Likely True"
        elif confidence_score >= 30:
            validation_result = "Possibly True"
        elif confidence_score <= -70:
            validation_result = "Likely False"
        elif confidence_score <= -30:
            validation_result = "Possibly False"

        # Create result object
        result = {
            "statement": statement,
            "validation_result": validation_result,
            "confidence_score": confidence_score,
            "supporting_sources": supporting_sources,
            "contradicting_sources": contradicting_sources,
            "neutral_sources": neutral_sources,
            "sources": sources[
                : min_sources * 2
            ],  # Limit the number of sources returned
        }

        logger.info(
            f"Fact check result for '{statement}': {validation_result} (confidence: {confidence_score})"
        )
        return result

    except Exception as e:
        error_msg = f"Error in fact_check: {e!s}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        if hasattr(ctx, "error"):
            await ctx.error(error_msg)
        raise
