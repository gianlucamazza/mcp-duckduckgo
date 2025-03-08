"""
DuckDuckGo search plugin for Model Context Protocol.

This package provides search functionality using DuckDuckGo.
"""

__version__ = "0.1.0"

from .models import SearchResult, SearchResponse
from .search import duckduckgo_search
from .server import mcp
from .tools import duckduckgo_web_search

# Import main function to make it available at package level
from .main import main

__all__ = [
    "SearchResult",
    "SearchResponse",
    "duckduckgo_search",
    "duckduckgo_web_search",
    "mcp",
]

# Define __main__ entry point
def __main__() -> None:
    main()
