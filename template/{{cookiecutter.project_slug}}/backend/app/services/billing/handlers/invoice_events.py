{%- if cookiecutter.enable_billing %}
import logging
import stripe
from sqlalchemy.ext.asyncio import AsyncSession

import app.repositories.subscription as sub_repo
{%- if cookiecutter.enable_email %}
from app.core.config import settings
from app.services.email.service import get_email_service
{%- endif %}

logger = logging.getLogger(__name__)


def _format_amount(invoice) -> str:
    amount = (invoice.amount_paid or invoice.amount_due or 0) / 100
    currency = (invoice.currency or "usd").upper()
    return f"{currency} {amount:.2f}"


async def _send_payment_succeeded_email(invoice) -> None:
{%- if cookiecutter.enable_email %}
    try:
        email_svc = get_email_service()
        await email_svc.send_payment_succeeded(
            to=invoice.customer_email or "",
            name=invoice.customer_name or invoice.customer_email or "there",
            plan_name=invoice.lines.data[0].description if invoice.lines and invoice.lines.data else "subscription",
            amount=_format_amount(invoice),
            invoice_url=invoice.hosted_invoice_url or settings.BILLING_PORTAL_RETURN_URL,
        )
    except Exception:
        logger.exception("email_payment_succeeded_failed")
{%- else %}
    pass
{%- endif %}


async def _send_payment_failed_email(invoice) -> None:
{%- if cookiecutter.enable_email %}
    try:
        email_svc = get_email_service()
        await email_svc.send_payment_failed(
            to=invoice.customer_email or "",
            name=invoice.customer_name or invoice.customer_email or "there",
            amount=_format_amount(invoice),
            update_url=settings.BILLING_PORTAL_RETURN_URL,
        )
    except Exception:
        logger.exception("email_payment_failed_failed")
{%- else %}
    pass
{%- endif %}


async def handle_payment_succeeded(db: AsyncSession, event: stripe.Event) -> None:
    invoice = event.data.object
    if invoice.billing_reason not in ("subscription_create", "subscription_cycle", "subscription_update"):
        return

    sub = await sub_repo.get_by_stripe_id(db, invoice.subscription)
    if not sub:
        logger.warning(
            "invoice_sub_not_found",
            extra={"subscription_id": invoice.subscription},
        )
        return
    # Note: monthly credit grants are handled by customer.subscription.updated
    # (period rollover) and customer.subscription.created (first activation).
    # We don't grant here to avoid double-crediting on renewal.

    await _send_payment_succeeded_email(invoice)


async def handle_payment_failed(db: AsyncSession, event: stripe.Event) -> None:
    invoice = event.data.object
    logger.warning(
        "invoice_payment_failed",
        extra={"invoice_id": invoice.id, "subscription_id": invoice.subscription},
    )
    await _send_payment_failed_email(invoice)


async def handle_upcoming(db: AsyncSession, event: stripe.Event) -> None:
    invoice = event.data.object
    logger.info(
        "invoice_upcoming",
        extra={"invoice_id": invoice.id, "subscription_id": invoice.subscription},
    )

{%- else %}
"""invoice_events — not enabled (enable_billing=false)."""
{%- endif %}
