# Configuration

All available options when generating a project.

## Core Options

| Option | Values | Description |
|--------|--------|-------------|
| `--database` | `postgresql`, `none` | Async PostgreSQL (SQLAlchemy 2.0 + Alembic) |
| `--orm` | `sqlalchemy`, `sqlmodel` | ORM choice (SQLModel for simplified syntax) |
| `--oauth-google` | flag | Enable Google OAuth2 login |
| `--ai-framework` | `pydantic_ai`, `pydantic_deep`, `langchain`, `langgraph`, `deepagents` | AI agent framework |
| `--llm-provider` | `openai`, `anthropic`, `google`, `openrouter` | LLM provider |
| `--task-queue` | `none`, `celery`, `taskiq`, `arq` | Background task queue (Redis-backed). **Prefect** is available via the interactive wizard. |
| `--frontend` | `none`, `nextjs` | Frontend framework |

## Presets

```bash
# Full production setup
fastapi-fullstack create my_app --preset production

# AI agent with streaming
fastapi-fullstack create my_app --preset ai-agent

# Minimal project
fastapi-fullstack create my_app --minimal
```

## AI Framework Options

| Framework | Providers | Description |
|-----------|-----------|-------------|
| `pydantic_ai` | OpenAI, Anthropic, Google, OpenRouter | Type-safe agents with WebSearch/WebFetch built-in |
| `pydantic_deep` | OpenAI, Anthropic, Google | Deep coding assistant (filesystem tools, Docker/Daytona sandbox) |
| `langchain` | OpenAI, Anthropic, Google | Comprehensive chain-based agents |
| `langgraph` | OpenAI, Anthropic, Google | Graph-based ReAct agents |
| `deepagents` | OpenAI, Anthropic, Google | Agentic framework with subagent delegation |

```bash
fastapi-fullstack create my_app --ai-framework pydantic_ai --llm-provider openai
fastapi-fullstack create my_app --ai-framework pydantic_deep --llm-provider anthropic
fastapi-fullstack create my_app --ai-framework langgraph --llm-provider google
```

## Database Options

### PostgreSQL

```bash
fastapi-fullstack create my_app --database postgresql
```

- Async via `asyncpg`
- SQLAlchemy 2.0 + Alembic migrations
- Connection pooling
- pgvector-ready (use it as your RAG vector store)

> PostgreSQL is the single supported database. To generate without any database (e.g. a stateless service), pass `--database none` — note that JWT auth, RAG, and teams require a database.

## Background Task Options

| Queue | Description |
|-------|-------------|
| `celery` | Classic, battle-tested (Redis broker) |
| `taskiq` | Async-native, modern (Redis broker) |
| `arq` | Lightweight async (Redis) |
| `prefect` | Workflow orchestration — self-hosted server + runner, cron/interval scheduled flows, web UI on `:4200`. Set `PREFECT_API_KEY` to use Prefect Cloud |

```bash
# celery / taskiq / arq via the create flag
fastapi-fullstack create my_app --task-queue celery --redis

# Prefect is selected through the interactive wizard
fastapi-fullstack
```

## Messaging Channels

Enable Telegram and/or Slack multi-bot integration via the interactive wizard (`fastapi-fullstack new`).

| Platform | Mode | Feature |
|----------|------|---------|
| **Telegram** | Polling (dev) | Long-polling via aiogram v3 Socket Mode |
| **Telegram** | Webhook (prod) | `POST /telegram/{bot_id}/webhook` with HMAC verification |
| **Slack** | Socket Mode (dev) | `slack-sdk` Socket Mode for development |
| **Slack** | Events API (prod) | `POST /slack/{bot_id}/events` with HMAC-SHA256 signature |

Both platforms share the same underlying infrastructure:

- **Multi-bot** — Multiple bots per platform, each with encrypted token storage (Fernet)
- **Per-thread sessions** — Telegram replies + Slack thread_ts each get their own `ChannelSession`
- **Group concurrency** — Per-chat `asyncio.Lock` prevents interleaved agent calls in group chats
- **Access policies** — `open`, `whitelist`, `jwt_linked`, `group_only`
- **Commands** — `/start`, `/new`, `/help`, `/link`, `/unlink`
- **Identity linking** — Connect Telegram/Slack user to an app account via one-time link code

### Environment Variables (Telegram)

```bash
TELEGRAM_WEBHOOK_BASE_URL=https://yourdomain.com  # for webhook mode
CHANNEL_ENCRYPTION_KEY=...  # Fernet key for token storage
```

### Environment Variables (Slack)

```bash
SLACK_SIGNING_SECRET=...    # From Slack app settings (Events API verification)
SLACK_BOT_TOKEN=xoxb-...    # Bot OAuth token (for sending messages)
SLACK_APP_TOKEN=xapp-...    # App-level token (for Socket Mode dev)
CHANNEL_ENCRYPTION_KEY=...  # Fernet key for token storage
```

## Integrations

Enable during project generation:

```bash
fastapi-fullstack new
# ✓ Redis (caching/sessions)
# ✓ Rate limiting (slowapi)
# ✓ Pagination
# ✓ Admin Panel (SQLAdmin)
# ✓ Webhooks
# ✓ Telegram integration
# ✓ Slack integration
# ✓ Sentry
# ✓ Logfire / LangSmith
# ✓ Prometheus
```

## Environment Variables

Generated projects use `.env` files:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db

# Auth
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# AI
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Messaging channels (if enabled)
CHANNEL_ENCRYPTION_KEY=...           # Fernet key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TELEGRAM_WEBHOOK_BASE_URL=https://...  # Telegram webhook mode only
SLACK_SIGNING_SECRET=...             # Slack Events API signature verification
SLACK_BOT_TOKEN=xoxb-...             # Slack Web API
SLACK_APP_TOKEN=xapp-...             # Slack Socket Mode (dev only)

# Observability
LOGFIRE_TOKEN=...
SENTRY_DSN=...
```

## Next Steps

- [Quick Start](quick-start.md) - Run your project
- [AI Agents](../ai-agent.md) - Configure AI frameworks
- [Deployment](../deployment.md) - Deploy to production
