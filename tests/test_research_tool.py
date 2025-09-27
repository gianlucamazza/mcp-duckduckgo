"""Tests for the multi-hop research tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_duckduckgo.models import (
    DetailedResult,
    KnowledgeGraph,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    SummaryResult,
)
from mcp_duckduckgo.sandbox.snapshots import snapshot_store
from mcp_duckduckgo.tools.research import duckduckgo_multi_hop_research


@pytest.mark.asyncio
async def test_multi_hop_research_workflow(mock_context):
    search_payload = {
        "results": [
            {
                "title": "Result One",
                "url": "https://example.com/1",
                "description": "Summary",
                "domain": "example.com",
            },
            {
                "title": "Result Two",
                "url": "https://example.com/2",
                "description": "Summary",
                "domain": "example.com",
            },
        ],
        "total_results": 2,
        "intent": "general",
        "related_searches": ["Example"],
    }

    knowledge_graph = KnowledgeGraph(
        nodes=[
            KnowledgeGraphNode(
                id="domain:example.com",
                label="example.com",
                source="duckduckgo",
                score=1.0,
            ),
            KnowledgeGraphNode(id="Q1", label="Example", source="wikidata", score=0.9),
        ],
        edges=[
            KnowledgeGraphEdge(
                source="domain:example.com", target="Q1", relation="mentions"
            ),
        ],
    )

    detailed_result = DetailedResult(
        title="Result One",
        url="https://example.com/1",
        description="Detail",
        domain="example.com",
        knowledge_graph=knowledge_graph,
    )

    summary_result = SummaryResult(
        url="https://example.com/1",
        title="Result One",
        summary="A concise summary",
        word_count=100,
        content_length=500,
    )

    async def fake_get_details(*, capture_snapshot: bool, **kwargs):
        if capture_snapshot:
            snapshot_store.record(
                url=kwargs["url"], content="<html></html>", metadata={}
            )
        return detailed_result

    with patch(
        "mcp_duckduckgo.tools.research.duckduckgo_search",
        AsyncMock(return_value=search_payload),
    ) as search_mock:
        with patch(
            "mcp_duckduckgo.tools.research.duckduckgo_get_details",
            side_effect=fake_get_details,
        ):
            with patch(
                "mcp_duckduckgo.tools.research.summarize_webpage",
                AsyncMock(return_value=summary_result),
            ) as summarize_mock:
                result = await duckduckgo_multi_hop_research(
                    query="test query",
                    count=2,
                    detail_count=1,
                    summary_length=200,
                    capture_snapshots=True,
                    ctx=mock_context,
                )

    assert result["query"] == "test query"
    assert result["search"]["total_results"] == 2
    assert len(result["details"]) == 1
    assert result["details"][0]["knowledge_graph"]["nodes"]
    assert len(result["summaries"]) == 1
    assert result["summaries"][0]["summary"] == "A concise summary"
    assert result["snapshots"]
    assert any(trace_entry["hop"] == "search" for trace_entry in result["trace"])

    search_mock.assert_awaited()
    summarize_mock.assert_awaited()
