#!/usr/bin/env python
"""
Script to test real DuckDuckGo searches.
This script makes actual HTTP requests to DuckDuckGo.
"""

import asyncio
import logging
import os

import httpx
from pydantic import BaseModel
import pytest

from mcp_duckduckgo.search import duckduckgo_search
from mcp_duckduckgo.tools import (
    duckduckgo_get_details,
    duckduckgo_related_searches,
    duckduckgo_web_search,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class MockContext(BaseModel):
    """A simple mock context to use for testing."""

    lifespan_context: dict = {}

    async def progress(self, message):
        """Print progress messages."""
        print(f"Progress: {message}")

    async def info(self, message):
        """Print info messages."""
        print(f"Info: {message}")

    async def error(self, message):
        """Print error messages."""
        print(f"Error: {message}")


async def test_real_search():
    """Test a real search against DuckDuckGo."""
    # Create a mock context with a real HTTP client
    ctx = MockContext()
    ctx.lifespan_context = {
        "http_client": httpx.AsyncClient(
            timeout=15.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            },
            follow_redirects=True,
        )
    }

    try:
        # Test basic search
        query = "Python programming language"
        print(f"\n1. Testing basic search for: '{query}'")
        search_params = {"query": query, "count": 5}
        search_results = await duckduckgo_search(search_params, ctx)

        print(f"Found {len(search_results['results'])} results:")
        for i, result in enumerate(search_results["results"], 1):
            print(f"\nResult {i}:")
            print(f"Title: {result['title']}")
            print(f"URL: {result['url']}")
            print(
                f"Description: {result['description'][:100]}..."
                if len(result["description"]) > 100
                else f"Description: {result['description']}"
            )

        # Test web search tool
        print(f"\n2. Testing web search tool for: '{query}'")
        web_search_results = await duckduckgo_web_search(
            query=query, count=5, page=1, site=None, time_period=None, ctx=ctx
        )

        print(f"Found {len(web_search_results.results)} results:")
        for i, result in enumerate(web_search_results.results, 1):
            print(f"\nResult {i}:")
            print(f"Title: {result.title}")
            print(f"URL: {result.url}")
            print(
                f"Description: {result.description[:100]}..."
                if len(result.description) > 100
                else f"Description: {result.description}"
            )

        # Test web search with site filter
        print("\n3. Testing web search with site filter: 'documentation' on python.org")
        site_filtered_results = await duckduckgo_web_search(
            query="documentation",
            count=3,
            page=1,
            site="python.org",
            time_period=None,
            ctx=ctx,
        )

        print(
            f"Found {len(site_filtered_results.results)} results for site python.org:"
        )
        for i, result in enumerate(site_filtered_results.results, 1):
            print(f"\nResult {i}:")
            print(f"Title: {result.title}")
            print(f"URL: {result.url}")
            print(
                f"Description: {result.description[:100]}..."
                if len(result.description) > 100
                else f"Description: {result.description}"
            )

        # Test web search with time filter
        print(
            "\n4. Testing web search with time filter: 'python release' from last year"
        )
        time_filtered_results = await duckduckgo_web_search(
            query="python release",
            count=3,
            page=1,
            site=None,
            time_period="year",
            ctx=ctx,
        )

        print(f"Found {len(time_filtered_results.results)} results from last year:")
        for i, result in enumerate(time_filtered_results.results, 1):
            print(f"\nResult {i}:")
            print(f"Title: {result.title}")
            print(f"URL: {result.url}")
            print(
                f"Description: {result.description[:100]}..."
                if len(result.description) > 100
                else f"Description: {result.description}"
            )

        # Test content extraction with different spider depths
        print("\n5. Testing enhanced content extraction with spidering:")

        # Test with an official documentation site
        print("\n5.1. Testing enhanced extraction on Python.org (no spidering)")
        python_org_details = await duckduckgo_get_details(
            url="https://www.python.org/", ctx=ctx
        )
        print_detailed_result(python_org_details, include_linked_content=False)

        # Test with a Wikipedia article with spidering depth 1
        print(
            "\n5.2. Testing enhanced extraction on Wikipedia with spidering (depth=1)"
        )
        wiki_details = await duckduckgo_get_details(
            url="https://en.wikipedia.org/wiki/Python_(programming_language)",
            spider_depth=1,
            max_links_per_page=2,
            same_domain_only=True,
            ctx=ctx,
        )
        print_detailed_result(wiki_details, include_linked_content=True)

        # Test with a documentation page
        print("\n5.3. Testing enhanced extraction on Python documentation")
        docs_details = await duckduckgo_get_details(
            url="https://docs.python.org/3/tutorial/", ctx=ctx
        )
        print_detailed_result(docs_details, include_linked_content=False)

        # Test related searches
        print(f"\n6. Testing related searches for: '{query}'")
        related_queries = await duckduckgo_related_searches(
            query=query, count=5, ctx=ctx
        )

        print(f"Found {len(related_queries)} related searches:")
        for i, related_query in enumerate(related_queries, 1):
            print(f"{i}. {related_query}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close HTTP client
        await ctx.lifespan_context["http_client"].aclose()


def print_detailed_result(result, include_linked_content=False):
    """Pretty print a DetailedResult."""
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print(f"Domain: {result.domain}")
    print(f"Official Source: {result.is_official}")

    if result.author:
        print(f"Author: {result.author}")

    if result.published_date:
        print(f"Published Date: {result.published_date}")

    if result.keywords:
        print(f"Keywords: {', '.join(result.keywords)}")

    if result.main_image:
        print(f"Main Image: {result.main_image}")

    if result.social_links:
        print("Social Links:")
        for platform, url in result.social_links.items():
            print(f"  - {platform}: {url}")

    if result.headings:
        print("Content Structure:")
        for i, heading in enumerate(result.headings[:5], 1):
            print(f"  {i}. {heading}")
        if len(result.headings) > 5:
            print(f"  ... ({len(result.headings) - 5} more headings)")

    print("Description:", end=" ")
    if result.description:
        if len(result.description) > 150:
            print(f"{result.description[:150]}...")
        else:
            print(result.description)
    else:
        print("None")

    print("Content Snippet:", end=" ")
    if result.content_snippet:
        if len(result.content_snippet) > 200:
            print(f"{result.content_snippet[:200]}...")
        else:
            print(result.content_snippet)
    else:
        print("None")

    if result.related_links:
        print(f"Related Links: {len(result.related_links)} found")
        for i, link in enumerate(result.related_links[:3], 1):
            print(f"  {i}. {link}")
        if len(result.related_links) > 3:
            print(f"  ... ({len(result.related_links) - 3} more links)")

    if include_linked_content and result.linked_content:
        print(f"\nLinked Content: {len(result.linked_content)} pages")
        for i, content in enumerate(result.linked_content[:2], 1):
            print(f"\n  Linked Page {i} ({content.relation}):")
            print(f"  Title: {content.title}")
            print(f"  URL: {content.url}")
            if content.content_snippet:
                if len(content.content_snippet) > 150:
                    print(f"  Snippet: {content.content_snippet[:150]}...")
                else:
                    print(f"  Snippet: {content.content_snippet}")
        if len(result.linked_content) > 2:
            print(f"  ... ({len(result.linked_content) - 2} more linked pages)")


# Run the test
if __name__ == "__main__":
    asyncio.run(test_real_search())
pytestmark = pytest.mark.skipif(
    not os.getenv("ENABLE_REAL_SEARCH_TESTS"),
    reason="Real DuckDuckGo search disabled in this environment",
)
