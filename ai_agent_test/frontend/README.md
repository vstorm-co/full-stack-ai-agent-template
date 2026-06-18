# Full-Stack FastAPI + Next.js Template for AI/LLM Applications

<p align="center">
  <a href="https://github.com/vstorm-co/full-stack-ai-agent-template/stargazers"><img src="https://img.shields.io/github/stars/vstorm-co/full-stack-ai-agent-template?style=flat&logo=github&color=yellow" alt="GitHub Stars"></a>
  <a href="https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/LICENSE"><img src="https://img.shields.io/github/license/vstorm-co/full-stack-ai-agent-template?color=blue" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white" alt="Python"></a>
  <a href="https://pypi.org/project/fastapi-fullstack/"><img src="https://img.shields.io/pypi/v/fastapi-fullstack?color=green&logo=pypi&logoColor=white" alt="PyPI"></a>
  <img src="https://img.shields.io/badge/coverage-100%25-brightgreen" alt="Coverage">
  <img src="https://img.shields.io/badge/integrations-20%2B-brightgreen" alt="20+ Integrations">
</p>

<p align="center">
  <b>Production-ready project generator for AI/LLM applications with 20+ enterprise integrations.</b><br>
  <sub>Built with FastAPI, Next.js 15, PydanticAI/LangChain, and everything you need for professional business applications.</sub>
</p>

<p align="center">
  <a href="#-why-this-template">Why This Template</a> •
  <a href="#-features">Features</a> •
  <a href="#-demo">Demo</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-ai-agent">AI Agent</a> •
  <a href="#-observability-with-logfire">Logfire</a> •
  <a href="#-documentation">Documentation</a>
</p>

## Related Projects

