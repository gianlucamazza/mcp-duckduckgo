"""
Search functionality for the DuckDuckGo search plugin.
"""

from __future__ import annotations

import contextlib
import logging
import urllib.parse
from collections.abc import Iterable
from typing import Any, cast

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import Context

from .http import get_http_client
from .rerank import rerank_results
from .models import SearchIntent
from .semantic_cache import semantic_cache

# Configure logging
logger = logging.getLogger("mcp_duckduckgo.search")


class DuckDuckGoSearchError(RuntimeError):
    """Raised when DuckDuckGo search cannot complete successfully."""


def extract_domain(url: str) -> str:
    """
    Extract the domain name from a URL.

    Args:
        url: The URL to extract the domain from

    Returns:
        The domain name
    """
    try:
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc
        return domain
    except Exception as e:
        logger.error(f"Error extracting domain from URL {url}: {e}")
        return ""


def _ensure_iterable_text(nodes: Iterable[Any]) -> list[str]:
    """Return a list of stripped text values from BeautifulSoup nodes."""

    texts: list[str] = []
    for node in nodes:
        text = getattr(node, "text", "")
        candidate = text.strip()
        if candidate:
            texts.append(candidate)
    return texts


def _extract_related_queries(soup: BeautifulSoup) -> list[str]:
    """Extract related search queries from the DuckDuckGo Lite HTML page."""

    selectors = (
        "tr.result-link--related a",
        "tr.result-link.related a",
        "a.result--more__link",
        "a.related-searches__item",
    )

    related: list[str] = []
    seen: set[str] = set()

    for selector in selectors:
        for anchor in soup.select(selector):
            text = anchor.text.strip()
            if text and text not in seen:
                related.append(text)
                seen.add(text)

    if not related:
        fallback_tables = soup.find_all("table", class_="related-searches")
        for table in fallback_tables:
            related.extend(_ensure_iterable_text(table.find_all("a")))

    return related


def _summarize_html(html: str, limit: int = 360) -> str:
    """Return a whitespace-collapsed excerpt of HTML for diagnostics."""

    collapsed = " ".join(html.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 1]}…"


