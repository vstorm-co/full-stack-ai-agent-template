{%- if cookiecutter.enable_antv_charts %}
"""AntV chart MCP server integration.

The AntV ``mcp-server-chart`` sidecar exposes advanced diagram tools (flowchart,
mind-map, org-chart, sankey, fishbone, network, treemap, radar, funnel, ...)
over MCP (streamable HTTP). Each AI framework attaches MCP differently, so this
module exposes one loader per framework family.

All loaders no-op (return ``None`` / ``[]``) when ``ENABLE_ANTV_CHARTS`` is
false, and degrade gracefully (log a warning + return empty) if the sidecar or
adapter is unavailable — so the agent always starts, with or without AntV.
"""

import logging
{%- if cookiecutter.use_langchain or cookiecutter.use_langgraph or cookiecutter.use_deepagents or cookiecutter.use_crewai %}
import threading
{%- endif %}
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

{%- if cookiecutter.use_langchain or cookiecutter.use_langgraph or cookiecutter.use_deepagents %}


def _run_sync(coro: Any) -> Any:
    """Run an async coroutine from sync code, even inside a running event loop.

    MCP tool discovery is async, but agent construction in the LangChain-family
    frameworks is sync. When no loop is running we use ``asyncio.run``; otherwise
    we run the coroutine in a dedicated event loop on a worker thread so we never
    touch a loop that is already running.
    """
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()
{%- endif %}
{%- if cookiecutter.use_pydantic_ai or cookiecutter.use_pydantic_deep %}


def get_antv_toolset() -> Any | None:
    """Return a PydanticAI MCP toolset for the AntV server, or None if disabled.

    PydanticAI connects lazily when the agent runs, so nothing async happens
    here — the toolset is simply handed to ``Agent(toolsets=[...])``.
    """
    if not settings.ENABLE_ANTV_CHARTS:
        return None
    try:
        from pydantic_ai.mcp import MCPServerStreamableHTTP

        return MCPServerStreamableHTTP(settings.ANTV_MCP_URL)
    except Exception as exc:
        logger.warning("AntV MCP toolset unavailable, continuing without it: %s", exc)
        return None
{%- endif %}
{%- if cookiecutter.use_langchain or cookiecutter.use_langgraph or cookiecutter.use_deepagents %}


_antv_langchain_tools: list[Any] | None = None
_antv_langchain_lock = threading.Lock()


def get_antv_langchain_tools() -> list[Any]:
    """Return AntV MCP tools as LangChain tools, or [] if disabled/unavailable.

    Discovery is a blocking MCP round-trip and the assistant is rebuilt on every
    request, so a successful result is memoized for the process lifetime — we
    discover once (the sidecar is long-lived), not on every agent construction.
    A module-level lock makes the check-and-load atomic across the FastAPI
    threadpool, and we cache only on success so a transient failure (e.g. the
    sidecar still warming up) is retried on the next request instead of pinning
    AntV off until the process restarts.
    """
    global _antv_langchain_tools
    if not settings.ENABLE_ANTV_CHARTS:
        return []
    if _antv_langchain_tools is not None:
        return _antv_langchain_tools
    with _antv_langchain_lock:
        if _antv_langchain_tools is not None:
            return _antv_langchain_tools
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient

            async def _load() -> list[Any]:
                client = MultiServerMCPClient(
                    {"antv": {"url": settings.ANTV_MCP_URL, "transport": "streamable_http"}}
                )
                return await client.get_tools()

            _antv_langchain_tools = _run_sync(_load())
            return _antv_langchain_tools
        except Exception as exc:
            logger.warning("AntV MCP tools unavailable, continuing without them: %s", exc)
            return []
{%- endif %}
{%- if cookiecutter.use_crewai %}


_antv_crewai_tools: list[Any] | None = None
_antv_crewai_lock = threading.Lock()


def get_antv_crewai_tools() -> list[Any]:
    """Return AntV MCP tools for CrewAI, or [] if disabled/unavailable.

    ``MCPServerAdapter`` is normally used as a context manager; for a long-lived
    crew we start it once and keep the tools for the life of the process (the
    sidecar is always up). The assistant is rebuilt on every request, so the
    started adapter and its tools are memoized here — without this we would leak
    a new adapter connection per request. A module-level lock makes the
    check-and-start atomic across the FastAPI threadpool (so two racing requests
    can't each start an adapter), and we cache only on success so a transient
    failure is retried — and never leaves a half-started adapter cached.
    """
    global _antv_crewai_tools
    if not settings.ENABLE_ANTV_CHARTS:
        return []
    if _antv_crewai_tools is not None:
        return _antv_crewai_tools
    with _antv_crewai_lock:
        if _antv_crewai_tools is not None:
            return _antv_crewai_tools
        try:
            from crewai_tools import MCPServerAdapter

            server_params = {"url": settings.ANTV_MCP_URL, "transport": "streamable-http"}
            adapter = MCPServerAdapter(server_params)
            adapter.start()
            _antv_crewai_tools = list(adapter.tools)
            return _antv_crewai_tools
        except Exception as exc:
            logger.warning("AntV MCP tools unavailable, continuing without them: %s", exc)
            return []
{%- endif %}
{%- endif %}
