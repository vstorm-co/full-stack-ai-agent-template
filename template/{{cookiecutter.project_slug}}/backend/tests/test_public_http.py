"""Verify that outbound requests use a validated IP and retain TLS identity."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.public_http import PublicHTTPTransport
from app.core.sanitize import SSRFBlockedError

pytestmark = pytest.mark.anyio


async def test_transport_connects_to_the_resolved_address() -> None:
    request = httpx.Request("GET", "https://example.com:8443/page")
    send = AsyncMock(return_value=httpx.Response(200))
    with (
        patch("app.core.public_http.resolve_public_addresses", return_value=("1.1.1.1",)) as resolve,
        patch.object(httpx.AsyncHTTPTransport, "handle_async_request", send),
    ):
        async with PublicHTTPTransport() as transport:
            response = await transport.handle_async_request(request)

    assert response.status_code == 200
    resolve.assert_called_once_with("https://example.com:8443/page")
    pinned = send.call_args.args[0]
    assert str(pinned.url) == "https://1.1.1.1:8443/page"
    assert pinned.headers["host"] == "example.com:8443"
    assert pinned.extensions["sni_hostname"] == "example.com"


async def test_transport_does_not_send_without_a_validated_address() -> None:
    request = httpx.Request("GET", "https://example.com/page")
    send = AsyncMock()
    with (
        patch("app.core.public_http.resolve_public_addresses", side_effect=SSRFBlockedError),
        patch.object(httpx.AsyncHTTPTransport, "handle_async_request", send),
    ):
        async with PublicHTTPTransport() as transport:
            with pytest.raises(SSRFBlockedError):
                await transport.handle_async_request(request)
    send.assert_not_awaited()
