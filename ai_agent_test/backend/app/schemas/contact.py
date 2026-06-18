"""Contact form schemas — public-facing inquiries from the marketing site."""

from typing import Literal

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema

ContactTopic = Literal["support", "sales", "partnerships", "press"]


class ContactSubmissionCreate(BaseSchema):
    """Inbound contact-form payload.

    Validated by Pydantic; the service layer treats every submission as accepted
    (logs + best-effort notification) unless validation fails.
    """

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr = Field(..., description="Reply-to address")
    topic: ContactTopic = Field(default="support", description="Routing hint")
    message: str = Field(..., min_length=1, max_length=5000)


class ContactSubmissionRead(BaseSchema):
    """Public confirmation — intentionally minimal so we don't echo PII back."""

    received: bool = True
    message: str = "Thanks — we'll get back to you within 24 hours on weekdays."
