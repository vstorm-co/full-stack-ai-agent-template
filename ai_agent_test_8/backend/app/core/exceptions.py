"""Application exceptions.

Domain exceptions with HTTP status codes for the hybrid approach.
These exceptions are caught by exception handlers and converted to proper HTTP responses.
"""

from typing import Any


class AppException(Exception):
    """Base exception for all application errors.

    Attributes:
        message: Human-readable error message.
        code: Machine-readable error code for clients.
        status_code: HTTP status code to return.
        details: Additional error details (e.g., field names, IDs). ``None`` when not provided.
    """

    message: str = "An error occurred"
    code: str = "APP_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message or self.__class__.message
        self.code = code or self.__class__.code
        self.details = details
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, code={self.code!r})"


class NotFoundError(AppException):
    """Resource not found (404)."""

    message = "Resource not found"
    code = "NOT_FOUND"
    status_code = 404


class AlreadyExistsError(AppException):
    """Resource already exists (409)."""

    message = "Resource already exists"
    code = "ALREADY_EXISTS"
    status_code = 409


class ValidationError(AppException):
    """Validation error (422)."""

    message = "Validation error"
    code = "VALIDATION_ERROR"
    status_code = 422


class AuthenticationError(AppException):
    """Authentication failed (401)."""

    message = "Authentication failed"
    code = "AUTHENTICATION_ERROR"
    status_code = 401


class AuthorizationError(AppException):
    """Authorization failed - insufficient permissions (403)."""

    message = "Insufficient permissions"
    code = "AUTHORIZATION_ERROR"
    status_code = 403


class RateLimitError(AppException):
    """Rate limit exceeded (429)."""

    message = "Rate limit exceeded"
    code = "RATE_LIMIT_EXCEEDED"
    status_code = 429


class BadRequestError(AppException):
    """Bad request (400)."""

    message = "Bad request"
    code = "BAD_REQUEST"
    status_code = 400


class PaymentRequiredError(AppException):
    """Payment required — seat or usage limit reached (402)."""

    message = "Payment required"
    code = "PAYMENT_REQUIRED"
    status_code = 402


class ExternalServiceError(AppException):
    """External service unavailable (503)."""

    message = "External service unavailable"
    code = "EXTERNAL_SERVICE_ERROR"
    status_code = 503


class DatabaseError(AppException):
    """Database error (500)."""

    message = "Database error"
    code = "DATABASE_ERROR"
    status_code = 500


class InternalError(AppException):
    """Internal server error (500)."""

    message = "Internal server error"
    code = "INTERNAL_ERROR"
    status_code = 500
