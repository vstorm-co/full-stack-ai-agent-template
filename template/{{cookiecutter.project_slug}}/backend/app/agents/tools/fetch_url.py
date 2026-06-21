{%- if cookiecutter.web_fetch_tool %}
"""Fetch-a-URL tool.

LangChain / LangGraph / DeepAgents don't have a model-native web-fetch
capability (only PydanticAI/PydanticDeep do), so this gives them a portable,
SSRF-safe "read this web page" tool.

SSRF protection reuses ``app.core.sanitize.validate_webhook_url`` (scheme +
userinfo + DNS-resolves-to-public-IP checks). Redirects are followed manually
so every hop is re-validated — ``httpx``'s built-in redirect following would
bypass the per-hop check.
"""

import asyncio

import httpx
from bs4 import BeautifulSoup

from app.core.sanitize import SSRFBlockedError, validate_webhook_url

# Keep tool output bounded so a huge page can't blow up the context window.
DEFAULT_MAX_CHARS = 8000
MAX_RESPONSE_BYTES = 5_000_000
MAX_REDIRECTS = 5
REQUEST_TIMEOUT = 15.0
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AI-Agent/1.0; +fetch_url tool)"}


def _extract_text(html: str, max_chars: int) -> str:
    """Reduce an HTML document to readable plain text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    for tag in soup(["nav", "header", "footer", "aside", "form"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    body = soup.body or soup
    text = body.get_text(separator="\n", strip=True)
    # Collapse runs of blank lines produced by stripped tags.
    lines = [ln for ln in (line.strip() for line in text.splitlines()) if ln]
    text = "\n".join(lines)

    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n\n[... content truncated ...]"

    header = f"Title: {title}\n\n" if title else ""
    return header + text


async def _resolve_safe(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """GET ``url``, validating SSRF safety on the initial URL and every redirect."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        validate_webhook_url(current)  # raises SSRFBlockedError / ValueError
        resp = await client.get(current, headers=_HEADERS, follow_redirects=False)
        if resp.is_redirect and "location" in resp.headers:
            current = str(resp.next_request.url) if resp.next_request else resp.headers["location"]
            continue
        return resp
    raise SSRFBlockedError(f"Too many redirects while fetching {url!r}")


async def fetch_url(url: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Fetch a web page and return its readable text content.

    Use this to read a specific URL the user gave you (an article, doc, or
    page) — distinct from web search, which finds pages. Returns the page
    title and main text with markup stripped.

    Args:
        url: The absolute http(s) URL to fetch.
        max_chars: Maximum characters of extracted text to return.

    Returns:
        The page's readable text, or a short error message the agent can act on.
    """
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await _resolve_safe(client, url)
    except SSRFBlockedError as e:
        return f"Could not fetch URL — blocked for security reasons: {e}"
    except (httpx.HTTPError, ValueError) as e:
        return f"Could not fetch URL: {e}"

    if resp.status_code >= 400:
        return f"Could not fetch URL: HTTP {resp.status_code} {resp.reason_phrase}"

    content_type = resp.headers.get("content-type", "").lower()
    raw = resp.content[:MAX_RESPONSE_BYTES]
    if "html" in content_type:
        return _extract_text(raw.decode(resp.encoding or "utf-8", errors="replace"), max_chars)
    if "text/" in content_type or "json" in content_type or "xml" in content_type:
        text = raw.decode(resp.encoding or "utf-8", errors="replace")
        return text[:max_chars] + ("\n\n[... content truncated ...]" if len(text) > max_chars else "")
    return f"Fetched {url} ({content_type or 'unknown type'}); content is not text and was not returned."


{%- endif %}
