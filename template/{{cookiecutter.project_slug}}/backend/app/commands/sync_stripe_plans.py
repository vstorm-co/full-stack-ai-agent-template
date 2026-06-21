{%- if cookiecutter.enable_billing %}
"""Sync Stripe Products/Prices to local DB.

Run after any changes to your Stripe Dashboard catalog:
    uv run {{ cookiecutter.project_slug }} cmd sync-stripe-plans

Convention:
  - Each Stripe Product must have metadata.code  (plan code in our DB)
  - Optional metadata.features                   (JSON object)
  - Optional metadata.monthly_credits            (integer)
  - Optional metadata.included_seats             (integer)
  - Optional metadata.extra_seat_cents           (integer)
  - Optional metadata.credits_grant              (for one-time top-up prices)
"""
import asyncio
import json
import click
import stripe

from app.commands import command, info, success, warning, error
from app.core.config import settings
from app.db.session import async_session_maker

from sqlalchemy.ext.asyncio import AsyncSession
import app.repositories.plan as plan_repo


async def _run_sync() -> None:
    stripe.api_key = settings.STRIPE_SECRET_KEY

    async with async_session_maker() as db:
        products = stripe.Product.list(active=True, limit=100)
        synced_plans = 0
        synced_prices = 0

        for product in products.auto_paging_iter():
            meta = product.metadata or {}
            code = meta.get("code", product.id)

            plan = await plan_repo.upsert_plan(
                db,
                code=code,
                display_name=product.name,
                description=product.description,
                is_active=product.active,
                features=json.loads(meta.get("features", "{}")),
                monthly_credits_base=int(meta.get("monthly_credits", 0)),
                monthly_credits_per_seat=int(meta.get("monthly_credits_per_seat", 0)),
                included_seats=int(meta.get("included_seats", 1)),
                extra_seat_amount_cents=int(meta.get("extra_seat_cents", 0)),
            )
            synced_plans += 1
            info(f"  Plan: {plan.code} — {plan.display_name}")

            prices = stripe.Price.list(product=product.id, active=True, limit=100)
            for stripe_price in prices.auto_paging_iter():
                await plan_repo.upsert_price(
                    db,
                    stripe_price_id=stripe_price.id,
                    plan_id=plan.id,
                    interval=stripe_price.recurring.interval if stripe_price.recurring else "one_time",
                    amount_cents=stripe_price.unit_amount or 0,
                    currency=stripe_price.currency,
                    billing_scheme=stripe_price.billing_scheme,
                    tiers_mode=stripe_price.tiers_mode,
                    credits_grant=int(stripe_price.metadata.get("credits_grant", 0)) or None,
                )
                synced_prices += 1

        await db.commit()
        success(f"Synced {synced_plans} plans and {synced_prices} prices from Stripe.")


@command("sync-stripe-plans", help="Pull active products/prices from Stripe and upsert into local DB")
def sync_stripe_plans() -> None:
    asyncio.run(_run_sync())

{%- else %}
"""sync_stripe_plans — not enabled (enable_billing=false)."""
{%- endif %}
