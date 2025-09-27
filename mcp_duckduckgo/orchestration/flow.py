"""Declarative multi-hop orchestration primitives."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from mcp.server.fastmcp import Context

ToolCallable = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class Hop:
    """Single tool invocation within a multi-hop plan."""

    name: str
    tool: str
    params: Mapping[str, Any] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()


@dataclass
class HopResult:
    """Execution metadata for a hop."""

    hop: Hop
    output: Any
    metadata: dict[str, Any]


@dataclass
class OrchestrationResult:
    """Aggregated execution outcome and trace."""

    results: dict[str, HopResult]
    trace: list[dict[str, Any]]


class MultiHopPlan:
    """Topologically sorted set of hops with dependency validation."""

    def __init__(self, hops: Iterable[Hop]):
        hop_list = list(hops)
        if not hop_list:
            raise ValueError("MultiHopPlan requires at least one hop")

        names = {hop.name for hop in hop_list}
        if len(names) != len(hop_list):
            raise ValueError("Hop names must be unique")

        for hop in hop_list:
            missing = set(hop.depends_on) - names
            if missing:
                raise ValueError(f"Hop '{hop.name}' depends on unknown hops: {missing}")

        self._hops = hop_list
        self._ordered = self._topological_sort(hop_list)

    @staticmethod
    def _topological_sort(hops: list[Hop]) -> list[Hop]:
        pending = {hop.name: hop for hop in hops}
        resolved: set[str] = set()
        order: list[Hop] = []

        while pending:
            progress = False
            for name, hop in list(pending.items()):
                if set(hop.depends_on).issubset(resolved):
                    order.append(hop)
                    resolved.add(name)
                    pending.pop(name)
                    progress = True
            if not progress:
                raise ValueError("Cycle detected in hop dependencies")

        return order

    def ordered_hops(self) -> list[Hop]:
        return list(self._ordered)


class MultiHopOrchestrator:
    """Execute multi-hop plans with contextual awareness."""

    def __init__(self, tool_registry: Mapping[str, ToolCallable]) -> None:
        self._tools = dict(tool_registry)

    async def execute(
        self,
        plan: MultiHopPlan,
        ctx: Context,
        *,
        shared_state: dict[str, Any] | None = None,
    ) -> OrchestrationResult:
        state = shared_state or {}
        results: dict[str, HopResult] = {}
        trace: list[dict[str, Any]] = []

        for hop in plan.ordered_hops():
            tool_callable = self._resolve_tool(hop.tool)
            dependency_outputs = {name: results[name].output for name in hop.depends_on}

            invocation_params = self._build_invocation_params(
                tool_callable,
                hop,
                ctx,
                dependency_outputs,
                state,
            )

            output = await tool_callable(**invocation_params)
            hop_result = HopResult(
                hop=hop,
                output=output,
                metadata={
                    "dependencies": list(hop.depends_on),
                    "tool": hop.tool,
                },
            )

            results[hop.name] = hop_result
            trace.append(
                {
                    "hop": hop.name,
                    "tool": hop.tool,
                    "depends_on": list(hop.depends_on),
                }
            )

        return OrchestrationResult(results=results, trace=trace)

    def _resolve_tool(self, tool_name: str) -> ToolCallable:
        try:
            return self._tools[tool_name]
        except KeyError as exc:
            raise ValueError(f"Tool '{tool_name}' is not registered") from exc

    @staticmethod
    def _build_invocation_params(
        tool_callable: ToolCallable,
        hop: Hop,
        ctx: Context,
        dependency_outputs: Mapping[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        params = dict(hop.params)
        signature = inspect.signature(tool_callable)

        if "ctx" in signature.parameters and "ctx" not in params:
            params["ctx"] = ctx
        if "dependencies" in signature.parameters and "dependencies" not in params:
            params["dependencies"] = dependency_outputs
        if "state" in signature.parameters and "state" not in params:
            params["state"] = state

        return params
