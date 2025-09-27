"""Tests covering resources, prompts, server lifecycle, and main entry points."""

from __future__ import annotations

import asyncio
import importlib
import signal
import types
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from mcp_duckduckgo.prompts import (
    fact_check_assistant,
    location_search_assistant,
    search_assistant,
    summary_assistant,
    technical_search_assistant,
)
from mcp_duckduckgo.resources import get_search_docs, get_search_results
from mcp_duckduckgo.server import app_lifespan, close_http_client

main_module = importlib.import_module("mcp_duckduckgo.main")


def test_get_search_docs_returns_guide() -> None:
    docs = get_search_docs()
    assert "DuckDuckGo Search API" in docs
    assert "duckduckgo_web_search" in docs


@pytest.mark.asyncio
async def test_get_search_results_formats_output() -> None:
    html = """
    <html>
        <body>
            <table>
                <tr class="result-link"><td><a href="https://example.com/a">Example A</a></td></tr>
                <tr class="result-snippet"><td>Description A</td></tr>
            </table>
        </body>
    </html>
    """

    class Response:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    client = AsyncMock()
    client.post.return_value = Response(html)
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False

    with patch("mcp_duckduckgo.resources.httpx.AsyncClient", return_value=client):
        formatted = await get_search_results("example")

    assert "Search Results for: example" in formatted
    assert "Example A" in formatted


def test_prompts_provide_expected_language() -> None:
    search_prompt = search_assistant("machine learning")
    fact_prompt = fact_check_assistant("The sky is green")
    tech_prompt = technical_search_assistant("asyncio", language="Python")
    location_prompt = location_search_assistant("coffee shops", "Milan")
    summary_prompt = summary_assistant("https://example.com")

    assert "machine learning" in search_prompt
    assert "fact_check" in fact_prompt
    assert "Python" in tech_prompt
    assert "Milan" in location_prompt
    assert "summarize_webpage" in summary_prompt


@pytest.mark.asyncio
async def test_app_lifespan_initializes_and_cleans_up() -> None:
    client = AsyncMock()
    client.aclose = AsyncMock()

    with patch("mcp_duckduckgo.server.httpx.AsyncClient", return_value=client):
        async with app_lifespan(MagicMock()) as resources:
            assert resources["http_client"] is client

    client.aclose.assert_awaited()


@pytest.mark.asyncio
async def test_close_http_client_handles_existing_client() -> None:
    from mcp_duckduckgo import server as server_module

    server_module.http_client = AsyncMock()
    await close_http_client()
    assert server_module.http_client is None


class LoopStub:
    def __init__(self) -> None:
        self.ran = False

    def is_running(self) -> bool:
        return False

    def run_until_complete(self, coro) -> None:
        asyncio.run(coro)
        self.ran = True


class ImmediateThread:
    def __init__(self, target, daemon=False) -> None:
        self._target = target
        self.daemon = daemon
        self.started = False

    def start(self) -> None:
        self.started = True
        self._target()


def test_signal_handler_closes_client_and_exits(monkeypatch) -> None:
    close_called = False

    async def close_http_client() -> None:
        nonlocal close_called
        close_called = True

    main_module.server_module = types.SimpleNamespace(
        close_http_client=close_http_client
    )
    main_module.is_shutting_down = False
    main_module.last_interrupt_time = 0

    with patch("mcp_duckduckgo.main.asyncio.get_event_loop", return_value=LoopStub()):
        with patch("mcp_duckduckgo.main.threading.Thread", ImmediateThread):
            with patch("mcp_duckduckgo.main.os._exit") as mock_exit:
                with patch("mcp_duckduckgo.main.time.sleep", return_value=None):
                    main_module.signal_handler(signal.SIGINT, None)

    assert close_called is True
    mock_exit.assert_called_once()
    main_module.server_module = None


def test_main_handles_keyboard_interrupt(monkeypatch) -> None:
    close_called = False

    async def close_http_client() -> None:
        nonlocal close_called
        close_called = True

    stub_loop = LoopStub()
    fake_mcp = MagicMock()
    fake_mcp.run.side_effect = KeyboardInterrupt

    with patch("mcp_duckduckgo.main.signal.signal"):
        with patch("mcp_duckduckgo.main.initialize_mcp", return_value=fake_mcp):
            with patch(
                "mcp_duckduckgo.main.asyncio.get_event_loop", return_value=stub_loop
            ):
                main_module.server_module = types.SimpleNamespace(
                    close_http_client=close_http_client
                )
                main_module.is_shutting_down = False
                main_module.last_interrupt_time = 0
                main_module.main()

    assert close_called is True
    assert stub_loop.ran is True
    main_module.server_module = None


def test_main_propagates_unexpected_errors() -> None:
    with patch("mcp_duckduckgo.main.signal.signal"):
        with patch(
            "mcp_duckduckgo.main.initialize_mcp", side_effect=RuntimeError("boom")
        ):
            with pytest.raises(RuntimeError):
                main_module.main()


def test_main_runs_until_system_exit() -> None:
    fake_mcp = MagicMock()
    fake_mcp.run.side_effect = SystemExit

    with patch("mcp_duckduckgo.main.signal.signal"):
        with patch("mcp_duckduckgo.main.initialize_mcp", return_value=fake_mcp):
            with pytest.raises(SystemExit):
                main_module.main()

    main_module.server_module = None
    main_module.mcp_instance = None


class RunningLoopStub:
    def __init__(self) -> None:
        self.is_running_called = False

    def is_running(self) -> bool:
        self.is_running_called = True
        return True

    def run_until_complete(
        self, coro
    ) -> None:  # pragma: no cover - not used in this scenario
        raise AssertionError(
            "run_until_complete should not be called when loop is running"
        )


def test_signal_handler_with_running_loop(monkeypatch) -> None:
    created_tasks = []

    async def close_http_client() -> None:
        return None

    running_loop = RunningLoopStub()
    main_module.server_module = types.SimpleNamespace(
        close_http_client=close_http_client
    )
    main_module.is_shutting_down = False
    main_module.last_interrupt_time = 0

    def create_task_stub(coro):
        created_tasks.append(coro)
        asyncio.run(coro)
        return coro

    with patch("mcp_duckduckgo.main.asyncio.get_event_loop", return_value=running_loop):
        with patch(
            "mcp_duckduckgo.main.asyncio.create_task", side_effect=create_task_stub
        ):
            with patch("mcp_duckduckgo.main.threading.Thread", ImmediateThread):
                with patch("mcp_duckduckgo.main.os._exit") as mock_exit:
                    with patch("mcp_duckduckgo.main.time.sleep", return_value=None):
                        main_module.signal_handler(signal.SIGINT, None)

    assert running_loop.is_running_called is True
    assert len(created_tasks) == 1
    mock_exit.assert_called_once()
    main_module.server_module = None


def test_signal_handler_forced_exit(monkeypatch) -> None:
    main_module.server_module = None
    main_module.is_shutting_down = True
    main_module.last_interrupt_time = 0.1

    with patch("mcp_duckduckgo.main.threading.Thread", ImmediateThread):
        with patch("mcp_duckduckgo.main.os._exit") as mock_exit:
            with patch("mcp_duckduckgo.main.time.sleep", return_value=None):
                main_module.signal_handler(signal.SIGINT, None)

    assert any(call.args and call.args[0] == 1 for call in mock_exit.call_args_list)
    main_module.server_module = None
