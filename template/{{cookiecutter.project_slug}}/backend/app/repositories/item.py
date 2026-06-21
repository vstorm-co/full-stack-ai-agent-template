{%- if cookiecutter.include_example_crud %}
"""Item repository — example resource scaffold.

Pure data-access functions. Always `db.flush()` + `db.refresh()`, never
`db.commit()` — the session auto-commits in `get_db_session`.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.item import Item




async def get_by_id(db: AsyncSession, item_id: UUID) -> Item | None:
    result = await db.execute(select(Item).where(Item.id == item_id))
    return result.scalar_one_or_none()


async def list_for_owner(
    db: AsyncSession,
    *,
    owner_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Item], int]:
    base = select(Item).where(Item.owner_id == owner_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await db.execute(
            base.order_by(Item.created_at.desc()).offset(skip).limit(limit)
        )
    ).scalars().all()
    return list(rows), int(total)


async def create(
    db: AsyncSession,
    *,
    owner_id: UUID,
    name: str,
    description: str | None = None,
    is_published: bool = False,
) -> Item:
    item = Item(
        owner_id=owner_id,
        name=name,
        description=description,
        is_published=is_published,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def update(
    db: AsyncSession,
    *,
    db_item: Item,
    update_data: dict[str, Any],
) -> Item:
    for field, value in update_data.items():
        setattr(db_item, field, value)
    await db.flush()
    await db.refresh(db_item)
    return db_item


async def delete(db: AsyncSession, item_id: UUID) -> Item | None:
    item = await get_by_id(db, item_id)
    if item:
        await db.delete(item)
        await db.flush()
    return item
{%- endif %}
