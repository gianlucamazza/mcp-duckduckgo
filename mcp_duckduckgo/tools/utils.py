"""
Utility functions for DuckDuckGo search tools.

These functions provide common functionality used by multiple tools.
"""

import json
import logging
import urllib.parse
from typing import Any, Optional, Tuple, List, Dict

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import Context

from ..models import LinkedContent
from ..search import extract_domain
from ..typing_utils import (
    safe_get_attr,
    safe_get_text,
    safe_find_all,
    ensure_string,
    safe_href_extract,
)

# Configure logging
logger = logging.getLogger("mcp_duckduckgo.tools.utils")


def extract_metadata(soup: BeautifulSoup, domain: str, url: str) -> dict[str, Any]:
    """Extract metadata from a web page."""
    metadata: dict[str, Any] = {
        "description": "",
        "published_date": None,
        "is_official": False,
    }

    # Try to find description (meta description or first paragraph)
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc:
        content = safe_get_attr(meta_desc, "content")
        if content:
            metadata["description"] = ensure_string(content).strip()
    
    if not metadata["description"]:
        # Try Open Graph description
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc:
            content = safe_get_attr(og_desc, "content")
            if content:
                metadata["description"] = ensure_string(content).strip()
    
    if not metadata["description"]:
        # Try to find the first substantive paragraph
        paragraphs = soup.find_all("p")
        for p in paragraphs:
            p_text = safe_get_text(p, strip=True)
            if p_text and len(p_text) > 50:  # Consider it substantial if > 50 chars
                metadata["description"] = p_text
                break

    # Get publication date if available
    for date_meta in [
        "article:published_time",
        "datePublished",
        "pubdate",
        "date",
        "publishdate",
    ]:
        date_tag = soup.find("meta", attrs={"property": date_meta}) or soup.find(
            "meta", attrs={"name": date_meta}
        )
        if date_tag:
            content = safe_get_attr(date_tag, "content")
            if content:
                metadata["published_date"] = ensure_string(content)
                break

    # If no meta date, try looking for a date in the page content
    if not metadata["published_date"]:
        # Look for common date formats in time tags
        time_tags = soup.find_all("time")
        if time_tags:
            for time_tag in time_tags:
                datetime_attr = safe_get_attr(time_tag, "datetime")
                if datetime_attr:
                    metadata["published_date"] = ensure_string(datetime_attr)
                    break

    # Determine if this is an official source
    # 1. Domain ends with .gov, .edu, or similar
    if domain.endswith((".gov", ".edu", ".org", ".mil")):
        metadata["is_official"] = True
    # 2. "official" in the title or URL
    elif "official" in url.lower():
        metadata["is_official"] = True
    elif soup.title:
        title_text = safe_get_text(soup.title)
        if title_text and "official" in title_text.lower():
            metadata["is_official"] = True
    # 3. Check for verification badges or verified text
    if not metadata["is_official"]:
        verified_elements = soup.find_all(string=lambda text: text and "verified" in str(text).lower())
        if verified_elements:
            metadata["is_official"] = True

    return metadata


def extract_author(soup: BeautifulSoup) -> str | None:
    """Extract author information from a web page."""
    # Try common author meta tags
    for author_meta in ["author", "article:author", "dc.creator", "twitter:creator"]:
        author_tag = soup.find("meta", attrs={"name": author_meta}) or soup.find(
            "meta", attrs={"property": author_meta}
        )
        if author_tag:
            content = safe_get_attr(author_tag, "content")
            if content:
                return ensure_string(content).strip()

    # Try looking for author in structured data
    author_elem = soup.find(["span", "div", "a"], attrs={"class": ["author", "byline"]})
    if author_elem:
        return safe_get_text(author_elem, strip=True)

    # Try looking for an author in rel="author" links
    author_link = soup.find("a", attrs={"rel": "author"})
    if author_link:
        return safe_get_text(author_link, strip=True)

    return None


