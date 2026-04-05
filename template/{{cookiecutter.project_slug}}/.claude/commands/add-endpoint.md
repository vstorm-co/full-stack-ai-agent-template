---
description: Scaffold a new API endpoint with full layering
---

Create a new API endpoint: $ARGUMENTS

Follow the project's layered architecture. Create files in this order:

1. **Schema** (`backend/app/schemas/<entity>.py`):
   - Inherit `BaseSchema` (and `TimestampSchema` for Read)
   - Create `*Create`, `*Update`, `*Read`, `*List` models
   - Use `Field()` with constraints, `EmailStr` where applicable

2. **DB Model** (`backend/app/db/models/<entity>.py`):
   - Inherit `Base, TimestampMixin`
   - Use `Mapped[type]` + `mapped_column()`
   - Add `__repr__`, relationships with `cascade="all, delete-orphan"`

3. **Repository** (`backend/app/repositories/<entity>_repo.py`):
   - Stateless async functions: `get_by_id`, `get_multi`, `create`, `update`, `delete`
   - Use `db.flush()` + `db.refresh()`, keyword-only args after `db`

4. **Service** (`backend/app/services/<entity>.py`):
   - Class with `__init__(self, db: AsyncSession)`
   - Raise `NotFoundError`, `AlreadyExistsError` as appropriate

5. **DI** (`backend/app/api/deps.py`):
   - Add factory function and `Annotated` alias: `EntitySvc = Annotated[EntityService, Depends(get_entity_service)]`

6. **Route** (`backend/app/api/routes/v1/<entity>.py`):
   - CRUD: GET list, GET by id, POST (201), PATCH, DELETE (204)
   - Use DI aliases, `response_model`, `-> Any` return type

7. **Register** router in `backend/app/api/routes/v1/__init__.py`

8. **Migration**: `cd backend && uv run alembic revision --autogenerate -m "Add <entity> table"`

9. **Test** (`backend/tests/`): mirror source structure

10. Lint: `cd backend && uv run ruff check . --fix && uv run ruff format .`
