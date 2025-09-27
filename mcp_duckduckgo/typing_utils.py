"""
Modern typing utilities and type guards for enhanced type safety.

This module provides type guards, protocols, and utility functions
to enhance type safety throughout the codebase.
"""

from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeGuard, cast

from bs4 import NavigableString, PageElement, Tag

if TYPE_CHECKING:
    from bs4.element import ResultSet

# Modern type aliases using Literal
SearchTimePeriod = Literal["day", "week", "month", "year"]
ContentType = Literal["wikipedia", "documentation", "news_blog", "generic"]
ValidationResult = Literal[
    "Likely True", "Possibly True", "Inconclusive", "Possibly False", "Likely False"
]
SentimentType = Literal["supporting", "contradicting", "neutral"]


# Protocol definitions for structured typing
class Searchable(Protocol):
    """Protocol for objects that can be searched."""

    def search(self, query: str, count: int = 10) -> Any:
        """Perform a search operation."""
        ...


class Extractable(Protocol):
    """Protocol for objects that support content extraction."""

    def extract_text(self, strip: bool = False) -> str:
        """Extract text content."""
        ...

    def extract_links(self) -> list[str]:
        """Extract links."""
        ...


class Summarizable(Protocol):
    """Protocol for content that can be summarized."""

    @property
    def title(self) -> str:
        """Get the title."""
        ...

    @property
    def content(self) -> str:
        """Get the content."""
        ...

    def summarize(self, max_length: int = 500) -> str:
        """Generate a summary."""
        ...


def is_tag(element: PageElement) -> TypeGuard[Tag]:
    """Type guard to check if a PageElement is a Tag."""
    return hasattr(element, "get") and hasattr(element, "find_all")


def is_navigable_string(element: PageElement) -> TypeGuard[NavigableString]:
    """Type guard to check if a PageElement is a NavigableString."""
    return isinstance(element, NavigableString)


def safe_get_attr(element: PageElement, attr: str, default: Any = None) -> Any:
    """Safely get an attribute from a PageElement."""
    if is_tag(element):
        return element.get(attr, default)
    return default


def safe_get_text(element: PageElement, strip: bool = False) -> str:
    """Safely get text from a PageElement."""
    if hasattr(element, "get_text"):
        return element.get_text(strip=strip)
    elif isinstance(element, str):
        return element.strip() if strip else element
    else:
        return str(element).strip() if strip else str(element)


def safe_find_all(
    element: PageElement, *args: Any, **kwargs: Any
) -> "ResultSet[PageElement]":
    """Safely call find_all on a PageElement."""
    if is_tag(element):
        return element.find_all(*args, **kwargs)
    # Return empty ResultSet-like list
    from bs4.element import ResultSet, SoupStrainer

    return ResultSet(SoupStrainer(), [])


def safe_string_check(value: Any, method: str) -> bool:
    """Safely check if a value has a string method and is not None."""
    return value is not None and isinstance(value, str) and hasattr(value, method)


def ensure_string(value: str | Any, default: str = "") -> str:
    """Ensure a value is a string, with fallback."""
    if isinstance(value, str):
        return value
    elif value is None:
        return default
    else:
        return str(value)


class HTMLElementProtocol:
    """Protocol for HTML elements that support tag-like operations."""

    def get(self, attr: str, default: Any = None) -> Any:
        """Get an attribute value."""
        ...

    def find_all(self, *args: Any, **kwargs: Any) -> "ResultSet[PageElement]":
        """Find all matching elements."""
        return cast("ResultSet[PageElement]", [])

    def get_text(self, strip: bool = False) -> str:
        """Get text content."""
        return ""


def as_tag(element: PageElement) -> Tag:
    """Cast a PageElement to Tag (use only when you're sure it's a Tag)."""
    return cast(Tag, element)


def safe_href_extract(link: PageElement) -> str:
    """Safely extract href from a link element."""
    href = safe_get_attr(link, "href", "")
    return ensure_string(href)
