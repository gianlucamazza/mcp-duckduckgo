"""Tests for utility helpers and typing guards."""

from __future__ import annotations

try:
    from builtins import ExceptionGroup
except ImportError:
    # Python < 3.11 compatibility
    from exceptiongroup import ExceptionGroup
from unittest.mock import AsyncMock, patch

import pytest
from bs4 import BeautifulSoup, NavigableString

from mcp_duckduckgo.exceptions import (
    DuckDuckGoError,
    ErrorCollector,
    ErrorResult,
    handle_multiple_errors,
)
from mcp_duckduckgo.tools.utils import (
    _extract_generic_content,
    extract_author,
    extract_entities,
    extract_keywords,
    extract_main_image,
    extract_metadata,
    extract_related_links,
    extract_social_links,
    extract_structured_data,
    extract_targeted_content,
    spider_links,
)
from mcp_duckduckgo.typing_utils import (
    as_tag,
    ensure_string,
    is_navigable_string,
    is_tag,
    safe_find_all,
    safe_get_attr,
    safe_get_text,
    safe_href_extract,
    safe_string_check,
)


def test_extract_metadata_flags_official(utils_soup: BeautifulSoup) -> None:
    metadata = extract_metadata(utils_soup, "example.gov", "https://example.gov/page")

    assert metadata["description"] == "This page describes official procedures."
    assert metadata["published_date"] == "2023-12-12"
    assert metadata["is_official"] is True

    structured = extract_structured_data(utils_soup)
    assert (
        "meta" in structured
        and structured["meta"]["description"]
        == "This page describes official procedures."
    )


def test_extract_structured_data_json_ld(detail_soup: BeautifulSoup) -> None:
    structured = extract_structured_data(detail_soup)
    assert "json_ld" in structured
    assert structured["json_ld"][0]["@type"] == "NewsArticle"


def test_extract_author_keywords_and_main_image(utils_soup: BeautifulSoup) -> None:
    author = extract_author(utils_soup)
    keywords = extract_keywords(utils_soup)
    image = extract_main_image(utils_soup, "https://docs.example.com/guide")
    social = extract_social_links(utils_soup)

    assert author == "Documentation Team"
    assert keywords == ["alpha", "beta", "gamma"]
    assert image == "https://docs.example.com/main.png"
    assert social == {"twitter": "https://twitter.com/docs"}


def test_extract_targeted_content_variants(utils_soup: BeautifulSoup) -> None:
    doc_snippet, doc_headings = extract_targeted_content(utils_soup, "docs.example.com")
    assert "documentation paragraph" in doc_snippet
    assert doc_headings[0] == "Main Doc Heading"

    wikipedia_html = BeautifulSoup(
        """
        <div id="mw-content-text">
            <p>Wikipedia article paragraph with sufficient detail.</p>
            <p>Another informative paragraph that should be captured.</p>
        </div>
        """,
        "html.parser",
    )
    wiki_snippet, _ = extract_targeted_content(wikipedia_html, "en.wikipedia.org")
    assert "Wikipedia article paragraph" in wiki_snippet

    news_html = BeautifulSoup(
        """
        <article class="article">
            <p>This news article paragraph contains enough characters to qualify.</p>
        </article>
        """,
        "html.parser",
    )
    news_snippet, _ = extract_targeted_content(news_html, "news.example.com")
    assert "news article paragraph" in news_snippet


def test_extract_related_links(utils_soup: BeautifulSoup) -> None:
    links = extract_related_links(
        utils_soup,
        "https://docs.example.com/root",
        "docs.example.com",
        same_domain_only=True,
    )

    assert links == [
        "https://docs.example.com/internal",
        "https://docs.example.com/guide",
    ]

    # allow external links when same_domain_only=False
    all_links = extract_related_links(
        utils_soup,
        "https://docs.example.com/root",
        "docs.example.com",
        same_domain_only=False,
    )
    assert "https://twitter.com/docs" in all_links


