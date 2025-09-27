"""Context utilities for MCP tools."""

from pydantic import BaseModel


class MinimalContext(BaseModel):
    """Minimal context implementation for fallback scenarios."""
    
    pass