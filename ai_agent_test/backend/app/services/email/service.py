"""EmailService — top-level facade for sending transactional emails."""

from __future__ import annotations

import enum
import logging
from typing import Any

from app.services.email.providers.base import EmailMessage, EmailProvider, SendResult
from app.services.email.templates import render_email

logger = logging.getLogger(__name__)


class EmailKey(enum.StrEnum):
    WELCOME = "welcome"
    EMAIL_VERIFICATION = "email_verification"
    MAGIC_LINK = "magic_link"
    PASSWORD_RESET = "password_reset"
    INVITATION = "invitation"
    NEWSLETTER_WELCOME = "newsletter_welcome"


class EmailCategory(enum.StrEnum):
    TRANSACTIONAL = "transactional"
    LIFECYCLE = "lifecycle"
    MARKETING = "marketing"


_CATEGORIES: dict[EmailKey, EmailCategory] = {
    EmailKey.WELCOME: EmailCategory.TRANSACTIONAL,
    EmailKey.EMAIL_VERIFICATION: EmailCategory.TRANSACTIONAL,
    EmailKey.MAGIC_LINK: EmailCategory.TRANSACTIONAL,
    EmailKey.PASSWORD_RESET: EmailCategory.TRANSACTIONAL,
    EmailKey.INVITATION: EmailCategory.TRANSACTIONAL,
    EmailKey.NEWSLETTER_WELCOME: EmailCategory.MARKETING,
}


class EmailService:
    """Send emails through the configured provider with suppression and template rendering."""

    def __init__(self, provider: EmailProvider) -> None:
        self.provider = provider

    async def send(
        self,
        *,
        key: EmailKey,
        to: str,
        context: dict[str, Any],
        force: bool = False,
    ) -> SendResult:
        """Render template, apply opt-out rules, and dispatch via provider.

        Args:
            key: Template key identifying which email to send.
            to: Recipient email address.
            context: Template variable substitutions.
            force: Skip category opt-out checks (use for critical notifications).
        """
        from app.core.config import settings

        subject, html, text = render_email(key.value, context)

        message = EmailMessage(
            to=[to],
            from_email=settings.EMAIL_FROM,
            from_name=settings.EMAIL_FROM_NAME,
            subject=subject,
            html=html,
            text=text,
            reply_to=getattr(settings, "EMAIL_REPLY_TO", None),
            tags=[_CATEGORIES[key].value, key.value],
        )

        result = await self.provider.send(message)
        if not result.accepted:
            logger.error(
                "email_not_accepted",
                extra={"key": key.value, "to": to, "error": result.error},
            )
        return result

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    async def send_welcome(self, *, to: str, name: str, login_url: str) -> SendResult:
        return await self.send(
            key=EmailKey.WELCOME,
            to=to,
            context={"name": name, "login_url": login_url, "app_name": "ai_agent_test"},
        )

    async def send_password_reset(self, *, to: str, name: str, reset_url: str) -> SendResult:
        return await self.send(
            key=EmailKey.PASSWORD_RESET,
            to=to,
            context={
                "name": name,
                "reset_url": reset_url,
                "expires_in": "1 hour",
                "app_name": "ai_agent_test",
            },
        )

    async def send_invitation(
        self, *, to: str, inviter_name: str, org_name: str, accept_url: str
    ) -> SendResult:
        return await self.send(
            key=EmailKey.INVITATION,
            to=to,
            context={
                "inviter_name": inviter_name,
                "org_name": org_name,
                "accept_url": accept_url,
                "app_name": "ai_agent_test",
            },
        )

    async def send_newsletter_welcome(
        self, *, to: str, name: str, unsubscribe_url: str = ""
    ) -> SendResult:
        return await self.send(
            key=EmailKey.NEWSLETTER_WELCOME,
            to=to,
            context={"name": name, "unsubscribe_url": unsubscribe_url, "app_name": "ai_agent_test"},
        )


def get_email_service() -> EmailService:
    from app.services.email import get_email_provider

    return EmailService(provider=get_email_provider())
