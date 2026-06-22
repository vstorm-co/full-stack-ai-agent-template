---
name: billing-stripe
description: Work with Stripe billing — subscriptions, plans/prices, the Customer Portal, credits, usage metering, invoices, and webhook events. Use when changing plans, handling a new Stripe webhook, debugging a payment/subscription flow, or touching credit balances and usage.
---

# Billing & Credits (Stripe)

Billing is a **thick service** at `backend/app/services/billing/`. Routes never touch Stripe directly — everything goes through `BillingService` (the facade in `facade.py`, re-exported from `__init__.py`).

## Layout

| File | Responsibility |
|------|---------------|
| `facade.py` | `BillingService` — the only thing routes/workers import |
| `checkout_service.py` | Checkout sessions (seat-configurable) |
| `subscription_service.py` | Subscription CRUD, change plan, cancel/reactivate |
| `credit_service.py` | Credit ledger + usage aggregation |
| `stripe_client.py` | Thin Stripe API wrapper |
| `webhook_handler.py` + `handlers/` | Event processing (customer / invoice / payment / subscription) |
| `pricing.py` | Static plan/price data |
| `exceptions.py` | Billing domain errors (extend `core/exceptions`) |

Data model: `plan` / `price` mirror Stripe products; `subscription` is one-per-org; `stripe_event` is an idempotency log; `credit_transaction` is an immutable ledger; `usage_event` records per-message token spend, rolled up into the `mv_usage_daily` materialized view.

## Common tasks

**Handle a new webhook event:** add a handler module/function under `services/billing/handlers/`, dispatch it from `webhook_handler.py`, and record it in `stripe_event` for idempotency (skip if already processed). Verify the signature — never trust unsigned payloads.

**Add/adjust a plan:** update `pricing.py` and the corresponding Stripe product/price; the `sync-stripe-plans` command (`{{ cookiecutter.project_slug }} cmd sync-stripe-plans`) mirrors Stripe → local `plan`/`price` tables.

**Charge/grant credits:** go through `credit_service` so every change writes a `credit_transaction` row (grants, purchases, debits) and the running balance stays consistent. Never mutate balances directly.

**Meter usage:** write a `usage_event` (input/output/cached tokens, model, provider, credits charged) — the daily rollup and dashboard charts read from `mv_usage_daily` (refreshed by a background task).

## Local testing

Use the Stripe CLI to forward webhooks: `stripe listen --forward-to localhost:8000/api/v1/billing/webhook`. Use Stripe test keys/mode. The webhook endpoint is unauthenticated but signature-verified.

## Rules

- Routes call `BillingService`; never import `stripe_client` or a sub-service directly from a route.
- Every webhook is idempotent via `stripe_event` — re-delivery must be a no-op.
- Credit changes always go through the ledger; the balance is derived, not authoritative state you overwrite.
- Keep Stripe secrets in `settings` / `.env`, never inline.
