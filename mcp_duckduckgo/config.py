"""Centralized configuration for the DuckDuckGo MCP plugin."""

# Default timeout settings
DEFAULT_TIMEOUT = 10.0
REQUEST_TIMEOUT = 15.0

# Search configuration
MAX_RESULTS_PER_REQUEST = 20
DEFAULT_RESULTS_COUNT = 10
MAX_QUERY_LENGTH = 400
MAX_QUERY_WORDS = 50

# Cache TTL settings by intent (in seconds)
CACHE_TTL_MAPPING: dict[str, int] = {
    "news": 900,  # 15 minutes for news
    "general": 3600,  # 1 hour for general queries
    "technical": 86400,  # 24 hours for technical docs
    "shopping": 3600,  # 1 hour for shopping
    "academic": 86400,  # 24 hours for academic content
    "finance": 1800,  # 30 minutes for finance
    "local": 3600,  # 1 hour for local searches
}

# User agent for HTTP requests
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)

# DuckDuckGo endpoint
DUCKDUCKGO_LITE_URL = "https://lite.duckduckgo.com/lite/"

# Server configuration
DEFAULT_SERVER_PORT = 3000
DEFAULT_HOST = "localhost"

# Feature flags
ENABLE_SEMANTIC_CACHE = True
ENABLE_KNOWLEDGE_GRAPH = True
ENABLE_SANDBOX_SNAPSHOTS = True
ENABLE_CONTENT_EXTRACTION = True
