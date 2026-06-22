# {{ cookiecutter.project_name }}

{{ cookiecutter.project_description }}

> Generated with [Full-Stack AI Agent Template](https://github.com/vstorm-co/full-stack-ai-agent-template).

---

## Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI + Pydantic v2 |
| **Database** | PostgreSQL (async via asyncpg) |
| **Auth** | JWT + refresh tokens{% if cookiecutter.use_api_key %} + API keys{% endif %}{% if cookiecutter.enable_oauth %} + OAuth{% endif %} |
{%- if cookiecutter.enable_redis %}
| **Cache** | Redis |
{%- endif %}
| **AI Framework** | {{ cookiecutter.ai_framework }} ({{ cookiecutter.llm_provider }}) |
{%- if cookiecutter.enable_rag %}
| **RAG** | {{ cookiecutter.vector_store }} vector store |
{%- endif %}
{%- if cookiecutter.background_tasks != "none" %}
| **Tasks** | {{ cookiecutter.background_tasks }} |
{%- endif %}
{%- if cookiecutter.use_frontend %}
| **Frontend** | Next.js 15 + React 19 + Tailwind v4 |
{%- endif %}
{%- if cookiecutter.enable_billing %}
| **Billing** | Stripe |
{%- endif %}

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| **Docker** | Desktop / Engine 24+ | <https://docs.docker.com/get-docker/> |
| **Make** | GNU Make 3.81+ (preinstalled on macOS/Linux) | Windows: install via [chocolatey](https://chocolatey.org/) `choco install make` or use WSL2 |
| **uv** | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
{%- if cookiecutter.use_frontend %}
| **bun** | 1.x | `curl -fsSL https://bun.sh/install \| bash` (or use `npm` / `pnpm` if you prefer) |
{%- endif %}

> **Windows users:** the Makefile and shell helpers assume bash. Use **WSL2** or **Git Bash** for the smoothest experience. The Docker workflow below works identically on macOS, Linux, and WSL2.

---

## Quick Start (Local Dev)

### First time

```bash
make bootstrap       # = make dev + make seed
```

That's the only command you need on a fresh clone. After this, day-to-day is just `make dev`.

### Subsequent runs

```bash
make dev
```

`make dev` is **idempotent** — re-run it any time. It will:

1. Build the backend Docker image (cached after first run)
2. Start services via `docker-compose.dev.yml` (with hot-reload bind mounts)
3. Poll Postgres until it accepts connections (`pg_isready` — no fixed sleeps)
4. Apply pending Alembic migrations (no-op if already at head)

It does **not** re-seed the admin user — that lives in `make seed` and is run once. This way `make dev` stays cheap to re-run after every code/config change.

**Then access:**

- API: <http://localhost:{{ cookiecutter.backend_port }}>
- Docs: <http://localhost:{{ cookiecutter.backend_port }}/docs>
{%- if cookiecutter.use_jwt %}
- Admin: <http://localhost:{{ cookiecutter.backend_port }}/admin> — `admin@example.com` / `admin123` after `make seed`
{%- endif %}
{%- if cookiecutter.use_frontend %}
- Frontend: <http://localhost:{{ cookiecutter.frontend_port }}> — start with `make dev-frontend` (Docker) or `cd frontend && bun install && bun dev` (local)
{%- endif %}

### Day-to-day commands

```bash
make dev           # bootstrap or restart (idempotent, no admin re-seed)
{%- if cookiecutter.use_jwt %}
make seed          # one-shot admin creation (no-op if admin already exists)
{%- endif %}
make dev-down      # stop everything
make dev-logs      # tail logs (Ctrl-C to exit)
make dev-rebuild   # force-rebuild backend image (after pyproject.toml change)
{%- if cookiecutter.use_frontend %}
make dev-frontend  # start the Next.js container
{%- endif %}
```

If you prefer running the backend on the host (not in Docker) — useful for breakpoints / IDE debugging:

```bash
make install       # uv sync + pre-commit install
docker compose -f docker-compose.dev.yml up -d db{% if cookiecutter.enable_redis %} redis{% endif %}{% if cookiecutter.enable_rag %} milvus etcd minio{% endif %}
make db-upgrade    # apply migrations
make run           # run uvicorn locally with --reload
```

---

## Environments

| `make` target | Compose file | Use case |
|---|---|---|
| `make dev` | `docker-compose.dev.yml` | Local development with hot-reload + bind-mounted source. |
| `make stage` | `docker-compose.yml` | Production-like build, no bind mounts, runs on localhost. Good for sanity-checking before deploy. |
| `make prod` | `docker-compose.prod.yml` | Production. Requires `backend/.env` (copy from `backend/.env.example`, fill real secrets) and an external Nginx using `nginx/nginx.conf`. |

Each env has matching `-down`, `-logs`, `-rebuild` siblings (e.g. `make stage-down`).

---

## Project Structure

```
backend/app/
├── main.py               # FastAPI app + lifespan
├── api/
│   ├── deps.py           # Annotated DI aliases (DBSession, CurrentUser, *Svc)
│   ├── exception_handlers.py
│   └── routes/v1/        # HTTP endpoints — call services, never repos
├── core/
│   ├── config.py         # pydantic-settings (reads .env)
│   ├── security.py       # JWT, bcrypt, API key verification
│   ├── exceptions.py     # AppException → NotFound / Auth / etc.
│   └── middleware.py
├── db/
│   ├── base.py           # DeclarativeBase + TimestampMixin
│   └── models/           # SQLAlchemy models (Mapped[] type hints)
├── schemas/              # Pydantic v2: *Create / *Update / *Read / *List
├── repositories/         # Data access — db.flush() never commit
├── services/             # Business logic — raises domain exceptions
├── agents/               # AI agent wrappers + tools
{%- if cookiecutter.enable_rag %}
├── rag/                  # RAG: vectorstore + embeddings + ingestion + sources
│   └── connectors/       # Pluggable sync sources (Google Drive, S3, …)
{%- endif %}
{%- if cookiecutter.background_tasks != "none" %}
├── worker/
│   ├── background/       # FastAPI BackgroundTasks fallback (in-process)
│   └── tasks/            # Distributed tasks ({{ cookiecutter.background_tasks }})
{%- endif %}
└── commands/             # Click CLI commands (auto-discovered by `{{ cookiecutter.project_slug }} cmd …`)
{%- if cookiecutter.use_frontend %}

frontend/src/
├── app/
│   ├── [locale]/         # next-intl routes (en/pl)
{%- if cookiecutter.enable_marketing_site %}
│   │   ├── (marketing)/  # Public landing, pricing, FAQ, blog
{%- endif %}
│   │   └── (dashboard)/  # Authenticated app
│   └── api/              # Server-side API proxies (forward auth cookies)
├── components/           # React components (chat, marketing, ui primitives)
├── hooks/                # useAuth, useChat, useConversations, …
├── stores/               # Zustand stores
└── lib/                  # api-client, server-api, utils
{%- endif %}
```

---

## CLI

The generated project ships a Click CLI exposed as `{{ cookiecutter.project_slug }}` (after `make install`):

```bash
{{ cookiecutter.project_slug }} server run --reload          # dev server
{{ cookiecutter.project_slug }} db upgrade                   # apply migrations
{{ cookiecutter.project_slug }} db migrate -m "message"      # create new migration
{{ cookiecutter.project_slug }} user create-admin            # interactive admin creation
{%- if cookiecutter.enable_rag %}
{{ cookiecutter.project_slug }} rag-ingest <path> -c docs    # ingest local files
{{ cookiecutter.project_slug }} rag-search "query" -c docs   # semantic search
{{ cookiecutter.project_slug }} rag-collections              # list collections
{%- endif %}
{%- if cookiecutter.background_tasks == "celery" %}
{{ cookiecutter.project_slug }} celery worker                # start worker
{{ cookiecutter.project_slug }} celery beat                  # start scheduler
{%- elif cookiecutter.background_tasks == "taskiq" %}
{{ cookiecutter.project_slug }} taskiq worker                # start worker
{{ cookiecutter.project_slug }} taskiq scheduler             # start scheduler
{%- endif %}
```
{%- if cookiecutter.background_tasks == "prefect" %}

Background work runs on **Prefect** — the `prefect-server` (UI at <http://localhost:4200>) and `prefect-runner` containers start with `make dev`. Flows live in `app/worker/tasks/` and are registered in `app/worker/prefect_app.py`.
{%- endif %}

Run `make help` for a categorized list, or `{{ cookiecutter.project_slug }} --help` for full CLI docs.

---

## Configuration

All backend config lives in `backend/.env` (committed for dev defaults). Key variables:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB={{ cookiecutter.project_slug }}
{%- if cookiecutter.use_openai %}

# OpenAI — required for chat + embeddings
OPENAI_API_KEY=sk-…
{%- endif %}
{%- if cookiecutter.use_anthropic %}
ANTHROPIC_API_KEY=sk-ant-…
{%- endif %}
{%- if cookiecutter.use_google %}
GOOGLE_API_KEY=…
{%- endif %}
{%- if cookiecutter.enable_oauth_google %}

# Google OAuth (Sign in with Google)
GOOGLE_CLIENT_ID=…
GOOGLE_CLIENT_SECRET=…
{%- endif %}
{%- if cookiecutter.enable_billing %}

# Stripe billing
STRIPE_SECRET_KEY=sk_test_…
STRIPE_WEBHOOK_SECRET=whsec_…
{%- endif %}
{%- if cookiecutter.enable_email %}

# Email (transactional + lifecycle)
EMAIL_PROVIDER={{ cookiecutter.email_provider }}
{%- if cookiecutter.email_provider == "resend" %}
RESEND_API_KEY=re_…
{%- endif %}
EMAIL_FROM=noreply@your-domain.com
{%- endif %}
```

See `backend/.env.example` for the full list with comments.

For production, **never** commit secrets — `backend/.env` is gitignored. Fill it with real values on the server (or inject them via your platform's secret manager: Doppler, AWS Secrets Manager, GitHub Actions secrets, etc.). The same `backend/.env` is used for dev and prod — there is no separate `.env.prod`.

---

## Development

| Command | What it does |
|---|---|
| `make test` | Run pytest |
| `make lint` | Run ruff check + format check + ty |
| `make format` | Auto-format with ruff |
| `make db-migrate` | Generate a new migration from model changes (interactive) |
| `make db-upgrade` | Apply pending migrations |
| `make db-downgrade` | Roll back one migration |
| `make db-current` | Show current head |
{%- if cookiecutter.use_jwt %}
| `make create-admin` | Interactive admin creation |
| `make user-list` | List all users |
{%- endif %}
{%- if cookiecutter.background_tasks == "celery" %}
| `make celery-worker` | Run Celery worker locally |
| `make celery-beat` | Run Celery beat |
| `make celery-flower` | Open Flower UI at <http://localhost:5555> |
{%- elif cookiecutter.background_tasks == "taskiq" %}
| `make taskiq-worker` | Run Taskiq worker locally |
| `make taskiq-scheduler` | Run Taskiq scheduler |
{%- elif cookiecutter.background_tasks == "prefect" %}
| `make dev` | Starts the Prefect server + runner (UI at <http://localhost:4200>) |
{%- endif %}

---
{%- if cookiecutter.enable_rag %}

## RAG (Knowledge Base)

Using **{{ cookiecutter.vector_store }}** as the vector store with **{{ cookiecutter.embedding_provider }}** embeddings.

```bash
# Ingest local files (recursive)
{{ cookiecutter.project_slug }} rag-ingest /path/to/docs/ --collection documents --recursive

{%- if cookiecutter.enable_google_drive_ingestion %}
# Pull from Google Drive (service-account auth)
{{ cookiecutter.project_slug }} rag-sync-gdrive --collection documents --folder-id <id>
{%- endif %}
{%- if cookiecutter.enable_s3_ingestion %}
# Pull from S3 / MinIO
{{ cookiecutter.project_slug }} rag-sync-s3 --collection documents --prefix docs/
{%- endif %}

# Semantic search
{{ cookiecutter.project_slug }} rag-search "your query" --collection documents
```

PDF parsing uses **{{ cookiecutter.pdf_parser }}**. See `docs/howto/add-rag-source.md` to add a new source connector.
{%- endif %}
{%- if cookiecutter.use_frontend %}

---

## Frontend

```bash
cd frontend
bun install
bun dev          # http://localhost:{{ cookiecutter.frontend_port }}
bun run lint
bun run build
```

The frontend talks to the backend through Next.js API route handlers in `src/app/api/*` (server-side proxy that forwards auth cookies to the FastAPI backend). Direct calls to `localhost:{{ cookiecutter.backend_port }}` from the browser are deliberately avoided.

i18n (PL + EN) ships out of the box via `next-intl`. Add a new locale by extending `messages/<lang>.json` and `src/i18n.ts`.
{%- endif %}

---

## Deployment

### Frontend → Vercel

```bash
cd frontend && npx vercel --prod
```

Set in the Vercel dashboard:

- `BACKEND_URL` = `https://api.your-domain.com`
- `BACKEND_WS_URL` = `wss://api.your-domain.com`
- `NEXT_PUBLIC_AUTH_ENABLED` = `true`
{%- if cookiecutter.enable_rag %}
- `NEXT_PUBLIC_RAG_ENABLED` = `true`
{%- endif %}

### Backend → your server

```bash
# 1. SSH to the box, clone the repo
# 2. cp backend/.env.example backend/.env, fill in real secrets
# 3. Configure nginx using nginx/nginx.conf as reference
# 4. Bring up the stack:
make prod

# Day-to-day:
make prod-logs
make prod-down
```

Migrations run automatically on `make prod`. For a fresh deploy on a new host, the same `make prod` is the bootstrap command.

---

## Guides

| Guide | What |
|-------|-------|
| `docs/howto/add-api-endpoint.md` | Add a new REST endpoint |
| `docs/howto/add-agent-tool.md` | Create an agent tool |
| `docs/howto/customize-agent-prompt.md` | Tune system prompts |
{%- if cookiecutter.background_tasks != "none" %}
| `docs/howto/add-background-task.md` | Add a background task |
{%- endif %}
{%- if cookiecutter.enable_rag %}
| `docs/howto/add-rag-source.md` | Add a RAG document source |
| `docs/howto/add-sync-connector.md` | Build a custom sync connector |
{%- endif %}

---

*Generated with [Full-Stack AI Agent Template](https://github.com/vstorm-co/full-stack-ai-agent-template) v{{ cookiecutter.generator_version }}.*
