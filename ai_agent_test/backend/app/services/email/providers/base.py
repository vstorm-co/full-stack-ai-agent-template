"""Base types for email providers."""

from typing import Protocol

from pydantic import BaseModel


class EmailMessage(BaseModel):
    to: list[str]
    cc: list[str] = []
    bcc: list[str] = []
    from_email: str
    from_name: str | None = None
    subject: str
    html: str
    text: str
    reply_to: str | None = None
    tags: list[str] = []
    metadata: dict = {}


class SendResult(BaseModel):
    provider_message_id: str
    accepted: bool
    error: str | None = None


class EmailProvider(Protocol):
    async def send(self, message: EmailMessage) -> SendResult: ...