def extract_keywords(soup: BeautifulSoup) -> list[str] | None:
    """Extract keywords or tags from a web page."""
    keywords = []

    # Try keywords meta tag
    keywords_tag = soup.find("meta", attrs={"name": "keywords"})
    if keywords_tag:
        content = safe_get_attr(keywords_tag, "content")
        if content:
            keywords_text = ensure_string(content).strip()
            keywords = [k.strip() for k in keywords_text.split(",") if k.strip()]

    # Try article:tag meta tags
    tag_tags = soup.find_all("meta", attrs={"property": "article:tag"})
    if tag_tags:
        for tag in tag_tags:
            content = safe_get_attr(tag, "content")
            if content:
                keywords.append(ensure_string(content).strip())

    # Try to find tags in the page content
    if not keywords:
        tag_elements = soup.find_all(
            ["a", "span"], attrs={"class": ["tag", "keyword", "category"]}
        )
        if tag_elements:
            for tag_elem in tag_elements:
                tag_text = safe_get_text(tag_elem, strip=True)
                if tag_text and len(tag_text) < 30:  # Reasonable tag length
                    keywords.append(tag_text)

    return keywords if keywords else None


def extract_main_image(soup: BeautifulSoup, base_url: str) -> str | None:
    """Extract the main image from a web page."""
    # Try Open Graph image
    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image:
        content = safe_get_attr(og_image, "content")
        if content:
            return ensure_string(content)

    # Try Twitter image
    twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
    if twitter_image:
        content = safe_get_attr(twitter_image, "content")
        if content:
            return ensure_string(content)

    # Try schema.org image
    schema_image = soup.find("meta", attrs={"itemprop": "image"})
    if schema_image:
        content = safe_get_attr(schema_image, "content")
        if content:
            return ensure_string(content)

    # Try to find a likely main image - large image at the top of the article
    article = soup.find(
        ["article", "main", "div"], attrs={"class": ["article", "post", "content"]}
    )
    if article:
        images = safe_find_all(article, "img")
        for img in images:
            # Prefer images with width/height attributes that suggest a large image
            src = safe_get_attr(img, "src")
            if src:
                width_attr = safe_get_attr(img, "width")
                height_attr = safe_get_attr(img, "height")
                
                # Try to parse width/height if they exist
                try:
                    width = int(width_attr) if width_attr else 0
                    height = int(height_attr) if height_attr else 0
                except (ValueError, TypeError):
                    width = height = 0
                    
                if width > 300 or height > 200:  # Reasonable size for a main image
                    img_src = ensure_string(src)
                    # Handle relative URLs
                    if img_src.startswith("/"):
                        # Parse the base URL to get the domain
                        parsed_url = urllib.parse.urlparse(base_url)
                        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        img_src = base_domain + img_src
                    return img_src

    # If we still don't have an image, just take the first substantive image
    images = soup.find_all("img")
    for img in images:
        src = safe_get_attr(img, "src")
        if src:
            img_src = ensure_string(src)
            if not img_src.endswith((".ico", ".svg")):
                # Handle relative URLs
                if img_src.startswith("/"):
                    parsed_url = urllib.parse.urlparse(base_url)
                    base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                    img_src = base_domain + img_src
                return img_src

    return None


def extract_social_links(soup: BeautifulSoup) -> dict[str, str] | None:
    """Extract social media links from a web page."""
    social_links: dict[str, str] = {}
    social_platforms = {
        "twitter.com": "twitter",
        "facebook.com": "facebook",
        "linkedin.com": "linkedin",
        "instagram.com": "instagram",
        "github.com": "github",
        "youtube.com": "youtube",
        "medium.com": "medium",
        "tiktok.com": "tiktok",
        "pinterest.com": "pinterest",
    }

    # Find all links that might be social media
    links = soup.find_all("a", href=True)
    for link in links:
        href = safe_href_extract(link)
        if href:
            href_lower = href.lower()
            for platform_url, platform_name in social_platforms.items():
                if platform_url in href_lower:
                    social_links[platform_name] = href
                    break

    return social_links if social_links else None


