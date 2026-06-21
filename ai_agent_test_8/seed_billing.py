"""
Seed billing data for admin's personal org:
  - 6 monthly subscription grant transactions (past 6 months)
  - 2 top-up transactions
  - 30 days of daily usage-deduct credit_transaction rows
  - Ensure credit_balance is positive
Run: cd backend && uv run python ../seed_billing.py
"""

import asyncio
import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_test_8"

random.seed(42)

engine = create_async_engine(DATABASE_URL, echo=False)
Session = async_sessionmaker(engine, expire_on_commit=False)


async def seed() -> None:
    async with Session() as db:
        # ── get admin org & user ─────────────────────────────────────────────
        row = (
            await db.execute(
                text("""
                    SELECT o.id FROM organizations o
                    JOIN users u ON u.id = o.created_by_user_id
                    WHERE u.email = 'admin@example.com' AND o.is_personal = true
                    LIMIT 1
                """)
            )
        ).fetchone()
        if not row:
            raise SystemExit("❌ admin personal org not found")
        org_id = str(row[0])

        row = (
            await db.execute(text("SELECT id FROM users WHERE email = 'admin@example.com' LIMIT 1"))
        ).fetchone()
        admin_id = str(row[0])

        print(f"org_id = {org_id}")
        print(f"admin  = {admin_id}")

        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        inserted = 0

        # ── 1. Monthly subscription grants — last 6 months ───────────────────
        PLAN_CREDITS = [5000, 5000, 5000, 7500, 7500, 10000]
        PLAN_CENTS = [2900, 2900, 2900, 4900, 4900, 9900]
        balance = 0
        for m in range(6, 0, -1):
            # first day of that month
            month_start = (today.replace(day=1) - timedelta(days=m * 28)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            credits = PLAN_CREDITS[6 - m]
            balance += credits
            await db.execute(
                text("""
                    INSERT INTO credit_transaction
                        (id, organization_id, actor_user_id, delta, balance_after,
                         type, description, created_at, updated_at)
                    VALUES
                        (:id, :oid, :uid, :delta, :bal,
                         'grant_subscription', :desc, :ts, :ts)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()),
                    "oid": org_id,
                    "uid": admin_id,
                    "delta": credits,
                    "bal": balance,
                    "desc": f"Monthly subscription — {month_start.strftime('%B %Y')}",
                    "ts": month_start,
                },
            )
            inserted += 1

        # ── 2. Two top-up purchases ───────────────────────────────────────────
        topups = [
            (today - timedelta(days=75), 2000, "Credit top-up — 2 000 credits"),
            (today - timedelta(days=20), 5000, "Credit top-up — 5 000 credits"),
        ]
        for ts, credits, desc in topups:
            balance += credits
            await db.execute(
                text("""
                    INSERT INTO credit_transaction
                        (id, organization_id, actor_user_id, delta, balance_after,
                         type, description, created_at, updated_at)
                    VALUES
                        (:id, :oid, :uid, :delta, :bal,
                         'purchase_topup', :desc, :ts, :ts)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()),
                    "oid": org_id,
                    "uid": admin_id,
                    "delta": credits,
                    "bal": balance,
                    "desc": desc,
                    "ts": ts,
                },
            )
            inserted += 1

        # ── 3. Daily deduction rows — last 30 days ────────────────────────────
        for day_offset in range(30, 0, -1):
            day = today - timedelta(days=day_offset)
            # 3-8 deduction rows per day
            n = random.randint(3, 8)
            for _ in range(n):
                charge = random.randint(5, 60)
                balance = max(0, balance - charge)
                hour = random.randint(8, 22)
                minute = random.randint(0, 59)
                ts = day.replace(hour=hour, minute=minute)
                await db.execute(
                    text("""
                        INSERT INTO credit_transaction
                            (id, organization_id, actor_user_id, delta, balance_after,
                             type, description, created_at, updated_at)
                        VALUES
                            (:id, :oid, :uid, :delta, :bal,
                             'deduct_usage', :desc, :ts, :ts)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "oid": org_id,
                        "uid": admin_id,
                        "delta": -charge,
                        "bal": balance,
                        "desc": "LLM usage charge",
                        "ts": ts,
                    },
                )
                inserted += 1

        # ── 4. Sync credits_balance on the org row ────────────────────────────
        await db.execute(
            text("UPDATE organizations SET credits_balance = :bal WHERE id = :oid"),
            {"bal": balance, "oid": org_id},
        )

        await db.commit()

    await engine.dispose()
    print(f"✅ inserted {inserted} credit_transaction rows, final balance = {balance}")


asyncio.run(seed())
