"""
Seed script — populates the database with ~100 realistic objects per major table.
Run from the backend directory:
    uv run python ../seed_data.py

Requires the DB to already have migrations applied (alembic upgrade head).
Admin user admin@example.com must already exist.
"""

import asyncio
import random
import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from faker import Faker
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── DB connection (matches .env defaults) ────────────────────────────────────
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_test_8"

fake = Faker("pl_PL")
Faker.seed(42)
random.seed(42)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# ── helpers ───────────────────────────────────────────────────────────────────
def now() -> datetime:
    return datetime.now(UTC)

def past(days: int = 0, hours: int = 0) -> datetime:
    return now() - timedelta(days=days, hours=hours)

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=4)).decode()

def random_token(n: int = 32) -> str:
    return secrets.token_urlsafe(n)

LOREM_SENTENCES = [
    "Pydantic AI automatycznie waliduje dane wejściowe i wyjściowe modelu.",
    "RAG pozwala agentowi korzystać z własnej bazy wiedzy firmy.",
    "Embeddingi semantyczne umożliwiają wyszukiwanie kontekstowe zamiast pełnotekstowego.",
    "Architektura mikroserwisów wymaga odpowiedniej orchestracji kontenerów.",
    "FastAPI generuje dokumentację OpenAPI w czasie rzeczywistym.",
    "Asynchroniczne operacje I/O znacząco zwiększają przepustowość serwisu.",
    "Milvus obsługuje wyszukiwanie wektorowe w skali miliardów rekordów.",
    "JWT tokeny mają ograniczony czas życia ze względów bezpieczeństwa.",
    "PostgreSQL JSONB kolumny łączą elastyczność NoSQL z rygorem SQL.",
    "Celery umożliwia przetwarzanie zadań w tle bez blokowania głównego wątku.",
    "Next.js 15 wprowadza server actions dla mutacji danych po stronie serwera.",
    "Tailwind CSS pozwala budować spójne UI bez opuszczania HTML.",
    "Docker Compose upraszcza uruchamianie złożonych środowisk wielocontainerowych.",
    "Alembic automatycznie generuje migracje na podstawie zmian w modelach SQLAlchemy.",
    "WebSocket umożliwia dwukierunkową komunikację w czasie rzeczywistym.",
]

TOPICS = [
    "Analiza danych sprzedażowych Q3",
    "Dokumentacja API dla partnerów",
    "Optymalizacja zapytań do bazy",
    "Przegląd architektury systemu",
    "Plan migracji na nową infrastrukturę",
    "Raport bezpieczeństwa aplikacji",
    "Strategie skalowania horyzontalnego",
    "Integracja z systemem ERP",
    "Audyt kodu backendu",
    "Design sprint — nowy onboarding",
    "Konfiguracja CI/CD pipeline",
    "Monitoring i alerty produkcyjne",
    "Dokumentacja procesów RAG",
    "Testy obciążeniowe systemu",
    "Podsumowanie sprintu #47",
]

MODELS = ["claude-sonnet-4-6", "claude-opus-4-8", "gpt-4o", "gemini-2.0-flash", "gpt-4o-mini"]
PLATFORMS = ["slack", "telegram"]
SUBSCRIPTION_STATUSES = ["active", "trialing", "past_due", "canceled"]
ORG_ROLES = ["owner", "admin", "member", "viewer"]
CREDIT_TYPES = [
    "grant_subscription", "grant_trial", "purchase_topup",
    "debit_agent", "debit_rag_ingest", "admin_adjustment",
]


