"""Tests for knowledge graph enrichment."""

import pytest

from mcp_duckduckgo.knowledge_graph import get_local_entity_index, link_entities


@pytest.mark.asyncio
async def test_link_entities_builds_graph():
    graph = await link_entities(["OpenAI", "DuckDuckGo"], domain="example.com")
    assert graph is not None
    assert any(node.label == "OpenAI" for node in graph.nodes)
    assert any(edge.relation == "mentions" for edge in graph.edges)


def test_local_entity_index_contains_known_entities():
    index = get_local_entity_index()
    assert "openai" in index
    assert index["openai"].identifier.startswith("Q")


@pytest.mark.asyncio
async def test_link_entities_handles_unknown_and_deduplicates():
    graph = await link_entities(
        ["Unknown Entity", "Unknown Entity"], domain="Example.com"
    )
    assert graph is not None
    ids = {node.id for node in graph.nodes}
    assert any(identifier.startswith("E:") for identifier in ids)
    # ensure domain node is present and edge created
    assert any(node.id.startswith("domain:") for node in graph.nodes)
    assert graph.edges and graph.edges[0].relation == "mentions"
