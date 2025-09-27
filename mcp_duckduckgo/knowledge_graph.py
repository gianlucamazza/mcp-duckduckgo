"""Offline-friendly knowledge graph enrichment utilities."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .models import KnowledgeGraph, KnowledgeGraphEdge, KnowledgeGraphNode


logger = logging.getLogger("mcp_duckduckgo.knowledge_graph")


@dataclass(frozen=True)
class _EntityRecord:
    identifier: str
    label: str
    source: str
    score: float
    metadata: dict[str, Any]


_LOCAL_ENTITY_INDEX: dict[str, _EntityRecord] = {
    "openai": _EntityRecord(
        identifier="Q24233392",
        label="OpenAI",
        source="wikidata",
        score=0.92,
        metadata={"description": "Artificial intelligence research laboratory"},
    ),
    "duckduckgo": _EntityRecord(
        identifier="Q494180",
        label="DuckDuckGo",
        source="wikidata",
        score=0.9,
        metadata={"description": "Privacy-focused internet search engine"},
    ),
}


def _normalize_entity(entity: str) -> str:
    return " ".join(entity.split()).strip()


def _resolve_entity(entity: str) -> _EntityRecord:
    normalized = _normalize_entity(entity)
    if not normalized:
        raise ValueError("Cannot resolve blank entity")

    cached = _LOCAL_ENTITY_INDEX.get(normalized.lower())
    if cached:
        return cached

    digest = hashlib.sha256(normalized.lower().encode("utf-8")).hexdigest()[:12]
    identifier = f"E:{digest}"
    metadata: dict[str, Any] = {"label": normalized}
    return _EntityRecord(
        identifier=identifier,
        label=normalized,
        source="synthetic",
        score=0.45,
        metadata=metadata,
    )


def _build_domain_node(domain: str) -> KnowledgeGraphNode:
    pretty = domain.lower()
    return KnowledgeGraphNode(
        id=f"domain:{pretty}",
        label=domain,
        source="duckduckgo",
        score=1.0,
        metadata={"type": "domain"},
    )


async def link_entities(
    entities: Sequence[str] | None,
    domain: str | None = None,
) -> KnowledgeGraph | None:
    """Link extracted entities into a lightweight knowledge graph."""

    if not entities:
        return None

    seen: set[str] = set()
    nodes: list[KnowledgeGraphNode] = []
    edges: list[KnowledgeGraphEdge] = []

    domain_node_id: str | None = None
    if domain:
        domain_node = _build_domain_node(domain)
        domain_node_id = domain_node.id
        nodes.append(domain_node)

    for entity in entities:
        normalized = _normalize_entity(entity)
        if not normalized:
            continue

        lowered = normalized.lower()
        if lowered in seen:
            continue

        try:
            record = _resolve_entity(normalized)
        except ValueError:
            logger.debug("Skipping unresolved entity '%s'", entity)
            continue

        seen.add(lowered)
        nodes.append(
            KnowledgeGraphNode(
                id=record.identifier,
                label=record.label,
                source=record.source,
                score=record.score,
                metadata=record.metadata,
            )
        )

        if domain_node_id:
            edges.append(
                KnowledgeGraphEdge(
                    source=domain_node_id,
                    target=record.identifier,
                    relation="mentions",
                    weight=min(1.0, record.score + 0.05),
                    metadata={"evidence": "page"},
                )
            )

    if not nodes:
        return None

    provenance = {"linked_entities": len(nodes) - (1 if domain_node_id else 0)}

    return KnowledgeGraph(nodes=nodes, edges=edges, provenance=provenance)


def get_local_entity_index() -> dict[str, _EntityRecord]:
    """Expose the embedded entity index for testing and diagnostics."""

    return dict(_LOCAL_ENTITY_INDEX)
