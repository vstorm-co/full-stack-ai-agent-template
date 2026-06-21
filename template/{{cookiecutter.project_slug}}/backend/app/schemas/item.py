{%- if cookiecutter.include_example_crud %}
"""Item schemas — example resource scaffold."""

from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class ItemBase(BaseSchema):
    """Shared fields between create / update / read."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    is_published: bool = False


class ItemCreate(ItemBase):
    """Payload for ``POST /items``."""


class ItemUpdate(BaseSchema):
    """Payload for ``PATCH /items/{id}`` — all fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    is_published: bool | None = None


class ItemRead(ItemBase, TimestampSchema):
    """Response shape for ``GET /items/{id}`` and inside ``ItemList``."""

    id: UUID
    owner_id: UUID


class ItemList(BaseSchema):
    """Paginated list response."""

    items: list[ItemRead]
    total: int
{%- endif %}
