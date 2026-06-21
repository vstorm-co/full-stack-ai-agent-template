---
description: Pydantic schema patterns and SQLAlchemy model conventions
globs: ["backend/app/schemas/**/*.py", "backend/app/db/models/**/*.py", "backend/app/db/base.py"]
---

# Schemas & Models

## Pydantic Schemas (`app/schemas/`)

Base schema with shared config:

```python
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )
```

Separate models per operation:

```python
class UserCreate(BaseSchema):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)

class UserUpdate(BaseSchema):
    email: EmailStr | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None

class UserRead(BaseSchema, TimestampSchema):
    id: UUID
    email: EmailStr
    full_name: str | None = None
    role: UserRole = UserRole.USER
    avatar_url: str | None = None

class UserList(BaseSchema):
    items: list[UserRead]
    total: int
```

Rules:
- `*Create` — required fields for creation, with `Field()` constraints
- `*Update` — all fields optional (`type | None = None`)
- `*Read` — includes `id` and timestamps, inherits `TimestampSchema`
- `*List` — `items` list + `total` count
- Use `@field_validator` for complex deserialization (e.g., JSON string → dict)

## SQLAlchemy Models (`app/db/models/`)

```python
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
```

Rules:
- Always inherit `Base` and `TimestampMixin` (provides `created_at`, `updated_at`)
- Use `Mapped[type]` with `mapped_column()` for all columns
- ForeignKey with `ondelete="CASCADE"` for parent references
- Always define `__repr__`
- Naming convention in `Base.metadata`: `{table}_{col}_key`, `{table}_{col}_fkey`, etc.

## TimestampMixin

```python
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
```
