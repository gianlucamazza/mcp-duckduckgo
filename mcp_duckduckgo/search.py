"""
Search functionality for the DuckDuckGo search plugin.
"""

import logging
from typing import Dict, Any
import urllib.parse

import httpx
from mcp.server.fastmcp import Context
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger("mcp_duckduckgo.search")

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

async def duckduckgo_search(params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """
    Perform a web search using DuckDuckGo API.
    
    Args:
        params: Dictionary containing search parameters
        ctx: MCP context object providing access to lifespan resources
        
    Returns:
        Dictionary with search results
    """
    query = params.get("query")
    count = params.get("count", 10)
    offset = params.get("offset", 0)
    page = params.get("page", 1)
    
    if not query:
        logger.error("Query parameter is required")
        raise ValueError("Query parameter is required")
    
    logger.info(f"Searching DuckDuckGo for: {query}")
    
    # We'll use the DuckDuckGo Lite API endpoint which doesn't require an API key
    # This is for demonstration purposes. For production, consider using a proper search API
    url = "https://lite.duckduckgo.com/lite/"
    
    # Create a new HTTP client if lifespan_context is not available
    http_client = None
    close_client = False
    
    try:
        # Try to get the HTTP client from the lifespan context
        if hasattr(ctx, 'lifespan_context') and 'http_client' in ctx.lifespan_context:
            logger.info("Using HTTP client from lifespan context")
            http_client = ctx.lifespan_context["http_client"]
        else:
            # Create a new HTTP client if not available in the context
            logger.info("Creating new HTTP client")
            http_client = httpx.AsyncClient(
                timeout=10.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                }
            )
            close_client = True
        
        # Log the search operation
        if hasattr(ctx, 'info'):
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
        
        # Log the response status and content length
        logger.info(f"Response status: {response.status_code}, Content length: {len(response.text)}")
        
        # Parse the HTML response to extract search results
        # Note: This is a simplified implementation and might break if DuckDuckGo changes their HTML structure
        # For a production service, consider using a more robust solution
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Log the HTML structure to understand what we're working with
        logger.info(f"HTML title: {soup.title.string if soup.title else 'No title'}")
        
        # Log all available table classes to see what's in the response
        tables = soup.find_all("table")
        logger.info(f"Found {len(tables)} tables in the response")
        
        for i, table in enumerate(tables):
            logger.info(f"Table {i} class: {table.get('class', 'No class')}")
        
        # Find all result rows in the HTML
        result_rows = soup.find_all("tr", class_="result-link")
        result_snippets = soup.find_all("tr", class_="result-snippet")
        
        logger.info(f"Found {len(result_rows)} result rows and {len(result_snippets)} result snippets")
        
        # If we didn't find any results with the expected classes, try to find links in a different way
        if len(result_rows) == 0:
            logger.info("No results found with expected classes, trying alternative parsing")
            
            # Try to find all links in the document
            all_links = soup.find_all("a")
            logger.info(f"Found {len(all_links)} links in the document")
            
            # Log the first few links to see what we're working with
            for i, link in enumerate(all_links[:5]):
                logger.info(f"Link {i}: text='{link.text.strip()}', href='{link.get('href', '')}'")
        
        total_results = len(result_rows)
        
        # Report progress to the client if the method is available
        if hasattr(ctx, 'report_progress'):
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
            results.append({
                "title": title,
                "url": url,
                "description": description,
                "published_date": None,
                "domain": domain
            })
            
            # Update progress if the method is available
            if hasattr(ctx, 'report_progress'):
                await ctx.report_progress(i + 1, total_results)
        
        # If we still don't have results, try an alternative approach
        if len(results) == 0:
            logger.info("No results found with standard parsing, trying alternative approach")
            
            # Try to find results in a different way - this is a fallback approach
            # Look for any links that might be search results
            all_links = soup.find_all("a")
            
            # Filter links that look like search results (not navigation links)
            potential_results = [link for link in all_links if link.get('href') and 
                                 not link.get('href').startswith('#') and 
                                 not link.get('href').startswith('/')]
            
            logger.info(f"Found {len(potential_results)} potential result links")
            
            # Take up to 'count' results
            for i, link in enumerate(potential_results[:count]):
                if i >= count:
                    break
                    
                title = link.text.strip()
                url = link.get('href', '')
                domain = extract_domain(url)
                
                # Try to find a description - look for text in the parent or next sibling
                description = ""
                parent = link.parent
                if parent and parent.text and len(parent.text.strip()) > len(title):
                    description = parent.text.strip()
                
                if not description and link.next_sibling:
                    description = link.next_sibling.text.strip() if hasattr(link.next_sibling, 'text') else ""
                
                results.append({
                    "title": title,
                    "url": url,
                    "description": description,
                    "published_date": None,
                    "domain": domain
                })
            
            total_results = len(potential_results)
        
        # Calculate more accurate total_results estimation
        # DuckDuckGo doesn't provide exact total counts, but we can estimate
        # based on pagination and number of results per page
        estimated_total = max(total_results, offset + len(results))
        
        # For pagination purposes, we should always claim there are more results
        # unless we received fewer than requested
        if len(results) >= count:
            estimated_total = max(estimated_total, offset + count + 1)
        
        return {
            "results": results,
            "total_results": estimated_total,
        }
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e}")
        if hasattr(ctx, 'error'):
            await ctx.error(f"HTTP error: {str(e)}")
        raise ValueError(f"HTTP error: {str(e)}") from e
    except httpx.RequestError as e:
        logger.error(f"Request error occurred: {e}")
        if hasattr(ctx, 'error'):
            await ctx.error(f"Request error: {str(e)}")
        raise ValueError(f"Request error: {str(e)}") from e
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        if hasattr(ctx, 'error'):
            await ctx.error(f"Unexpected error: {str(e)}")
        raise ValueError(f"Unexpected error: {str(e)}") from e
    finally:
        # Close the HTTP client if we created it
        if close_client and http_client:
            await http_client.aclose() 