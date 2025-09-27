"""Tests for multi-hop orchestration scaffolding."""

from __future__ import annotations

from typing import Any

import pytest

from mcp_duckduckgo.orchestration import Hop, MultiHopOrchestrator, MultiHopPlan


@pytest.mark.asyncio
async def test_plan_enforces_dependencies():
    plan = MultiHopPlan(
        [
            Hop(name="search", tool="search", params={}),
            Hop(name="details", tool="details", params={}, depends_on=("search",)),
        ]
    )
    ordered = [hop.name for hop in plan.ordered_hops()]
    assert ordered == ["search", "details"]


@pytest.mark.asyncio
async def test_orchestrator_executes_in_order():
    async def search_tool(
        *, ctx: Any, state: dict[str, Any], **_: Any
    ) -> dict[str, str]:
        state["search"] = True
        return {"results": ["item"]}

    async def details_tool(*, dependencies: dict[str, Any], **_: Any) -> dict[str, str]:
        assert "search" in dependencies
        return {"detail": dependencies["search"]["results"][0]}

    orchestrator = MultiHopOrchestrator(
        {"search": search_tool, "details": details_tool}
    )
    plan = MultiHopPlan(
        [
            Hop(name="search", tool="search", params={}),
            Hop(name="details", tool="details", params={}, depends_on=("search",)),
        ]
    )

    class DummyCtx:
        pass

    result = await orchestrator.execute(plan, DummyCtx())
    assert "search" in result.results
    assert "details" in result.results
    assert result.results["details"].output["detail"] == "item"
