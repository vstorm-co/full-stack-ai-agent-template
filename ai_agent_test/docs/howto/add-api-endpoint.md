# How to: Add a New API Endpoint

This example adds a "Notification" endpoint following the repository + service
pattern. Routes **never** contain direct database calls — all data access goes
through a service, which delegates to a repository.

## Step-by-Step

### 1. Create the schema (`app/schemas/`)

```python
# app/schemas/notification.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    title: str = Field(max_length=255)
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

### 2. Create the database model (`app/db/models/`)

```python
# app/db/models/notification.py
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

Don't forget to import it in `app/db/models/__init__.py`.

### 3. Create the repository (`app/repositories/`)

```python
# app/repositories/notification.py
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

### 4. Create the service (`app/services/`)

```python
# app/services/notification.py
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

### 5. Register dependency (`app/api/deps.py`)

```python
from app.services.notification import NotificationService


def get_notification_service(db: DBSession) -> NotificationService:
    """Create NotificationService instance with database session."""
    return NotificationService(db)


NotificationSvc = Annotated[NotificationService, Depends(get_notification_service)]
```

### 6. Create the route (`app/api/routes/v1/`)

```python
# app/api/routes/v1/notifications.py
from fastapi import APIRouter, status

from app.api.deps import NotificationSvc
from app.schemas.notification import NotificationCreate, NotificationResponse
from app.api.deps import CurrentUser

router = APIRouter()


@router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    data: NotificationCreate,
    service: NotificationSvc,
    current_user: CurrentUser,
):
    return await service.create(data)


@router.get("/", response_model=list[NotificationResponse])
async def list_unread(
    service: NotificationSvc,
    current_user: CurrentUser,
):
    return await service.list_unread()
```

### 7. Register the route

In `app/api/routes/v1/__init__.py`:

```python
from app.api.routes.v1 import notifications

v1_router.include_router(
    notifications.router, prefix="/notifications", tags=["notifications"]
)
```

### 8. Create and apply migration

```bash
make db-migrate    # Enter message: "Add notifications table"
make db-upgrade
```

### 9. Test it

Visit `http://localhost:8000/docs` and try the new endpoint.
