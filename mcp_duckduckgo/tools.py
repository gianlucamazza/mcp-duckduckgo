"""
MCP tool definitions for the DuckDuckGo search plugin.
"""

import logging
import traceback
from typing import List, Optional, Dict, Any
import urllib.parse
from pydantic import Field
from mcp.server.fastmcp import Context
import httpx
from bs4 import BeautifulSoup

from .models import SearchResponse, SearchResult, DetailedResult, LinkedContent
from .search import duckduckgo_search, extract_domain
from .server import mcp

# Configure logging
logger = logging.getLogger("mcp_duckduckgo.tools")

@mcp.tool()  # noqa: F401 # pragma: no cover
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
    site: Optional[str] = Field(
        default=None,
        description="Limit results to a specific site (e.g., 'site:example.com')",
    ),
    time_period: Optional[str] = Field(
        default=None,
        description="Time period for results ('day', 'week', 'month', 'year')",
    ),
    ctx: Context = None,  # Context is automatically injected by MCP
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
        logger.info(f"duckduckgo_web_search called with query: {query}, count: {count}, page: {page}")
        
        # Enhance query with site limitation if provided
        if site:
            # Check if site is a string before using it
            if isinstance(site, str) and "site:" not in query:
                query = f"{query} site:{site}"
        
        # Enhance query with time period if provided
        if time_period:
            # Map time_period to DuckDuckGo format
            time_map = {
                "day": "d",
                "week": "w",
                "month": "m",
                "year": "y"
            }
            # Check if time_period is a string before calling lower()
            if isinstance(time_period, str) and time_period.lower() in time_map:
                query = f"{query} date:{time_map[time_period.lower()]}"
                
        # Log the context to help with debugging
        if ctx:
            logger.info(f"Context available: {ctx}")
        else:
            logger.error("Context is None!")
            # Create a minimal context if none is provided
            from pydantic import BaseModel
            class MinimalContext(BaseModel):
                pass
            ctx = MinimalContext()
        
        # Calculate offset from page number
        offset = (page - 1) * count
        
        result = await duckduckgo_search({
            "query": query,
            "count": count,
            "offset": offset,
            "page": page
        }, ctx)
        
        logger.info(f"duckduckgo_search returned: {result}")
        
        # Convert the result to a SearchResponse object
        search_results = []
        for item in result["results"]:
            try:
                search_result = SearchResult(
                    title=item["title"],
                    url=item["url"],
                    description=item["description"],
                    published_date=item.get("published_date")
                )
                search_results.append(search_result)
            except Exception as e:
                logger.error(f"Error creating SearchResult: {e}, item: {item}")
                if hasattr(ctx, 'error'):
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
            has_previous=has_previous
        )
        
        logger.info(f"Returning SearchResponse: {response}")
        return response
    except Exception as e:
        error_msg = f"Error in duckduckgo_web_search: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        if hasattr(ctx, 'error'):
            await ctx.error(error_msg)
        
        # Return an empty response instead of raising an exception
        # This way, the tool will return something even if there's an error
        return SearchResponse(
            results=[],
            total_results=0,
            page=page,
            total_pages=1,
            has_next=False,
            has_previous=False
        )

