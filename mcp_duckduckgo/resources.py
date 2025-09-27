"""
MCP resource definitions for the DuckDuckGo search plugin.
"""

from typing import Any

import httpx
from bs4 import BeautifulSoup

from .server import mcp


@mcp.resource("docs://search")  # pragma: no cover
def get_search_docs() -> str:  # vulture: ignore
    """
    Provides documentation about the DuckDuckGo search functionality.
    """
    return """
    # DuckDuckGo Search API

    This MCP server provides a web search capability using DuckDuckGo.

    ## Usage

    Use the `duckduckgo_web_search` tool to search the web:

    ```python
    result = await duckduckgo_web_search(
        query="your search query",
        count=10,  # Number of results (1-20)
        offset=0   # For pagination
    )
    ```

    ## Response Format

    The search returns a structured response with:

    - `results`: List of search results, each containing:
      - `title`: The title of the result
      - `url`: The URL of the result
      - `description`: A snippet or description of the result
      - `published_date`: Publication date if available
    - `total_results`: Total number of results found

    ## Limitations

    - Maximum query length is 400 characters or 50 words
    - Results are limited to 20 per request
    - This is a simplified implementation using DuckDuckGo Lite
    """


@mcp.resource("search://{query}")  # pragma: no cover
async def get_search_results(query: str) -> str:  # vulture: ignore
    """
    Provides search results for a specific query as a resource.

    Args:
        query: The search query

    Returns:
        Formatted search results as text
    """

    # Create a simple search function that doesn't require the context
    async def simple_search(query: str, count: int = 5) -> dict[str, Any]:
        url = "https://lite.duckduckgo.com/lite/"

        async with httpx.AsyncClient(
            timeout=10.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            },
        ) as client:
            response = await client.post(
                url,
                data={
                    "q": query,
                    "kl": "wt-wt",  # No region localization
                },
                timeout=10.0,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            # Find all result rows in the HTML
            result_rows = soup.find_all("tr", class_="result-link")
            result_snippets = soup.find_all("tr", class_="result-snippet")

            total_results = len(result_rows)

            # Extract only the requested number of results
            for i in range(min(count, len(result_rows))):
                title_elem = result_rows[i].find("a")
                if not title_elem:
                    continue

                title = title_elem.text.strip()
                url = title_elem.get("href", "")

                description = ""
                if i < len(result_snippets):
                    description = result_snippets[i].text.strip()

                results.append(
                    {
                        "title": title,
                        "url": url,
                        "description": description,
                        "published_date": None,
                    }
                )

            return {
                "results": results,
                "total_results": total_results,
            }

    # Perform the search
    result = await simple_search(query)

    # Format the results as markdown
    formatted_results = f"# Search Results for: {query}\n\n"

    for i, item in enumerate(result["results"], 1):
        formatted_results += f"## {i}. {item['title']}\n"
        formatted_results += f"URL: {item['url']}\n\n"
        formatted_results += f"{item['description']}\n\n"
        if item.get("published_date"):
            formatted_results += f"Published: {item['published_date']}\n\n"
        formatted_results += "---\n\n"

    formatted_results += f"\nTotal results found: {result['total_results']}"

    return formatted_results
