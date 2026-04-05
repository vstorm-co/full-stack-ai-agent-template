---
description: Code style, formatting, naming, imports, and type hints
globs: ["backend/**/*.py", "*.py"]
---

# Code Style

## Formatting

- Use `ruff` for linting and formatting: `ruff check . --fix && ruff format .`
- Line length: 120 characters

## Type Hints

- Type hints on ALL function signatures — parameters and return types
- Use modern syntax: `str | None` not `Optional[str]`, `list[User]` not `List[User]`
- Use `Annotated[Type, Depends(...)]` for DI (defined as aliases in `deps.py`)
- Use `dict[str, Any]` for generic dicts
- Use `Literal["value1", "value2"]` for string enums in schemas
- Use `TYPE_CHECKING` block for circular import resolution:
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from app.db.models.session import Session
  ```

## Naming

| Element | Convention | Example |
|---------|-----------|---------|
| Files | snake_case | `user_repo.py`, `conversation_service.py` |
| Classes | PascalCase | `UserService`, `ConversationRead` |
| Functions/variables | snake_case | `get_by_id`, `user_service` |
| Constants | UPPER_CASE | `DEFAULT_SYSTEM_PROMPT` |
| Private | _leading_underscore | `_create_agent` |
| DB tables | snake_case plural | `users`, `conversations` |
| API URLs | kebab-case | `/api/v1/conversations` |

## Imports — strictly ordered, separated by blank lines

```python
# 1. Standard library
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

# 2. Third-party
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local application
from app.api.deps import CurrentUser, UserSvc
from app.core.exceptions import NotFoundError
from app.schemas.user import UserCreate, UserRead
```

## Other Conventions

- `datetime.now(UTC)` not `datetime.utcnow()`
- `secrets.compare_digest()` for constant-time comparisons
- `__repr__` on all DB models
- Async for PostgreSQL/MongoDB I/O, sync for SQLite
- Keyword-only args in repo functions after `db` parameter
