"""API versioning utilities and deprecation handling.

This module provides tools for managing API version deprecation:
- Deprecation middleware for entire API versions
- Deprecation decorator for individual endpoints
- RFC 8594 compliant deprecation headers
"""

import logging
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class VersionDeprecationMiddleware(BaseHTTPMiddleware):
    """Middleware to add deprecation headers for deprecated API versions.

    Adds RFC 8594 compliant headers:
    - Deprecation: Indicates the version is deprecated
    - Sunset: Indicates when the version will be removed
    - Link: Points to migration documentation

    Usage in main.py:
        app.add_middleware(
            VersionDeprecationMiddleware,
            deprecated_versions={"v1": {"sunset": "2025-06-01", "link": "/docs/migration/v2"}},
        )
    """

    def __init__(
        self,
        app: ASGIApp,
        deprecated_versions: dict[str, dict[str, str]] | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            deprecated_versions: Dict mapping version prefixes to deprecation info.
                Each entry should have:
                - sunset: ISO date string when version will be removed (optional)
                - link: URL to migration documentation (optional)
                - message: Custom deprecation message (optional)

        Example:
            {
                "v1": {
                    "sunset": "2025-06-01",
                    "link": "https://api.example.com/docs/migration/v2",
                    "message": "Please migrate to API v2",
                }
            }
        """
        super().__init__(app)
        self.deprecated_versions = deprecated_versions or {}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process the request and add deprecation headers if needed."""
        response = await call_next(request)

        # Check if request path matches a deprecated version
        path = request.url.path
        for version, info in self.deprecated_versions.items():
            if f"/api/{version}/" in path or path.endswith(f"/api/{version}"):
                self._add_deprecation_headers(response, version, info)
                self._log_deprecated_usage(request, version)
                break

        return response

    def _add_deprecation_headers(
        self, response: Response, version: str, info: dict[str, str]
    ) -> None:
        """Add RFC 8594 deprecation headers to the response."""
        # Deprecation header - indicates the API is deprecated
        response.headers["Deprecation"] = "true"

        # Sunset header - when the API will be removed
        if sunset := info.get("sunset"):
            # Convert to HTTP date format
            sunset_date = datetime.fromisoformat(sunset)
            response.headers["Sunset"] = sunset_date.strftime("%a, %d %b %Y %H:%M:%S GMT")

        # Link header - documentation for migration
        if link := info.get("link"):
            response.headers["Link"] = f'<{link}>; rel="deprecation"'

        # Custom warning header
        message = info.get("message", f"API {version} is deprecated")
        response.headers["X-API-Deprecation-Warning"] = message

    def _log_deprecated_usage(self, request: Request, version: str) -> None:
        """Log usage of deprecated API version for monitoring."""
        logger.warning(
            "Deprecated API version accessed: %s %s %s",
            version,
            request.method,
            request.url.path,
        )


def deprecated(
    sunset: str | None = None,
    message: str | None = None,
    link: str | None = None,
) -> Callable[..., Any]:
    """Decorator to mark an endpoint as deprecated.

    Adds deprecation headers to responses from the decorated endpoint.
    Use this for deprecating individual endpoints within an active API version.

    Args:
        sunset: ISO date string when endpoint will be removed.
        message: Custom deprecation message.
        link: URL to migration documentation.

    Usage:
        @router.get("/old-endpoint")
        @deprecated(
            sunset="2025-06-01",
            message="Use /new-endpoint instead",
            link="/docs/migration",
        )
        async def old_endpoint():
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get the response from the endpoint
            result = await func(*args, **kwargs)

            # Find Response object in args (FastAPI injects it)
            response = None
            for arg in args:
                if isinstance(arg, Response):
                    response = arg
                    break
            for value in kwargs.values():
                if isinstance(value, Response):
                    response = value
                    break

            # If we have a Response object, add headers
            if response:
                response.headers["Deprecation"] = "true"
                if sunset:
                    sunset_date = datetime.fromisoformat(sunset)
                    response.headers["Sunset"] = sunset_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                if link:
                    response.headers["Link"] = f'<{link}>; rel="deprecation"'
                if message:
                    response.headers["X-API-Deprecation-Warning"] = message

            return result

        # Add deprecation info to OpenAPI schema
        wrapper.__doc__ = (
            f"{func.__doc__ or ''}\n\n"
            f"**DEPRECATED**"
            f"{f': {message}' if message else ''}"
            f"{f' (Sunset: {sunset})' if sunset else ''}"
        )

        return wrapper

    return decorator


# Example usage documentation
"""
## Adding a New API Version

1. Create a new version folder:
   ```
   app/api/routes/v2/
   ├── __init__.py
   ├── health.py
   ├── auth.py
   └── ...
   ```

2. Create the v2 router in `v2/__init__.py`:
   ```python
   from fastapi import APIRouter
   v2_router = APIRouter()
   # Include routes...
   ```

3. Add the v2 router in `app/api/router.py`:
   ```python
   from app.api.routes.v2 import v2_router

   api_router.include_router(v1_router, prefix="/v1")
   api_router.include_router(v2_router, prefix="/v2")
   ```

4. Mark v1 as deprecated in `main.py`:
   ```python
   app.add_middleware(
       VersionDeprecationMiddleware,
       deprecated_versions={
           "v1": {
               "sunset": "2025-12-31",
               "link": "/docs/migration/v2",
               "message": "Please migrate to API v2",
           }
       },
   )
   ```
"""