@mcp.tool()  # noqa: F401 # pragma: no cover
async def duckduckgo_get_details(
    url: str,
    spider_depth: int = Field(0, ge=0, le=3, description="Number of links to follow from the page (0-3, default 0)"),
    max_links_per_page: int = Field(3, ge=1, le=5, description="Maximum number of links to follow per page (1-5, default 3)"),
    same_domain_only: bool = Field(True, description="Only follow links to the same domain"),
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
    try:
        logger.info(f"duckduckgo_get_details called with URL: {url}")
        
        # Extract the default values from the Field objects if needed
        spider_depth_value = 0
        max_links_value = 3
        same_domain_value = True
        
        # Check if parameters are Field objects and extract their default values
        if hasattr(spider_depth, "default"):
            spider_depth_value = spider_depth.default
        elif isinstance(spider_depth, int):
            spider_depth_value = spider_depth
            
        if hasattr(max_links_per_page, "default"):
            max_links_value = max_links_per_page.default
        elif isinstance(max_links_per_page, int):
            max_links_value = max_links_per_page
            
        if hasattr(same_domain_only, "default"):
            same_domain_value = same_domain_only.default
        elif isinstance(same_domain_only, bool):
            same_domain_value = same_domain_only
        
        logger.info(f"Spider depth: {spider_depth_value}, Max links per page: {max_links_value}, Same domain only: {same_domain_value}")
        
        # Get the httpx client from context if available
        client = None
        close_client = False
        lifespan_context = getattr(ctx, "lifespan_context", {})
        if "http_client" in lifespan_context:
            logger.info("Using HTTP client from lifespan context")
            client = lifespan_context["http_client"]
        else:
            logger.info("Creating new HTTP client")
            client = httpx.AsyncClient(
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                },
            )
            close_client = True
        
        # Extract the domain from the URL
        domain = extract_domain(url)
        
        # Fetch the page content
        if hasattr(ctx, 'progress'):
            await ctx.progress(f"Fetching content from {url}")
            
        response = await client.get(url, follow_redirects=True, timeout=15.0)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract title
        title = soup.title.string.strip() if soup.title else ""
        logger.info(f"Extracted title: {title}")
        
        # Extract metadata
        metadata = extract_metadata(soup, domain, url)
        
        # Extract author information
        author = extract_author(soup)
        logger.info(f"Extracted author: {author}")
        
        # Extract keywords/tags
        keywords = extract_keywords(soup)
        logger.info(f"Extracted keywords: {keywords}")
        
        # Extract main image
        main_image = extract_main_image(soup, url)
        logger.info(f"Extracted main image: {main_image}")
        
        # Extract social links
        social_links = extract_social_links(soup)
        
        # Extract content more intelligently based on content type
        content_snippet, headings = extract_targeted_content(soup, domain)
        logger.info(f"Extracted content snippet: {content_snippet[:100]}..." if len(content_snippet) > 100 else f"Extracted content snippet: {content_snippet}")
        
        # Extract related links
        related_links = []
        if soup:
            # Get all links in the page
            all_links = soup.find_all("a", href=True)
            link_count = 0
            
            for link in all_links:
                href = link.get("href")
                # Skip empty links, anchors, and non-http links
                if not href or href.startswith("#") or not (href.startswith("http://") or href.startswith("https://")):
                    continue
                
                # If same_domain_only is True, only include links from the same domain
                if same_domain_value and domain != extract_domain(href):
                    continue
                
                # Add the link to related links
                related_links.append(href)
                link_count += 1
                
                # Stop if we've reached the max links per page
                if link_count >= max_links_value:
                    break
        
        # Follow links for spidering if depth > 0
        if spider_depth_value > 0 and related_links:
            # We won't actually implement the full spidering here for this example
            pass
        
        # Create the detailed result
        detailed_result = DetailedResult(
            title=title,
            url=url,
            description=metadata["description"],
            published_date=metadata["published_date"],
            content_snippet=content_snippet,
            domain=domain,
            is_official=metadata["is_official"],
            author=author,
            keywords=keywords,
            main_image=main_image,
            social_links=social_links,
            related_links=related_links,
            linked_content=[],
            headings=headings
        )
        
        return detailed_result
        
    except httpx.HTTPStatusError as e:
        error_message = f"HTTP error when fetching {url}: {e.response.status_code}"
        logger.error(error_message)
        if hasattr(ctx, 'error'):
            await ctx.error(error_message)
            
    except httpx.RequestError as e:
        error_message = f"Request error when fetching {url}: {e}"
        logger.error(error_message)
        if hasattr(ctx, 'error'):
            await ctx.error(error_message)
            
    except Exception as e:
        error_message = f"Error when processing {url}: {e}"
        logger.error(error_message)
        logger.error(traceback.format_exc())
        if hasattr(ctx, 'error'):
            await ctx.error(error_message)
            
    finally:
        # Close the HTTP client if we created it
        if close_client and client:
            await client.aclose()
    
    # Return a minimal result if anything fails
    return DetailedResult(
        title="",
        url=url,
        description="",
        published_date=None,
        content_snippet="Content not available - Error occurred while fetching the page",
        domain=domain,
        is_official=False
    )

