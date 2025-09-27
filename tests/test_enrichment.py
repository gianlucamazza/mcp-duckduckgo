"""Tests for enrichment utilities."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_duckduckgo.enrichment import build_knowledge_graph, _normalize_entities


def test_normalize_entities_strips_and_deduplicates():
    entities = ["  OpenAI  ", "openai", "", "Duck  Duck  Go"]
    normalized = _normalize_entities(entities)
    assert normalized == ["OpenAI", "Duck Duck Go"]


@pytest.mark.asyncio
async def test_build_knowledge_graph_calls_link_entities():
    with patch("mcp_duckduckgo.enrichment.link_entities", AsyncMock(return_value="graph")) as link_mock:
        graph = await build_knowledge_graph(["OpenAI"], domain="example.com")
    assert graph == "graph"
    link_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_build_knowledge_graph_handles_failures(caplog):
    with patch("mcp_duckduckgo.enrichment.link_entities", AsyncMock(side_effect=RuntimeError("boom"))):
        graph = await build_knowledge_graph(["Entity"], domain="domain")
    assert graph is None
    assert any("Failed to construct knowledge graph" in message for message in caplog.text.splitlines())