def extract_targeted_content(soup: BeautifulSoup, domain: str) -> tuple[str, list[str]]:
    """
    Extract content more intelligently based on content type/domain.
    Returns both the content snippet and headings.
    """
    content_snippet = ""
    headings = []

    # Extract headings for structure
    for h_tag in soup.find_all(["h1", "h2", "h3"]):
        heading_text = safe_get_text(h_tag, strip=True)
        if heading_text and len(heading_text) > 3:  # Skip very short headings
            headings.append(heading_text)

    # Use modern pattern matching for site-specific extraction
    content_parts = []
    
    # Determine site type using modern pattern matching
    site_type = None
    if "wikipedia.org" in domain:
        site_type = "wikipedia"
    elif any(docs_site in domain for docs_site in ["docs.", ".docs.", "documentation.", "developer."]):
        site_type = "documentation"
    elif any(news_site in domain for news_site in ["news.", "blog.", "article.", ".com/news", ".com/blog"]):
        site_type = "news_blog"
    else:
        site_type = "generic"

    # Extract content based on site type using pattern matching
    match site_type:
        case "wikipedia":
            # For Wikipedia, grab the first few paragraphs
            content_div = soup.find("div", attrs={"id": "mw-content-text"})
            if content_div:
                paragraphs = safe_find_all(content_div, "p")
                for p in paragraphs[:5]:  # First 5 paragraphs
                    p_text = safe_get_text(p, strip=True)
                    if p_text:
                        content_parts.append(p_text)
                        
        case "documentation":
            # For documentation, focus on the main content area and code samples
            main_content = soup.find(
                ["main", "article", "div"],
                attrs={"class": ["content", "documentation", "article"]},
            )
            if main_content:
                # Get text and preserve code samples
                for elem in safe_find_all(main_content, ["p", "pre", "code"])[:10]:
                    elem_text = safe_get_text(elem, strip=True)
                    if elem_text:
                        if hasattr(elem, 'name') and elem.name in ["pre", "code"]:
                            content_parts.append(f"Code: {elem_text}")
                        else:
                            content_parts.append(elem_text)
                            
        case "news_blog":
            # For news sites, focus on paragraphs within the article container
            article_container = soup.find(
                ["article", "div"], attrs={"class": ["article", "post", "entry", "content"]}
            )
            if article_container:
                paragraphs = safe_find_all(article_container, "p")
                for p in paragraphs[:10]:  # First 10 paragraphs
                    p_text = safe_get_text(p, strip=True)
                    if p_text and len(p_text) > 20:  # Skip very short paragraphs
                        content_parts.append(p_text)
                        
        case _:  # generic or unknown site type
            # Try common content containers
            _extract_generic_content(soup, content_parts)
    
    content_snippet = " ".join(content_parts)

    # If we haven't found suitable content yet, try common content containers
    if not content_snippet:
        # Try common content containers
        for container_id in ["content", "main", "article", "post", "entry"]:
            content_div = soup.find(
                ["div", "article", "main"], attrs={"id": container_id}
            )
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
                content_div = soup.find(
                    ["div", "article", "main"], attrs={"class": container_class}
                )
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
        content_snippet = content_snippet[:2000] + (
            "..." if len(content_snippet) > 2000 else ""
        )

    return content_snippet, headings[:10]  # Limit to 10 headings


def _extract_generic_content(soup: BeautifulSoup, content_parts: list[str]) -> None:
    """Extract generic content from common containers."""
    # Try common content containers by ID
    for container_id in ["content", "main", "article", "post", "entry"]:
        content_div = soup.find(
            ["div", "article", "main"], attrs={"id": container_id}
        )
        if content_div:
            paragraphs = safe_find_all(content_div, "p")
            for p in paragraphs[:10]:
                p_text = safe_get_text(p, strip=True)
                if p_text:
                    content_parts.append(p_text)
            if content_parts:  # Found content, stop searching
                return

    # Try common content classes if we still don't have content
    for container_class in ["content", "main", "article", "post", "entry"]:
        content_div = soup.find(
            ["div", "article", "main"], attrs={"class": container_class}
        )
        if content_div:
            paragraphs = safe_find_all(content_div, "p")
            for p in paragraphs[:10]:
                p_text = safe_get_text(p, strip=True)
                if p_text:
                    content_parts.append(p_text)
            if content_parts:  # Found content, stop searching
                return

    # Fallback to body if we still don't have content
    if soup.body and not content_parts:
        paragraphs = soup.body.find_all("p")
        for p in paragraphs[:10]:
            p_text = safe_get_text(p, strip=True)
            if p_text and len(p_text) > 50:  # Only substantive paragraphs
                content_parts.append(p_text)


