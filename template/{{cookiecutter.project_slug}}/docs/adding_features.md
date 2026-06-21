# Adding New Features

## Adding a New API Endpoint

This example adds a "Notification" feature end-to-end, following the
repository + service pattern used throughout the codebase. **Routes never
contain direct database calls** — all data access goes through a service,
which delegates to a repository.

1. **Create schema** in `schemas/`
   ```python
   # schemas/notification.py
   from datetime import datetime
   from uuid import UUID

   from pydantic import BaseModel


   class NotificationCreate(BaseModel):
       title: str
       body: str
       channel: str = "email"


   class NotificationResponse(BaseModel):
       id: UUID
       title: str
       body: str
       channel: str
       is_read: bool
       created_at: datetime
   ```

2. **Create model** in `db/models/`
   ```python
   # db/models/notification.py
   from uuid import uuid4

   from sqlalchemy import Boolean, DateTime, String, func
   from sqlalchemy.dialects.postgresql import UUID
   from sqlalchemy.orm import Mapped, mapped_column

   from app.db.base import Base


   class Notification(Base):
       __tablename__ = "notifications"

       id: Mapped[UUID] = mapped_column(
           UUID(as_uuid=True), primary_key=True, default=uuid4
       )
       title: Mapped[str] = mapped_column(String(255))
       body: Mapped[str] = mapped_column(String)
       channel: Mapped[str] = mapped_column(String(50), default="email")
       is_read: Mapped[bool] = mapped_column(Boolean, default=False)
       created_at: Mapped[DateTime] = mapped_column(
           DateTime(timezone=True), server_default=func.now()
       )
   ```

   Don't forget to import it in `db/models/__init__.py`.

3. **Create repository** in `repositories/`
   ```python
   # repositories/notification.py
   from uuid import UUID

   from sqlalchemy import select
   from sqlalchemy.ext.asyncio import AsyncSession

   from app.db.models.notification import Notification


   class NotificationRepository:
       async def create(self, db: AsyncSession, **kwargs) -> Notification:
           notification = Notification(**kwargs)
           db.add(notification)
           await db.flush()
           await db.refresh(notification)
           return notification

       async def get_by_id(self, db: AsyncSession, notification_id: UUID) -> Notification | None:
           return await db.get(Notification, notification_id)

       async def list_unread(self, db: AsyncSession, limit: int = 50) -> list[Notification]:
           result = await db.execute(
               select(Notification)
               .where(Notification.is_read.is_(False))
               .order_by(Notification.created_at.desc())
               .limit(limit)
           )
           return list(result.scalars().all())
   ```

4. **Create service** in `services/`
   ```python
   # services/notification.py
   from uuid import UUID

   from sqlalchemy.ext.asyncio import AsyncSession

   from app.core.exceptions import NotFoundError
   from app.repositories.notification import NotificationRepository
   from app.schemas.notification import NotificationCreate


   class NotificationService:
       def __init__(self, db: AsyncSession):
           self.db = db
           self.repo = NotificationRepository()

       async def create(self, data: NotificationCreate) -> "Notification":
           return await self.repo.create(self.db, **data.model_dump())

       async def get_or_raise(self, notification_id: UUID) -> "Notification":
           notification = await self.repo.get_by_id(self.db, notification_id)
           if not notification:
               raise NotFoundError(
                   message="Notification not found",
                   details={"id": str(notification_id)},
               )
           return notification

       async def list_unread(self) -> list["Notification"]:
           return await self.repo.list_unread(self.db)
   ```

5. **Register dependency** in `api/deps.py`
   ```python
   from app.services.notification import NotificationService


   def get_notification_service(db: DBSession) -> NotificationService:
       """Create NotificationService instance with database session."""
       return NotificationService(db)


   NotificationSvc = Annotated[NotificationService, Depends(get_notification_service)]
   ```

6. **Create route** in `api/routes/v1/`
   ```python
   # api/routes/v1/notifications.py
   from fastapi import APIRouter, status

   from app.api.deps import CurrentUser, NotificationSvc
   from app.schemas.notification import NotificationCreate, NotificationResponse

   router = APIRouter()


   @router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
   async def create_notification(
       data: NotificationCreate,
       current_user: CurrentUser,
       service: NotificationSvc,
   ):
       return await service.create(data)


   @router.get("/", response_model=list[NotificationResponse])
   async def list_unread(
       current_user: CurrentUser,
       service: NotificationSvc,
   ):
       return await service.list_unread()
   ```

7. **Register router** in `api/routes/v1/__init__.py`
   ```python
   from app.api.routes.v1 import notifications

   v1_router.include_router(
       notifications.router, prefix="/notifications", tags=["notifications"]
   )
   ```

## Adding a Custom CLI Command

Commands are auto-discovered from `app/commands/`.

```python
# app/commands/my_command.py
from app.commands import command, success, error
import click

@command("my-command", help="Description of what this does")
@click.option("--name", "-n", required=True, help="Name parameter")
def my_command(name: str):
    # Your logic here
    success(f"Done: {name}")
```

Run with: `uv run {{ cookiecutter.project_slug }} cmd my-command --name test`
{%- if cookiecutter.use_pydantic_ai %}

## Adding an AI Agent Tool (PydanticAI)

```python
# app/agents/assistant.py
@agent.tool
async def my_tool(ctx: RunContext[Deps], param: str) -> dict:
    """Tool description for LLM - be specific about what it does."""
    # Access dependencies via ctx.deps
    result = await some_operation(param)
    return {"result": result}
```
{%- endif %}
{%- if cookiecutter.use_langchain %}

## Adding an AI Agent Tool (LangChain)

```python
# app/agents/langchain_assistant.py
from langchain.tools import tool

@tool
def my_tool(param: str) -> dict:
    """Tool description for LLM - be specific about what it does."""
    result = some_operation(param)
    return {"result": result}
```
{%- endif %}

## Adding a Database Migration

```bash
# Create migration
uv run alembic revision --autogenerate -m "Add notifications table"

# Apply migration
uv run alembic upgrade head

# Or use CLI
uv run {{ cookiecutter.project_slug }} db migrate -m "Add notifications table"
uv run {{ cookiecutter.project_slug }} db upgrade
```
