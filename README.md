<p align="center">
  <img src="https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/landing_hero.png" alt="AI that knows your work — generated marketing site and chat assistant" width="100%">
</p>

<h1 align="center">Full-Stack AI Agent Template</h1>

<p align="center">
  <i>Production-ready FastAPI + Next.js project generator with AI agents, RAG, and 20+ enterprise integrations.</i>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-demo">Demo</a> •
  <a href="https://vstorm-co.github.io/full-stack-ai-agent-template/">Documentation</a> •
  <a href="https://oss.vstorm.co/projects/full-stack-ai-agent-template/configurator/">Configurator</a> •
  <a href="https://pypi.org/project/fastapi-fullstack/">PyPI</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/fastapi-fullstack/"><img src="https://img.shields.io/pypi/v/fastapi-fullstack?color=green&logo=pypi&logoColor=white" alt="PyPI"></a>
  <a href="https://pepy.tech/projects/fastapi-fullstack"><img src="https://static.pepy.tech/badge/fastapi-fullstack/month" alt="PyPI Downloads"></a>
  <a href="https://github.com/vstorm-co/full-stack-ai-agent-template/stargazers"><img src="https://img.shields.io/github/stars/vstorm-co/full-stack-ai-agent-template?style=flat&logo=github&color=yellow" alt="GitHub Stars"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/LICENSE"><img src="https://img.shields.io/github/license/vstorm-co/full-stack-ai-agent-template?color=blue" alt="License"></a>
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen" alt="Coverage">
  <a href="https://github.com/vstorm-co/full-stack-ai-agent-template/actions/workflows/ci.yml"><img src="https://github.com/vstorm-co/full-stack-ai-agent-template/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/SECURITY.md"><img src="https://img.shields.io/badge/security-policy-blueviolet?logo=shieldsdotio&logoColor=white" alt="Security Policy"></a>
  <a href="https://www.bestpractices.dev/projects/12539"><img src="https://www.bestpractices.dev/projects/12539/badge" alt="OpenSSF Best Practices"></a>
  <a href="https://github.com/pydantic/pydantic-ai"><img src="https://img.shields.io/badge/Powered%20by-Pydantic%20AI-E92063?logo=pydantic&logoColor=white" alt="Pydantic AI"></a>
  <a href="https://x.com/Kacper95682155"><img src="https://img.shields.io/badge/X-000000?logo=x&logoColor=white" alt="X"></a>
</p>

<p align="center">
  <b>🤖 5 AI Agent Frameworks</b> <i>(PydanticAI, PydanticDeep, LangChain, LangGraph, DeepAgents)</i>
  <br>
  <b>📄 RAG Pipeline</b> <i>(Milvus, Qdrant, pgvector, ChromaDB)</i>
  <br>
  <b>⚡ FastAPI + Next.js 15</b> <i>(WebSocket streaming, real-time chat UI)</i>
  <br>
  <b>🔗 Conversation Sharing</b> <i>(direct sharing, public links, admin browser)</i>
  <br>
  <b>🔒 Enterprise-Ready</b> <i>(JWT, OAuth, admin panel, Celery, Docker, K8s)</i>
</p>

<details>
<summary><b>Table of Contents</b></summary>

