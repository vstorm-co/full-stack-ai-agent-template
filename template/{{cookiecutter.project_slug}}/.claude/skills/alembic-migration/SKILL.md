---
name: alembic-migration
description: Create, review, and apply database schema changes with Alembic. Use whenever a SQLAlchemy model is added or changed, a column/index/constraint needs to change, or a data backfill is required — anything that alters the PostgreSQL schema.
---

# Alembic Migrations

This project uses **async SQLAlchemy 2.0 + Alembic** on PostgreSQL. Migrations live in `backend/alembic/versions/` and are numbered (`0001_…`, `0002_…`).

## Workflow

1. **Change the model first** in `backend/app/db/models/` (`Mapped[...]` + `mapped_column()`, `__repr__`, relationships with `ondelete="CASCADE"`). Make sure the model is imported in `backend/app/db/models/__init__.py` so autogenerate sees it.

2. **Autogenerate** the migration:
   ```bash
   cd backend && uv run alembic revision --autogenerate -m "add <thing>"
   # or: make db-migrate
   ```

3. **ALWAYS review the generated file.** Autogenerate is a draft, not the truth:
   - Confirm `upgrade()` matches your intent and `downgrade()` actually reverses it.
   - Check the `down_revision` chains onto the current head (`uv run alembic heads`).
   - Watch for dropped columns/tables you didn't intend, server defaults, enum changes, and JSON/array types.
   - Name the revision file with the next sequential prefix to match the existing convention.

4. **Apply and verify:**
   ```bash
   cd backend && uv run alembic upgrade head   # or: make db-upgrade
   uv run alembic current                       # confirm at head
   ```
   Then round-trip once to prove `downgrade()` works: `alembic downgrade -1 && alembic upgrade head`.

## Data migrations / backfills

For backfills, add explicit `op.execute(...)` or a small data-loop in `upgrade()` (see the existing `*_backfill_*.py` migrations for the pattern). Keep schema and data changes in separate, well-named revisions when practical.

## Rules

- Never edit a migration that has already been applied in shared environments — add a new one.
- `make dev` / `make bootstrap` run `alembic upgrade head` automatically; you don't need a separate step in dev.
- Keep models and migrations in sync — a model change without a migration will pass tests (sessions are mocked) but break on real Postgres.
