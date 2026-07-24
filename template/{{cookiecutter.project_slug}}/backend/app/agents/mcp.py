"""MCP server toolsets for the assistant agent.

Two kinds of servers end up here as uniform :class:`McpServerSpec` entries:
  - deployment-managed servers from ``settings.MCP_SERVERS``, and
  - per-user connections configured in Settings → Integrations
    (built by :mod:`app.services.mcp_connection`).

Each spec is probed with a short ``tools/list`` round-trip before the turn;
unreachable servers are skipped (with a warning) instead of failing the chat,
because pydantic-ai enters every toolset when the run starts and a dead
server would otherwise abort the whole turn.

The transport (streamable HTTP or SSE) is inferred from each server's URL, so
SSE-only servers such as Atlassian/Jira work alongside streamable-HTTP ones.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.core.sanitize import validate_webhook_url

logger = logging.getLogger(__name__)


class McpProbeError(Exception):
    """A failed liveness probe, with its root cause already unwrapped.

    The MCP client runs on anyio task groups, so a failure surfaces as a
    (possibly ``BaseException``-carrying) group that ``except Exception``
    would miss. :func:`probe_mcp_server` collapses those into this type so
    every caller can handle a dead server with a plain ``except Exception``.
    """


async def validate_mcp_url(url: str) -> str:
    """SSRF-check a URL before we talk to it (same policy as webhooks).

    Applies to every URL we request, not just the one the user typed: OAuth
    discovery hands us endpoints the remote server chose, and those deserve
    the same check. Runs in a thread because validation resolves DNS.
    """
    return await asyncio.to_thread(validate_webhook_url, url)


@dataclass(frozen=True)
class McpToolInfo:
    """One tool advertised by an MCP server (for the /test endpoint and UI)."""

    name: str
    description: str


@dataclass(frozen=True)
class McpServerSpec:
    """Transport-level description of one MCP server to attach to a run."""

    name: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    # None = expose every tool the server offers.
    allowed_tools: list[str] | None = None


def static_server_specs() -> list[McpServerSpec]:
    """Specs for the deployment-managed servers from ``MCP_SERVERS``."""
    return [
        McpServerSpec(
            name=cfg.name,
            url=cfg.url,
            headers=cfg.headers,
            allowed_tools=cfg.allowed_tools,
        )
        for cfg in settings.MCP_SERVERS
    ]


@asynccontextmanager
async def _mcp_transport(
    url: str, headers: dict[str, str] | None
) -> AsyncIterator[tuple[Any, Any]]:
    """Open the right client transport for *url*, yielding ``(read, write)``.

    The transport is inferred from the URL exactly as the toolset layer does it
    (FastMCP): a path segment ``/sse`` selects the SSE client (used by servers
    like Atlassian/Jira), everything else uses streamable HTTP. The streamable
    client yields a third session-id callable we don't need here.
    """
    from pydantic_ai.mcp import infer_transport_type_from_url

    if infer_transport_type_from_url(url) == "sse":
        from mcp.client.sse import sse_client

        async with sse_client(url, headers=headers or None) as (read, write):
            yield read, write
    else:
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(url, headers=headers or None) as (read, write, _):
            yield read, write


async def probe_mcp_server(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
) -> list[McpToolInfo]:
    """Connect to an MCP server and list its tools.

    Any failure is raised as :class:`McpProbeError` with the root cause already
    unwrapped, so callers can skip a dead server with ``except Exception``.
    Cancellation always propagates.

    Used both as the pre-flight liveness check before a chat turn and as the
    backing call for the connection "test" endpoint. The transport (streamable
    HTTP or SSE) is inferred from the URL, matching the toolset layer.
    """
    from mcp import ClientSession

    try:
        async with asyncio.timeout(timeout or settings.MCP_CONNECT_TIMEOUT_SECS):
            async with (
                _mcp_transport(url, headers) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                result = await session.list_tools()
    except (Exception, BaseExceptionGroup) as exc:
        if _carries_base_exception(exc):
            raise
        raise McpProbeError(probe_error_message(exc)) from exc
    return [McpToolInfo(name=t.name, description=t.description or "") for t in result.tools]


def _carries_base_exception(exc: BaseException) -> bool:
    """True when *exc* is (or wraps) something that isn't an ``Exception``.

    A group carrying a ``CancelledError`` means the turn was cancelled, not
    that the server is down — swallowing it would keep the run alive.
    """
    if isinstance(exc, BaseExceptionGroup):
        return any(_carries_base_exception(inner) for inner in exc.exceptions)
    return not isinstance(exc, Exception)


def probe_error_message(exc: BaseException) -> str:
    """Human-readable reason for a failed probe.

    The MCP client runs on anyio task groups, so failures surface as nested
    ExceptionGroups ("unhandled errors in a TaskGroup") — unwrap to the root
    cause before showing anything to a user.
    """
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    if isinstance(exc, TimeoutError):
        return f"Connection timed out after {settings.MCP_CONNECT_TIMEOUT_SECS:g}s"
    return str(exc) or exc.__class__.__name__


def _tool_prefix(name: str) -> str:
    """Connection name → tool prefix, e.g. "github-work" → "github_work"."""
    return re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_") or "mcp"


def _make_toolset(spec: McpServerSpec) -> Any:
    """Build a pydantic-ai toolset for one MCP server.

    Tools are prefixed with the connection name so two servers exposing the
    same tool name can't collide (pydantic-ai raises on duplicates). The
    allowlist filter runs before prefixing, so it compares against the
    unprefixed names the user picked in the UI.
    """
    from pydantic_ai.mcp import MCPToolset

    server: Any = MCPToolset(
        spec.url,
        headers=spec.headers or None,
        id=f"mcp:{spec.name}",
        init_timeout=settings.MCP_CONNECT_TIMEOUT_SECS,
    )
    if spec.allowed_tools is not None:
        allowed = set(spec.allowed_tools)
        server = server.filtered(lambda _ctx, tool: tool.name in allowed)
    return server.prefixed(_tool_prefix(spec.name))


def _dedupe_by_prefix(specs: list[McpServerSpec]) -> list[McpServerSpec]:
    """Drop specs whose tool prefix an earlier spec already claimed.

    Two servers sharing a prefix emit identical tool names and pydantic-ai
    raises on duplicates, which aborts the whole turn. Deployment-managed
    servers come first, so they win over a user connection that happens to
    pick the same name (e.g. both called "github").
    """
    unique: list[McpServerSpec] = []
    taken: set[str] = set()
    for spec in specs:
        prefix = _tool_prefix(spec.name)
        if prefix in taken:
            logger.warning(
                "Skipping MCP server %r: tool prefix %r is already used by another server",
                spec.name,
                prefix,
            )
            continue
        taken.add(prefix)
        unique.append(spec)
    return unique


async def build_mcp_toolsets(specs: list[McpServerSpec]) -> list[Any]:
    """Toolsets for every reachable server in *specs* (probed concurrently)."""
    specs = _dedupe_by_prefix(specs)
    if not specs:
        return []

    async def _try(spec: McpServerSpec) -> Any | None:
        try:
            await probe_mcp_server(spec.url, spec.headers)
        except Exception as exc:
            logger.warning(
                "Skipping MCP server %r for this turn: %s", spec.name, probe_error_message(exc)
            )
            return None
        return _make_toolset(spec)

    results = await asyncio.gather(*(_try(spec) for spec in specs))
    return [toolset for toolset in results if toolset is not None]