# ─────────────────────────────────────────────────────────────────────────────
async def seed(db: AsyncSession) -> None:
    print("🌱 Starting seed…")

    # ── 1. Find admin user ───────────────────────────────────────────────────
    result = await db.execute(
        text("SELECT id FROM users WHERE email = 'admin@example.com' LIMIT 1")
    )
    row = result.fetchone()
    if not row:
        raise SystemExit("❌ admin@example.com not found — run the app first to create it.")
    admin_id: uuid.UUID = row[0]
    print(f"   admin id: {admin_id}")

    # ── 2. Find admin's personal org ────────────────────────────────────────
    result = await db.execute(
        text(
            "SELECT id FROM organizations WHERE created_by_user_id = :uid AND is_personal = true LIMIT 1"
        ),
        {"uid": str(admin_id)},
    )
    row = result.fetchone()
    admin_org_id: uuid.UUID = row[0] if row else None

    # ── 3. Create 100 regular users ─────────────────────────────────────────
    print("   creating 100 users…")
    hashed_pw = hash_password("Password123!")
    user_ids: list[uuid.UUID] = []
    user_emails: list[str] = []

    for i in range(100):
        uid = uuid.uuid4()
        email = f"user{i+1:03d}@example.com"
        full_name = fake.name()
        created = past(days=random.randint(10, 365))
        await db.execute(
            text("""
                INSERT INTO users (id, email, hashed_password, full_name, is_active, role,
                                   is_app_admin, created_at, updated_at)
                VALUES (:id, :email, :pw, :name, true, 'user', false, :ca, :ua)
                ON CONFLICT (email) DO NOTHING
            """),
            {
                "id": str(uid), "email": email, "pw": hashed_pw,
                "name": full_name, "ca": created, "ua": created,
            },
        )
        user_ids.append(uid)
        user_emails.append(email)

    await db.flush()
    print(f"   ✓ {len(user_ids)} users")

    # ── 4. Create 20 team organizations ─────────────────────────────────────
    print("   creating 20 organizations…")
    org_ids: list[uuid.UUID] = []
    for i in range(20):
        oid = uuid.uuid4()
        name = f"{fake.company()} {random.choice(['AI', 'Tech', 'Labs', 'Group'])}"
        slug = f"org-{i+1:02d}-{random_token(4).lower()}"
        creator = random.choice(user_ids)
        created = past(days=random.randint(30, 300))
        tier = random.choice(["free", "free", "free", "pro", "pro", "enterprise"])
        await db.execute(
            text("""
                INSERT INTO organizations (id, name, slug, is_personal, created_by_user_id,
                                           subscription_tier, credits_balance, created_at, updated_at)
                VALUES (:id, :name, :slug, false, :creator, :tier, :credits, :ca, :ua)
            """),
            {
                "id": str(oid), "name": name, "slug": slug, "creator": str(creator),
                "tier": tier, "credits": random.randint(0, 50000),
                "ca": created, "ua": created,
            },
        )
        org_ids.append(oid)

        # Add 3-8 members
        members = random.sample(user_ids, k=random.randint(3, 8))
        for j, member_uid in enumerate(members):
            role = ORG_ROLES[0] if j == 0 else random.choice(ORG_ROLES[1:])
            await db.execute(
                text("""
                    INSERT INTO organization_members (id, organization_id, user_id, role,
                                                       invited_by_user_id, joined_at)
                    VALUES (:id, :oid, :uid, :role, :inv, :ja)
                    ON CONFLICT (organization_id, user_id) DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()), "oid": str(oid), "uid": str(member_uid),
                    "role": role, "inv": str(creator),
                    "ja": created + timedelta(days=random.randint(0, 10)),
                },
            )

    await db.flush()
    if admin_org_id:
        org_ids.append(admin_org_id)
    print(f"   ✓ {len(org_ids)} organizations")

    # ── 5. Invitations (100) ─────────────────────────────────────────────────
    print("   creating invitations…")
    statuses = ["pending", "accepted", "rejected", "expired", "revoked"]
    for _ in range(100):
        oid = random.choice(org_ids)
        expires = past(days=random.randint(-30, 30))
        status = random.choice(statuses)
        await db.execute(
            text("""
                INSERT INTO invitations (id, organization_id, email, role,
                                         invited_by_user_id, token, status, expires_at,
                                         created_at)
                VALUES (:id, :oid, :email, :role, :inv, :token, :status, :exp, :ca)
            """),
            {
                "id": str(uuid.uuid4()), "oid": str(oid),
                "email": fake.email(), "role": random.choice(ORG_ROLES[1:]),
                "inv": str(random.choice(user_ids)), "token": random_token(48),
                "status": status, "exp": expires,
                "ca": past(days=random.randint(5, 60)),
            },
        )
    await db.flush()
    print("   ✓ 100 invitations")

    # ── 6. Conversations + messages + tool calls ─────────────────────────────
    print("   creating conversations + messages + tool calls…")
    all_user_ids = [admin_id] + user_ids
    conversation_ids: list[uuid.UUID] = []
    message_ids_with_role: list[tuple[uuid.UUID, str]] = []

    for i in range(100):
        cid = uuid.uuid4()
        uid = random.choice(all_user_ids)
        oid = random.choice(org_ids) if random.random() > 0.4 else None
        created = past(days=random.randint(0, 180), hours=random.randint(0, 23))
        title = random.choice(TOPICS) + (f" #{random.randint(1, 99)}" if random.random() > 0.5 else "")
        await db.execute(
            text("""
                INSERT INTO conversations (id, user_id, organization_id, title, is_archived,
                                           created_at, updated_at)
                VALUES (:id, :uid, :oid, :title, :arch, :ca, :ua)
            """),
            {
                "id": str(cid), "uid": str(uid), "oid": str(oid) if oid else None,
                "title": title, "arch": random.random() < 0.1,
                "ca": created, "ua": created + timedelta(hours=random.randint(0, 5)),
            },
        )
        conversation_ids.append(cid)

        # 2–12 messages per conversation
        n_msgs = random.randint(2, 12)
        for j in range(n_msgs):
            mid = uuid.uuid4()
            role = "user" if j % 2 == 0 else "assistant"
            n_sentences = random.randint(1, 4)
            content = " ".join(random.choices(LOREM_SENTENCES, k=n_sentences))
            model = random.choice(MODELS) if role == "assistant" else None
            tokens = random.randint(50, 2000) if role == "assistant" else None
            msg_time = created + timedelta(minutes=j * random.randint(1, 10))
            await db.execute(
                text("""
                    INSERT INTO messages (id, conversation_id, role, content,
                                          model_name, tokens_used, created_at, updated_at)
                    VALUES (:id, :cid, :role, :content, :model, :tokens, :ca, :ua)
                """),
                {
                    "id": str(mid), "cid": str(cid), "role": role, "content": content,
                    "model": model, "tokens": tokens, "ca": msg_time, "ua": msg_time,
                },
            )
            message_ids_with_role.append((mid, role))

            # ~30% assistant messages have tool calls
            if role == "assistant" and random.random() < 0.3:
                tool_names = ["search_knowledge_base", "web_search", "run_python",
                              "search_documents", "get_datetime"]
                for _ in range(random.randint(1, 3)):
                    tool_name = random.choice(tool_names)
                    started = msg_time - timedelta(seconds=random.randint(1, 10))
                    dur = random.randint(200, 5000)
                    await db.execute(
                        text("""
                            INSERT INTO tool_calls (id, message_id, tool_call_id, tool_name,
                                                     args, result, status,
                                                     started_at, completed_at, duration_ms)
                            VALUES (:id, :mid, :tcid, :name, :args, :result, :status,
                                    :started, :completed, :dur)
                        """),
                        {
                            "id": str(uuid.uuid4()), "mid": str(mid),
                            "tcid": f"call_{random_token(8)}",
                            "name": tool_name,
                            "args": '{"query": "' + random.choice(LOREM_SENTENCES)[:40] + '"}',
                            "result": random.choice(LOREM_SENTENCES),
                            "status": random.choice(["completed", "completed", "failed"]),
                            "started": started, "completed": started + timedelta(milliseconds=dur),
                            "dur": dur,
                        },
                    )

    await db.flush()
    print(f"   ✓ {len(conversation_ids)} conversations, {len(message_ids_with_role)} messages")

    # ── 7. Message ratings ───────────────────────────────────────────────────
    print("   creating message ratings…")
    assistant_msgs = [(mid, role) for mid, role in message_ids_with_role if role == "assistant"]
    rated_pairs: set[tuple] = set()
    count = 0
    for _ in range(150):
        mid, _ = random.choice(assistant_msgs)
        rater = random.choice(all_user_ids)
        key = (str(mid), str(rater))
        if key in rated_pairs:
            continue
        rated_pairs.add(key)
        rating = random.choice([1, 1, 1, -1])
        created = past(days=random.randint(0, 60))
        await db.execute(
            text("""
                INSERT INTO message_ratings (id, message_id, user_id, rating, created_at, updated_at)
                VALUES (:id, :mid, :uid, :rating, :ca, :ua)
                ON CONFLICT (message_id, user_id) DO NOTHING
            """),
            {
                "id": str(uuid.uuid4()), "mid": str(mid), "uid": str(rater),
                "rating": rating, "ca": created, "ua": created,
            },
        )
        count += 1
    await db.flush()
    print(f"   ✓ {count} message ratings")

    # ── 8. Knowledge bases ───────────────────────────────────────────────────
    print("   creating knowledge bases…")
    kb_ids: list[uuid.UUID] = []
    kb_names = [
        "Dokumentacja produktu", "Baza wiedzy HR", "Regulaminy i polityki",
        "Techniczne FAQ", "Raporty finansowe", "Szkolenia onboarding",
        "Procedury bezpieczeństwa", "Instrukcje obsługi", "Kontrakty i umowy",
        "Artykuły naukowe", "Notatki ze spotkań", "Wytyczne brandingowe",
    ]
    scopes = ["personal", "personal", "org", "org", "app"]
    for i in range(min(len(kb_names), 12)):
        kid = uuid.uuid4()
        scope = random.choice(scopes)
        oid = random.choice(org_ids) if scope == "org" else None
        uid = random.choice(all_user_ids) if scope == "personal" else None
        collection = f"kb_{uuid.uuid4().hex[:12]}"
        created = past(days=random.randint(10, 200))
        await db.execute(
            text("""
                INSERT INTO knowledge_bases (id, name, description, scope, collection_name,
                                              is_default, owner_user_id, organization_id,
                                              created_at, updated_at)
                VALUES (:id, :name, :desc, :scope, :col, :default,
                        :uid, :oid, :ca, :ua)
            """),
            {
                "id": str(kid), "name": kb_names[i],
                "desc": fake.sentence(),
                "scope": scope, "col": collection,
                "default": i == 0,
                "uid": str(uid) if uid else None,
                "oid": str(oid) if oid else None,
                "ca": created, "ua": created,
            },
        )
        kb_ids.append(kid)
    await db.flush()
    print(f"   ✓ {len(kb_ids)} knowledge bases")

    # ── 9. RAG documents (100) ────────────────────────────────────────────────
    print("   creating RAG documents…")
    doc_statuses = ["completed", "completed", "completed", "processing", "failed"]
    file_types = ["pdf", "docx", "txt", "md", "xlsx", "pptx"]
    for i in range(100):
        kid = random.choice(kb_ids) if kb_ids else None
        oid = random.choice(org_ids)
        result = await db.execute(
            text("SELECT collection_name FROM knowledge_bases WHERE id = :kid LIMIT 1"),
            {"kid": str(kid)},
        ) if kid else None
        collection = result.fetchone()[0] if result else f"col_{i}"
        status = random.choice(doc_statuses)
        started = past(days=random.randint(1, 90))
        completed = started + timedelta(seconds=random.randint(5, 120)) if status != "processing" else None
        ftype = random.choice(file_types)
        fname = f"{fake.word()}_{fake.word()}_{random.randint(1, 99)}.{ftype}"
        await db.execute(
            text("""
                INSERT INTO rag_documents (id, collection_name, filename, filesize, filetype,
                                           status, chunk_count,
                                           started_at, completed_at,
                                           organization_id, knowledge_base_id,
                                           created_at, updated_at)
                VALUES (:id, :col, :fname, :fsize, :ftype,
                        :status, :chunks,
                        :started, :completed,
                        :oid, :kid,
                        :ca, :ua)
            """),
            {
                "id": str(uuid.uuid4()), "col": collection,
                "fname": fname, "fsize": random.randint(10_000, 10_000_000),
                "ftype": ftype, "status": status,
                "chunks": random.randint(5, 200) if status == "completed" else 0,
                "started": started, "completed": completed,
                "oid": str(oid), "kid": str(kid) if kid else None,
                "ca": started, "ua": completed or started,
            },
        )
    await db.flush()
    print("   ✓ 100 RAG documents")

    # ── 10. Sync sources (20) + sync logs (100) ───────────────────────────────
    print("   creating sync sources + logs…")
    sync_source_ids: list[uuid.UUID] = []
    connector_types = ["google_drive", "s3", "s3", "google_drive"]
    for i in range(20):
        sid = uuid.uuid4()
        oid = random.choice(org_ids)
        ctype = random.choice(connector_types)
        kid = random.choice(kb_ids) if kb_ids else None
        col = None
        if kid:
            r = await db.execute(
                text("SELECT collection_name FROM knowledge_bases WHERE id = :kid LIMIT 1"),
                {"kid": str(kid)},
            )
            row = r.fetchone()
            col = row[0] if row else None
        created = past(days=random.randint(5, 120))
        last_sync = created + timedelta(days=random.randint(1, 4)) if random.random() > 0.3 else None
        await db.execute(
            text("""
                INSERT INTO sync_sources (id, organization_id, name, connector_type,
                                          collection_name, config, sync_mode,
                                          schedule_minutes, is_active,
                                          last_sync_at, last_sync_status,
                                          created_at, updated_at)
                VALUES (:id, :oid, :name, :ctype, :col, :config, :mode,
                        :sched, :active,
                        :last_sync, :last_status,
                        :ca, :ua)
            """),
            {
                "id": str(sid), "oid": str(oid),
                "name": f"{ctype.replace('_', ' ').title()} — {fake.company()[:30]}",
                "ctype": ctype, "col": col,
                "config": '{"bucket": "my-bucket", "prefix": "docs/"}' if ctype == "s3"
                          else '{"folder_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"}',
                "mode": random.choice(["new_only", "incremental", "full"]),
                "sched": random.choice([60, 360, 720, 1440, None]),
                "active": random.random() > 0.2,
                "last_sync": last_sync, "last_status": "success" if last_sync else None,
                "ca": created, "ua": last_sync or created,
            },
        )
        sync_source_ids.append(sid)

    await db.flush()

    for _ in range(100):
        sid = random.choice(sync_source_ids)
        r = await db.execute(
            text("SELECT collection_name FROM sync_sources WHERE id = :sid LIMIT 1"),
            {"sid": str(sid)},
        )
        row = r.fetchone()
        col = row[0] if row and row[0] else "default"
        started = past(days=random.randint(0, 60))
        status = random.choice(["success", "success", "success", "failed", "running"])
        total = random.randint(10, 500)
        ingested = random.randint(0, total)
        await db.execute(
            text("""
                INSERT INTO sync_logs (id, source, collection_name, sync_source_id, status,
                                       mode, total_files, ingested, updated, skipped, failed,
                                       started_at, completed_at, created_at, updated_at)
                VALUES (:id, :src, :col, :sid, :status, :mode,
                        :total, :ingested, :updated, :skipped, :failed,
                        :started, :completed, :ca, :ua)
            """),
            {
                "id": str(uuid.uuid4()), "src": "sync_job", "col": col, "sid": str(sid),
                "status": status,
                "mode": random.choice(["full", "incremental", "new_only"]),
                "total": total, "ingested": ingested,
                "updated": random.randint(0, ingested // 2 + 1),
                "skipped": total - ingested - random.randint(0, 5),
                "failed": random.randint(0, 3) if status == "failed" else 0,
                "started": started,
                "completed": started + timedelta(minutes=random.randint(1, 30)) if status != "running" else None,
                "ca": started, "ua": started + timedelta(minutes=1),
            },
        )
    await db.flush()
    print("   ✓ 20 sync sources, 100 sync logs")

    # ── 11. Usage events (100) ────────────────────────────────────────────────
    print("   creating usage events…")
    providers = ["anthropic", "openai", "google", "openrouter"]
    frameworks = ["pydantic_ai", "langchain", "langgraph"]
    for _ in range(100):
        oid = random.choice(org_ids)
        uid = random.choice(all_user_ids)
        model = random.choice(MODELS)
        provider = "anthropic" if "claude" in model else ("openai" if "gpt" in model else "google")
        inp = random.randint(100, 8000)
        out = random.randint(50, 2000)
        credits = (inp + out * 3) // 100
        created = past(days=random.randint(0, 90))
        await db.execute(
            text("""
                INSERT INTO usage_event (id, organization_id, actor_user_id,
                                          model, provider,
                                          input_tokens, output_tokens, cached_tokens,
                                          credits_charged, ai_framework,
                                          created_at, updated_at)
                VALUES (:id, :oid, :uid, :model, :prov,
                        :inp, :out, :cached, :credits, :fw,
                        :ca, :ua)
            """),
            {
                "id": str(uuid.uuid4()), "oid": str(oid), "uid": str(uid),
                "model": model, "prov": provider,
                "inp": inp, "out": out, "cached": random.randint(0, inp // 4),
                "credits": credits, "fw": random.choice(frameworks),
                "ca": created, "ua": created,
            },
        )
    await db.flush()
    print("   ✓ 100 usage events")

    # ── 12. Credit transactions (100) ─────────────────────────────────────────
    print("   creating credit transactions…")
    for _ in range(100):
        oid = random.choice(org_ids)
        uid = random.choice(all_user_ids)
        tx_type = random.choice(CREDIT_TYPES)
        delta = (
            random.randint(1000, 100000)
            if tx_type in ("grant_subscription", "grant_trial", "purchase_topup")
            else -random.randint(1, 500)
        )
        created = past(days=random.randint(0, 180))
        await db.execute(
            text("""
                INSERT INTO credit_transaction (id, organization_id, actor_user_id,
                                                 delta, balance_after, type, description,
                                                 created_at, updated_at)
                VALUES (:id, :oid, :uid, :delta, :bal, :type, :desc, :ca, :ua)
            """),
            {
                "id": str(uuid.uuid4()), "oid": str(oid), "uid": str(uid),
                "delta": delta, "bal": max(0, random.randint(0, 200000) + delta),
                "type": tx_type,
                "desc": f"{'Doładowanie' if delta > 0 else 'Zużycie'} kredytów — {tx_type}",
                "ca": created, "ua": created,
            },
        )
    await db.flush()
    print("   ✓ 100 credit transactions")

    # ── 13. Stripe events (100) ───────────────────────────────────────────────
    print("   creating stripe events…")
    stripe_event_types = [
        "customer.subscription.created", "customer.subscription.updated",
        "customer.subscription.deleted", "invoice.payment_succeeded",
        "invoice.payment_failed", "customer.created", "charge.succeeded",
        "checkout.session.completed",
    ]
    for i in range(100):
        event_id = f"evt_{random_token(16)}"
        etype = random.choice(stripe_event_types)
        created = past(days=random.randint(0, 365))
        status = random.choice(["processed", "processed", "processed", "failed", "pending"])
        await db.execute(
            text("""
                INSERT INTO stripe_event (id, stripe_event_id, event_type, payload,
                                           status, created_at, updated_at)
                VALUES (:id, :evid, :etype, :payload, :status, :ca, :ua)
                ON CONFLICT (stripe_event_id) DO NOTHING
            """),
            {
                "id": str(uuid.uuid4()), "evid": event_id, "etype": etype,
                "payload": f'{{"id": "{event_id}", "type": "{etype}", "amount": {random.randint(999, 49900)}}}',
                "status": status, "ca": created, "ua": created,
            },
        )
    await db.flush()
    print("   ✓ 100 stripe events")

    # ── 14. Slash commands (100) ──────────────────────────────────────────────
    print("   creating slash commands…")
    command_templates = [
        ("summarize", "Podsumuj następujący tekst w 3 punktach:"),
        ("translate", "Przetłumacz na angielski:"),
        ("explain", "Wyjaśnij jak dla pięciolatka:"),
        ("code_review", "Przeprowadź code review następującego kodu:"),
        ("email", "Napisz profesjonalny email na temat:"),
        ("brainstorm", "Wygeneruj 10 pomysłów na:"),
        ("bug_report", "Utwórz raport błędu dla:"),
        ("standup", "Przygotuj standup na podstawie:"),
        ("sql", "Napisz zapytanie SQL które:"),
        ("regex", "Napisz wyrażenie regularne które:"),
    ]
    slash_pairs: set[tuple] = set()
    count = 0
    users_sample = random.sample(all_user_ids, min(50, len(all_user_ids)))
    for uid in users_sample:
        cmds = random.sample(command_templates, k=random.randint(1, 4))
        for name, prompt in cmds:
            key = (str(uid), name)
            if key in slash_pairs:
                continue
            slash_pairs.add(key)
            await db.execute(
                text("""
                    INSERT INTO user_slash_commands (id, user_id, name, prompt,
                                                      is_enabled, created_at, updated_at)
                    VALUES (:id, :uid, :name, :prompt, true, :ca, :ua)
                    ON CONFLICT (user_id, name) DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()), "uid": str(uid),
                    "name": name, "prompt": prompt,
                    "ca": past(days=random.randint(1, 90)),
                    "ua": past(days=random.randint(0, 30)),
                },
            )
            count += 1
    await db.flush()
    print(f"   ✓ {count} slash commands")

    # ── 15. Channel bots (10) + identities (50) + sessions (40) ──────────────
    print("   creating channel bots + identities + sessions…")
    bot_ids: list[uuid.UUID] = []
    for i in range(10):
        bid = uuid.uuid4()
        platform = random.choice(PLATFORMS)
        created = past(days=random.randint(10, 200))
        access_policy = (
            '{"mode":"open","whitelist":[],"allowed_groups":[],'
            '"require_link":false,"rate_limit_rpm":10,'
            '"denied_message":"You are not authorised to use this bot."}'
        )
        await db.execute(
            text("""
                INSERT INTO channel_bots (id, platform, name, token_encrypted,
                                          is_active, webhook_mode, access_policy,
                                          created_at, updated_at)
                VALUES (:id, :platform, :name, :token, :active, :webhook, CAST(:policy AS jsonb),
                        :ca, :ua)
            """),
            {
                "id": str(bid), "platform": platform,
                "name": f"{platform.title()} Bot #{i+1} — {fake.company()[:20]}",
                "token": f"enc_{random_token(40)}",
                "active": random.random() > 0.2, "webhook": random.random() > 0.5,
                "policy": access_policy,
                "ca": created, "ua": created,
            },
        )
        bot_ids.append(bid)

    identity_ids: list[uuid.UUID] = []
    for i in range(50):
        iid = uuid.uuid4()
        platform = random.choice(PLATFORMS)
        uid = random.choice(all_user_ids) if random.random() > 0.3 else None
        created = past(days=random.randint(5, 150))
        await db.execute(
            text("""
                INSERT INTO channel_identities (id, platform, platform_user_id,
                                                 platform_username, platform_display_name,
                                                 user_id, is_active,
                                                 created_at, updated_at)
                VALUES (:id, :platform, :puid, :pname, :dname,
                        :uid, true, :ca, :ua)
            """),
            {
                "id": str(iid), "platform": platform,
                "puid": f"U{random.randint(10000, 99999)}",
                "pname": fake.user_name(), "dname": fake.name(),
                "uid": str(uid) if uid else None,
                "ca": created, "ua": created,
            },
        )
        identity_ids.append(iid)

    session_pairs: set[tuple] = set()
    for _ in range(40):
        bid = random.choice(bot_ids)
        chat_id = f"C{random.randint(100000, 999999)}"
        key = (str(bid), chat_id)
        if key in session_pairs:
            continue
        session_pairs.add(key)
        iid = random.choice(identity_ids)
        cid = random.choice(conversation_ids) if random.random() > 0.3 else None
        created = past(days=random.randint(0, 60))
        await db.execute(
            text("""
                INSERT INTO channel_sessions (id, bot_id, identity_id, conversation_id,
                                               platform_chat_id, chat_type, is_active,
                                               last_message_at, created_at, updated_at)
                VALUES (:id, :bid, :iid, :cid, :chat_id, :chat_type, :active,
                        :last_msg, :ca, :ua)
                ON CONFLICT (bot_id, platform_chat_id) DO NOTHING
            """),
            {
                "id": str(uuid.uuid4()), "bid": str(bid), "iid": str(iid),
                "cid": str(cid) if cid else None, "chat_id": chat_id,
                "chat_type": random.choice(["private", "group", "channel"]),
                "active": random.random() > 0.15,
                "last_msg": past(days=random.randint(0, 30)),
                "ca": created, "ua": created,
            },
        )
    await db.flush()
    print("   ✓ 10 bots, 50 identities, 40 sessions")

    # ── 16. Audit logs (100) ─────────────────────────────────────────────────
    print("   creating audit logs…")
    actions = [
        "create_user", "delete_user", "edit_billing", "assign_role",
        "create_org", "delete_org", "invite_member", "revoke_invite",
        "create_knowledge_base", "delete_knowledge_base", "ingest_document",
        "toggle_sync_source", "export_conversations", "reset_credits",
    ]
    for _ in range(100):
        created = past(days=random.randint(0, 365))
        await db.execute(
            text("""
                INSERT INTO app_admin_audit_logs (id, actor_user_id, organization_id,
                                                    action, target_type, target_id,
                                                    details, ip_address,
                                                    created_at, updated_at)
                VALUES (:id, :actor, :oid, :action, :ttype, :tid,
                        :details, :ip, :ca, :ua)
            """),
            {
                "id": str(uuid.uuid4()),
                "actor": str(random.choice([admin_id] + user_ids[:10])),
                "oid": str(random.choice(org_ids)) if random.random() > 0.2 else None,
                "action": random.choice(actions),
                "ttype": random.choice(["user", "organization", "knowledge_base", "conversation"]),
                "tid": str(uuid.uuid4()),
                "details": '{"reason": "' + random.choice(["routine", "request", "policy"]) + '"}',
                "ip": fake.ipv4(),
                "ca": created, "ua": created,
            },
        )
    await db.flush()
    print("   ✓ 100 audit logs")

    # ── commit ────────────────────────────────────────────────────────────────
    await db.commit()
    print()
    print("✅ Seed complete!")
    print(f"   users:          {len(user_ids)}")
    print(f"   organizations:  {len(org_ids)}")
    print(f"   conversations:  {len(conversation_ids)}")
    print(f"   messages:       {len(message_ids_with_role)}")
    print("   knowledge bases, docs, sync sources, stripe events, audit logs — all seeded")


async def main() -> None:
    async with SessionLocal() as db:
        await seed(db)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