- [Quick Start](#-quick-start)
- [Demo](#-demo)
- [Screenshots](#-screenshots)
- [Why This Template](#-why-this-template)
- [Features](#-features)
- [Architecture](#-architecture)
- [AI Agent](#-ai-agent)
- [RAG](#-rag-retrieval-augmented-generation)
- [Observability](#-observability)
- [Django-style CLI](#-django-style-cli)
- [Generated Project Structure](#-generated-project-structure)
- [Configuration Options](#-configuration-options)
- [Comparison](#-comparison)
- [FAQ](#-faq)
- [Documentation](#-documentation)
- [Contributing](#-contributing)

</details>

---

## Vstorm OSS Ecosystem

This template is part of a broader open-source ecosystem for production AI agents:

| Project | Description | |
|---------|-------------|---|
| **[pydantic-deepagents](https://github.com/vstorm-co/pydantic-deepagents)** | The modular agent runtime for Python. Claude Code-style CLI with Docker sandbox, browser automation, multi-agent teams, and /improve. | [![Stars](https://img.shields.io/github/stars/vstorm-co/pydantic-deepagents?style=flat&logo=github&color=yellow)](https://github.com/vstorm-co/pydantic-deepagents) |
| **[pydantic-ai-shields](https://github.com/vstorm-co/pydantic-ai-shields)** | Drop-in guardrails for Pydantic AI agents. 5 infra + 5 content shields. | [![Stars](https://img.shields.io/github/stars/vstorm-co/pydantic-ai-shields?style=flat&logo=github&color=yellow)](https://github.com/vstorm-co/pydantic-ai-shields) |
| **[pydantic-ai-subagents](https://github.com/vstorm-co/pydantic-ai-subagents)** | Declarative multi-agent orchestration with token tracking. | [![Stars](https://img.shields.io/github/stars/vstorm-co/pydantic-ai-subagents?style=flat&logo=github&color=yellow)](https://github.com/vstorm-co/pydantic-ai-subagents) |
| **[summarization-pydantic-ai](https://github.com/vstorm-co/pydantic-ai-summarization)** | Smart context compression for long-running agents. | [![Stars](https://img.shields.io/github/stars/vstorm-co/summarization-pydantic-ai?style=flat&logo=github&color=yellow)](https://github.com/vstorm-co/summarization-pydantic-ai) |
| **[pydantic-ai-backend](https://github.com/vstorm-co/pydantic-ai-backend)** | Sandboxed execution for AI agents. Docker + Daytona. | [![Stars](https://img.shields.io/github/stars/vstorm-co/pydantic-ai-backend?style=flat&logo=github&color=yellow)](https://github.com/vstorm-co/pydantic-ai-backend) |

> **Want the runtime behind this template's AI agents?** [pydantic-deepagents](https://github.com/vstorm-co/pydantic-deepagents) powers the `deepagents` framework option — install it standalone with `curl -fsSL .../install.sh | bash`.

Browse all projects at [oss.vstorm.co](https://oss.vstorm.co)

---

## 🚀 Quick Start

> [!TIP]
> **Prefer a visual configurator?** Use the [Web Configurator](https://oss.vstorm.co/projects/full-stack-ai-agent-template/configurator/) to configure your project in the browser and download a ZIP — no CLI installation needed.

### Installation

```bash
# pip
pip install fastapi-fullstack

# uv (recommended)
uv tool install fastapi-fullstack

# pipx
pipx install fastapi-fullstack
```

### From zero to a running app

Three steps. The wizard scaffolds the project, `make bootstrap` brings up the whole backend, and the frontend runs with a single command:

```bash
# 1. Generate your project — just answer the wizard's prompts
fastapi-fullstack

# 2. Backend + PostgreSQL up, migrations applied, default admin seeded
cd my_ai_app
make bootstrap

# 3. Frontend (in a second terminal)
cd frontend && bun install && bun dev
```

> **What `make bootstrap` does** (= `make dev` + `make seed`): builds the backend Docker image, starts the stack via `docker-compose.dev.yml`, waits for PostgreSQL (`pg_isready`), applies Alembic migrations, and seeds `admin@example.com` / `admin123`. It's idempotent — re-run it anytime.

**Then access:**

| | URL | |
|---|---|---|
| Backend API | <http://localhost:8000> | |
| Docs | <http://localhost:8000/docs> | OpenAPI / Swagger |
| Admin | <http://localhost:8000/admin> | `admin@example.com` / `admin123` (after `make seed`) |
| Frontend | <http://localhost:3000> | `make dev-frontend` (Docker) or `cd frontend && bun install && bun dev` (local) |

### Day-to-day commands

```bash
make dev           # bootstrap or restart (no admin re-seed)
make seed          # one-shot admin creation (no-op if admin exists)
make dev-down      # stop everything
make dev-logs      # tail container logs
make dev-rebuild   # force-rebuild backend image (after pyproject.toml changes)
make dev-frontend  # start the Next.js container
```

After the first `make bootstrap`, day-to-day you just run `make dev` (skips admin re-seed). Run `make help` inside the project for the full list.

<details>
<summary><b>Other ways to generate (flags, presets, minimal)</b></summary>

Skip the wizard and pass options directly:

```bash
# Non-interactive with explicit options
fastapi-fullstack create my_ai_app --database postgresql --frontend nextjs

# Presets for common scenarios (run `fastapi-fullstack templates` for the full list)
fastapi-fullstack create my_ai_app --preset ai-agent           # AI agent with streaming
fastapi-fullstack create my_ai_app --preset production         # Full production setup
fastapi-fullstack create my_ai_app --preset production-saas    # SaaS: billing, teams, admin

# Bare-bones project (PostgreSQL, no Docker/Redis/CI)
fastapi-fullstack create my_ai_app --minimal
```

</details>

### Environments

| `make` target | Compose file | When to use |
|---|---|---|
| `make dev` | `docker-compose.dev.yml` | Local development with hot-reload + bind-mounted source. |
| `make stage` | `docker-compose.yml` | Production-like build (no bind mounts) running on localhost. Sanity-check before deploy. |
| `make prod` | `docker-compose.prod.yml` | Production. Requires `backend/.env` (copy from `backend/.env.example`, fill real secrets) + external Nginx using `nginx/nginx.conf`. |

Each env has matching `-down`, `-logs`, `-rebuild` siblings.

> [!NOTE]
> **Windows users:** `make` requires GNU Make. Install via [Chocolatey](https://chocolatey.org/) (`choco install make`) or use **WSL2 / Git Bash**. The Docker workflow is identical across macOS, Linux, and WSL2.

<details>
<summary><b>Local backend (no Docker, for IDE breakpoints)</b></summary>

If you want to run the backend on the host while the database stays in Docker:

```bash
cd my_ai_app
make install                                                # uv sync + pre-commit hooks

# Start only infrastructure containers
docker compose -f docker-compose.dev.yml up -d db redis    # add 'milvus etcd minio' if RAG

make db-upgrade                                             # apply migrations
make create-admin                                           # interactive
make run                                                    # uvicorn --reload
```

</details>

<details>
<summary><b>Production deploy</b></summary>

```bash
# On your server
git clone <your-repo>
cd my_ai_app

cp backend/.env.example backend/.env            # fill in real secrets
# Configure your nginx host using nginx/nginx.conf as reference

make prod                                       # builds + starts + migrates
make prod-logs                                  # tail logs
```

For frontend deployment to **Vercel**:

```bash
cd frontend && npx vercel --prod
```

In the Vercel dashboard set `BACKEND_URL`, `BACKEND_WS_URL`, `NEXT_PUBLIC_AUTH_ENABLED=true`.

</details>

### Using the Project CLI

Each generated project has a CLI named after your `project_slug`. For example, if you created `my_ai_app`:

```bash
cd backend

# The CLI command is: uv run <project_slug> <command>
uv run my_ai_app server run --reload     # Start dev server
uv run my_ai_app db migrate -m "message" # Create migration
uv run my_ai_app db upgrade              # Apply migrations
uv run my_ai_app user create-admin       # Create admin user
```

Use `make help` to see all available Makefile shortcuts.

---

## 🎬 Demo

> The videos below are best viewed on GitHub. On other viewers, see the [Screenshots](#-screenshots) gallery.

**Live AI chat** — streaming responses, tool calls, charts, and a live plan/task checklist:

<video src="https://github.com/vstorm-co/full-stack-ai-agent-template/raw/main/assets/new3/chat_demo_with_tasks.mp4" controls muted width="100%"></video>

**File upload & RAG ingestion** — drop a document, watch it get parsed, chunked, embedded, and answered against:

<video src="https://github.com/vstorm-co/full-stack-ai-agent-template/raw/main/assets/new3/rag_demo.mp4" controls muted width="100%"></video>

**Generated marketing site** — the public landing page that ships with `enable_marketing_site`:

<video src="https://github.com/vstorm-co/full-stack-ai-agent-template/raw/main/assets/new3/landing.mp4" controls muted width="100%"></video>

**CLI generator** — configure and scaffold a project in seconds:

<video src="https://github.com/vstorm-co/full-stack-ai-agent-template/raw/main/assets/new3/cli_generator_demo_2.mp4" controls muted width="100%"></video>

---

## 📸 Screenshots

### AI Chat

The chat UI streams responses over WebSocket and renders each tool call as a purpose-built card instead of a raw JSON dump.

**Plan & tasks** — a sticky plan/task checklist sits above the composer, updating live as the agent (or Deep Research planner) works through steps, with an inline "thinking" indicator.

![Chat plan and tasks](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/chat_tasks.png)

**Subagents** — when work is delegated, a live subagent feed and side panel show each subagent's status, streamed messages, and final result.

![Chat subagents](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/chat_subagents.png)

**Charts** — the agent's `create_chart` tool renders interactive, theme-aware bar / area / line / pie / scatter charts directly in the conversation.

![Chat charts](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/chat_graphs.png)

**Code execution** — the optional `run_python` tool shows the executed code alongside its stdout / result (or error) in a collapsible card.

![Chat Python code execution](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/chat_python_code.png)

**Ask user** — the agent can pause to ask clarifying questions and resume once you answer; the card keeps the full question/answer transcript.

![Chat ask-user tool](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/chat_ask_user.png)

**Reasoning & answered questions** — a clean reasoning/"thinking" view plus answered-question history keeps long agent turns readable.

![Chat reasoning and answered questions](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/chat_answered_questions_and_thinking.png)

### Marketing Site

**Landing Page** — Full-page marketing site with hero, features breakdown, testimonials, pricing preview, and FAQ. Generated with the `enable_marketing_site` option.

![Landing Page](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/landing_full.png)

**Pricing** — Three-tier pricing page with monthly/annual toggle. Pulls live plan data from Stripe when connected; shows template plans otherwise.

![Pricing](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/landing_pricing.png)

**Blog** — Engineering blog included out of the box. Posts are MDX files in the repo — no CMS needed. Supports tags, featured posts, and author bylines.

![Blog](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/blogs.png)

### Auth

**Login** — Split-screen login with Google OAuth and email/password. Left panel shows a product pitch with a social proof quote. HTTP-only cookie session on submit.

![Login](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/login.png)

**Register** — Same split-screen layout as login. Google sign-up and email/password form with confirm-password field and terms acceptance.

![Register](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/register.png)

### Dashboard

**Dashboard (light mode)** — Workspace overview with conversation count, knowledge base vectors, sparkline stat cards, a usage timeline, recent activity, and team info. Onboarding banner guides new users through setup.

![Dashboard Light](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/dashboard_light.png)

**Dashboard (dark mode)** — Same dashboard in dark theme. Theme is saved per-device and can be overridden per-workspace in appearance settings.

![Dashboard Dark](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/dashboard_dark.png)

### Teams & Organizations

**Workspaces** — List of all organizations the user belongs to. Shows plan tier and role for each. Users can switch active workspace or create a new organization.

![Organizations](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/organizations_light.png)

**Team Management** — Organization detail page with workspace profile (name + avatar), member list with roles, and an "Invite teammate" button. Owners and admins can adjust roles inline.

![Organization Details](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/organization_light.png)

### Knowledge Bases

**Knowledge Bases** — List of RAG knowledge bases scoped to the current workspace. Each base shows its collection slug. Users can create new bases, toggle which ones are active in chat, and upload documents through the UI.

![Knowledge Bases](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/knowledge_bases_light.png)

**Documents & Sync Sources** — Inspect a knowledge base's documents, preview or download any file in-app, and manage connected sync sources (Google Drive, S3/MinIO) with manual triggers and per-run logs.

![Knowledge Base Source](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/knowledge_base_source_light.png)

### Billing & Usage

**Billing Overview** — Workspace billing dashboard showing the current plan, seats, storage usage (chat attachments + indexed RAG documents), and quick links to usage, invoices, payment methods, and subscription. "Manage in Stripe" opens the Customer Portal.

![Billing and usage](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/billing_and_usage_light.png)

**Usage** — Daily credits-spent and call-count charts plus a by-model token breakdown, built from per-message usage events.

![Billing usage charts](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/billing_usage_light.png)

**Credits** — Credit balance and an immutable transaction ledger (grants, purchases, debits) with a usage sparkline.

![Billing credits](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/billing_credits_light.png)

**Subscription, Invoices & Payment Methods** — Manage the plan, view invoices, and update payment methods — all backed by Stripe.

![Billing subscription](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/billing_subscription_light.png)
![Billing invoices](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/billing_invoices_light.png)

### Profile & Settings

**Profile** — Personal info tab: avatar upload, display name, email, and active session list with per-device revoke buttons. Visibility note explains which fields are shown to teammates.

![Profile](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/profile_light.png)

**Account & Security** — Change password form with strength guidance, "Sign out everywhere" button, and danger zone for permanent account deletion.

![Account](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/account_light.png)

**Slash Commands** — Customize the `/command` palette in chat. Toggle built-in commands (`/clear`, `/regen`, `/settings`, `/summarize`, `/explain`) and create custom shortcuts that send a stored prompt with a few keystrokes.

![Slash Commands](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/commands_light.png)

**Appearance** — Theme switcher (light / dark / system) and brand color picker with five presets: Blue, Green, Red, Orange, and Violet. Brand color updates CSS variables across the entire workspace and is saved per-device.

![Appearance](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/appearance_light.png)

**Notification Preferences** — Per-category notification controls with separate toggles for email and in-app delivery. Categories: Billing, Team activity, Security alerts, and Product updates.

![Notifications](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/notifications_light.png)

### Admin Panel

**Admin Overview** — Workspace-wide metrics (total users, active sessions last 24h, conversation count, MRR) plus a recent activity feed showing all conversations across all users. Requires the `admin` role.

![Admin Overview](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/admin_overview_light.png)

**User Management** — Full user list with search by email or name. Shows role, status, join date, and an "Inspect" action to impersonate or suspend any user. Pagination built in.

![Admin Users](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/admin_users_light.png)

**Conversation Browser** — Browse all conversations across the workspace. Filter by status and owner, sort by any column, open any conversation in a read-only view. Useful for support and quality review.

![Admin Conversations](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/admin_conversations_light.png)

**Message Quality & Ratings** — Aggregated like/dislike feedback on AI responses. Shows approval rate, a daily chart, and a filterable table of individual ratings with optional user comments.

![Admin Ratings](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/admin_ratings_light.png)

**Stripe Events Log** — Webhook event browser for debugging Stripe billing flows. Lists all received events (type, customer, amount, status, timestamp) and lets admins manually replay any event.

![Stripe Events](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/admin_stripe_events_light.png)

**System Health** — Live readiness dashboard. Checks API, PostgreSQL, Redis, Vector store, LLM provider, Background worker, and Stripe API, with uptime percentage per service.

![System Health](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/admin_system_light.png)

### Background Tasks & Orchestration

**Prefect** — Choose Prefect as your task queue (in the interactive wizard) and the project ships a self-hosted Prefect server and runner. Flows cover RAG ingestion/sync, billing & email reminders, and credits maintenance, each on a cron/interval schedule visible in the Prefect UI.

![Prefect dashboard](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/prefect_dashboard.png)
![Prefect flow runs](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/prefect_runs.png)
![Prefect task timeline](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new3/prefect_task_timeline.png)

### Observability

**Logfire (PydanticAI)** — Full distributed tracing for PydanticAI agent runs, FastAPI requests, database queries, Redis, Celery tasks, and HTTPX calls — all in one timeline.

![Logfire](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/logfire.png)

**LangSmith (LangChain / LangGraph)** — Trace viewer for LangChain agent runs with step-by-step chain inspection, token usage, and feedback collection.

![LangSmith](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/langsmith.png)

### Messaging Channels

**Telegram Bot** — Multi-bot integration with both polling and webhook modes. Each bot gets its own session, supports group concurrency control, and routes messages through the same agent pipeline as the web UI.

![Telegram](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/telegram.png)

### Monitoring & API

**Celery Flower** — Real-time task queue monitor. Track worker status, task throughput, and failure rates for background jobs (document ingestion, email, webhooks).

![Flower](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/flower.png)

**API Documentation** — Auto-generated OpenAPI / Swagger UI at `/docs`. All endpoints documented with request/response schemas, auth requirements, and example payloads.

![API Docs](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/docs_2.png)

---

## 🎯 Why This Template

Building AI/LLM applications requires more than just an API wrapper. You need:

- **Type-safe AI agents** with tool/function calling
- **Real-time streaming** responses via WebSocket
- **Conversation persistence** and history management
- **Production infrastructure** - auth, rate limiting, observability
- **Enterprise integrations** - background tasks, webhooks, admin panels

This template gives you all of that out of the box, with **20+ configurable integrations** so you can focus on building your AI product, not boilerplate.

### Perfect For

- 🤖 **AI Chatbots & Assistants** - PydanticAI or LangChain agents with streaming responses
- 📊 **ML Applications** - Background task processing with Celery/Taskiq
- 🏢 **Enterprise SaaS** - Full auth, admin panel, webhooks, and more
- 🚀 **Startups** - Ship fast with production-ready infrastructure

### AI-Agent Friendly

Generated projects include **CLAUDE.md** and **AGENTS.md** files optimized for AI coding assistants (Claude Code, Codex, Copilot, Cursor, Zed). Following [progressive disclosure](https://humanlayer.dev/blog/writing-a-good-claude-md) best practices - concise project overview with pointers to detailed docs when needed.

They also ship a ready-to-use **`.claude/` toolkit** that adapts to the options you selected:

- **Agent Skills** (`.claude/skills/`) — model-invoked playbooks that auto-trigger when relevant: `alembic-migration`, `pytest-suite`, `agent-tool` (framework-aware), `frontend-feature`, `rag-knowledge`, `background-task` (queue-aware), `billing-stripe`, and `channel-bot`. Feature-gated — only the skills that match your stack are generated.
- **Slash commands** (`.claude/commands/`) — `/add-endpoint`, `/fix-issue`, `/review`.
- **Convention rules** (`.claude/rules/`) — architecture, code style, schemas, exceptions/security, testing, and frontend conventions, loaded automatically.

---

## ✨ Features

<p align="center">
  <a href="https://ai.pydantic.dev"><img src="https://img.shields.io/badge/PydanticAI-E92063?logo=pydantic&logoColor=white" alt="PydanticAI"></a>
  <a href="https://python.langchain.com"><img src="https://img.shields.io/badge/LangChain-1C3C3C?logo=langchain&logoColor=white" alt="LangChain"></a>
  <a href="https://langchain-ai.github.io/langgraph/"><img src="https://img.shields.io/badge/LangGraph-005A9C?logo=langchain&logoColor=white" alt="LangGraph"></a>
  <a href="https://milvus.io"><img src="https://img.shields.io/badge/Milvus-FF6B35?logoColor=white" alt="Milvus"></a>
  <a href="https://openai.com"><img src="https://img.shields.io/badge/OpenAI-412991?logo=openai&logoColor=white" alt="OpenAI"></a>
  <a href="https://anthropic.com"><img src="https://img.shields.io/badge/Anthropic-D4A373?logo=anthropic&logoColor=white" alt="Anthropic"></a>
  <a href="https://ai.google.dev"><img src="https://img.shields.io/badge/Gemini-4285F4?logo=google&logoColor=white" alt="Google Gemini"></a>
  <a href="https://openrouter.ai"><img src="https://img.shields.io/badge/OpenRouter-6366F1?logoColor=white" alt="OpenRouter"></a>
</p>

<p align="center">
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://nextjs.org"><img src="https://img.shields.io/badge/Next.js_15-000000?logo=next.js&logoColor=white" alt="Next.js 15"></a>
  <a href="https://react.dev"><img src="https://img.shields.io/badge/React_19-61DAFB?logo=react&logoColor=black" alt="React 19"></a>
  <a href="https://www.typescriptlang.org"><img src="https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="https://tailwindcss.com"><img src="https://img.shields.io/badge/Tailwind_v4-06B6D4?logo=tailwindcss&logoColor=white" alt="Tailwind CSS"></a>
  <a href="https://www.sqlalchemy.org"><img src="https://img.shields.io/badge/SQLAlchemy-D71F00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy"></a>
</p>

<p align="center">
  <a href="https://www.postgresql.org"><img src="https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL"></a>
  <a href="https://redis.io"><img src="https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white" alt="Redis"></a>
  <a href="https://milvus.io"><img src="https://img.shields.io/badge/Milvus-00A1EA?logoColor=white" alt="Milvus"></a>
  <a href="https://qdrant.tech"><img src="https://img.shields.io/badge/Qdrant-FF6B6B?logoColor=white" alt="Qdrant"></a>
  <a href="https://www.trychroma.com"><img src="https://img.shields.io/badge/ChromaDB-FF6F61?logoColor=white" alt="ChromaDB"></a>
  <a href="https://docs.celeryq.dev"><img src="https://img.shields.io/badge/Celery-37814A?logo=celery&logoColor=white" alt="Celery"></a>
  <a href="https://www.prefect.io"><img src="https://img.shields.io/badge/Prefect-070E10?logo=prefect&logoColor=white" alt="Prefect"></a>
  <a href="https://logfire.pydantic.dev"><img src="https://img.shields.io/badge/Logfire-E92063?logo=pydantic&logoColor=white" alt="Logfire"></a>
  <a href="https://sentry.io"><img src="https://img.shields.io/badge/Sentry-362D59?logo=sentry&logoColor=white" alt="Sentry"></a>
  <a href="https://prometheus.io"><img src="https://img.shields.io/badge/Prometheus-E6522C?logo=prometheus&logoColor=white" alt="Prometheus"></a>
</p>

<p align="center">
  <a href="https://www.docker.com"><img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white" alt="Docker"></a>
  <a href="https://kubernetes.io"><img src="https://img.shields.io/badge/Kubernetes-326CE5?logo=kubernetes&logoColor=white" alt="Kubernetes"></a>
  <a href="https://github.com/features/actions"><img src="https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white" alt="GitHub Actions"></a>
  <a href="https://aws.amazon.com/s3/"><img src="https://img.shields.io/badge/S3-569A31?logo=amazons3&logoColor=white" alt="S3"></a>
</p>

### 🤖 AI/LLM First

- **5 AI Frameworks** - [PydanticAI](https://ai.pydantic.dev), [PydanticDeep](https://github.com/vstorm-co/pydantic-deep), [LangChain](https://python.langchain.com), [LangGraph](https://langchain-ai.github.io/langgraph/), [DeepAgents](https://github.com/vstorm-co/pydantic-deepagents)
- **4 LLM Providers** - OpenAI, Anthropic, Google Gemini, OpenRouter
- **RAG** - Document ingestion, vector search, reranking (Milvus, Qdrant, ChromaDB, pgvector)
- **WebSocket Streaming** - Real-time responses with full event access
- **Rich Chat UI** - Specialized tool-call cards (web search, knowledge base, Python, charts, skills), live subagent feed, citation sources panel, plan/task checklist, reasoning view, and in-chat file previews
- **Agent Tools** - Web search, URL fetch, charts, code execution (`run_python`), skills, `ask_user`, plus optional Deep Research (TODO planner + parallel subagents)
- **Messaging Channels** - Telegram and Slack multi-bot integration with polling, webhooks, per-thread sessions, group concurrency control
- **Conversation Sharing** - Share conversations with users or via public links, admin conversation browser
- **Conversation Persistence** - Save chat history to database
- **Message Ratings** - Like/dislike responses with feedback, admin analytics
- **Image Description** - Extract images from documents, describe via LLM vision
- **Multimodal Embeddings** - Provider-aware: OpenAI, Voyage (Anthropic), Gemini (multimodal text + images)
- **Document Sources** - Local files, API upload, Google Drive, S3/MinIO
- **Sync Sources** - Per-organization connector management UI (Google Drive, S3/MinIO) with scheduled sync, manual triggers, encrypted credentials, and per-run logs
- **Observability** - Logfire for PydanticAI, LangSmith for LangChain/LangGraph/DeepAgents

### ⚡ Backend (FastAPI)

- **[FastAPI](https://fastapi.tiangolo.com)** + **[Pydantic v2](https://docs.pydantic.dev)** - High-performance async API
- **PostgreSQL** (async) - SQLAlchemy 2.0 + Alembic migrations, pgvector-ready
- **Authentication** - JWT + Refresh tokens, API Keys, OAuth2 (Google)
- **Background Tasks** - Celery, Taskiq, ARQ, or Prefect
- **Django-style CLI** - Custom management commands with auto-discovery

### 🎨 Frontend (Next.js 15)

- **React 19** + **TypeScript** + **Tailwind CSS v4**
- **AI Chat Interface** - WebSocket streaming, tool call visualization
- **Authentication** - HTTP-only cookies, auto-refresh, password reset, magic link
- **Marketing Site** - hero, pricing, FAQ, blog, contact form, legal pages (PL + EN)
- **Billing Dashboard** - subscription, payment methods, invoices, credits balance/ledger, and usage charts (Stripe)
- **User Settings** - profile, API keys CRUD (`sk_*` tokens), onboarding tracking
- **Admin Panel** - workspace stats, message-rating analytics, Stripe events browser
- **SEO** - per-page metadata, OG image, sitemap, robots, manifest, favicons
- **Dark Mode** + **i18n** (PL/EN via next-intl, locale-prefixed routes)

### 🔌 20+ Enterprise Integrations

| Category | Integrations |
|----------|-------------|
| **AI Frameworks** | PydanticAI, PydanticDeep, LangChain, LangGraph, DeepAgents |
| **LLM Providers** | OpenAI, Anthropic, Google Gemini, OpenRouter |
| **RAG / Vector Stores** | Milvus, Qdrant, ChromaDB, pgvector |
| **RAG Sources** | Local files, API upload, Google Drive, S3/MinIO, Sync Sources (per-org UI, scheduled) |
| **Embeddings** | OpenAI, Voyage, Gemini (multimodal), SentenceTransformers |
| **Background Tasks** | Celery, Taskiq, ARQ, Prefect |
| **Billing** | Stripe subscriptions (seat-based), credits + usage metering, invoices, Customer Portal |
| **Caching & State** | Redis, fastapi-cache2 |
| **Security** | Rate limiting, CORS, CSRF protection |
| **Observability** | Logfire, LangSmith, Sentry, Prometheus |
| **Admin** | SQLAdmin panel with auth |
| **Collaboration** | Conversation sharing (direct + link), admin conversation browser |
| **Messaging** | Telegram multi-bot (polling + webhook), Slack multi-bot (Events API + Socket Mode) |
| **Events** | Webhooks, WebSockets |
| **DevOps** | Docker, GitHub Actions, GitLab CI, Kubernetes |

### 🗺️ Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND  (Next.js 15)                           │
│  Chat UI · Knowledge Base · Dashboard · Settings · Dark Mode · i18n      │
└──────────────┬───────────────────────────────────────────┬───────────────┘
               │  REST / WebSocket                         │  Vercel
               ▼                                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         BACKEND  (FastAPI)                               │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                     AI AGENTS                                   │     │
│  │  PydanticAI · LangChain · LangGraph · DeepAgents                │     │
│  │  ────────────────────────────────────────────────────────────   │     │
│  │  Tools: datetime · web_search (Tavily) · search_knowledge_base  │     │
│  │  Providers: OpenAI · Anthropic · Gemini · OpenRouter            │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                     RAG PIPELINE                                │     │
│  │                                                                 │     │
│  │  Sources        Parse           Chunk          Embed            │     │
│  │  ─────────      ──────────      ──────────     ──────────────   │     │
│  │  Local files    PyMuPDF         recursive      OpenAI           │     │
│  │  API upload     LiteParse       markdown       Voyage           │     │
│  │  Google Drive   LlamaParse      fixed          Gemini (multi)   │     │
│  │  S3/MinIO       python-docx                    SentenceTransf.  │     │
│  │  Sync Sources                                                   │     │
│  │                                                                 │     │
│  │  Store              Search              Rank                    │     │
│  │  ──────────────     ──────────────      ──────────────          │     │
│  │  Milvus             Vector similarity   Cohere reranker         │     │
│  │  Qdrant             BM25 + vector RRF   CrossEncoder            │     │
│  │  ChromaDB           Multi-collection                            │     │
│  │  pgvector                                                       │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│  Auth (JWT/API Key/OAuth) · Rate Limiting · Webhooks · Admin Panel       │
│  Billing (Stripe + credits) · Background Tasks (Celery/Taskiq/ARQ/       │
│  Prefect) · Django-style CLI · Observability (Logfire/LangSmith/         │
│  Sentry/Prometheus)                                                      │
└───────┬──────────────┬──────────────┬──────────────┬─────────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
   PostgreSQL       Redis         Vector DB      LLM APIs
   (async)                        (Milvus/       (OpenAI/
                                  Qdrant/        Anthropic/
                                  ChromaDB/      Gemini)
                                  pgvector)
```

---

## 🏗️ Architecture

```mermaid
graph TB
    subgraph Frontend["Frontend (Next.js 15)"]
        UI[React Components]
        WS[WebSocket Client]
        Store[Zustand Stores]
    end

    subgraph Backend["Backend (FastAPI)"]
        API[API Routes]
        Services[Services Layer]
        Repos[Repositories]
        Agent[AI Agent]
    end

    subgraph Infrastructure
        DB[(PostgreSQL)]
        Redis[(Redis)]
        Queue[Celery/Taskiq/ARQ/Prefect]
    end

    subgraph External
        LLM[OpenAI/Anthropic]
        Webhook[Webhook Endpoints]
    end

    UI --> API
    WS <--> Agent
    API --> Services
    Services --> Repos
    Services --> Agent
    Repos --> DB
    Agent --> LLM
    Services --> Redis
    Services --> Queue
    Services --> Webhook
```

### Layered Architecture

The backend follows a clean **Repository + Service** pattern:

```mermaid
graph LR
    A[API Routes] --> B[Services]
    B --> C[Repositories]
    C --> D[(Database)]

    B --> E[External APIs]
    B --> F[AI Agents]
```

| Layer | Responsibility |
|-------|---------------|
| **Routes** | HTTP handling, validation, auth |
| **Services** | Business logic, orchestration |
| **Repositories** | Data access, queries |

See [Architecture Documentation](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/architecture.md) for details.

---

## 🤖 AI Agent

Choose from **5 AI frameworks** and **4 LLM providers** when generating your project:

```bash
# PydanticAI with OpenAI (default)
fastapi-fullstack create my_app --ai-framework pydantic_ai

# LangGraph with Anthropic
fastapi-fullstack create my_app --ai-framework langgraph --llm-provider anthropic

# DeepAgents with OpenAI
fastapi-fullstack create my_app --ai-framework deepagents

# With RAG enabled
fastapi-fullstack create my_app --rag --database postgresql --task-queue celery
```

### Supported Combinations

| Framework | OpenAI | Anthropic | Gemini | OpenRouter |
|-----------|:------:|:---------:|:------:|:----------:|
| **PydanticAI** | ✓ | ✓ | ✓ | ✓ |
| **PydanticDeep** | ✓ | ✓ | ✓ | - |
| **LangChain** | ✓ | ✓ | ✓ | - |
| **LangGraph** | ✓ | ✓ | ✓ | - |
| **DeepAgents** | ✓ | ✓ | ✓ | - |

### PydanticAI Integration

Type-safe agents with full dependency injection:

```python
# app/agents/assistant.py
from pydantic_ai import Agent, RunContext

@dataclass
class Deps:
    user_id: str | None = None
    db: AsyncSession | None = None

agent = Agent[Deps, str](
    model="openai:gpt-4o-mini",
    system_prompt="You are a helpful assistant.",
)

@agent.tool
async def search_database(ctx: RunContext[Deps], query: str) -> list[dict]:
    """Search the database for relevant information."""
    # Access user context and database via ctx.deps
    ...
```

### LangChain Integration

Flexible agents with LangGraph:

```python
# app/agents/langchain_assistant.py
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent

@tool
def search_database(query: str) -> list[dict]:
    """Search the database for relevant information."""
    ...

agent = create_react_agent(
    model=ChatOpenAI(model="gpt-4o-mini"),
    tools=[search_database],
    prompt="You are a helpful assistant.",
)
```

### WebSocket Streaming

Both frameworks use the same WebSocket endpoint with real-time streaming:

```python
@router.websocket("/ws")
async def agent_ws(websocket: WebSocket):
    await websocket.accept()

    # Works with both PydanticAI and LangChain
    async for event in agent.stream(user_input):
        await websocket.send_json({
            "type": "text_delta",
            "content": event.content
        })
```

### Observability

Each framework has its own observability solution:

| Framework | Observability | Dashboard |
|-----------|--------------|-----------|
| **PydanticAI** | [Logfire](https://logfire.pydantic.dev) | Agent runs, tool calls, token usage |
| **LangChain** | [LangSmith](https://smith.langchain.com) | Traces, feedback, datasets |

See [AI Agent Documentation](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/ai-agent.md) for more.

---

## 📄 RAG (Retrieval-Augmented Generation)

Enable RAG to give your AI agents access to a knowledge base built from your documents.

### Vector Store Backends

| Backend | Type | Docker Required | Best For |
|---------|------|:---:|---------|
| **Milvus** | Dedicated vector DB | Yes (3 services) | Production, large scale |
| **Qdrant** | Dedicated vector DB | Yes (1 service) | Production, simple setup |
| **ChromaDB** | Embedded / HTTP | No | Development, prototyping |
| **pgvector** | PostgreSQL extension | No (uses existing PG) | Already have PostgreSQL |

### Document Ingestion (CLI)

```bash
# Local files
uv run my_app rag-ingest /path/to/document.pdf --collection docs
uv run my_app rag-ingest /path/to/folder/ --recursive

# Google Drive (service account)
uv run my_app rag-sync-gdrive --collection docs --folder-id <drive_folder_id>

# S3/MinIO
uv run my_app rag-sync-s3 --collection docs --prefix reports/ --bucket my-bucket
```

### Embedding Providers

| Provider | Model | Dimensions | Multimodal |
|----------|-------|:---:|:---:|
| **OpenAI** | text-embedding-3-small | 1536 | - |
| **Voyage** | voyage-3 | 1024 | - |
| **Gemini** | gemini-embedding-exp-03-07 | 3072 | Text + Images |
| **SentenceTransformers** | all-MiniLM-L6-v2 | 384 | - |

### Features

- **Document parsing** - PDF (PyMuPDF with tables, headers/footers, OCR), DOCX, TXT, MD + 130+ formats via LlamaParse
- **Image description** - Extract images from documents, describe via LLM vision API (opt-in)
- **Chunking** - RecursiveCharacterTextSplitter with configurable size/overlap
- **Reranking** - Cohere API or local CrossEncoder for improved search quality
- **Agent integration** - All 5 AI frameworks get a `search_knowledge_base` tool automatically

---

## 📊 Observability

### Logfire (for PydanticAI)

[Logfire](https://logfire.pydantic.dev) provides complete observability for your application - from AI agents to database queries. Built by the Pydantic team, it offers first-class support for the entire Python ecosystem.

```mermaid
graph LR
    subgraph Your App
        API[FastAPI]
        Agent[PydanticAI]
        DB[(Database)]
        Cache[(Redis)]
        Queue[Celery/Taskiq]
        HTTP[HTTPX]
    end

    subgraph Logfire
        Traces[Traces]
        Metrics[Metrics]
        Logs[Logs]
    end

    API --> Traces
    Agent --> Traces
    DB --> Traces
    Cache --> Traces
    Queue --> Traces
    HTTP --> Traces
```

| Component | What You See |
|-----------|-------------|
| **PydanticAI** | Agent runs, tool calls, LLM requests, token usage, streaming events |
| **FastAPI** | Request/response traces, latency, status codes, route performance |
| **PostgreSQL** | Query execution time, slow queries, connection pool stats |
| **Redis** | Cache hits/misses, command latency, key patterns |
| **Celery/Taskiq** | Task execution, queue depth, worker performance |
| **HTTPX** | External API calls, response times, error rates |

### LangSmith (for LangChain)

[LangSmith](https://smith.langchain.com) provides observability specifically designed for LangChain applications:

| Feature | Description |
|---------|-------------|
| **Traces** | Full execution traces for agent runs and chains |
| **Feedback** | Collect user feedback on agent responses |
| **Datasets** | Build evaluation datasets from production data |
| **Monitoring** | Track latency, errors, and token usage |

LangSmith is automatically configured when you choose LangChain:

```bash
# .env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-api-key
LANGCHAIN_PROJECT=my_project
```

### Configuration

Enable Logfire and select which components to instrument:

```bash
fastapi-fullstack new
# ✓ Enable Logfire observability
#   ✓ Instrument FastAPI
#   ✓ Instrument Database
#   ✓ Instrument Redis
#   ✓ Instrument Celery
#   ✓ Instrument HTTPX
```

### Usage

```python
# Automatic instrumentation in app/main.py
import logfire

logfire.configure()
logfire.instrument_fastapi(app)
logfire.instrument_asyncpg()
logfire.instrument_redis()
logfire.instrument_httpx()
```

```python
# Manual spans for custom logic
with logfire.span("process_order", order_id=order.id):
    await validate_order(order)
    await charge_payment(order)
    await send_confirmation(order)
```

For more details, see [Logfire Documentation](https://logfire.pydantic.dev/docs/integrations/).

---

## 🛠️ Django-style CLI

Each generated project includes a powerful CLI inspired by Django's management commands:

### Built-in Commands

```bash
# Server
my_app server run --reload
my_app server routes

# Database (Alembic wrapper)
my_app db init
my_app db migrate -m "Add users"
my_app db upgrade

# Users
my_app user create --email admin@example.com --superuser
my_app user list
```

### Custom Commands

Create your own commands with auto-discovery:

```python
# app/commands/seed.py
from app.commands import command, success, error
import click

@command("seed", help="Seed database with test data")
@click.option("--count", "-c", default=10, type=int)
@click.option("--dry-run", is_flag=True)
def seed_database(count: int, dry_run: bool):
    """Seed the database with sample data."""
    if dry_run:
        info(f"[DRY RUN] Would create {count} records")
        return

    # Your logic here
    success(f"Created {count} records!")
```

Commands are **automatically discovered** from `app/commands/` - just create a file and use the `@command` decorator.

```bash
my_app cmd seed --count 100
my_app cmd seed --dry-run
```

---

## 📁 Generated Project Structure

```
my_project/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app with lifespan
│   │   ├── api/
│   │   │   ├── routes/v1/       # Versioned API endpoints
│   │   │   ├── deps.py          # Dependency injection
│   │   │   └── router.py        # Route aggregation
│   │   ├── core/                # Config, security, middleware
│   │   ├── db/models/           # SQLAlchemy 2.0 models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── repositories/        # Data access layer
│   │   ├── services/            # Business logic
│   │   ├── agents/              # AI agents with centralized prompts
│   │   ├── rag/                 # RAG module (vector store, embeddings, ingestion)
│   │   ├── commands/            # Django-style CLI commands
│   │   └── worker/              # Background tasks
│   ├── cli/                     # Project CLI
│   ├── tests/                   # pytest test suite
│   └── alembic/                 # Database migrations
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router
│   │   ├── components/          # React components
│   │   ├── hooks/               # useChat, useWebSocket, etc.
│   │   └── stores/              # Zustand state management
│   └── e2e/                     # Playwright tests
├── docker-compose.yml
├── Makefile
└── README.md
```

Generated projects include version metadata in `pyproject.toml` for tracking:

```toml
[tool.fastapi-fullstack]
generator_version = "0.1.5"
generated_at = "2024-12-21T10:30:00+00:00"
```

---

## ⚙️ Configuration Options

### Core Options

| Option | Values | Description |
|--------|--------|-------------|
| **Database** | `postgresql`, `none` | Async PostgreSQL (SQLAlchemy 2.0 + Alembic) |
| **ORM** | `sqlalchemy`, `sqlmodel` | SQLModel for simplified syntax |
| **Auth** | `jwt`, `api_key`, `both`, `none` | JWT includes user management |
| **OAuth** | `none`, `google` | Social login |
| **AI Framework** | `pydantic_ai`, `pydantic_deep`, `langchain`, `langgraph`, `deepagents` | Choose your AI agent framework |
| **LLM Provider** | `openai`, `anthropic`, `google`, `openrouter` | OpenRouter only with PydanticAI |
| **RAG** | `--rag` | Enable RAG with vector database |
| **Vector Store** | `milvus`, `qdrant`, `chromadb`, `pgvector` | pgvector uses existing PostgreSQL |
| **Background Tasks** | `none`, `celery`, `taskiq`, `arq`, `prefect` | Distributed queues / orchestration |
| **Frontend** | `none`, `nextjs` | Next.js 15 + React 19 |

### Presets

| Preset | Description |
|--------|-------------|
| `--preset production` | Full production setup with Redis, Sentry, Kubernetes, Prometheus |
| `--preset ai-agent` | AI agent with WebSocket streaming and conversation persistence |
| `--minimal` | Minimal project with no extras |

### Integrations

Select what you need:

```bash
fastapi-fullstack new
# ✓ Redis (caching/sessions)
# ✓ Rate limiting (slowapi)
# ✓ Pagination (fastapi-pagination)
# ✓ Admin Panel (SQLAdmin)
# ✓ AI Agent (PydanticAI or LangChain)
# ✓ Webhooks
# ✓ Sentry
# ✓ Logfire / LangSmith
# ✓ Prometheus
# ... and more
```

---

## 🔄 Comparison

### vs. Manual Setup

Setting up a production AI agent stack manually means wiring together 10+ tools yourself:

```bash
# Without this template, you'd need to manually:
# 1. Set up FastAPI project structure
# 2. Configure SQLAlchemy + Alembic migrations
# 3. Implement JWT auth with refresh tokens
# 4. Build WebSocket streaming for AI responses
# 5. Integrate PydanticAI/LangChain with tool calling
# 6. Set up RAG pipeline (parsing, chunking, embedding, vector store)
# 7. Configure Celery + Redis for background tasks
# 8. Build Next.js frontend with auth and chat UI
# 9. Write Docker Compose for all services
# 10. Add observability, rate limiting, admin panel...

# With this template:
pip install fastapi-fullstack
fastapi-fullstack
# Done. All of the above, configured and working.
```

### vs. Alternatives

| Feature | **This Template** | [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | [create-t3-app](https://github.com/t3-oss/create-t3-app) |
|---------|:-:|:-:|:-:|
| **AI Agents** (5 frameworks) | ✅ | ❌ | ❌ |
| **RAG Pipeline** (4 vector stores) | ✅ | ❌ | ❌ |
| **WebSocket Streaming** | ✅ | ❌ | ❌ |
| **Conversation Persistence** | ✅ | ❌ | ❌ |
| **LLM Observability** (Logfire/LangSmith) | ✅ | ❌ | ❌ |
| **FastAPI Backend** | ✅ | ✅ | ❌ |
| **Next.js Frontend** | ✅ (v15) | ❌ | ✅ |
| **JWT + OAuth Authentication** | ✅ | ✅ | ✅ (NextAuth) |
| **Background Tasks** (Celery/Taskiq/ARQ/Prefect) | ✅ | ✅ (Celery) | ❌ |
| **Billing & Credits** (Stripe + usage metering) | ✅ | ❌ | ❌ |
| **Admin Panel** | ✅ (SQLAdmin) | ❌ | ❌ |
| **Async PostgreSQL** (SQLAlchemy 2.0 + pgvector) | ✅ | ✅ | Prisma |
| **Docker + K8s** | ✅ | ✅ | ❌ |
| **Interactive CLI Wizard** | ✅ | ❌ | ✅ |
| **Django-style Commands** | ✅ | ❌ | ❌ |
| **Document Sources** (GDrive, S3, API) | ✅ | ❌ | ❌ |
| **AI-Agent Friendly** (CLAUDE.md) | ✅ | ❌ | ❌ |

---

## ❓ FAQ

<details>
<summary><b>How is this different from full-stack-fastapi-template?</b></summary>

[full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) by @tiangolo is a great starting point for FastAPI projects, but it focuses on traditional web apps. This template is purpose-built for **AI/LLM applications** — it adds AI agents (5 frameworks), RAG with 4 vector stores, WebSocket streaming, conversation persistence, LLM observability, and a Next.js chat UI out of the box.

</details>

<details>
<summary><b>Can I use this without AI/LLM features?</b></summary>

Yes. The AI agent and RAG modules are optional. You can use this as a pure FastAPI + Next.js template with auth, admin panel, background tasks, and all other infrastructure — just skip the AI framework selection during setup.

</details>

<details>
<summary><b>What Python and Node.js versions are required?</b></summary>

Python 3.11+ and Node.js 18+ (for the Next.js frontend). We recommend using [uv](https://docs.astral.sh/uv/) for Python and [bun](https://bun.sh) for the frontend.

</details>

<details>
<summary><b>Can I add integrations after project generation?</b></summary>

The generated project is plain code — no lock-in or runtime dependency on the generator. You can add, remove, or modify any integration manually. The template just gives you a well-structured starting point.

</details>

<details>
<summary><b>Can I use a different LLM provider than the one I selected?</b></summary>

Yes. The LLM provider is configured via environment variables (`AI_MODEL`, `OPENAI_API_KEY`, etc.). You can switch providers by changing the `.env` file and the model name — no code changes needed for PydanticAI (which supports all providers natively).

</details>

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/architecture.md) | Repository + Service pattern, layered design |
| [Frontend](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/frontend.md) | Next.js setup, auth, state management |
| [AI Agent](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/ai-agent.md) | PydanticAI, tools, WebSocket streaming |
| [Observability](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/observability.md) | Logfire integration, tracing, metrics |
| [Deployment](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/deployment.md) | Docker, Kubernetes, production setup |
| [Development](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/development.md) | Local setup, testing, debugging |
| [Changelog](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/CHANGELOG.md) | Version history and release notes |

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=vstorm-co/full-stack-fastapi-nextjs-llm-template&type=date&legend=top-left)](https://www.star-history.com/#vstorm-co/full-stack-fastapi-nextjs-llm-template&type=date&legend=top-left)

---

## 🙏 Inspiration

This project is inspired by:

- [full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) by @tiangolo
- [fastapi-template](https://github.com/s3rius/fastapi-template) by @s3rius
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) by @zhanymkanov
- Django's management commands system

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/CONTRIBUTING.md) for details.

<a href="https://github.com/vstorm-co/full-stack-ai-agent-template/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=vstorm-co/full-stack-ai-agent-template" alt="Contributors" />
</a>

---

## 📄 License

MIT License - see [LICENSE](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/LICENSE) for details.

---

<div align="center">

### Need help implementing this in your company?

<p>We're <a href="https://vstorm.co"><b>Vstorm</b></a> — an Applied Agentic AI Engineering Consultancy<br>with 30+ production AI agent implementations.</p>

<a href="https://vstorm.co/contact-us/">
  <img src="https://img.shields.io/badge/Talk%20to%20us%20%E2%86%92-0066FF?style=for-the-badge&logoColor=white" alt="Talk to us">
</a>

<br><br>

Made with ❤️ by <a href="https://vstorm.co"><b>Vstorm</b></a>

</div>
