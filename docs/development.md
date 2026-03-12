# Development Guide

This guide covers setting up a local development environment for your generated project.

## Prerequisites

- **Python 3.11+** (3.12 recommended)
- **uv** - Fast Python package manager
- **Docker** (optional, for databases)
- **Bun** - JavaScript runtime (for frontend)
- **PostgreSQL** or **MongoDB** (depending on your choice)

---

## Quick Start

### 1. Generate Project

```bash
# Interactive mode
fastapi-fullstack new

# Or quick mode
fastapi-fullstack create my_project --database postgresql --auth jwt
```

### 2. Backend Setup

```bash
cd my_project/backend

# Install dependencies
uv sync

# Copy environment file
cp .env.example .env

# Start PostgreSQL (Docker)
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=my_project \
  -p 5432:5432 \
  postgres:16-alpine

# Run migrations
alembic upgrade head

# Create admin user
uv run python -m cli.commands user create-admin --email admin@example.com

# Start development server
uv run uvicorn app.main:app --reload
```

### 3. Frontend Setup (if enabled)

```bash
cd my_project/frontend

# Install dependencies
bun install

# Start development server
bun dev
```

### 4. Access the application

- **Backend API**: <http://localhost:8000>
- **API Docs**: <http://localhost:8000/docs>
- **Frontend**: <http://localhost:3000> (if enabled)

---

## Using Docker Compose

For a complete development environment:

```bash
cd my_project

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Run migrations
docker compose exec backend alembic upgrade head

# Stop services
docker compose down
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| backend | 8000 | FastAPI application |
| frontend | 3000 | Next.js application |
| db | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache (if enabled) |
| mailcatcher | 1080 | Email testing UI |

---

## Environment Variables

### Backend (.env)

```bash
# Application
ENVIRONMENT=local
DEBUG=true
PROJECT_NAME=my_project

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret
POSTGRES_DB=my_project

# Auth
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080

# Logfire (optional)
LOGFIRE_TOKEN=

# Redis (if enabled)
REDIS_HOST=localhost
REDIS_PORT=6379

# AI Agent (if enabled)
OPENAI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini
```

### Frontend (.env.local)

```bash
# Backend URL (server-side only - not exposed to browser)
BACKEND_URL=http://localhost:8000

# WebSocket URL for real-time features
BACKEND_WS_URL=ws://localhost:8000

# Authentication (set to true when JWT or OAuth is enabled)
NEXT_PUBLIC_AUTH_ENABLED=true

# RAG (Retrieval Augmented Generation)
NEXT_PUBLIC_RAG_ENABLED=true

# Public API URL for OAuth redirects (exposed to browser)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Project CLI

The generated project includes a CLI for common tasks:

```bash
# Show all commands
uv run python -m cli.commands --help

# Server commands
uv run python -m cli.commands server run --reload
uv run python -m cli.commands server routes

# Database commands
uv run python -m cli.commands db init
uv run python -m cli.commands db migrate -m "Add table"
uv run python -m cli.commands db upgrade
uv run python -m cli.commands db downgrade

# User commands
uv run python -m cli.commands user create
uv run python -m cli.commands user create-admin
uv run python -m cli.commands user list

# Custom commands
uv run python -m cli.commands cmd seed --count 100
```

---

## Using Makefile

Common commands are available via Makefile:

```bash
# Install dependencies
make install
make install-dev

# Run development server
make run

# Testing
make test
make test-cov

# Code quality
make lint
make format
make typecheck

# Database
make db-init
make db-migrate
make db-upgrade

# Docker
make docker-build
make docker-up
make docker-down
```

---

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/api/test_items.py -v

# Run specific test
pytest tests/api/test_items.py::test_create_item -v

# Run with verbose output
pytest -v --tb=short

# Run async tests only
pytest -m asyncio
```

### Frontend Tests

```bash
cd frontend

# Unit tests (Vitest)
bun test
bun test:run
bun test:coverage

# E2E tests (Playwright)
bun test:e2e
bun test:e2e:ui
bun test:e2e:headed
```

### Test Configuration

```python
# tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.db.base import Base
from app.api.deps import get_db


# Test database
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:secret@localhost:5432/test_db"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="function")
async def db_session():
    """Create a fresh database session for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session):
    """Create test client with database override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
```

---

## Code Quality

### Ruff (Linting & Formatting)

```bash
# Check for issues
ruff check .

# Fix auto-fixable issues
ruff check . --fix

# Format code
ruff format .

# Check formatting
ruff format . --check
```

### Mypy (Type Checking)

```bash
# Run type checker
mypy app

# With specific options
mypy app --strict --ignore-missing-imports
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files

# Update hooks
pre-commit autoupdate
```

Configuration in `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]
```

---

## Database Management

### PostgreSQL

```bash
# Start PostgreSQL container
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=my_project \
  -p 5432:5432 \
  postgres:16-alpine

# Connect to database
docker exec -it postgres psql -U postgres -d my_project

# Stop container
docker stop postgres
docker rm postgres
```

### Migrations (Alembic)

```bash
# Create migration
alembic revision --autogenerate -m "Add users table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade abc123

# Show current revision
alembic current

# Show history
alembic history
```

### Reset Database

```bash
# Drop and recreate database
docker exec -it postgres psql -U postgres -c "DROP DATABASE my_project;"
docker exec -it postgres psql -U postgres -c "CREATE DATABASE my_project;"

# Re-run migrations
alembic upgrade head
```

---

## Debugging

### FastAPI

```python
# Add breakpoint
breakpoint()

# Or use debugpy for remote debugging
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()
```

### VS Code Launch Configuration

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload"],
      "cwd": "${workspaceFolder}/backend",
      "envFile": "${workspaceFolder}/backend/.env"
    }
  ]
}
```

### Logfire

View traces and logs in the Logfire dashboard:

```bash
# Set token
export LOGFIRE_TOKEN=your-token

# Run with Logfire enabled
uv run uvicorn app.main:app --reload
```

---

## Hot Reloading

### Backend

The development server reloads automatically when files change:

```bash
uvicorn app.main:app --reload
```

### Frontend

Next.js Fast Refresh is enabled by default:

```bash
bun dev
```

---

## IDE Setup

### VS Code Extensions

Recommended extensions:

- **Python** - Microsoft Python extension
- **Pylance** - Type checking and IntelliSense
- **Ruff** - Linting and formatting
- **Python Test Explorer** - Test discovery and running
- **GitLens** - Git integration

### Settings

```json
// .vscode/settings.json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "python.analysis.typeCheckingMode": "basic",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

### PyCharm

1. Open the project in PyCharm
2. Set Python interpreter to the virtual environment
3. Mark `app` as Sources Root
4. Mark `tests` as Test Sources Root
5. Enable pytest as the test runner

---

## Common Issues

### "ModuleNotFoundError: No module named 'app'"

```bash
# Ensure you're in the backend directory
cd backend

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### "Connection refused" to database

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Start if not running
docker start postgres
```

### "Permission denied" on Docker

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or run
newgrp docker
```

### Alembic "Target database is not up to date"

```bash
# Check current revision
alembic current

# Stamp as current (if database was created manually)
alembic stamp head
```