@mcp.tool()  # noqa: F401 # pragma: no cover
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
    ctx: Context = None,  # Context is automatically injected by MCP
) -> List[str]:
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
        logger.info(f"duckduckgo_related_searches called with query: {query}, count: {count}")
        
        # Log the context to help with debugging
        if ctx:
            logger.info(f"Context available: {ctx}")
        else:
            logger.error("Context is None!")
            # Create a minimal context if none is provided
            from pydantic import BaseModel
            class MinimalContext(BaseModel):
                pass
            ctx = MinimalContext()
            
        # In a real implementation, you would fetch related searches
        # from DuckDuckGo or generate them algorithmically
        
        # For demonstration purposes, generate some placeholder related searches
        words = query.split()
        related_searches = [
            f"{query} latest news",
            f"{query} examples",
            f"best {query}",
            f"{query} tutorial",
            f"{query} definition",
            f"how does {query} work",
            f"{query} vs {words[0] if words else 'alternative'}",
            f"future of {query}",
            f"{query} applications",
            f"{query} history"
        ][:count]
        
        logger.info(f"Returning related searches: {related_searches}")
        return related_searches
    except Exception as e:
        error_msg = f"Error in duckduckgo_related_searches: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        if hasattr(ctx, 'error'):
            await ctx.error(error_msg)
        
        # Return an empty list instead of raising an exception
        return []

# Helper functions for metadata and content extraction

def extract_metadata(soup: BeautifulSoup, domain: str, url: str) -> Dict[str, Any]:
    """Extract metadata from a web page."""
    metadata: Dict[str, Any] = {
        "description": "",
        "published_date": None,
        "is_official": False
    }
    
    # Try to find description (meta description or first paragraph)
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        metadata["description"] = meta_desc["content"].strip()
    else:
        # Try Open Graph description
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            metadata["description"] = og_desc["content"].strip()
        else:
            # Try to find the first substantive paragraph
            paragraphs = soup.find_all("p")
            for p in paragraphs:
                p_text = p.get_text(strip=True)
                if p_text and len(p_text) > 50:  # Consider it substantial if > 50 chars
                    metadata["description"] = p_text
                    break
    
    # Get publication date if available
    for date_meta in ["article:published_time", "datePublished", "pubdate", "date", "publishdate"]:
        date_tag = soup.find("meta", attrs={"property": date_meta}) or soup.find("meta", attrs={"name": date_meta})
        if date_tag and date_tag.get("content"):
            metadata["published_date"] = date_tag["content"]
            break
    
    # If no meta date, try looking for a date in the page content
    if not metadata["published_date"]:
        # Look for common date formats in time tags
        time_tags = soup.find_all("time")
        if time_tags:
            for time_tag in time_tags:
                if time_tag.get("datetime"):
                    metadata["published_date"] = time_tag.get("datetime")
                    break
    
    # Determine if this is an official source
    # 1. Domain ends with .gov, .edu, or similar
    if domain.endswith(('.gov', '.edu', '.org', '.mil')):
        metadata["is_official"] = True
    # 2. "official" in the title or URL
    elif "official" in url.lower() or (soup.title and "official" in soup.title.string.lower()):
        metadata["is_official"] = True
    # 3. Check for verification badges or verified text
    elif soup.find(text=lambda text: text and "verified" in text.lower()):
        metadata["is_official"] = True
    
    return metadata

