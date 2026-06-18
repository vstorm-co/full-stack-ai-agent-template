"""Password-reset and magic-link request/confirm schemas."""

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema


class PasswordResetRequest(BaseSchema):
    """Step 1 — user submits their email; we email a reset link."""

    email: EmailStr


class PasswordResetConfirm(BaseSchema):
    """Step 2 — user clicks link, posts new password with token."""

    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetResponse(BaseSchema):
    """Symmetric response for both request + confirm to avoid email enumeration."""

    sent: bool = True
    message: str = "If an account exists for that email, you'll get a reset link shortly."


class PasswordResetConfirmResponse(BaseSchema):
    """Returned after a successful confirm — front-end then redirects to login."""

    success: bool = True
    message: str = "Password updated. You can now sign in."


class MagicLinkRequest(BaseSchema):
    """Email-only request — symmetric with password reset."""

    email: EmailStr


class MagicLinkVerifyRequest(BaseSchema):
    """Step 2 — user clicked email link, exchange token for session."""

    token: str = Field(..., min_length=10)
