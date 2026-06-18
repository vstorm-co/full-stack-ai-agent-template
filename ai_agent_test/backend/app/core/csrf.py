"""CSRF protection middleware for FastAPI.

This module provides CSRF (Cross-Site Request Forgery) protection for
state-changing HTTP methods (POST, PUT, PATCH, DELETE).

The protection works by:
1. Setting a CSRF token in a cookie on initial request
2. Requiring the token to be sent in a header for state-changing requests
3. Comparing the cookie token with the header token

Usage:
    Add to your main.py:

    from app.core.csrf import CSRFMiddleware

    app.add_middleware(CSRFMiddleware)

    For endpoints that should be exempt (e.g., login):

    @router.post("/login", tags=["csrf-exempt"])
    async def login(...):
        ...
"""

import secrets
from typing import Any, ClassVar

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.config import settings


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware.

    Protects against Cross-Site Request Forgery attacks by requiring
    a token to be present in both a cookie and a header for state-changing requests.
    """

    # Methods that require CSRF protection
    PROTECTED_METHODS: ClassVar[set[str]] = {"POST", "PUT", "PATCH", "DELETE"}

    # Cookie settings
    COOKIE_NAME: ClassVar[str] = "csrf_token"
    HEADER_NAME: ClassVar[str] = "X-CSRF-Token"

    # Paths to exclude from CSRF protection
    EXEMPT_PATHS: ClassVar[set[str]] = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/health",
        "/api/v1/ready",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    def __init__(self, app: ASGIApp, **kwargs: Any) -> None:
        super().__init__(app)
        self.exempt_paths: set[str] = set(kwargs.get("exempt_paths", self.EXEMPT_PATHS))
        self.cookie_name: str = kwargs.get("cookie_name", self.COOKIE_NAME)
        self.header_name: str = kwargs.get("header_name", self.HEADER_NAME)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Handle the request and apply CSRF protection."""
        # Skip for exempt paths
        if self._is_exempt(request):
            return await call_next(request)

        # Get or generate CSRF token
        csrf_token = request.cookies.get(self.cookie_name)
        if not csrf_token:
            csrf_token = self._generate_token()

        # Check CSRF for protected methods
        if request.method in self.PROTECTED_METHODS:
            header_token = request.headers.get(self.header_name)

            if not header_token:
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "CSRF token missing",
                        "message": f"Include the '{self.header_name}' header with the CSRF token",
                    },
                )

            if not secrets.compare_digest(csrf_token, header_token):
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "CSRF token invalid",
                        "message": "The CSRF token does not match",
                    },
                )

        # Process the request
        response = await call_next(request)

        # Set CSRF token cookie if not present
        if not request.cookies.get(self.cookie_name):
            response.set_cookie(
                key=self.cookie_name,
                value=csrf_token,
                httponly=False,  # JavaScript needs to read this
                secure=not settings.DEBUG,
                samesite="lax",
                max_age=3600 * 24,  # 24 hours
            )

        return response

    def _is_exempt(self, request: Request) -> bool:
        """Check if the request path is exempt from CSRF protection."""
        path = request.url.path

        # Check exact path matches
        if path in self.exempt_paths:
            return True

        # Check path prefixes
        for exempt in self.exempt_paths:
            if path.startswith(exempt):
                return True

        # Check if endpoint has "csrf-exempt" tag
        route = request.scope.get("route")
        return bool(route and hasattr(route, "tags") and "csrf-exempt" in route.tags)

    @staticmethod
    def _generate_token() -> str:
        """Generate a secure CSRF token."""
        return secrets.token_urlsafe(32)


def get_csrf_token(request: Request) -> str:
    """Get the current CSRF token from cookies or generate a new one.

    Use this in templates or API responses to provide the token to clients.
    """
    token = request.cookies.get(CSRFMiddleware.COOKIE_NAME)
    if not token:
        token = secrets.token_urlsafe(32)
    return token