def test_typing_utilities(utils_soup: BeautifulSoup) -> None:
    heading = utils_soup.find("h1")
    assert heading is not None
    assert is_tag(heading)
    assert not is_tag("not a tag")

    nav_string = NavigableString("text")
    assert is_navigable_string(nav_string)

    assert safe_get_attr(heading, "class") is None
    assert safe_get_attr("plain", "class", "fallback") == "fallback"

    assert safe_get_text(heading, strip=True) == "Main Doc Heading"
    assert safe_get_text("  spaced  ", strip=True) == "spaced"

    empty_result = safe_find_all("non-tag", "a")
    assert list(empty_result) == []

    anchor = utils_soup.find("a", href=True)
    assert anchor is not None
    assert safe_href_extract(anchor) == "/internal"

    assert ensure_string(None, default="missing") == "missing"
    assert ensure_string(123) == "123"

    assert safe_string_check("value", "lower") is True
    assert safe_string_check(None, "lower") is False

    tag = utils_soup.find("a")
    assert tag is not None
    assert as_tag(tag) is tag


def test_error_handling_utilities() -> None:
    error = DuckDuckGoError("boom", details={"query": "test"})
    result = ErrorResult(error, context="search", recoverable=True)
    as_dict = result.to_dict()
    assert as_dict["error_type"] == "DuckDuckGoError"
    assert as_dict["context"] == "search"
    assert as_dict["recoverable"] is True
    assert as_dict["details"] == {"query": "test"}

    with pytest.raises(ValueError):
        handle_multiple_errors([ValueError("single")], context="single test")

    with pytest.raises(ExceptionGroup) as exc_info:
        handle_multiple_errors(
            [ValueError("first"), RuntimeError("second")], context="multi"
        )
    exceptions = exc_info.value.exceptions
    assert len(exceptions) == 2

    with pytest.raises(ExceptionGroup):
        with ErrorCollector() as collector:
            collector.set_context("batch")
            collector.add_error(ValueError("a"))
            collector.add_error(RuntimeError("b"))

    collector = ErrorCollector()
    collector.add_error(ValueError("only"))
    assert collector.has_errors() is True
    with pytest.raises(ValueError):
        collector.raise_if_errors()


def test_extract_main_image_relative_url() -> None:
    soup = BeautifulSoup(
        """
        <html>
            <body>
                <img src="/images/hero.png" width="600" height="400" />
            </body>
        </html>
        """,
        "html.parser",
    )
    image = extract_main_image(soup, "https://relative.example.com/page")
    assert image == "https://relative.example.com/images/hero.png"


@pytest.mark.asyncio
async def test_spider_links_recurses(mock_context) -> None:
    link_html = """
    <html>
        <head><title>Primary Page</title></head>
        <body>
            <div id="content">
                <p>This is a sufficiently long paragraph to be captured for snippets.</p>
                <a href="https://docs.example.com/child">Child Link</a>
            </div>
        </body>
    </html>
    """

    child_html = """
    <html>
        <head><title>Child Page</title></head>
        <body>
            <div id="content">
                <p>Child content that should be included when spidering.</p>
            </div>
        </body>
    </html>
    """

    class Response:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    http_client = AsyncMock()
    http_client.get.side_effect = [Response(link_html), Response(child_html)]

    with patch(
        "mcp_duckduckgo.tools.utils.extract_related_links",
        side_effect=[["https://docs.example.com/child"], []],
    ):
        contents = await spider_links(
            ["https://docs.example.com/start", "https://other.com/skip"],
            http_client,
            "docs.example.com",
            depth=2,
            max_links_per_page=3,
            same_domain_only=True,
            ctx=mock_context,
        )

    assert len(contents) == 2
    assert contents[0].title == "Primary Page"
    assert contents[1].relation == "nested"
    assert http_client.get.await_count == 2


