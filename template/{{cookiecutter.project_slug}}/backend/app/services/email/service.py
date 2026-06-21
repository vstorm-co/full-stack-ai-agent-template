{%- if cookiecutter.enable_email %}
from __future__ import annotations

import enum
import logging
import uuid
from typing import Any

from app.core.config import settings
from app.services.email import get_email_provider
from app.services.email.exceptions import EmailSuppressedError, EmailUnsubscribedError
from app.services.email.providers.base import EmailMessage, EmailProvider, SendResult
from app.services.email.templates import render_email

logger = logging.getLogger(__name__)


class EmailKey(enum.StrEnum):
    WELCOME = "welcome"
    EMAIL_VERIFICATION = "email_verification"
    MAGIC_LINK = "magic_link"
    PASSWORD_RESET = "password_reset"
    INVITATION = "invitation"
{%- if cookiecutter.enable_billing %}
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    TRIAL_ENDING = "trial_ending"
    TRIAL_EXPIRED = "trial_expired"
    SUBSCRIPTION_CANCELED = "subscription_canceled"
    SUBSCRIPTION_CHANGED = "subscription_changed"
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
    LOW_CREDITS = "low_credits"
{%- endif %}
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
{%- if cookiecutter.enable_billing %}
    EmailKey.PAYMENT_SUCCEEDED: EmailCategory.TRANSACTIONAL,
    EmailKey.PAYMENT_FAILED: EmailCategory.TRANSACTIONAL,
    EmailKey.SUBSCRIPTION_CANCELED: EmailCategory.TRANSACTIONAL,
    EmailKey.SUBSCRIPTION_CHANGED: EmailCategory.TRANSACTIONAL,
    EmailKey.TRIAL_ENDING: EmailCategory.LIFECYCLE,
    EmailKey.TRIAL_EXPIRED: EmailCategory.LIFECYCLE,
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
    EmailKey.LOW_CREDITS: EmailCategory.LIFECYCLE,
{%- endif %}
    EmailKey.NEWSLETTER_WELCOME: EmailCategory.MARKETING,
}


class EmailService:
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
        """`force=True` skips category opt-out checks — use for critical notifications."""
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

    async def send_welcome(self, *, to: str, name: str, login_url: str) -> SendResult:
        return await self.send(
            key=EmailKey.WELCOME,
            to=to,
            context={"name": name, "login_url": login_url, "app_name": "{{ cookiecutter.project_name }}"},
        )

    async def send_password_reset(self, *, to: str, name: str, reset_url: str) -> SendResult:
        return await self.send(
            key=EmailKey.PASSWORD_RESET,
            to=to,
            context={"name": name, "reset_url": reset_url, "expires_in": "1 hour", "app_name": "{{ cookiecutter.project_name }}"},
        )

    async def send_invitation(self, *, to: str, inviter_name: str, org_name: str, accept_url: str) -> SendResult:
        return await self.send(
            key=EmailKey.INVITATION,
            to=to,
            context={"inviter_name": inviter_name, "org_name": org_name, "accept_url": accept_url, "app_name": "{{ cookiecutter.project_name }}"},
        )

{%- if cookiecutter.enable_billing %}
    async def send_payment_succeeded(self, *, to: str, name: str, plan_name: str, amount: str, invoice_url: str) -> SendResult:
        return await self.send(
            key=EmailKey.PAYMENT_SUCCEEDED,
            to=to,
            context={"name": name, "plan_name": plan_name, "amount": amount, "invoice_url": invoice_url, "app_name": "{{ cookiecutter.project_name }}"},
        )

    async def send_payment_failed(self, *, to: str, name: str, amount: str, update_url: str) -> SendResult:
        return await self.send(
            key=EmailKey.PAYMENT_FAILED,
            to=to,
            context={"name": name, "amount": amount, "update_url": update_url, "app_name": "{{ cookiecutter.project_name }}"},
        )

    async def send_trial_ending(self, *, to: str, name: str, days_left: int, upgrade_url: str) -> SendResult:
        return await self.send(
            key=EmailKey.TRIAL_ENDING,
            to=to,
            context={"name": name, "days_left": days_left, "upgrade_url": upgrade_url, "app_name": "{{ cookiecutter.project_name }}"},
        )

    async def send_trial_expired(self, *, to: str, name: str, upgrade_url: str) -> SendResult:
        return await self.send(
            key=EmailKey.TRIAL_EXPIRED,
            to=to,
            context={"name": name, "upgrade_url": upgrade_url, "app_name": "{{ cookiecutter.project_name }}"},
        )

    async def send_subscription_changed(self, *, to: str, name: str, old_plan: str, new_plan: str, effective_date: str) -> SendResult:
        return await self.send(
            key=EmailKey.SUBSCRIPTION_CHANGED,
            to=to,
            context={"name": name, "old_plan": old_plan, "new_plan": new_plan, "effective_date": effective_date, "app_name": "{{ cookiecutter.project_name }}"},
        )

    async def send_subscription_canceled(self, *, to: str, name: str, plan_name: str, access_until: str, resubscribe_url: str) -> SendResult:
        return await self.send(
            key=EmailKey.SUBSCRIPTION_CANCELED,
            to=to,
            context={"name": name, "plan_name": plan_name, "access_until": access_until, "resubscribe_url": resubscribe_url, "app_name": "{{ cookiecutter.project_name }}"},
        )

{%- endif %}
{%- if cookiecutter.enable_credits_system %}
    async def send_low_credits(self, *, to: str, name: str, balance: int, topup_url: str) -> SendResult:
        return await self.send(
            key=EmailKey.LOW_CREDITS,
            to=to,
            context={"name": name, "balance": balance, "topup_url": topup_url, "app_name": "{{ cookiecutter.project_name }}"},
        )

{%- endif %}
    async def send_newsletter_welcome(self, *, to: str, name: str, unsubscribe_url: str = "") -> SendResult:
        return await self.send(
            key=EmailKey.NEWSLETTER_WELCOME,
            to=to,
            context={"name": name, "unsubscribe_url": unsubscribe_url, "app_name": "{{ cookiecutter.project_name }}"},
        )


def get_email_service() -> EmailService:
    return EmailService(provider=get_email_provider())

{%- else %}
"""Email service — not enabled (enable_email=false)."""
{%- endif %}
