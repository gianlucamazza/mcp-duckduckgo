"""
Summarization tools for the DuckDuckGo search plugin.
"""

import logging
import re
import traceback
from typing import Any

from bs4 import BeautifulSoup
from mcp.server.fastmcp import Context
from pydantic import Field

from ..http import get_http_client
from ..search import extract_domain
from ..server import mcp

# Import helper functions from the utils module
from .utils import extract_targeted_content

# Configure logging
logger = logging.getLogger("mcp_duckduckgo.tools.summarize")


@mcp.tool()  # pragma: no cover
async def summarize_webpage(
    url: str = Field(
        ...,
        description="URL of the webpage to summarize",
    ),
    max_length: int = Field(
        default=500,
        description="Maximum length of the summary in characters (100-2000)",
        ge=100,
        le=2000,
    ),
    extract_key_points: bool = Field(
        default=True,
        description="Whether to extract key points as bullet points",
    ),
    *,
    ctx: Context,  # Context is automatically injected by MCP
) -> dict[str, Any]:
    """
    Generate a concise summary of a webpage's content.

    This tool fetches a webpage, analyzes its content, and creates
    a readable summary that captures the most important information.

    Args:
        url: The URL of the webpage to summarize
        max_length: Maximum length of the summary in characters (100-2000)
        extract_key_points: Whether to extract key points as bullet points
        ctx: MCP context object (automatically injected)

    Returns:
        A dictionary containing the summary, key points, and metadata

    Example:
        summarize_webpage(url="https://example.com/article", max_length=300)
    """
    try:
        logger.info(
            f"summarize_webpage called with URL: {url}, max_length: {max_length}"
        )

        # Log the context to help with debugging
        if ctx:
            logger.info(f"Context available: {ctx}")
        else:
            logger.warning("Context is None!")

        # Extract domain from the URL
        domain = extract_domain(url)

        client, should_close = get_http_client(ctx, timeout=15.0)

        try:
            # Fetch the requested URL
            if hasattr(ctx, "progress"):
                await ctx.progress(f"Fetching URL: {url}")

            response = await client.get(url, timeout=15.0)
            response.raise_for_status()

            # Parse the HTML content
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title
            title = soup.title.string.strip() if soup.title and soup.title.string else "No title"

            # Extract targeted content
            content_snippet, headings = extract_targeted_content(soup, domain)

            sentences = [
                segment.strip()
                for segment in re.split(r"[\.!?]", content_snippet)
                if len(segment.strip()) > 40
            ]

            if hasattr(ctx, "progress") and sentences:
                bullets = min(5, len(sentences))
                for index in range(bullets):
                    sentence = sentences[index]
                    preview = sentence[:200]
                    suffix = "..." if len(sentence) > 200 else ""
                    await ctx.progress(f"- {preview}{suffix}")
                    if hasattr(ctx, "report_progress"):
                        await ctx.report_progress(index + 1, bullets)

            # Generate a summary using the first part of the content
            # This is a simple approach - in a production system you might want
            # to use a more sophisticated summarization algorithm or an LLM
            summary = content_snippet[:max_length]
            if len(content_snippet) > max_length:
                summary = summary.rsplit(".", 1)[0] + "."

            # Extract key points if requested
            key_points = []
            if extract_key_points:
                if hasattr(ctx, "progress"):
                    await ctx.progress("Extracting key points...")

                # Use headings as key points, or extract sentences with important keywords
                if headings and len(headings) >= 3:
                    key_points = headings[:5]  # Use top 5 headings as key points
                else:
                    # Split content into sentences and select important ones
                    sentences = [
                        s.strip()
                        for s in content_snippet.split(".")
                        if len(s.strip()) > 20
                    ]
                    important_keywords = [
                        "important",
                        "key",
                        "significant",
                        "main",
                        "primary",
                        "crucial",
                        "essential",
                    ]

                    # First, try to find sentences with important keywords
                    for sentence in sentences:
                        if any(
                            keyword in sentence.lower()
                            for keyword in important_keywords
                        ):
                            if sentence not in key_points:
                                key_points.append(sentence)

                    # If we didn't find enough sentences with keywords, take from the beginning and after headings
                    if len(key_points) < 3 and sentences:
                        # Add the first sentence if not already included
                        if sentences[0] not in key_points:
                            key_points.append(sentences[0])

                        # Take a few more sentences from different parts of the content
                        indices = [len(sentences) // 3, len(sentences) * 2 // 3]
                        for idx in indices:
                            if (
                                idx < len(sentences)
                                and sentences[idx] not in key_points
                            ):
                                key_points.append(sentences[idx])

                    # Limit to 5 points maximum
                    key_points = key_points[:5]

            # Create and return the result
            result = {
                "url": url,
                "title": title,
                "summary": summary,
                "key_points": key_points,
                "domain": domain,
                "headings": headings[:3] if headings else [],  # Include top 3 headings
                "content_length": len(content_snippet),
            }

            logger.info(f"Summarized webpage: {url}")
            return result

        finally:
            if should_close:
                await client.aclose()

    except Exception as e:
        error_msg = f"Error in summarize_webpage: {e!s}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        if hasattr(ctx, "error"):
            await ctx.error(error_msg)
        raise