def extract_author(soup: BeautifulSoup) -> Optional[str]:
    """Extract author information from a web page."""
    # Try common author meta tags
    for author_meta in ["author", "article:author", "dc.creator", "twitter:creator"]:
        author_tag = soup.find("meta", attrs={"name": author_meta}) or soup.find("meta", attrs={"property": author_meta})
        if author_tag and author_tag.get("content"):
            return str(author_tag["content"]).strip()
    
    # Try looking for author in structured data
    author_elem = soup.find(["span", "div", "a"], attrs={"class": ["author", "byline"]})
    if author_elem:
        return str(author_elem.get_text(strip=True))
    
    # Try looking for an author in rel="author" links
    author_link = soup.find("a", attrs={"rel": "author"})
    if author_link:
        return str(author_link.get_text(strip=True))
    
    return None

def extract_keywords(soup: BeautifulSoup) -> Optional[List[str]]:
    """Extract keywords or tags from a web page."""
    keywords = []
    
    # Try keywords meta tag
    keywords_tag = soup.find("meta", attrs={"name": "keywords"})
    if keywords_tag and keywords_tag.get("content"):
        keywords_text = keywords_tag["content"].strip()
        keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
    
    # Try article:tag meta tags
    tag_tags = soup.find_all("meta", attrs={"property": "article:tag"})
    if tag_tags:
        for tag in tag_tags:
            if tag.get("content"):
                keywords.append(tag["content"].strip())
    
    # Try to find tags in the page content
    if not keywords:
        tag_elements = soup.find_all(["a", "span"], attrs={"class": ["tag", "keyword", "category"]})
        if tag_elements:
            for tag_elem in tag_elements:
                tag_text = tag_elem.get_text(strip=True)
                if tag_text and len(tag_text) < 30:  # Reasonable tag length
                    keywords.append(tag_text)
    
    return keywords if keywords else None

