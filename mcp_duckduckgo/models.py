"""
Data models for the DuckDuckGo search plugin.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# Type aliases for better type safety
SearchTimePeriod = Literal["day", "week", "month", "year"]
SearchIntent = Literal[
    "news",
    "technical",
    "shopping",
    "academic",
    "finance",
    "local",
    "general",
]
ValidationResult = Literal[
    "Likely True", "Possibly True", "Inconclusive", "Possibly False", "Likely False"
]
SentimentType = Literal["supporting", "contradicting", "neutral"]


class SearchResult(BaseModel):
    """A single search result."""

    title: str
    url: str
    description: str
    published_date: str | None = None


class SearchResponse(BaseModel):
    """Response from DuckDuckGo search."""

    results: list[SearchResult]
    total_results: int
    page: int = 1  # Current page number
    total_pages: int = 1  # Total number of pages
    has_next: bool = False  # Whether there are more pages
    has_previous: bool = False  # Whether there are previous pages
    intent: SearchIntent = "general"
    intent_confidence: float = 0.0


class LinkedContent(BaseModel):
    """Content from a linked page discovered through spidering."""

    url: str
    title: str
    content_snippet: str | None = None
    relation: str = "linked"


class KnowledgeGraphNode(BaseModel):
    """A node in the lightweight knowledge graph."""

    id: str
    label: str
    source: str
    score: float = 0.0
    metadata: dict[str, Any] | None = None


class KnowledgeGraphEdge(BaseModel):
    """A relationship edge within the knowledge graph."""

    source: str
    target: str
    relation: str
    weight: float = 0.5
    metadata: dict[str, Any] | None = None


class KnowledgeGraph(BaseModel):
    """Structured representation of entities and relations."""

    nodes: list[KnowledgeGraphNode]
    edges: list[KnowledgeGraphEdge] = Field(default_factory=list)
    provenance: dict[str, Any] | None = None


class DetailedResult(BaseModel):
    """Detailed information about a search result."""

    title: str
    url: str
    description: str
    published_date: str | None = None
    content_snippet: str | None = None  # A snippet of the content
    domain: str | None = None  # The domain of the result
    is_official: bool | None = None  # Whether this is an official source

    # Enhanced metadata
    author: str | None = None  # Author of the content
    keywords: list[str] | None = None  # Keywords or tags
    main_image: str | None = None  # URL of the main image

    # Social metadata
    social_links: dict[str, str] | None = None  # Links to social profiles

    # Spidering results
    related_links: list[str] | None = None  # URLs of related links found on the page
    linked_content: list[LinkedContent] | None = None  # Content from linked pages

    # Content structure
    headings: list[str] | None = None  # Main headings on the page

    # Structured enrichment
    structured_data: dict[str, Any] | None = None
    entities: list[str] | None = None
    knowledge_graph: KnowledgeGraph | None = None


class ValidationSource(BaseModel):
    """Source used for fact validation."""

    url: str
    title: str
    description: str
    sentiment: SentimentType


class FactCheckResult(BaseModel):
    """Result of a fact checking operation."""

    statement: str
    validation_result: ValidationResult
    confidence_score: int = Field(ge=-100, le=100)
    supporting_sources: int
    contradicting_sources: int
    neutral_sources: int
    sources: list[ValidationSource]


class SummaryResult(BaseModel):
    """Result of a webpage summarization."""

    url: str
    title: str
    summary: str
    key_points: list[str] | None = None
    word_count: int
    content_length: int
    headings: list[str] | None = None
    domain: str | None = None
