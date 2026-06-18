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
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


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
