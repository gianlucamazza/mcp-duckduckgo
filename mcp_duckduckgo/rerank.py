"""Lightweight semantic reranking for search results."""

from __future__ import annotations

import math
import unicodedata
from collections import Counter
from collections.abc import Iterable

from .models import SearchIntent

_INTENT_DOMAIN_BOOSTS: dict[SearchIntent, set[str]] = {
    "news": {"news", "cnn", "bbc", "reuters", "times", "guardian"},
    "technical": {"docs", "developer", "github", "stackoverflow", "spec"},
    "shopping": {"amazon", "bestbuy", "shop", "store", "price"},
    "academic": {"arxiv", "springer", "nature", "ieee", "acm", "journals"},
    "finance": {"invest", "markets", "finance", "stock", "bloomberg"},
    "local": {"city", "restaurant", "hotel", "map", "tripadvisor"},
    "general": set(),
}


def _normalise(text: str) -> str:
    """Normalize text to lowercase and NFKD form.

    Args:
        text: The text to normalize

    Returns:
        Normalized lowercase text
    """
    return unicodedata.normalize("NFKD", text).lower()


def _tokenise(text: str) -> list[str]:
    """Tokenize text into alphanumeric words.

    Args:
        text: The text to tokenize

    Returns:
        List of alphanumeric tokens
    """
    cleaned = _normalise(text)
    tokens: list[str] = []
    current = []
    for char in cleaned:
        if char.isalnum():
            current.append(char)
        else:
            if current:
                tokens.append("".join(current))
                current.clear()
    if current:
        tokens.append("".join(current))
    return tokens


def score_result(
    query_tokens: Counter[str],
    description_tokens: Counter[str],
    intent: SearchIntent,
    domain: str,
) -> float:
    """Score a search result based on query relevance and intent.

    Combines token overlap, cosine similarity, and domain-based boosting
    to produce a relevance score for ranking.

    Args:
        query_tokens: Token counts from the search query
        description_tokens: Token counts from the result description
        intent: The search intent classification
        domain: The domain of the search result

    Returns:
        A relevance score between 0 and 1+ (domain boost can exceed 1)
    """
    intersection = sum((query_tokens & description_tokens).values())
    if not intersection:
        overlap = 0.0
    else:
        overlap = intersection / max(1, sum(query_tokens.values()))

    domain_score = 0.0
    boosted = _INTENT_DOMAIN_BOOSTS.get(intent, set())
    if boosted:
        domain_lower = domain.lower()
        if any(keyword in domain_lower for keyword in boosted):
            domain_score = 0.15

    magnitude_query = math.sqrt(sum(v * v for v in query_tokens.values())) or 1.0
    magnitude_desc = math.sqrt(sum(v * v for v in description_tokens.values())) or 1.0
    dot = sum(query_tokens[token] * description_tokens[token] for token in query_tokens)
    cosine = dot / (magnitude_query * magnitude_desc)

    return overlap * 0.6 + cosine * 0.4 + domain_score


def rerank_results(
    query: str,
    results: Iterable[dict[str, str]],
    intent: SearchIntent,
) -> list[dict[str, str]]:
    """Rerank search results based on semantic relevance and intent.

    Args:
        query: The original search query
        results: An iterable of search result dictionaries
        intent: The classified search intent

    Returns:
        A list of reranked search results, ordered by relevance score
    """
    query_tokens = Counter(_tokenise(query))
    if not query_tokens:
        return list(results)

    scored = []
    for result in results:
        description = result.get("description", "")
        title = result.get("title", "")
        tokens = Counter(_tokenise(title) + _tokenise(description))
        score = score_result(query_tokens, tokens, intent, result.get("domain", ""))
        scored.append((score, result))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored]
