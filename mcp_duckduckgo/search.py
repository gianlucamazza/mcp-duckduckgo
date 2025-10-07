"""
Proper DuckDuckGo search implementation for MCP.
"""

import logging
import urllib.parse
from dataclasses import dataclass
from typing import List

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# HTTP Configuration
DEFAULT_TIMEOUT = 15
INSTANT_API_TIMEOUT = 10
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# DuckDuckGo Selectors
RESULT_SELECTORS = [
    "div.result",
    'div[class*="result"]',
    ".result",
    ".web-result",
    ".result_body",
]

TITLE_SELECTORS = [
    "a.result__a",
    'a[class*="result"]',
    ".result__title a",
    "h3 a",
    "a",
]

SNIPPET_SELECTORS = [
    "a.result__snippet",
    ".result__snippet",
    ".result__body",
    ".snippet",
    "p",
]


@dataclass
class SearchResult:
    title: str
    url: str
    description: str
    domain: str = ""


def extract_domain(url: str) -> str:
    """
    Extract domain from URL.

    Args:
        url: URL string to extract domain from

    Returns:
        Lowercase domain name or empty string if parsing fails
    """
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc.lower()
    except Exception as e:
        logger.debug("Failed to extract domain from URL %s: %s", url, e)
        return ""


async def search_duckduckgo_instant(
    query: str, http_client: httpx.AsyncClient
) -> List[SearchResult]:
    """
    Search using DuckDuckGo Instant Answer API.

    Args:
        query: Search query string
        http_client: HTTP client to use for the request

    Returns:
        List of SearchResult objects from instant answers
    """
    try:
        # Use DuckDuckGo's Instant Answer API
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }

        response = await http_client.get(url, params=params, timeout=INSTANT_API_TIMEOUT)  # type: ignore[arg-type]
        response.raise_for_status()

        data = response.json()
        results = []

        # Get the abstract/summary
        if data.get("Abstract"):
            abstract_url = data.get("AbstractURL", "")
            results.append(
                SearchResult(
                    title=data.get("Heading", query),
                    url=abstract_url,
                    description=data.get("Abstract", ""),
                    domain=extract_domain(abstract_url),
                )
            )

        # Get related topics
        for topic in data.get("RelatedTopics", []):
            if isinstance(topic, dict) and topic.get("Text") and topic.get("FirstURL"):
                topic_url = topic.get("FirstURL", "")
                results.append(
                    SearchResult(
                        title=topic.get("Text", ""),
                        url=topic_url,
                        description=topic.get("Text", ""),
                        domain=extract_domain(topic_url),
                    )
                )

        return results

    except Exception:
        logger.exception("DuckDuckGo instant search failed")
        return []


async def search_duckduckgo_html(
    query: str, http_client: httpx.AsyncClient, count: int = 10
) -> List[SearchResult]:
    """
    Search using DuckDuckGo HTML interface as fallback.

    Args:
        query: Search query string
        http_client: HTTP client to use for the request
        count: Maximum number of results to return

    Returns:
        List of SearchResult objects parsed from HTML
    """
    try:
        # Use DuckDuckGo's HTML interface
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}

        response = await http_client.get(
            url, params=params, headers=COMMON_HEADERS, timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        # DuckDuckGo result selectors (multiple attempts for robustness)
        result_divs: list = []
        for selector in RESULT_SELECTORS:
            result_divs = soup.select(selector)
            if result_divs:
                logger.info(
                    "Found %d results with selector: %s", len(result_divs), selector
                )
                break

        if not result_divs:
            logger.warning("No result divs found, trying fallback method")
            # Fallback: look for links that might be search results
            all_links = soup.find_all("a", href=True)
            for link in all_links[:count]:
                href = link.get("href", "")
                text = link.get_text().strip()
                if href and text and not href.startswith("#"):
                    results.append(
                        SearchResult(
                            title=text,
                            url=href,
                            description="",
                            domain=extract_domain(href),
                        )
                    )
            return results[:count]

        for i, div in enumerate(result_divs[:count]):
            try:
                # Multiple title/link selectors
                title_link = None
                for selector in TITLE_SELECTORS:
                    title_link = div.select_one(selector)
                    if title_link:
                        break

                if not title_link:
                    continue

                title = title_link.get_text().strip()
                url = title_link.get("href", "")

                # Extract snippet/description
                description = ""
                for selector in SNIPPET_SELECTORS:
                    snippet_elem = div.select_one(selector)
                    if snippet_elem:
                        description = snippet_elem.get_text().strip()
                        break

                # Clean up URL (remove DuckDuckGo redirect)
                if url.startswith("/l/?uddg="):
                    try:
                        querystr = urllib.parse.parse_qs(
                            urllib.parse.urlparse(url).query
                        )
                        if "uddg" in querystr:
                            url = querystr["uddg"][0]
                    except Exception as e:
                        logger.debug("Failed to parse redirect URL %s: %s", url, e)

                # Skip if no valid URL or title
                if not url or not title:
                    continue

                results.append(
                    SearchResult(
                        title=title,
                        url=url,
                        description=description,
                        domain=extract_domain(url),
                    )
                )

            except Exception as e:
                logger.warning("Failed to parse result %d: %s", i, e)
                continue

        logger.info("Successfully parsed %d HTML results", len(results))
        return results

    except Exception:
        logger.exception("DuckDuckGo HTML search failed")
        return []


async def search_web(
    query: str, http_client: httpx.AsyncClient, count: int = 10
) -> List[SearchResult]:
    """
    Main search function that tries multiple methods.

    Args:
        query: Search query string
        http_client: HTTP client to use for requests
        count: Maximum number of results to return

    Returns:
        List of unique SearchResult objects from both instant answers and HTML search
    """
    logger.info("Searching for: '%s' (max %d results)", query, count)

    # Try instant answers first
    instant_results = await search_duckduckgo_instant(query, http_client)
    logger.info("Instant answers found %d results", len(instant_results))

    # Always try HTML search for more comprehensive results
    html_results = await search_duckduckgo_html(query, http_client, count)
    logger.info("HTML search found %d results", len(html_results))

    # Combine and deduplicate
    all_results = instant_results + html_results

    # Remove duplicates based on URL
    seen_urls = set()
    unique_results = []
    for result in all_results:
        if result.url and result.url not in seen_urls and result.url.startswith("http"):
            seen_urls.add(result.url)
            unique_results.append(result)
            if len(unique_results) >= count:
                break

    logger.info("Returning %d unique valid results", len(unique_results))
    return unique_results
