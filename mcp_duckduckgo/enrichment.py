"""Content enrichment pipelines for DuckDuckGo detail results."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from .knowledge_graph import link_entities
from .models import KnowledgeGraph

logger = logging.getLogger("mcp_duckduckgo.enrichment")


def _normalize_entities(entities: Sequence[str] | None) -> list[str]:
    if not entities:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for entity in entities:
        candidate = " ".join(entity.split()).strip()
        if not candidate:
            continue
        lowered = candidate.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(candidate)
    return normalized


async def build_knowledge_graph(
    entities: Sequence[str] | None,
    domain: str | None,
) -> KnowledgeGraph | None:
    """Generate a knowledge graph artifact for a result."""

    normalized = _normalize_entities(entities)
    if not normalized:
        return None

    try:
        return await link_entities(normalized, domain)
    except Exception:
        logger.exception("Failed to construct knowledge graph for %s", domain)
        return None
