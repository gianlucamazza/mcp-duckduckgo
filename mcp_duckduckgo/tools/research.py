"""Multi-hop research tooling built on the orchestration primitives."""

import logging
from collections.abc import Sequence
from typing import Any, cast

from mcp.server.fastmcp import Context
from pydantic import Field

from ..models import DetailedResult
from ..orchestration import Hop, MultiHopOrchestrator, MultiHopPlan
from ..sandbox.snapshots import snapshot_store
from ..search import duckduckgo_search
from ..server import mcp
from .search import duckduckgo_get_details
from .summarize import summarize_webpage

logger = logging.getLogger("mcp_duckduckgo.tools.research")


async def _search_hop(
    *,
    query: str,
    count: int,
    intent: str | None,
    ctx: Context,
    state: dict[str, Any],
    **_: Any,
) -> dict[str, Any]:
    """Execute the search phase of the research workflow.

    Args:
        query: The search query
        count: Number of results to retrieve
        intent: Optional search intent classification
        ctx: MCP context
        state: Shared workflow state

    Returns:
        Search results payload
    """
    params = {
        "query": query,
        "count": count,
        "intent": intent or "general",
        "get_related": True,
        "related_count": min(count, 10),
    }
    logger.debug("Executing search hop with params %s", params)
    payload = await duckduckgo_search(params, ctx)
    state["search_payload"] = payload
    return payload


async def _detail_hop(
    *,
    dependencies: dict[str, Any],
    state: dict[str, Any],
    ctx: Context,
    detail_count: int,
    capture_snapshots: bool,
    **_: Any,
) -> list[DetailedResult]:
    """Execute the detail enrichment phase of the research workflow.

    Args:
        dependencies: Results from previous workflow hops
        state: Shared workflow state
        ctx: MCP context
        detail_count: Number of results to enrich with details
        capture_snapshots: Whether to capture page snapshots

    Returns:
        List of detailed result objects
    """
    search_payload = dependencies.get("search", {})
    results = search_payload.get("results", [])
    selected = results[:detail_count]
    detailed: list[DetailedResult] = []

    for item in selected:
        url = item.get("url")
        if not url:
            continue
        detail = await duckduckgo_get_details(
            url=url,
            spider_depth=state.get("spider_depth", 0),
            max_links_per_page=state.get("max_links_per_page", 3),
            same_domain_only=True,
            capture_snapshot=capture_snapshots,
            ctx=ctx,
        )
        detailed.append(detail)

    state["detailed_results"] = detailed
    return detailed


async def _summary_hop(
    *,
    dependencies: dict[str, Any],
    ctx: Context,
    state: dict[str, Any],
    summary_length: int,
    **_: Any,
) -> dict[str, Any]:
    """Execute the summarization phase of the research workflow.

    Args:
        dependencies: Results from previous workflow hops
        ctx: MCP context
        state: Shared workflow state
        summary_length: Maximum length for each summary

    Returns:
        Dictionary containing the generated summaries
    """
    detailed_results: Sequence[DetailedResult] = dependencies.get("details", [])
    if not detailed_results:
        return {"summaries": []}

    summaries = []
    for detail in detailed_results:
        result = await summarize_webpage(
            url=detail.url,
            max_length=summary_length,
            ctx=ctx,
        )
        summaries.append(result)

    state["summaries"] = summaries
    return {"summaries": summaries}


def _build_orchestrator() -> MultiHopOrchestrator:
    """Build the multi-hop orchestrator for research workflows.

    Returns:
        Configured orchestrator with research hop functions
    """
    registry = {
        "search": _search_hop,
        "details": _detail_hop,
        "summary": _summary_hop,
    }
    return MultiHopOrchestrator(cast(Any, registry))


def _build_plan() -> MultiHopPlan:
    """Build the execution plan for the research workflow.

    Returns:
        Multi-hop plan with search -> details -> summary flow
    """
    hops = [
        Hop(
            name="search",
            tool="search",
            params={},
        ),
        Hop(
            name="details",
            tool="details",
            depends_on=("search",),
            params={},
        ),
        Hop(
            name="summary",
            tool="summary",
            depends_on=("details",),
            params={},
        ),
    ]
    return MultiHopPlan(hops)


@mcp.tool()  # pragma: no cover
async def duckduckgo_multi_hop_research(
    query: str = Field(
        ...,
        description="Research query to investigate",
        max_length=400,
    ),
    count: int = Field(
        6,
        ge=1,
        le=15,
        description="Number of initial search results to retrieve",
    ),
    detail_count: int = Field(
        3,
        ge=1,
        le=6,
        description="Number of results to enrich with detailed fetching",
    ),
    summary_length: int = Field(
        300,
        ge=120,
        le=600,
        description="Maximum characters for each summary",
    ),
    capture_snapshots: bool = Field(
        False,
        description="If true, persist snapshots for reproducible auditing",
    ),
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Execute a multi-hop research workflow with enrichment and summarization."""

    orchestrator = _build_orchestrator()
    plan = _build_plan()

    state: dict[str, Any] = {
        "detail_count": detail_count,
        "spider_depth": 0,
        "max_links_per_page": 3,
        "capture_snapshots": capture_snapshots,
    }

    hop_overrides = {
        "search": {"query": query, "count": count, "intent": None},
        "details": {
            "detail_count": detail_count,
            "capture_snapshots": capture_snapshots,
        },
        "summary": {"summary_length": summary_length},
    }

    specialized_plan = MultiHopPlan(
        [
            Hop(
                name=hop.name,
                tool=hop.tool,
                depends_on=hop.depends_on,
                params=cast(Any, hop_overrides.get(hop.name, hop.params)),
            )
            for hop in plan.ordered_hops()
        ]
    )

    result = await orchestrator.execute(specialized_plan, ctx, shared_state=state)

    search_payload = state.get("search_payload", {})
    detailed_results: list[DetailedResult] = state.get("detailed_results", [])
    summaries = state.get("summaries", [])

    snapshot_ids = []
    if capture_snapshots:
        snapshot_ids = [snapshot.id for snapshot in snapshot_store.list_snapshots()]

    aggregate = {
        "query": query,
        "search": search_payload,
        "details": [detail.model_dump() for detail in detailed_results],
        "summaries": [
            summary.model_dump() if hasattr(summary, "model_dump") else summary
            for summary in summaries
        ],
        "trace": result.trace,
        "snapshots": snapshot_ids,
    }

    logger.info(
        "Multi-hop research finished for '%s' with %s details and %s summaries",
        query,
        len(detailed_results),
        len(summaries),
    )

    return aggregate


__all__ = ["duckduckgo_multi_hop_research"]