def _merge_results(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    for result in primary + secondary:
        url = result.get("url")
        if not url:
            continue
        if url in seen:
            continue
        seen.add(url)
        merged.append(result)

    return merged


async def duckduckgo_search(params: dict[str, Any], ctx: Context) -> dict[str, Any]:
    """
    Perform a web search using DuckDuckGo API.

    Args:
        params: Dictionary containing search parameters
        ctx: MCP context object providing access to lifespan resources

    Returns:
        Dictionary with search results
    """
    query = params.get("query")
    try:
        count = int(params.get("count", 10))
        offset = int(params.get("offset", 0))
        page = int(params.get("page", 1))
    except (TypeError, ValueError) as exc:
        logger.error("Invalid pagination parameters: %s", exc)
        raise ValueError("Pagination parameters must be integers") from exc

    if not query:
        logger.error("Query parameter is required")
        raise ValueError("Query parameter is required")

    logger.info("Searching DuckDuckGo for query '%s'", query)

    # We'll use the DuckDuckGo Lite API endpoint which doesn't require an API key
    # This is for demonstration purposes. For production, consider using a proper search API
    url = "https://lite.duckduckgo.com/lite/"

    http_client: httpx.AsyncClient | None = None
    close_client = False

    response_text: str | None = None

    intent = cast(SearchIntent, params.get("intent") or "general")
    embedding_signature = semantic_cache.embed_query(query)
    site = params.get("site")
    time_period = params.get("time_period")
    related_requested = bool(params.get("get_related"))

    raw_related_count = params.get("related_count")
    if raw_related_count is None and related_requested:
        raw_related_count = count
    try:
        related_count_value = (
            int(raw_related_count) if raw_related_count is not None else None
        )
    except (TypeError, ValueError):
        related_count_value = None

    cache_key = semantic_cache.make_key(
        intent=intent,
        embedding_signature=embedding_signature,
        count=count,
        offset=offset,
        page=page,
        site=site,
        time_period=time_period,
        related=related_requested,
        related_count=related_count_value,
    )

    cached_payload: dict[str, Any] | None = None
    cache_lookup = semantic_cache.get(cache_key, intent=intent)
    if cache_lookup:
        if cache_lookup.fresh:
            cached_result = cache_lookup.payload
            cached_result["intent"] = intent
            cached_result["cache_metadata"] = {
                "status": "hit",
                "age_seconds": round(cache_lookup.age_seconds, 2),
            }
            with contextlib.suppress(Exception):
                if hasattr(ctx, "debug"):
                    await ctx.debug(
                        f"Cache hit for query '{query}' (age {cache_lookup.age_seconds:.1f}s)"
                    )
            return cached_result

        cached_payload = cache_lookup.payload

    try:
        http_client, close_client = get_http_client(ctx, timeout=10.0)

        # Log the search operation
        if hasattr(ctx, "info"):
            await ctx.info(f"Searching for: {query} (page {page})")

        response = await http_client.post(
            url,
            data={
                "q": query,
                "kl": "wt-wt",  # No region localization
                "s": offset,  # Start index for pagination
            },
            timeout=10.0,
        )
        response.raise_for_status()

        response_text = response.text

        # Log the response status and content length
        logger.info(
            "Response status %s for query '%s' (content length %s)",
            response.status_code,
            query,
            len(response_text),
        )

        # Parse the HTML response to extract search results
        # Note: This is a simplified implementation and might break if DuckDuckGo changes their HTML structure
        # For a production service, consider using a more robust solution

        soup = BeautifulSoup(response_text, "html.parser")

        # Log the HTML structure to understand what we're working with
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "HTML title: %s",
                soup.title.string.strip()
                if soup.title and soup.title.string
                else "No title",
            )

            tables = soup.find_all("table")
            logger.debug("Found %s tables in the response", len(tables))

            for i, table in enumerate(tables):
                logger.debug("Table %s class: %s", i, table.get("class", "No class"))

        # Find all result rows in the HTML
        result_rows = soup.find_all("tr", class_="result-link")
        result_snippets = soup.find_all("tr", class_="result-snippet")

        logger.debug(
            "Found %s result rows and %s result snippets",
            len(result_rows),
            len(result_snippets),
        )

        # If we didn't find any results with the expected classes, try to find links in a different way
        if len(result_rows) == 0:
            logger.debug(
                "No results found with expected classes, trying alternative parsing"
            )

            # Try to find all links in the document
            all_links = soup.find_all("a")
            logger.debug("Found %s links in the document", len(all_links))

            # Log the first few links to see what we're working with
            if logger.isEnabledFor(logging.DEBUG):
                for i, link in enumerate(all_links[:5]):
                    logger.debug(
                        "Link %s: text='%s', href='%s'",
                        i,
                        link.text.strip(),
                        link.get("href", ""),
                    )

        total_results = len(result_rows)

        # Report progress to the client if the method is available
        if hasattr(ctx, "report_progress"):
            await ctx.report_progress(0, total_results)

        results = []

        # Extract only the requested number of results starting from the offset
        for i in range(min(count, len(result_rows))):
            if offset + i >= len(result_rows):
                break

            title_elem = result_rows[offset + i].find("a")
            if not title_elem:
                continue

            title = title_elem.text.strip()
            url = title_elem.get("href", "")
            domain = extract_domain(url)

            description = ""
            if offset + i < len(result_snippets):
                description = result_snippets[offset + i].text.strip()

            # Create a dictionary directly instead of using SearchResult model
            results.append(
                {
                    "title": title,
                    "url": url,
                    "description": description,
                    "published_date": None,
                    "domain": domain,
                }
            )

            # Update progress if the method is available
            if hasattr(ctx, "report_progress"):
                await ctx.report_progress(i + 1, total_results)

        # If we still don't have results, try an alternative approach
        if len(results) == 0:
            logger.debug(
                "No results found with standard parsing, trying alternative approach"
            )

            # Try to find results in a different way - this is a fallback approach
            # Look for any links that might be search results
            all_links = soup.find_all("a")

            # Filter links that look like search results (not navigation links)
            potential_results = [
                link
                for link in all_links
                if link.get("href")
                and not link.get("href").startswith("#")
                and not link.get("href").startswith("/")
            ]

            logger.debug("Found %s potential result links", len(potential_results))

            # Take up to 'count' results
            for i, link in enumerate(potential_results[:count]):
                if i >= count:
                    break

                title = link.text.strip()
                url = link.get("href", "")
                domain = extract_domain(url)

                # Try to find a description - look for text in the parent or next sibling
                description = ""
                parent = link.parent
                if parent and parent.text and len(parent.text.strip()) > len(title):
                    description = parent.text.strip()

                if not description and link.next_sibling:
                    description = (
                        link.next_sibling.text.strip()
                        if hasattr(link.next_sibling, "text")
                        else ""
                    )

                results.append(
                    {
                        "title": title,
                        "url": url,
                        "description": description,
                        "published_date": None,
                        "domain": domain,
                    }
                )

            total_results = len(potential_results)

        # Calculate more accurate total_results estimation
        # DuckDuckGo doesn't provide exact total counts, but we can estimate
        # based on pagination and number of results per page
        estimated_total = max(total_results, offset + len(results))

        # For pagination purposes, we should always claim there are more results
        # unless we received fewer than requested
        if len(results) >= count:
            estimated_total = max(estimated_total, offset + count + 1)

        reranked = rerank_results(query, results, intent)

        payload_results = reranked
        if cached_payload and cached_payload.get("results"):
            payload_results = _merge_results(reranked, cached_payload["results"])

        payload: dict[str, Any] = {
            "results": payload_results,
            "total_results": estimated_total,
            "intent": intent,
        }

        if params.get("get_related"):
            raw_related = _extract_related_queries(soup)
            deduped: list[str] = []
            seen: set[str] = set()
            max_related = related_count_value or 10
            for candidate in raw_related:
                normalized = candidate.strip()
                if not normalized:
                    continue
                lowered = normalized.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                deduped.append(normalized)
                if len(deduped) >= max_related:
                    break

            if not deduped and cached_payload:
                deduped = cached_payload.get("related_searches", [])

            payload["related_searches"] = deduped
            logger.debug(
                "Extracted %s related searches for query '%s'",
                len(deduped),
                query,
            )

        if cached_payload and not payload.get("cache_metadata"):
            payload["cache_metadata"] = {
                "status": "refresh",
                "age_seconds": round(cache_lookup.age_seconds, 2)
                if cache_lookup
                else None,
            }
        else:
            payload.setdefault(
                "cache_metadata",
                {
                    "status": "miss",
                    "age_seconds": 0.0,
                },
            )

        semantic_cache.set(
            cache_key,
            intent=intent,
            embedding_signature=embedding_signature,
            payload=payload,
        )

        return payload

    except httpx.HTTPStatusError as e:
        status = getattr(e.response, "status_code", "unknown")
        message = f"DuckDuckGo returned HTTP status {status} for query '{query}'."
        logger.exception(message)
        if hasattr(ctx, "error"):
            await ctx.error(message)
        raise DuckDuckGoSearchError(message) from e
    except httpx.RequestError as e:
        message = f"Failed to reach DuckDuckGo for query '{query}': {e!s}"
        logger.exception(message)
        if hasattr(ctx, "error"):
            await ctx.error(message)
        raise DuckDuckGoSearchError(message) from e
    except Exception as e:
        summary = _summarize_html(response_text) if response_text else ""
        message = (
            f"Unexpected error parsing DuckDuckGo results for query '{query}': {e!s}."
        )
        if summary:
            message = f"{message} HTML excerpt: {summary}"
        else:
            message = f"{message} Enable DEBUG logging for details."
        logger.exception(message)
        if hasattr(ctx, "error"):
            await ctx.error(message)
        raise DuckDuckGoSearchError(message) from e
    finally:
        # Close the HTTP client if we created it
        if close_client and http_client:
            await http_client.aclose()