def test_extract_metadata_paragraph_and_verified() -> None:
    soup = BeautifulSoup(
        """
        <html>
            <head>
                <title>Community Update</title>
            </head>
            <body>
                <p>This paragraph is intentionally long and detailed so that it exceeds the fifty character threshold required for extraction.</p>
                <span>Status: Verified account</span>
                <time datetime="2022-08-01">August 1, 2022</time>
            </body>
        </html>
        """,
        "html.parser",
    )
    metadata = extract_metadata(soup, "example.com", "https://example.com/info")

    assert "intentionally long" in metadata["description"]
    assert metadata["published_date"] == "2022-08-01"
    assert metadata["is_official"] is True


def test_generic_targeted_content_fallback() -> None:
    soup = BeautifulSoup(
        """
        <html>
            <body>
                <div id="content">
                    <p>This generic container paragraph provides adequate length for fallback extraction pathways to trigger.</p>
                </div>
            </body>
        </html>
        """,
        "html.parser",
    )
    snippet, headings = extract_targeted_content(soup, "example.com")
    assert "generic container paragraph" in snippet
    assert headings == []


def test_targeted_content_body_fallback() -> None:
    soup = BeautifulSoup(
        """
        <html>
            <body>
                <p>This fallback paragraph lives directly in the body element and is more than fifty characters long.</p>
            </body>
        </html>
        """,
        "html.parser",
    )
    snippet, _ = extract_targeted_content(soup, "example.com")
    assert "fallback paragraph" in snippet


def test_extract_related_links_deduplicates() -> None:
    soup = BeautifulSoup(
        """
        <a href="/same">Relative</a>
        <a href="https://docs.example.com/same">Duplicate Absolute</a>
        <a href="https://external.com/else">External</a>
        <a href="/same">Repeated</a>
        <a href="#anchor">Anchor</a>
        """,
        "html.parser",
    )

    links = extract_related_links(
        soup,
        "https://docs.example.com/root",
        "docs.example.com",
        same_domain_only=True,
    )

    assert links == ["https://docs.example.com/same"]

    all_links = extract_related_links(
        soup,
        "https://docs.example.com/root",
        "docs.example.com",
        same_domain_only=False,
    )
    assert "https://external.com/else" in all_links


def test_extract_generic_content_prefers_classes() -> None:
    soup = BeautifulSoup(
        """
        <div class="article">
            <p>Class based content that should be gathered by the helper.</p>
        </div>
        """,
        "html.parser",
    )
    parts: list[str] = []
    _extract_generic_content(soup, parts)
    assert any("Class based content" in part for part in parts)


def test_extract_entities_from_headings() -> None:
    headings = ["Important Update", "Agency Notice"]
    text = "Important Update delivered by Agency Director."
    entities = extract_entities(headings, text)
    assert "Important" in entities
    assert "Agency" in entities


@pytest.mark.asyncio
async def test_spider_links_handles_errors(mock_context) -> None:
    http_client = AsyncMock()
    http_client.get.side_effect = RuntimeError("boom")

    results = await spider_links(
        ["https://docs.example.com/broken"],
        http_client,
        "docs.example.com",
        depth=1,
        max_links_per_page=1,
        same_domain_only=True,
        ctx=mock_context,
    )

    assert results == []


@pytest.mark.asyncio
async def test_spider_links_allows_external_links(mock_context) -> None:
    class Response:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    html = """
    <html>
        <head><title>External Page</title></head>
        <body><div id="content"><p>External details.</p></div></body>
    </html>
    """

    http_client = AsyncMock()
    http_client.get.return_value = Response(html)

    with patch("mcp_duckduckgo.tools.utils.extract_related_links", return_value=[]):
        contents = await spider_links(
            ["https://external.com/page"],
            http_client,
            "docs.example.com",
            depth=1,
            max_links_per_page=2,
            same_domain_only=False,
            ctx=mock_context,
        )

    assert contents and contents[0].url == "https://external.com/page"
