"""
Tools for the DuckDuckGo search plugin.
This module contains various tools for searching, summarizing, and validating information.
"""

# Import and re-export the tools from the original file for backward compatibility
from mcp_duckduckgo.tools.location import location_search
from mcp_duckduckgo.tools.search import (
    duckduckgo_get_details,
    duckduckgo_related_searches,
    duckduckgo_web_search,
)
from mcp_duckduckgo.tools.research import duckduckgo_multi_hop_research

# Import and re-export new tools
from mcp_duckduckgo.tools.summarize import summarize_webpage
from mcp_duckduckgo.tools.technical import dev_search
from mcp_duckduckgo.tools.validate import fact_check

__all__ = [
    "dev_search",
    "duckduckgo_get_details",
    "duckduckgo_related_searches",
    "duckduckgo_multi_hop_research",
    "duckduckgo_web_search",
    "fact_check",
    "location_search",
    "summarize_webpage",
]
