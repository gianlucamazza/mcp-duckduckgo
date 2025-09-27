# Vulture whitelist for legitimate API definitions that appear unused
# This file tells vulture to ignore these symbols which are part of our public API

# Config constants - legitimate configuration values
REQUEST_TIMEOUT
DEFAULT_RESULTS_COUNT
MAX_QUERY_LENGTH
MAX_QUERY_WORDS
CACHE_TTL_MAPPING
DEFAULT_USER_AGENT
DUCKDUCKGO_LITE_URL
DEFAULT_SERVER_PORT
DEFAULT_HOST
ENABLE_SEMANTIC_CACHE
ENABLE_KNOWLEDGE_GRAPH
ENABLE_SANDBOX_SNAPSHOTS
ENABLE_CONTENT_EXTRACTION

# Exception classes and utilities - part of public API
ErrorCollector
ErrorCollector.add_error
ErrorCollector.set_context
ErrorCollector.has_errors
ErrorResult
ErrorResult.to_dict

# Knowledge graph utilities
get_local_entity_index

# Type definitions and protocols - part of type system
SearchTimePeriod
ContentType
published_date
relation
target
weight
is_official
FactCheckResult
SummaryResult
word_count
content_length

# Resource functions - part of public API
get_search_docs
get_search_results

# Sandbox functionality
diff

# Cache functionality
mark_domain_stale

# Protocol definitions - type system components
Searchable
search  # Protocol method
Extractable
extract_text  # Protocol method
extract_links  # Protocol method
Summarizable
summarize  # Protocol method
is_navigable_string
safe_string_check
HTMLElementProtocol
as_tag