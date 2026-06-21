{%- if cookiecutter.use_jwt %}
"""User repository."""

from typing import Any
from uuid import UUID

from sqlalchemy import delete as sql_delete, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
{%- if cookiecutter.use_ai %}
from app.db.models.conversation import Conversation
{%- endif %}


async def get_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """Get user by ID."""
    return await db.get(User, user_id)


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


{%- if cookiecutter.enable_oauth %}


async def get_by_oauth(db: AsyncSession, provider: str, oauth_id: str) -> User | None:
    """Get user by OAuth provider and ID."""
    result = await db.execute(
        select(User).where(User.oauth_provider == provider, User.oauth_id == oauth_id)
    )
    return result.scalar_one_or_none()
{%- endif %}
{%- if cookiecutter.use_delegated_auth %}


async def get_by_external_user_id(db: AsyncSession, external_user_id: str) -> User | None:
    """Get user by IdP-minted external ID (the JWT ``sub`` claim)."""
    result = await db.execute(
        select(User).where(User.external_user_id == external_user_id)
    )
    return result.scalar_one_or_none()
{%- endif %}


async def get_multi(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    """Get multiple users with pagination."""
    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())


def list_query() -> Any:
    """Return the SQL Select for listing users (used by paginate)."""
    return select(User)


async def create(
    db: AsyncSession,
    *,
    email: str,
    hashed_password: str | None,
    full_name: str | None = None,
    is_active: bool = True,
    role: str = "user",
    is_app_admin: bool = False,
{%- if cookiecutter.enable_oauth %}
    oauth_provider: str | None = None,
    oauth_id: str | None = None,
{%- endif %}
{%- if cookiecutter.use_delegated_auth %}
    external_user_id: str | None = None,
{%- endif %}
) -> User:
    """Create a new user.

    Note: Password should already be hashed by the service layer.
    """
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        is_active=is_active,
        role=role,
        is_app_admin=is_app_admin,
{%- if cookiecutter.enable_oauth %}
        oauth_provider=oauth_provider,
        oauth_id=oauth_id,
{%- endif %}
{%- if cookiecutter.use_delegated_auth %}
        external_user_id=external_user_id,
{%- endif %}
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update(
    db: AsyncSession,
    *,
    db_user: User,
    update_data: dict[str, Any],
) -> User:
    """Update a user.

    Note: If password needs updating, it should already be hashed.
    """
    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user


async def update_avatar(db: AsyncSession, user_id: UUID, avatar_url: str) -> User:
    """Update a user's avatar URL."""
    user = await db.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")
    user.avatar_url = avatar_url
    await db.flush()
    await db.refresh(user)
    return user


async def delete(db: AsyncSession, user_id: UUID) -> User | None:
    """Delete a user."""
    user = await get_by_id(db, user_id)
    if user:
        await db.delete(user)
        await db.flush()
    return user


async def delete_non_admins(db: AsyncSession) -> int:
    """Bulk-delete users without the admin role. Returns affected row count."""
    result = await db.execute(sql_delete(User).where(User.role != "admin"))
    await db.flush()
    return result.rowcount  # ty: ignore[unresolved-attribute]


async def has_any(db: AsyncSession) -> bool:
    """Return True if at least one user exists."""
    result = await db.execute(select(User).limit(1))
    return result.scalars().first() is not None


async def admin_list_with_counts(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
) -> tuple[list[tuple[User, int]], int]:
    """Admin: list users with their conversation counts.

    Returns list of (user, conversation_count) tuples and total count.
    """
{%- if cookiecutter.use_ai %}
    conv_count_col = func.count(Conversation.id).label("conversation_count")
    query = (
        select(User, conv_count_col)
        .outerjoin(Conversation, Conversation.user_id == User.id)
        .group_by(User.id)
    )
{%- else %}
    conv_count_col = literal(0).label("conversation_count")
    query = select(User, conv_count_col)
{%- endif %}
    count_query = select(func.count()).select_from(User)

    if search:
        condition = User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        query = query.where(condition)
        count_query = count_query.where(condition)

    sort_columns = {
        "email": User.email,
        "full_name": User.full_name,
        "created_at": User.created_at,
        "conversations": conv_count_col,
    }
    sort_col = sort_columns.get(sort_by, User.created_at)
    sort_col = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
    query = query.order_by(sort_col).offset(skip).limit(limit)

    total = await db.scalar(count_query) or 0
    rows = (await db.execute(query)).all()
    return [(user, count) for user, count in rows], total


{%- else %}
"""User repository - not configured."""
{%- endif %}
