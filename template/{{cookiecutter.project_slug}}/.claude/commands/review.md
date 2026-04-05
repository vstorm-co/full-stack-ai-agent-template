---
description: Review code changes against project conventions
---

Review all staged and unstaged changes in the current branch.

For each changed file, verify:

**Architecture:**
- Routes only call services, never repositories
- Services raise domain exceptions (NotFoundError, AlreadyExistsError, etc.), not HTTP exceptions
- Repositories use `db.flush()` + `db.refresh()`, never `db.commit()`
- DI uses Annotated aliases from `deps.py` (CurrentUser, *Svc), not raw `Depends()` in signatures

**Schemas & Types:**
- Separate Create/Update/Read/List Pydantic models
- Type hints on all function signatures (params + return)
- Modern syntax: `str | None` not `Optional[str]`
- Route return type is `-> Any`

**Code Quality:**
- No debug code (print, commented-out code, TODO without issue reference)
- No security issues (SQL injection, exposed secrets, missing auth)
- Consistent naming (snake_case functions, PascalCase classes)
- Imports ordered: stdlib → third-party → local

**Validation:**
1. Run `cd backend && uv run ruff check .`
2. Run `cd backend && uv run pytest` (if test files changed)

Provide findings with specific file:line references and suggest fixes.
