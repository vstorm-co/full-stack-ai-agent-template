# CLAUDE.md

## Project Overview

**{{ cookiecutter.project_name }}** - FastAPI application generated with [Full-Stack AI Agent Template](https://github.com/vstorm-co/full-stack-ai-agent-template).

**Stack:** FastAPI + Pydantic v2
{%- if True %}, PostgreSQL (async via asyncpg){%- endif %}
{%- if False %}, MongoDB (async via Motor){%- endif %}
{%- if False %}, SQLite (sync){%- endif %}
, JWT + API Key auth
{%- if cookiecutter.enable_redis %}, Redis{%- endif %}
{%- if cookiecutter.use_pydantic_ai %}, PydanticAI{%- endif %}
{%- if cookiecutter.use_langchain %}, LangChain{%- endif %}
{%- if cookiecutter.use_langgraph %}, LangGraph{%- endif %}{%- if cookiecutter.use_deepagents %}, DeepAgents{%- endif %}
{%- if cookiecutter.enable_rag %}, RAG ({{ cookiecutter.vector_store }}){%- endif %}
{%- if cookiecutter.use_celery %}, Celery{%- endif %}
{%- if cookiecutter.use_taskiq %}, Taskiq{%- endif %}
{%- if cookiecutter.use_frontend %}, Next.js 15 (i18n){%- endif %}

## Commands

```bash
# Backend
cd backend
uv run uvicorn app.main:app --reload --port {{ cookiecutter.backend_port }}
uv run pytest
uv run pytest tests/test_file.py::test_name -v
uv run ruff check . --fix && uv run ruff format .
uv run ty check

# Database migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "Description"
{%- if cookiecutter.use_frontend %}

# Frontend
cd frontend
bun dev
bun test
bun run lint
{%- endif %}
{%- if cookiecutter.enable_docker %}

# Docker
docker compose up -d
{%- endif %}
{%- if cookiecutter.enable_rag %}

# RAG
uv run {{ cookiecutter.project_slug }} rag-collections
uv run {{ cookiecutter.project_slug }} rag-ingest /path/to/file.pdf --collection docs
uv run {{ cookiecutter.project_slug }} rag-search "query" --collection docs
{%- if cookiecutter.enable_google_drive_ingestion %}
uv run {{ cookiecutter.project_slug }} rag-sync-gdrive --collection docs
{%- endif %}
{%- if cookiecutter.enable_s3_ingestion %}
uv run {{ cookiecutter.project_slug }} rag-sync-s3 --collection docs
{%- endif %}

# Sync Sources
uv run {{ cookiecutter.project_slug }} cmd rag-sources
uv run {{ cookiecutter.project_slug }} cmd rag-source-add
uv run {{ cookiecutter.project_slug }} cmd rag-source-sync
{%- endif %}
```

## Project Structure

```
backend/app/
├── main.py               # FastAPI app with lifespan (startup/shutdown)
├── api/
│   ├── deps.py           # Annotated DI aliases (DBSession, CurrentUser, *Svc)
│   ├── exception_handlers.py
│   └── routes/v1/        # HTTP endpoints — call services, never repos
├── core/
│   ├── config.py         # pydantic-settings Settings class
│   ├── security.py       # JWT (PyJWT), bcrypt password hashing, API key verification
│   ├── exceptions.py     # Domain exceptions (AppException → NotFoundError, etc.)
│   └── middleware.py      # RequestID, SecurityHeaders, CORS
├── db/
│   ├── base.py           # DeclarativeBase, TimestampMixin, naming convention
│   ├── session.py        # Engine, async_session_maker, get_db_session (auto-commit)
│   └── models/           # SQLAlchemy models (Mapped[] type hints)
├── schemas/              # Pydantic v2 models: *Create, *Update, *Read, *List
├── repositories/         # Data access functions — db.flush(), never commit
├── services/             # Business logic — flat *.py for thin domains, subpackage for thick
│   ├── user.py           #   thin: just a class with db + repo calls
{%- if cookiecutter.enable_billing %}
│   ├── billing/          #   thick: facade + sub-services + Stripe client + handlers
{%- endif %}
{%- if cookiecutter.enable_rag %}
│   ├── rag/              #   thick: ingestion + vectorstore + embeddings + connectors
{%- endif %}
{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
│   ├── channels/         #   thick: Slack/Telegram adapters + router
{%- endif %}
{%- if cookiecutter.enable_email %}
│   └── email/            #   thick: providers + templates
{%- endif %}
├── agents/               # AI agent wrappers + tools
├── worker/               # Background tasks (Celery/Taskiq/ARQ + in-process)
└── commands/             # CLI commands (auto-discovered)
```

## Architecture: Routes → Services → Repositories

**Routes** (`api/routes/v1/`) — HTTP layer only: validate input via Pydantic, call service, return response. Never import repositories.

**Services** (`services/`) — Business logic: class with `__init__(self, db)`, orchestrate repos, raise domain exceptions (`NotFoundError`, `AlreadyExistsError`, etc.).

**Repositories** (`repositories/`) — Pure data access functions. Always use `db.flush()` + `db.refresh()`, NEVER `db.commit()`. Session auto-commits via `get_db_session`.

## Dependency Injection Pattern

All DI uses `Annotated` type aliases defined in `api/deps.py`:

```python
# deps.py
DBSession = Annotated[AsyncSession, Depends(get_db_session)]
UserSvc = Annotated[UserService, Depends(get_user_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]

# Route usage — no raw Depends() in function signatures
@router.get("/{id}", response_model=ConversationRead)
async def get_conversation(
    id: UUID, service: ConversationSvc, user: CurrentUser
) -> Any:
    return await service.get(id, user_id=user.id)
```

## Schema Conventions (Pydantic v2)

- Base: `BaseSchema` with `ConfigDict(from_attributes=True, str_strip_whitespace=True)`
- Separate models per operation: `*Create`, `*Update`, `*Read`
- List responses: `*List` with `items: list[*Read]` and `total: int`
- Update schemas: all fields `Optional` (`str | None = None`)
- Use `Field(max_length=255)`, `Field(min_length=8)`, `EmailStr`
- `@field_validator` for complex deserialization (e.g., JSON string → dict)
- IDs are `UUID` type

## Exception Handling

Domain exceptions in `core/exceptions.py` — all extend `AppException`:

| Exception | HTTP | Code |
|-----------|------|------|
| `NotFoundError` | 404 | `NOT_FOUND` |
| `AlreadyExistsError` | 409 | `ALREADY_EXISTS` |
| `ValidationError` | 422 | `VALIDATION_ERROR` |
| `AuthenticationError` | 401 | `AUTHENTICATION_ERROR` |
| `AuthorizationError` | 403 | `AUTHORIZATION_ERROR` |
| `BadRequestError` | 400 | `BAD_REQUEST` |
| `ExternalServiceError` | 503 | `EXTERNAL_SERVICE_ERROR` |

Always pass `message` and `details` dict: `raise NotFoundError(message="User not found", details={"user_id": id})`

## Response Format

```python
# Single item — use response_model
@router.get("/{id}", response_model=ConversationRead)

# List — return *List schema
@router.get("", response_model=ConversationList)

# Create — 201
@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)

# Delete — 204, no body
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)

# All route return types are -> Any (avoids double Pydantic validation)
```

## Key Conventions

- Return type `-> Any` on route handlers (response_model handles serialization)
- Use `Query(default, ge=0, le=100, description="...")` for query params
- Keyword-only args in repo functions: `create(db, *, email: str, name: str)`
- `__repr__` on all DB models
- `datetime.now(UTC)` not `datetime.utcnow()`
- `secrets.compare_digest()` for API key comparison
- `TypedDict` for lifespan state
- Imports: stdlib → third-party → local, with `TYPE_CHECKING` block for circular refs
