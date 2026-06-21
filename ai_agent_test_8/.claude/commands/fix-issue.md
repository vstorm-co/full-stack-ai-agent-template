---
description: Investigate and fix an issue
---

Fix the issue: $ARGUMENTS

1. **Understand** — search the codebase for relevant code, read the files, understand current behavior
2. **Reproduce** — if possible, identify a test case or request that triggers the issue
3. **Root cause** — trace through Routes → Services → Repositories to find where the bug originates
4. **Fix** — implement the fix following project conventions:
   - Domain exceptions in services (not HTTP errors)
   - `db.flush()` in repositories (not `commit`)
   - Type hints on all changed signatures
5. **Test** — run `cd backend && uv run pytest` to verify no regressions
6. **Lint** — run `cd backend && uv run ruff check . --fix && uv run ruff format .`
7. **Summary** — explain what was changed and why