> **Building advanced AI agents?** Check out [pydantic-deep](https://github.com/vstorm-co/pydantic-deepagents) - a deep agent framework built on pydantic-ai with planning, filesystem, and subagent capabilities.

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

---

## ✨ Features

### 🤖 AI/LLM First

- **[PydanticAI](https://ai.pydantic.dev)** or **[LangChain](https://python.langchain.com)** - Choose your preferred AI framework
- **WebSocket Streaming** - Real-time responses with full event access
- **Conversation Persistence** - Save chat history to database
- **Custom Tools** - Easily extend agent capabilities
- **Multi-model Support** - OpenAI, Anthropic, and more
- **Observability** - Logfire for PydanticAI, LangSmith for LangChain

### ⚡ Backend (FastAPI)

- **[FastAPI](https://fastapi.tiangolo.com)** + **[Pydantic v2](https://docs.pydantic.dev)** - High-performance async API
- **Multiple Databases** - PostgreSQL (async), MongoDB (async), SQLite
- **Authentication** - JWT + Refresh tokens, API Keys, OAuth2 (Google)
- **Background Tasks** - Celery, Taskiq, or ARQ
- **Django-style CLI** - Custom management commands with auto-discovery

### 🎨 Frontend (Next.js 15)

- **React 19** + **TypeScript** + **Tailwind CSS v4**
- **AI Chat Interface** - WebSocket streaming, tool call visualization
- **Authentication** - HTTP-only cookies, auto-refresh
- **Dark Mode** + **i18n** (optional)

### 🔌 20+ Enterprise Integrations

| Category            | Integrations                                  |
| ------------------- | --------------------------------------------- |
| **AI Frameworks**   | PydanticAI, LangChain                         |
| **Caching & State** | Redis, fastapi-cache2                         |
| **Security**        | Rate limiting, CORS, CSRF protection          |
| **Observability**   | Logfire, LangSmith, Sentry, Prometheus        |
| **Admin**           | SQLAdmin panel with auth                      |
| **Events**          | Webhooks, WebSockets                          |
| **DevOps**          | Docker, GitHub Actions, GitLab CI, Kubernetes |

---

## 🎬 Demo

<p align="center">
  <img src="https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/app_start.gif" alt="FastAPI Fullstack Generator Demo">
</p>

---

## 🚀 Quick Start

### Installation

```bash
# pip
pip install fastapi-fullstack

# uv (recommended)
uv tool install fastapi-fullstack

# pipx
pipx install fastapi-fullstack
```

### Create Your Project

```bash
# Interactive wizard (recommended)
fastapi-fullstack new

# Quick mode with options
fastapi-fullstack create my_ai_app \
  --database postgresql \
  --auth jwt \
  --frontend nextjs

# Use presets for common setups
fastapi-fullstack create my_ai_app --preset production   # Full production setup
fastapi-fullstack create my_ai_app --preset ai-agent     # AI agent with streaming

# Minimal project (no extras)
fastapi-fullstack create my_ai_app --minimal
```

### Start Development

```bash
cd my_ai_app

# Backend
cd backend
uv sync
# .env is pre-configured for development - just add your API keys
alembic upgrade head

# Create admin user
uv run my_ai_app user create --email admin@example.com --password secret123 --superuser

# Start server
uv run uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
bun install
bun dev
```

> **Note:** The admin user is required to access the SQLAdmin panel at `/admin`. Use the `--superuser` flag to grant full admin privileges.

**Access:**

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Admin Panel: http://localhost:8000/admin
- Frontend: http://localhost:3000

---

## 📸 Screenshots

### Chat Interface

|                                                       Light Mode                                                       |                                                      Dark Mode                                                       |
| :--------------------------------------------------------------------------------------------------------------------: | :------------------------------------------------------------------------------------------------------------------: |
| ![Chat Light](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new_chat_light.png) | ![Chat Dark](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new_chat_dark.png) |

### Authentication

|                                                      Register                                                      |                                                    Login                                                     |
| :----------------------------------------------------------------------------------------------------------------: | :----------------------------------------------------------------------------------------------------------: |
| ![Register](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new_register.png) | ![Login](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/new_login.png) |

### Observability

|                                             Logfire (PydanticAI)                                             |                                              LangSmith (LangChain)                                               |
| :----------------------------------------------------------------------------------------------------------: | :--------------------------------------------------------------------------------------------------------------: |
| ![Logfire](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/logfire.png) | ![LangSmith](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/langsmith.png) |

### Admin, Monitoring & API

|                                               Celery Flower                                                |                                              SQLAdmin Panel                                              |
| :--------------------------------------------------------------------------------------------------------: | :------------------------------------------------------------------------------------------------------: |
| ![Flower](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/flower.png) | ![Admin](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/admin.png) |

|                                              API Documentation                                               |
| :----------------------------------------------------------------------------------------------------------: |
| ![API Docs](https://raw.githubusercontent.com/vstorm-co/full-stack-ai-agent-template/main/assets/docs_2.png) |

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
        DB[(PostgreSQL/MongoDB)]
        Redis[(Redis)]
        Queue[Celery/Taskiq]
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

| Layer            | Responsibility                  |
| ---------------- | ------------------------------- |
| **Routes**       | HTTP handling, validation, auth |
| **Services**     | Business logic, orchestration   |
| **Repositories** | Data access, queries            |

See [Architecture Documentation](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/architecture.md) for details.

---

## 🤖 AI Agent

Choose between **PydanticAI** or **LangChain** when generating your project, with support for multiple LLM providers:

```bash
# PydanticAI with OpenAI (default)
fastapi-fullstack create my_app --ai-agent --ai-framework pydantic_ai

# PydanticAI with Anthropic
fastapi-fullstack create my_app --ai-agent --ai-framework pydantic_ai --llm-provider anthropic

# PydanticAI with OpenRouter
fastapi-fullstack create my_app --ai-agent --ai-framework pydantic_ai --llm-provider openrouter

# LangChain with OpenAI
fastapi-fullstack create my_app --ai-agent --ai-framework langchain

# LangChain with Anthropic
fastapi-fullstack create my_app --ai-agent --ai-framework langchain --llm-provider anthropic
```

### Supported LLM Providers

| Framework      | OpenAI | Anthropic | OpenRouter |
| -------------- | :----: | :-------: | :--------: |
| **PydanticAI** |   ✓    |     ✓     |     ✓      |
| **LangChain**  |   ✓    |     ✓     |     -      |

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
    model="openai:gpt-5.5",
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
    model=ChatOpenAI(model="gpt-5.5"),
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

| Framework      | Observability                            | Dashboard                           |
| -------------- | ---------------------------------------- | ----------------------------------- |
| **PydanticAI** | [Logfire](https://logfire.pydantic.dev)  | Agent runs, tool calls, token usage |
| **LangChain**  | [LangSmith](https://smith.langchain.com) | Traces, feedback, datasets          |

See [AI Agent Documentation](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/ai-agent.md) for more.

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

| Component              | What You See                                                        |
| ---------------------- | ------------------------------------------------------------------- |
| **PydanticAI**         | Agent runs, tool calls, LLM requests, token usage, streaming events |
| **FastAPI**            | Request/response traces, latency, status codes, route performance   |
| **PostgreSQL/MongoDB** | Query execution time, slow queries, connection pool stats           |
| **Redis**              | Cache hits/misses, command latency, key patterns                    |
| **Celery/Taskiq**      | Task execution, queue depth, worker performance                     |
| **HTTPX**              | External API calls, response times, error rates                     |

### LangSmith (for LangChain)

[LangSmith](https://smith.langchain.com) provides observability specifically designed for LangChain applications:

| Feature        | Description                                     |
| -------------- | ----------------------------------------------- |
| **Traces**     | Full execution traces for agent runs and chains |
| **Feedback**   | Collect user feedback on agent responses        |
| **Datasets**   | Build evaluation datasets from production data  |
| **Monitoring** | Track latency, errors, and token usage          |

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
│   │   ├── db/models/           # SQLAlchemy/MongoDB models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── repositories/        # Data access layer
│   │   ├── services/            # Business logic
│   │   ├── agents/              # AI agents with centralized prompts
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

| Option               | Values                                    | Description                     |
| -------------------- | ----------------------------------------- | ------------------------------- |
| **Database**         | `postgresql`, `mongodb`, `sqlite`, `none` | Async by default                |
| **Auth**             | `jwt`, `api_key`, `both`, `none`          | JWT includes user management    |
| **OAuth**            | `none`, `google`                          | Social login                    |
| **AI Framework**     | `pydantic_ai`, `langchain`                | Choose your AI agent framework  |
| **LLM Provider**     | `openai`, `anthropic`, `openrouter`       | OpenRouter only with PydanticAI |
| **Background Tasks** | `none`, `celery`, `taskiq`, `arq`         | Distributed queues              |
| **Frontend**         | `none`, `nextjs`                          | Next.js 15 + React 19           |

### Presets

| Preset                | Description                                                      |
| --------------------- | ---------------------------------------------------------------- |
| `--preset production` | Full production setup with Redis, Sentry, Kubernetes, Prometheus |
| `--preset ai-agent`   | AI agent with WebSocket streaming and conversation persistence   |
| `--minimal`           | Minimal project with no extras                                   |

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

## 📚 Documentation

| Document                                                                                                   | Description                                  |
| ---------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| [Architecture](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/architecture.md)   | Repository + Service pattern, layered design |
| [Frontend](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/frontend.md)           | Next.js setup, auth, state management        |
| [AI Agent](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/ai-agent.md)           | PydanticAI, tools, WebSocket streaming       |
| [Observability](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/observability.md) | Logfire integration, tracing, metrics        |
| [Deployment](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/deployment.md)       | Docker, Kubernetes, production setup         |
| [Development](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/docs/development.md)     | Local setup, testing, debugging              |

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=vstorm-co/full-stack-ai-agent-template&type=date&legend=top-left)](https://www.star-history.com/#vstorm-co/full-stack-ai-agent-template&type=date&legend=top-left)

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

---

## 📄 License

MIT License - see [LICENSE](https://github.com/vstorm-co/full-stack-ai-agent-template/blob/main/LICENSE) for details.

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/vstorm-co">VStorm</a>
</p>
