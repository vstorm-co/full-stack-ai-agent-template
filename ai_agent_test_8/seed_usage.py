"""
Seed 6 months of realistic daily usage_event rows for admin's personal org.
Run from backend dir:  uv run python ../seed_usage.py
"""

import asyncio
import math
import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_test_8"

random.seed(99)

engine = create_async_engine(DATABASE_URL, echo=False)
Session = async_sessionmaker(engine, expire_on_commit=False)

MODELS = [
    ("claude-sonnet-4-6", "anthropic"),
    ("claude-opus-4-8", "anthropic"),
    ("gpt-4o", "openai"),
    ("gpt-4o-mini", "openai"),
    ("gemini-2.0-flash", "google"),
]
FRAMEWORKS = ["pydantic_ai", "pydantic_ai", "langchain", "langgraph"]


async def seed() -> None:
    async with Session() as db:
        # ── get admin org id ─────────────────────────────────────────────────
        row = (await db.execute(
            text("""
                SELECT o.id FROM organizations o
                JOIN users u ON u.id = o.created_by_user_id
                WHERE u.email = 'admin@example.com' AND o.is_personal = true
                LIMIT 1
            """)
        )).fetchone()
        if not row:
            raise SystemExit("❌ admin personal org not found")
        org_id = str(row[0])

        row = (await db.execute(
            text("SELECT id FROM users WHERE email = 'admin@example.com' LIMIT 1")
        )).fetchone()
        admin_id = str(row[0])

        print(f"org_id  = {org_id}")
        print(f"admin   = {admin_id}")

        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        start = today - timedelta(days=180)

        rows_inserted = 0

        # ── generate one week at a time for natural variation ─────────────────
        for day_offset in range(181):
            day = start + timedelta(days=day_offset)

            # weekly seasonality: Mon-Fri busy, weekends quiet
            weekday = day.weekday()  # 0=Mon 6=Sun
            base = 18 if weekday < 5 else 4

            # slow ramp-up over first 60 days, then steady growth
            growth = 1 + (day_offset / 180) * 1.8
            # mid-period spike (demo / launch event around day 80-100)
            spike = 1.6 if 80 <= day_offset <= 100 else 1.0
            # add noise
            noise = random.uniform(0.7, 1.3)

            n_calls = max(1, int(base * growth * spike * noise))

            for _ in range(n_calls):
                model, provider = random.choice(MODELS)
                inp = random.randint(200, 6000)
                out = random.randint(100, 2000)
                cached = random.randint(0, inp // 5)
                credits = max(1, (inp + out * 3) // 100)
                hour = random.randint(7, 22)
                minute = random.randint(0, 59)
                ts = day.replace(hour=hour, minute=minute)

                await db.execute(text("""
                    INSERT INTO usage_event
                        (id, organization_id, actor_user_id,
                         model, provider,
                         input_tokens, output_tokens, cached_tokens,
                         credits_charged, ai_framework,
                         created_at, updated_at)
                    VALUES
                        (:id, :oid, :uid,
                         :model, :prov,
                         :inp, :out, :cached,
                         :credits, :fw,
                         :ts, :ts)
                """), {
                    "id": str(uuid.uuid4()), "oid": org_id, "uid": admin_id,
                    "model": model, "prov": provider,
                    "inp": inp, "out": out, "cached": cached,
                    "credits": credits, "fw": random.choice(FRAMEWORKS),
                    "ts": ts,
                })
                rows_inserted += 1

        await db.commit()

    await engine.dispose()
    print(f"✅ inserted {rows_inserted} usage_event rows over 180 days")


asyncio.run(seed())
