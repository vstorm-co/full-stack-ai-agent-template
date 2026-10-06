"""Tests for core modules."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

{%- if cookiecutter.enable_rate_limiting %}
import contextlib

import pytest
from fastapi import HTTPException
{%- endif %}

from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsError,
    AppException,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from app.core.middleware import RequestIDMiddleware
{%- if cookiecutter.enable_caching %}
from app.core.cache import setup_cache
{%- endif %}
{%- if cookiecutter.enable_rate_limiting %}
from app.services.rate_limit import DEFAULT_RATE_LIMITS, RateLimitCategory, check_rate_limit
{%- endif %}
{%- if cookiecutter.enable_logfire %}
from unittest.mock import patch

from fastapi import FastAPI

from app.core.logfire_setup import instrument_app, setup_logfire
{%- endif %}


class TestSettings:
    """Tests for settings configuration."""

    def test_project_name_is_set(self):
        """Test project name is configured."""
        assert settings.PROJECT_NAME == "{{ cookiecutter.project_name }}"

    def test_api_v1_str_is_set(self):
        """Test API version string is set."""
        assert settings.API_V1_STR == "/api/v1"

    def test_debug_mode_default(self):
        """Test debug mode has default value."""
        assert isinstance(settings.DEBUG, bool)

{%- if cookiecutter.enable_cors %}
    def test_cors_origins_is_list(self):
        """Test CORS origins is a list."""
        assert isinstance(settings.CORS_ORIGINS, list)
{%- endif %}


class TestExceptions:
    """Tests for custom exceptions."""

    def test_app_exception(self):
        """Test AppException initialization."""
        error = AppException(message="Test error", code="TEST_ERROR")
        assert error.message == "Test error"
        assert error.code == "TEST_ERROR"
        assert str(error) == "Test error"

    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError(message="Item not found")
        assert error.status_code == 404
        assert error.code == "NOT_FOUND"

    def test_already_exists_error(self):
        """Test AlreadyExistsError."""
        error = AlreadyExistsError(message="Item already exists")
        assert error.status_code == 409
        assert error.code == "ALREADY_EXISTS"

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError(message="Invalid credentials")
        assert error.status_code == 401
        assert error.code == "AUTHENTICATION_ERROR"

    def test_authorization_error(self):
        """Test AuthorizationError."""
        error = AuthorizationError(message="Not authorized")
        assert error.status_code == 403
        assert error.code == "AUTHORIZATION_ERROR"

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError(message="Invalid input")
        assert error.status_code == 422
        assert error.code == "VALIDATION_ERROR"


{%- if cookiecutter.enable_caching %}


class TestCacheSetup:
    """Tests for cache setup."""

    def test_setup_cache_function_exists(self):
        """Test setup_cache function exists."""
        assert setup_cache is not None
        assert callable(setup_cache)
{%- endif %}


class TestMiddleware:
    """Tests for middleware."""

    def test_request_id_middleware_exists(self):
        """Test request ID middleware is configured."""
        assert RequestIDMiddleware is not None


{%- if cookiecutter.enable_rate_limiting %}


class TestRateLimit:
    """Tests for rate limiting.

    These assert the *effect* on a caller, not that the limiter object exists —
    a limiter that is never attached to a route passes the latter and protects
    nothing.
    """

    def test_auth_category_has_a_per_ip_limit(self):
        """The auth rule must be per-IP: /auth/* runs before authentication."""
        rule = DEFAULT_RATE_LIMITS[RateLimitCategory.AUTH]
        assert rule.per_ip is not None

    @pytest.mark.anyio
    async def test_exceeding_the_auth_limit_raises_429(self):
        """The (limit + 1)-th call from one IP is rejected with Retry-After."""
        limit = DEFAULT_RATE_LIMITS[RateLimitCategory.AUTH].per_ip
        assert limit is not None

        for _ in range(limit):
            await check_rate_limit(category=RateLimitCategory.AUTH, client_ip="203.0.113.7")

        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit(category=RateLimitCategory.AUTH, client_ip="203.0.113.7")

        assert exc_info.value.status_code == 429
        assert exc_info.value.headers is not None
        assert "Retry-After" in exc_info.value.headers

    @pytest.mark.anyio
    async def test_limits_are_scoped_per_ip(self):
        """One IP exhausting its budget must not lock out another."""
        limit = DEFAULT_RATE_LIMITS[RateLimitCategory.AUTH].per_ip
        assert limit is not None

        for _ in range(limit + 1):
            with contextlib.suppress(HTTPException):
                await check_rate_limit(category=RateLimitCategory.AUTH, client_ip="203.0.113.7")

        # A different caller is unaffected.
        await check_rate_limit(category=RateLimitCategory.AUTH, client_ip="198.51.100.4")

{%- endif %}


{%- if cookiecutter.enable_logfire %}


class TestLogfireSetup:
    """Tests for Logfire setup."""

    @patch("app.core.logfire_setup.logfire")
    def test_setup_logfire_configures(self, mock_logfire):
        """Test setup_logfire calls configure."""
        setup_logfire()
        mock_logfire.configure.assert_called_once()

    @patch("app.core.logfire_setup.logfire")
    def test_instrument_app_instruments_fastapi(self, mock_logfire):
        """Test instrument_app instruments FastAPI."""
        app = FastAPI()
        instrument_app(app)
        mock_logfire.instrument_fastapi.assert_called()
{%- endif %}
