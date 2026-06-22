<h1 align="center">Full-Stack AI Agent Template</h1>
<p align="center">
  <em>Production-Ready AI/LLM Applications — In Minutes, Not Weeks</em>
</p>
<p align="center">
  <a href="https://github.com/vstorm-co/full-stack-ai-agent-template/actions/workflows/ci.yml"><img src="https://github.com/vstorm-co/full-stack-ai-agent-template/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/gh/vstorm-co/full-stack-ai-agent-template"><img src="https://img.shields.io/badge/coverage-100%25-brightgreen" alt="Coverage"></a>
  <a href="https://pypi.org/project/fastapi-fullstack/"><img src="https://img.shields.io/pypi/v/fastapi-fullstack.svg" alt="PyPI"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue" alt="Python"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
</p>

---

**Full-Stack AI Agent Template** is a production-ready project generator for AI/LLM applications with 25+ enterprise integrations. Built with FastAPI, Next.js 15, and your choice of AI framework. Install it as the `fastapi-fullstack` CLI.

Generate complete, type-safe applications with authentication, WebSocket streaming, observability, and deployment configs — all in minutes.

## Why this template?

1. **AI-First Design**: Native support for PydanticAI, LangChain, LangGraph, DeepAgents with WebSocket streaming and conversation persistence.

2. **Production Ready**: 100% test coverage, strict typing, Docker/Kubernetes configs, and battle-tested in real applications.

3. **25+ Integrations**: PostgreSQL, Redis, Celery/Prefect, Logfire, Sentry, Prometheus, Stripe, S3, and more — all optional and configurable.

4. **AI-Agent Friendly**: Generated projects include `CLAUDE.md` and `AGENTS.md` files optimized for AI coding assistants.

## Quick Start

```bash
# Install
pip install fastapi-fullstack

# Create project with interactive wizard
fastapi-fullstack new

# Or use presets
fastapi-fullstack create my_app --preset ai-agent
```

## Supported AI Frameworks

| Framework | Streaming | Observability | Providers |
|-----------|:---------:|:-------------:|:---------:|
| **PydanticAI** | WebSocket | Logfire | OpenAI, Anthropic, OpenRouter |
| **LangChain** | WebSocket | LangSmith | OpenAI, Anthropic |
| **LangGraph** | WebSocket | LangSmith | OpenAI, Anthropic |

## Core Features

| Feature | Description |
|---------|-------------|
| **AI Agents** | PydanticAI, LangChain, LangGraph, DeepAgents with tool calling |
| **WebSocket Streaming** | Real-time responses with full event access |
| **Authentication** | JWT + Refresh tokens, API Keys, OAuth2 (Google) |
| **Database** | PostgreSQL (async, SQLAlchemy 2.0 + Alembic) |
| **Background Tasks** | Celery, Taskiq, ARQ, or Prefect |
| **Observability** | Logfire, LangSmith, Sentry, Prometheus |
| **Admin Panel** | SQLAdmin with authentication |
| **Deployment** | Docker, Kubernetes, GitHub Actions, GitLab CI |

## Generated Project Structure

```
my_project/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── api/routes/v1/       # Versioned endpoints
│   │   ├── agents/              # AI agents
│   │   ├── services/            # Business logic
│   │   └── repositories/        # Data access
│   ├── cli/                     # Django-style commands
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router
│   │   ├── components/          # React components
│   │   └── hooks/               # useChat, useWebSocket
│   └── e2e/                     # Playwright tests
├── docker-compose.yml
└── Makefile
```

## Related Projects

Building advanced AI agents? Check out [pydantic-deep](https://github.com/vstorm-co/pydantic-deepagents) - a deep agent framework with planning, filesystem, and subagent capabilities.

## Next Steps

- [Installation](installation.md) - Get started in minutes
- [Quick Start](guides/quick-start.md) - Create your first project
- [Architecture](architecture.md) - Learn about the project structure
- [AI Agents](ai-agent.md) - Configure AI frameworks
