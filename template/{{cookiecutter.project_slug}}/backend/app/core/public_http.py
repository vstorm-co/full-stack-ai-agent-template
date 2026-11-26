"""HTTP transport for outbound requests that may reach public networks only."""

import asyncio

import httpx

from app.core.sanitize import resolve_public_addresses


class PublicHTTPTransport(httpx.AsyncHTTPTransport):
    """Connect to a validated address while verifying TLS for the original host."""

    def __init__(self) -> None:
        # The pool keys connections by IP after pinning. Avoid reusing a
        # connection across hostnames that resolve to the same address.
        super().__init__(limits=httpx.Limits(max_keepalive_connections=0))

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        addresses = await asyncio.to_thread(resolve_public_addresses, str(request.url))
        extensions = {**request.extensions, "sni_hostname": request.url.raw_host.decode("ascii")}
        for index, address in enumerate(addresses):
            pinned_request = httpx.Request(
                request.method,
                request.url.copy_with(host=address),
                headers=request.headers,
                stream=request.stream,
                extensions=extensions,
            )
            try:
                return await super().handle_async_request(pinned_request)
            except (httpx.ConnectError, httpx.ConnectTimeout):
                if index == len(addresses) - 1:
                    raise
        raise RuntimeError("Public address resolution returned no addresses")
