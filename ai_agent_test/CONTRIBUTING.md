# Contributing to ai_agent_test

## Development setup

```bash
# Backend (uv-based)
cd backend
uv sync                    # install all deps including dev extras
cp .env.example .env       # then fill in required vars (see ENV_VARS.md)
uv run uvicorn app.main:app --reload --port 8000
uv run alembic upgrade head  # apply migrations

# Frontend (bun-based)
cd ../frontend
bun install
bun dev                    # http://localhost:3000

# Or everything in Docker
docker compose up
```

## Code style

- **Python:** ruff (`uv run ruff check . --fix && uv run ruff format .`). Line length 120.
- **Type hints:** modern syntax (`str | None`, `list[X]`, `dict[str, Any]`). Use `Annotated[T, Depends(...)]` for DI in route signatures.
- **TypeScript:** strict mode, no `any` unless typed external API. ESLint + Prettier (run `bun run lint`).
- **Imports:** stdlib → third-party → local, separated by blank lines. Use `TYPE_CHECKING` block to break circular refs.
- **Datetime:** `datetime.now(UTC)` not `datetime.utcnow()`.
- **Comparisons:** `secrets.compare_digest()` for tokens/keys (constant-time).

## Testing

```bash
cd backend
uv run pytest                              # all backend tests
uv run pytest tests/test_file.py::test -v  # single test
uv run pytest -k "name_substring" -v       # by name pattern
uv run pytest --cov=app                    # with coverage
```

```bash
cd frontend
bun test                  # vitest
bunx tsc --noEmit         # type-check without emit
```

## Architecture rules

- **Routes** never import repositories directly. Always go through a service.
- **Services** raise domain exceptions (`NotFoundError`, `AlreadyExistsError`) — never return `None` for "not found".
- **Repositories** use `db.flush()` + `db.refresh()`, NEVER `db.commit()` (session auto-commits in `get_db_session`).
- **Pydantic schemas:** separate `*Create`, `*Update`, `*Read`, `*List` per operation.
- **Migrations:** one Alembic revision per logical change; never edit a merged migration.

See `docs/architecture.md` for the full layered architecture rules.

## Pre-commit

Configured via `.pre-commit-config.yaml`. Install once:

```bash
uv run pre-commit install
```

Will run ruff + (frontend lint if present) on every commit. Bypass with `--no-verify` only when fixing a hook bug.

## Pull-request checklist

- [ ] `uv run ruff check . && uv run ruff format --check .` clean
- [ ] `cd frontend && bunx tsc --noEmit` clean
- [ ] Tests added for new code paths; `uv run pytest` green
- [ ] If schema changed: alembic migration committed (`uv run alembic revision --autogenerate -m "..."`)
- [ ] Updated `ENV_VARS.md` if new env vars added
- [ ] Updated `CHANGELOG.md` (if applicable)