def extract_related_links(
    soup: BeautifulSoup, base_url: str, domain: str, same_domain_only: bool = True
) -> list[str]:
    """Extract related links from a web page."""
    related_links = []
    seen_urls = set()

    # Parse the base URL
    parsed_base = urllib.parse.urlparse(base_url)
    base_domain = parsed_base.netloc

    # Find all links
    links = soup.find_all("a", href=True)
    for link in links:
        href = safe_href_extract(link)

        # Skip empty or javascript links
        if not href or href.startswith(("javascript:", "#", "mailto:", "tel:")):
            continue

        # Handle relative URLs
        if href.startswith("/"):
            href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
        elif not href.startswith(("http://", "https://")):
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


def extract_structured_data(soup: BeautifulSoup) -> dict[str, Any]:
    structured: dict[str, Any] = {}

    ld_payloads: list[Any] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        ld_payloads.append(parsed)

    if ld_payloads:
        structured["json_ld"] = ld_payloads

    meta_tags: dict[str, str] = {}
    for meta in soup.find_all("meta"):
        key = safe_get_attr(meta, "name") or safe_get_attr(meta, "property")
        value = safe_get_attr(meta, "content")
        if key and value:
            meta_tags[key.lower()] = ensure_string(value)

    if meta_tags:
        structured["meta"] = meta_tags

    tables: list[dict[str, Any]] = []
    for table in soup.find_all("table"):
        headers = [safe_get_text(th, strip=True) for th in table.find_all("th")]
        rows = []
        for tr in table.find_all("tr"):
            values = [safe_get_text(td, strip=True) for td in tr.find_all("td")]
            if values:
                rows.append(values)
        if rows:
            tables.append({"headers": headers, "rows": rows})

    if tables:
        structured["tables"] = tables

    return structured


async def spider_links(
    links: list[str],
    http_client: httpx.AsyncClient,
    original_domain: str,
    depth: int,
    max_links_per_page: int,
    same_domain_only: bool,
    ctx: Context,
) -> list[LinkedContent]:
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
            if hasattr(ctx, "progress"):
                await ctx.progress(f"Spidering link: {link}")

            response = await http_client.get(link, follow_redirects=True, timeout=10.0)
            response.raise_for_status()

            # Parse the HTML content
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title
            title = safe_get_text(soup.title).strip() if soup.title else "No title"

            # Extract content snippet
            content_snippet, _ = extract_targeted_content(soup, link_domain)

            # Add to linked content
            linked_content.append(
                LinkedContent(url=link, title=title, content_snippet=content_snippet)
            )

            processed_count += 1

            # Spider recursively if depth > 1
            if depth > 1:
                # Extract more links from this page
                next_links = extract_related_links(
                    soup, link, link_domain, same_domain_only
                )

                # Recursively spider these links
                child_content = await spider_links(
                    next_links[:max_links_per_page],
                    http_client,
                    original_domain,
                    depth - 1,
                    max_links_per_page,
                    same_domain_only,
                    ctx,
                )

                # Add child content with appropriate relation
                for child in child_content:
                    child.relation = "nested"
                    linked_content.append(child)

        except Exception as e:
            logger.error(f"Error spidering link {link}: {e}")
            # Continue with other links

    return linked_content


def extract_entities(headings: list[str] | None, text: str) -> list[str]:
    candidates: set[str] = set()

    if headings:
        for heading in headings:
            for token in heading.split():
                if token.istitle() and len(token) > 2:
                    candidates.add(token)

    for sentence in text.split("."):
        for word in sentence.strip().split():
            if word.istitle() and len(word) > 2:
                candidates.add(word)

    return sorted(candidates)
