"""
DuckDuckGo search plugin for Model Context Protocol.

This package provides search functionality using DuckDuckGo.
"""

__version__ = "0.1.1"

# Import main function to make it available at package level
from .intent import detect_query_intent
from .main import main
from .models import DetailedResult, LinkedContent, SearchResponse, SearchResult
from .search import duckduckgo_search, extract_domain
from .server import mcp
from .typing_utils import is_tag, safe_get_attr, safe_get_text

# Import tools
from .tools import (
    dev_search,
    duckduckgo_get_details,
    duckduckgo_related_searches,
    duckduckgo_web_search,
    fact_check,
    location_search,
    summarize_webpage,
)

__all__ = [
    "DetailedResult",
    "LinkedContent",
    "SearchResponse",
    "SearchResult",
    "dev_search",
    "duckduckgo_get_details",
    "duckduckgo_related_searches",
    "duckduckgo_search",
    "duckduckgo_web_search",
    "extract_domain",
    "detect_query_intent",
    "fact_check",
    "is_tag",
    "location_search",
    "main",
    "mcp",
    "safe_get_attr",
    "safe_get_text",
    "summarize_webpage",
]


# Define __main__ entry point
def __main__() -> None:
    main()
