{%- if cookiecutter.enable_web_search %}
"""Web search tool using Tavily API.

Provides AI agents with the ability to search the web for current information.
Requires TAVILY_API_KEY environment variable.

Get your API key at: https://tavily.com

The tool returns a JSON ``WebSearchResults`` payload (not prose) so the web
frontend can render results richly — clickable titles, domains, snippets —
the same way the chart tool returns a structured spec. Modern LLMs read JSON
tool results fine and can still cite by title/URL.
"""

import asyncio
import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings


class WebSearchResult(BaseModel):
    """A single web search hit."""

    title: str
    url: str
    content: str
    score: float | None = None


class WebSearchResults(BaseModel):
    """Structured web search payload returned by the ``web_search`` tool."""

    kind: Literal["web_search"] = "web_search"
    query: str
    results: list[WebSearchResult] = Field(default_factory=list)


async def web_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
) -> str:
    """Search the web for current information using Tavily.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (1-10, default: 5).
        search_depth: Search depth - "basic" (fast) or "advanced" (thorough).

    Returns:
        A JSON string with the structured results (a ``WebSearchResults``
        payload). Use the titles/URLs to cite sources in your answer; do not
        repeat the raw JSON back to the user.
    """
    try:
        from tavily import AsyncTavilyClient
    except ImportError:
        return "Web search unavailable: the 'tavily' package is not installed."

    try:
        client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
        response = await client.search(
            query=query,
            max_results=min(max_results, 10),
            search_depth=search_depth,
        )
    except Exception as e:
        # Surface a usable message to the agent instead of crashing the turn.
        return f"Web search failed: {e}"

    results = [
        WebSearchResult(
            title=r.get("title") or "Untitled",
            url=r.get("url") or "",
            content=(r.get("content") or "")[:1000],
            score=r.get("score"),
        )
        for r in response.get("results", [])
    ]
    return WebSearchResults(query=query, results=results).model_dump_json()


def parse_web_search(result: str) -> WebSearchResults | None:
    """Parse a ``web_search`` tool result back into a model.

    Returns None when the result is an error/plain string rather than a
    structured payload (the frontend/channel layers fall back to plain text).
    """
    try:
        payload = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or payload.get("kind") != "web_search":
        return None
    try:
        return WebSearchResults.model_validate(payload)
    except ValidationError:
        return None
{%- endif %}
