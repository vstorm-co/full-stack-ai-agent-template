{%- if cookiecutter.enable_web_search %}
"""Tests for the structured web_search tool."""

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.tools.web_search import (
    WebSearchResults,
    parse_web_search,
    web_search,
)

_FAKE_RESPONSE = {
    "results": [
        {
            "title": "Example Domain",
            "url": "https://www.example.com/page",
            "content": "Example content about the topic.",
            "score": 0.91,
        },
        {"title": "Second", "url": "https://docs.example.org", "content": "More info."},
    ]
}


def _patched_tavily(response: dict) -> MagicMock:
    client = MagicMock()
    client.search = AsyncMock(return_value=response)
    module = MagicMock()
    module.AsyncTavilyClient = MagicMock(return_value=client)
    return module


class TestWebSearch:
    @pytest.mark.anyio
    async def test_returns_structured_json(self):
        with patch.dict(sys.modules, {"tavily": _patched_tavily(_FAKE_RESPONSE)}):
            result = await web_search("python testing")
        payload = json.loads(result)
        assert payload["kind"] == "web_search"
        assert payload["query"] == "python testing"
        assert len(payload["results"]) == 2
        assert payload["results"][0]["url"] == "https://www.example.com/page"
        assert payload["results"][0]["score"] == 0.91

    @pytest.mark.anyio
    async def test_empty_results(self):
        with patch.dict(sys.modules, {"tavily": _patched_tavily({"results": []})}):
            result = await web_search("nothing here")
        payload = json.loads(result)
        assert payload["kind"] == "web_search"
        assert payload["results"] == []

    @pytest.mark.anyio
    async def test_missing_tavily_package_returns_message(self):
        with patch.dict(sys.modules, {"tavily": None}):
            result = await web_search("q")
        assert "tavily" in result.lower()
        assert parse_web_search(result) is None

    @pytest.mark.anyio
    async def test_search_error_returns_message(self):
        broken = _patched_tavily(_FAKE_RESPONSE)
        broken.AsyncTavilyClient.return_value.search = AsyncMock(
            side_effect=RuntimeError("rate limited")
        )
        with patch.dict(sys.modules, {"tavily": broken}):
            result = await web_search("q")
        assert "Web search failed" in result
        assert parse_web_search(result) is None


class TestParseWebSearch:
    @pytest.mark.anyio
    async def test_round_trip(self):
        with patch.dict(sys.modules, {"tavily": _patched_tavily(_FAKE_RESPONSE)}):
            result = await web_search("query here")
        parsed = parse_web_search(result)
        assert isinstance(parsed, WebSearchResults)
        assert parsed.query == "query here"
        assert parsed.results[0].title == "Example Domain"

    def test_non_json_returns_none(self):
        assert parse_web_search("Web search failed: boom") is None

    def test_wrong_kind_returns_none(self):
        assert parse_web_search('{"kind": "chart", "results": []}') is None
{%- endif %}
