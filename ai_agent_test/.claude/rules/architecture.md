---
description: Layered architecture patterns — Routes, Services, Repositories, DI
globs: ["backend/app/**/*.py"]
---

# Architecture

## Layered Architecture: Routes → Services → Repositories

Routes NEVER import or call repositories directly. Always go through a service.

## Repositories (`app/repositories/`)

Pure data access — stateless functions (not classes):

```python
async def get_by_id(db: AsyncSession, entity_id: UUID) -> Entity | None:
    result = await db.execute(select(Entity).where(Entity.id == entity_id))
    return result.scalar_one_or_none()

async def create(db: AsyncSession, *, field1: str, field2: str) -> Entity:
    entity = Entity(field1=field1, field2=field2)
    db.add(entity)
    await db.flush()
    await db.refresh(entity)
    return entity

async def update(db: AsyncSession, *, db_entity: Entity, update_data: dict[str, Any]) -> Entity:
    for field, value in update_data.items():
        setattr(db_entity, field, value)
    await db.flush()
    await db.refresh(db_entity)
    return db_entity

async def delete(db: AsyncSession, entity_id: UUID) -> Entity | None:
    entity = await get_by_id(db, entity_id)
    if entity:
        await db.delete(entity)
        await db.flush()
    return entity
```

Rules:
- ALWAYS `db.flush()` + `db.refresh()`, NEVER `db.commit()` — session auto-commits in `get_db_session`
- Use keyword-only args after `db`: `create(db, *, email: str, name: str)`
- Return the entity (or None for get/delete), never return IDs or dicts
- Functions are async for PostgreSQL/MongoDB, sync for SQLite

## Services (`app/services/`)

Business logic — class-based with DB session:

```python
class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User:
        user = await user_repo.get_by_id(self.db, user_id)
        if not user:
            raise NotFoundError(message="User not found", details={"user_id": user_id})
        return user

    async def create(self, data: UserCreate) -> User:
        existing = await user_repo.get_by_email(self.db, data.email)
        if existing:
            raise AlreadyExistsError(message="Email already registered", details={"email": data.email})
        hashed_password = get_password_hash(data.password)
        return await user_repo.create(self.db, email=data.email, hashed_password=hashed_password)
```

Rules:
- Raise domain exceptions, NEVER return error codes or None for "not found"
- Services call repo functions, never build raw queries
- One service per domain entity

## Thin vs. thick domains

Services come in two shapes — choose based on whether the domain owns infrastructure (clients, adapters, pipelines, parsers, templates):

**Thin domain → flat module (`app/services/<domain>.py`).** Default. Just a class with `db`, repo calls, and domain exceptions. Examples: `user.py`, `conversation.py`, `invitation.py`.

**Thick domain → subpackage (`app/services/<domain>/`).** When the domain has its own infra. The subpackage contains both the service classes AND the infra (clients, adapters, pipeline modules, domain-specific exceptions). External callers only import from the package root — sub-modules are package-internal.

```
app/services/billing/
├── __init__.py            # re-exports BillingService (the public facade)
├── facade.py              # BillingService — the only thing routes see
├── checkout_service.py    # internal sub-service
├── credit_service.py
├── subscription_service.py
├── webhook_handler.py
├── stripe_client.py       # external API client (infra)
├── pricing.py             # pure data
├── exceptions.py          # domain-specific, inherits from core/exceptions
└── handlers/              # event handler modules (infra)
```

Other thick domains using the same shape: `services/rag/` (ingestion + vectorstore + embeddings + connectors), `services/channels/` (Slack + Telegram adapters + router), `services/email/` (providers + templates).

Rules for thick subpackages:
- Public API: only the top-level facade exported from `__init__.py`. Routes/workers never import sub-modules directly.
- Domain-specific exceptions live in the subpackage and inherit from `core/exceptions.py` base classes.
- Top-level `app/` is reserved for framework concerns (`api/`, `core/`, `db/`, `repositories/`, `schemas/`, `services/`, `worker/`, `agents/`, `commands/`, `clients/`). No new top-level domain packages.

## Dependency Injection (`app/api/deps.py`)

Use `Annotated` type aliases — never raw `Depends()` in route signatures:

```python
DBSession = Annotated[AsyncSession, Depends(get_db_session)]
UserSvc = Annotated[UserService, Depends(get_user_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]
```

Service factories take `DBSession` and return service instances:

```python
def get_user_service(db: DBSession) -> UserService:
    return UserService(db)
```

## Routes (`app/api/routes/v1/`)

HTTP layer only — validate, delegate, return:

```python
@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: UUID, service: UserSvc, user: CurrentUser) -> Any:
    return await service.get_by_id(user_id)
```

Rules:
- Return type is always `-> Any` (response_model handles serialization)
- Use `status_code=status.HTTP_201_CREATED` for POST, `HTTP_204_NO_CONTENT` for DELETE
- DELETE endpoints: `response_model=None`
- Pagination: `skip: int = Query(0, ge=0)`, `limit: int = Query(50, ge=1, le=100)`
