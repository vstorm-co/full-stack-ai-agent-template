{%- if cookiecutter.web_fetch_tool %}
"""Tests for the fetch_url agent tool."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.tools.fetch_url import (
    _extract_text,
    fetch_url,
)
from app.core.sanitize import SSRFBlockedError


class _FakeResponse:
    """Minimal stand-in for httpx.Response."""

    def __init__(self, *, status_code=200, content=b"", content_type="text/html", encoding="utf-8"):
        self.status_code = status_code
        self.reason_phrase = "OK" if status_code < 400 else "Error"
        self.content = content
        self.encoding = encoding
        self.headers = {"content-type": content_type}


class TestExtractText:
    """_extract_text reduces HTML to readable text."""

    def test_strips_script_style_and_keeps_title(self):
        html = (
            "<html><head><title> Hello World </title>"
            "<style>.x{color:red}</style></head>"
            "<body><script>evil()</script><p>Visible paragraph.</p>"
            "<nav>menu</nav></body></html>"
        )
        out = _extract_text(html, max_chars=8000)
        assert "Title: Hello World" in out
        assert "Visible paragraph." in out
        assert "evil()" not in out
        assert "color:red" not in out
        assert "menu" not in out  # nav stripped

    def test_truncates_long_text(self):
        html = "<html><body><p>" + ("A" * 500) + "</p></body></html>"
        out = _extract_text(html, max_chars=100)
        assert "[... content truncated ...]" in out
        assert len(out) < 300


class TestFetchUrl:
    """fetch_url branching and SSRF handling (network mocked)."""

    @pytest.mark.anyio
    async def test_ssrf_blocked_returns_safe_error(self):
        with patch(
            "app.agents.tools.fetch_url._resolve_safe",
            new=AsyncMock(side_effect=SSRFBlockedError("private address")),
        ):
            result = await fetch_url("http://169.254.169.254/latest/meta-data/")
        assert "blocked for security reasons" in result
        assert "private address" in result

    @pytest.mark.anyio
    async def test_html_page_returns_readable_text(self):
        resp = _FakeResponse(
            content=b"<html><head><title>Doc</title></head><body><p>Body text here.</p></body></html>",
        )
        with patch("app.agents.tools.fetch_url._resolve_safe", new=AsyncMock(return_value=resp)):
            result = await fetch_url("https://example.com")
        assert "Title: Doc" in result
        assert "Body text here." in result

    @pytest.mark.anyio
    async def test_http_error_status(self):
        resp = _FakeResponse(status_code=404, content=b"nope")
        with patch("app.agents.tools.fetch_url._resolve_safe", new=AsyncMock(return_value=resp)):
            result = await fetch_url("https://example.com/missing")
        assert "HTTP 404" in result

    @pytest.mark.anyio
    async def test_plain_text_content_returned(self):
        resp = _FakeResponse(content=b"raw text body", content_type="text/plain")
        with patch("app.agents.tools.fetch_url._resolve_safe", new=AsyncMock(return_value=resp)):
            result = await fetch_url("https://example.com/file.txt")
        assert "raw text body" in result

    @pytest.mark.anyio
    async def test_binary_content_not_returned(self):
        resp = _FakeResponse(content=b"\x89PNG\r\n", content_type="image/png")
        with patch("app.agents.tools.fetch_url._resolve_safe", new=AsyncMock(return_value=resp)):
            result = await fetch_url("https://example.com/img.png")
        assert "not text" in result

{%- endif %}
