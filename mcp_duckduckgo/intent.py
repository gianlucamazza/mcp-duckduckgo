"""Heuristic query intent detection for routing and reporting."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable


_INTENT_KEYWORDS: dict[str, set[str]] = {
    "news": {
        "breaking",
        "headline",
        "latest",
        "today",
        "press release",
        "announcement",
    },
    "technical": {
        "api",
        "documentation",
        "error",
        "stack trace",
        "tutorial",
        "guide",
        "how to",
    },
    "shopping": {
        "buy",
        "price",
        "deal",
        "discount",
        "coupon",
        "review",
    },
    "academic": {
        "paper",
        "study",
        "journal",
        "doi",
        "research",
        "arxiv",
    },
    "local": {
        "near me",
        "closest",
        "nearby",
        "in my area",
        "open now",
        "map",
    },
    "finance": {
        "stock",
        "earnings",
        "forecast",
        "investment",
        "market",
        "share price",
    },
}

_SECONDARY_HINTS: dict[str, set[str]] = {
    "news": {"cnn", "bbc", "reuters", "times"},
    "technical": {"github", "stackoverflow", "rfc", "spec"},
    "shopping": {"amazon", "bestbuy", "walmart", "review"},
    "academic": {"springer", "nature", "ieee", "acm"},
    "local": {"city", "restaurant", "hotel"},
}

_INTENT_ORDER = (
    "news",
    "technical",
    "shopping",
    "academic",
    "finance",
    "local",
)


def _tokenise(query: str) -> Iterable[str]:
    lowered = query.lower()
    return re.findall(r"[\w']+", lowered)


def detect_query_intent(query: str) -> tuple[str, float]:
    tokens = list(_tokenise(query))
    if not tokens:
        return "general", 0.0

    joined = " ".join(tokens)
    scores: Counter[str] = Counter()

    for intent, phrases in _INTENT_KEYWORDS.items():
        for phrase in phrases:
            if phrase in joined:
                scores[intent] += 2

    token_set = set(tokens)
    for intent, hints in _SECONDARY_HINTS.items():
        overlap = token_set & hints
        if overlap:
            scores[intent] += len(overlap)

    if "site:" in joined and "github" in joined:
        scores["technical"] += 1
    if any(token.isdigit() and len(token) == 4 for token in tokens):
        scores["news"] += 0.5

    if not scores:
        return "general", 0.0

    best_intent = max(scores.items(), key=lambda item: (item[1], -_INTENT_ORDER.index(item[0]) if item[0] in _INTENT_ORDER else 0))[0]
    confidence = min(1.0, scores[best_intent] / 4.0)
    return best_intent, round(confidence, 2)