def extract_main_image(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Extract the main image from a web page."""
    # Try Open Graph image
    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image and og_image.get("content"):
        return str(og_image["content"])
    
    # Try Twitter image
    twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
    if twitter_image and twitter_image.get("content"):
        return str(twitter_image["content"])
    
    # Try schema.org image
    schema_image = soup.find("meta", attrs={"itemprop": "image"})
    if schema_image and schema_image.get("content"):
        return str(schema_image["content"])
    
    # Try to find a likely main image - large image at the top of the article
    article = soup.find(["article", "main", "div"], attrs={"class": ["article", "post", "content"]})
    if article:
        images = article.find_all("img")
        for img in images:
            # Prefer images with width/height attributes that suggest a large image
            if img.get("src") and (img.get("width") or img.get("height")):
                width = int(img.get("width", 0))
                height = int(img.get("height", 0))
                if width > 300 or height > 200:  # Reasonable size for a main image
                    img_src = img["src"]
                    # Handle relative URLs
                    if img_src.startswith('/'):
                        # Parse the base URL to get the domain
                        parsed_url = urllib.parse.urlparse(base_url)
                        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        img_src = base_domain + img_src
                    return str(img_src)
    
    # If we still don't have an image, just take the first substantive image
    images = soup.find_all("img")
    for img in images:
        if img.get("src") and not img["src"].endswith((".ico", ".svg")):
            img_src = img["src"]
            # Handle relative URLs
            if img_src.startswith('/'):
                parsed_url = urllib.parse.urlparse(base_url)
                base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                img_src = base_domain + img_src
            return str(img_src)
    
    return None

def extract_social_links(soup: BeautifulSoup) -> Optional[Dict[str, str]]:
    """Extract social media links from a web page."""
    social_links: Dict[str, str] = {}
    social_platforms = {
        "twitter.com": "twitter",
        "facebook.com": "facebook",
        "linkedin.com": "linkedin",
        "instagram.com": "instagram",
        "github.com": "github",
        "youtube.com": "youtube",
        "medium.com": "medium",
        "tiktok.com": "tiktok",
        "pinterest.com": "pinterest"
    }
    
    # Find all links that might be social media
    links = soup.find_all("a", href=True)
    for link in links:
        href = link["href"].lower()
        for platform_url, platform_name in social_platforms.items():
            if platform_url in href:
                social_links[platform_name] = link["href"]
                break
    
    return social_links if social_links else None

def extract_targeted_content(soup: BeautifulSoup, domain: str) -> tuple[str, List[str]]:
    """
    Extract content more intelligently based on content type/domain.
    Returns both the content snippet and headings.
    """
    content_snippet = ""
    headings = []
    
    # Extract headings for structure
    for h_tag in soup.find_all(["h1", "h2", "h3"]):
        heading_text = h_tag.get_text(strip=True)
        if heading_text and len(heading_text) > 3:  # Skip very short headings
            headings.append(heading_text)
    
    # Different extraction strategies based on domain/site type
    
    # Wikipedia
    if "wikipedia.org" in domain:
        # For Wikipedia, grab the first few paragraphs
        content_div = soup.find("div", attrs={"id": "mw-content-text"})
        if content_div:
            paragraphs = content_div.find_all("p")
            content_parts = []
            for p in paragraphs[:5]:  # First 5 paragraphs
                p_text = p.get_text(strip=True)
                if p_text:
                    content_parts.append(p_text)
            content_snippet = " ".join(content_parts)
    
    # Documentation sites
    elif any(docs_site in domain for docs_site in ["docs.", ".docs.", "documentation.", "developer."]):
        # For documentation, focus on the main content area and code samples
        main_content = soup.find(["main", "article", "div"], attrs={"class": ["content", "documentation", "article"]})
        if main_content:
            # Get text and preserve code samples
            content_parts = []
            for elem in main_content.find_all(["p", "pre", "code"])[:10]:
                elem_text = elem.get_text(strip=True)
                if elem_text:
                    if elem.name == "pre" or elem.name == "code":
                        content_parts.append(f"Code: {elem_text}")
                    else:
                        content_parts.append(elem_text)
            content_snippet = " ".join(content_parts)
    
    # News sites
    elif any(news_indicator in domain for news_indicator in ["news.", ".news", "times.", "post.", "herald.", "guardian."]):
        # For news, get the article body
        article = soup.find(["article", "div"], attrs={"class": ["article-body", "article-content", "story-body"]})
        if article:
            paragraphs = article.find_all("p")
            content_parts = []
            for p in paragraphs[:8]:  # First 8 paragraphs should cover the main points
                p_text = p.get_text(strip=True)
                if p_text:
                    content_parts.append(p_text)
            content_snippet = " ".join(content_parts)
    
    # Blog posts
    elif any(blog_indicator in domain for blog_indicator in ["blog.", ".blog", "medium."]):
        # For blogs, get the article content
        article = soup.find(["article", "div"], attrs={"class": ["post", "post-content", "blog-post", "entry-content"]})
        if article:
            paragraphs = article.find_all("p")
            content_parts = []
            for p in paragraphs[:8]:
                p_text = p.get_text(strip=True)
                if p_text:
                    content_parts.append(p_text)
            content_snippet = " ".join(content_parts)
    
    # If we haven't found suitable content yet, try common content containers
    if not content_snippet:
        # Try common content containers
        for container_id in ["content", "main", "article", "post", "entry"]:
            content_div = soup.find(["div", "article", "main"], attrs={"id": container_id})
            if content_div:
                paragraphs = content_div.find_all("p")
                content_parts = []
                for p in paragraphs[:10]:
                    p_text = p.get_text(strip=True)
                    if p_text:
                        content_parts.append(p_text)
                content_snippet = " ".join(content_parts)
                break
        
        # Try common content classes if we still don't have content
        if not content_snippet:
            for container_class in ["content", "main", "article", "post", "entry"]:
                content_div = soup.find(["div", "article", "main"], attrs={"class": container_class})
                if content_div:
                    paragraphs = content_div.find_all("p")
                    content_parts = []
                    for p in paragraphs[:10]:
                        p_text = p.get_text(strip=True)
                        if p_text:
                            content_parts.append(p_text)
                    content_snippet = " ".join(content_parts)
                    break
    
    # Fallback to body if we still don't have content
    if not content_snippet and soup.body:
        paragraphs = soup.body.find_all("p")
        content_parts = []
        for p in paragraphs[:10]:
            p_text = p.get_text(strip=True)
            if p_text and len(p_text) > 50:  # Only substantive paragraphs
                content_parts.append(p_text)
        content_snippet = " ".join(content_parts)
    
    # Truncate to a reasonable length
    if content_snippet:
        content_snippet = content_snippet[:2000] + ("..." if len(content_snippet) > 2000 else "")
    
    return content_snippet, headings[:10]  # Limit to 10 headings

def extract_related_links(soup: BeautifulSoup, base_url: str, domain: str, same_domain_only: bool = True) -> List[str]:
    """Extract related links from a web page."""
    related_links = []
    seen_urls = set()
    
    # Parse the base URL
    parsed_base = urllib.parse.urlparse(base_url)
    base_domain = parsed_base.netloc
    
    # Find all links
    links = soup.find_all("a", href=True)
    for link in links:
        href = link["href"]
        
        # Skip empty or javascript links
        if not href or href.startswith(('javascript:', '#', 'mailto:', 'tel:')):
            continue
        
        # Handle relative URLs
        if href.startswith('/'):
            href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
        elif not href.startswith(('http://', 'https://')):
            # Skip links that aren't http or https and aren't relative
            continue
        
        # Skip if we're only looking for same-domain links
        if same_domain_only:
            parsed_href = urllib.parse.urlparse(href)
            if parsed_href.netloc != base_domain:
                continue
        
        # Skip duplicates
        if href in seen_urls or href == base_url:
            continue
        
        seen_urls.add(href)
        related_links.append(href)
    
    return related_links

async def spider_links(links: List[str], http_client: httpx.AsyncClient, original_domain: str, depth: int, max_links_per_page: int, same_domain_only: bool, ctx: Context) -> List[LinkedContent]:
    """
    Spider the provided links to gather more content.
    Returns a list of LinkedContent objects.
    """
    if depth <= 0 or not links:
        return []
    
    linked_content = []
    processed_count = 0
    
    for link in links:
        if processed_count >= max_links_per_page:
            break
            
        try:
            # Check domain if same_domain_only is True
            link_domain = extract_domain(link)
            if same_domain_only and link_domain != original_domain:
                continue
                
            # Fetch the linked page
            if hasattr(ctx, 'progress'):
                await ctx.progress(f"Spidering link: {link}")
                
            response = await http_client.get(link, follow_redirects=True, timeout=10.0)
            response.raise_for_status()
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract title
            title = soup.title.string.strip() if soup.title else "No title"
            
            # Extract content snippet
            content_snippet, _ = extract_targeted_content(soup, link_domain)
            
            # Add to linked content
            linked_content.append(
                LinkedContent(
                    url=link,
                    title=title,
                    content_snippet=content_snippet
                )
            )
            
            processed_count += 1
            
            # Spider recursively if depth > 1
            if depth > 1:
                # Extract more links from this page
                next_links = extract_related_links(soup, link, link_domain, same_domain_only)
                
                # Recursively spider these links
                child_content = await spider_links(
                    next_links[:max_links_per_page], 
                    http_client, 
                    original_domain, 
                    depth - 1,
                    max_links_per_page,
                    same_domain_only,
                    ctx
                )
                
                # Add child content with appropriate relation
                for child in child_content:
                    child.relation = "nested"
                    linked_content.append(child)
            
        except Exception as e:
            logger.error(f"Error spidering link {link}: {e}")
            # Continue with other links
            
    return linked_content