{%- if cookiecutter.use_jwt %}
"""Admin conversation and user browsing routes.

All endpoints require admin role.

Endpoints:
    GET  /admin/conversations           — List all conversations (paginated, filterable)
    GET  /admin/conversations/{id}      — Get any conversation with messages (read-only)
    GET  /admin/users                   — List all users with conversation counts
    GET  /admin/users/{user_id}/conversations — List conversations for a specific user
"""

from typing import Any

{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from fastapi import APIRouter, Query

from app.api.deps import ConversationSvc, CurrentAdmin
from app.schemas.conversation import ConversationList, ConversationReadWithMessages
from app.schemas.conversation_share import AdminConversationList, AdminConversationRead, AdminUserList

router = APIRouter()


{%- if cookiecutter.use_postgresql %}


@router.get("", response_model=AdminConversationList)
async def admin_list_conversations(
    service: ConversationSvc,
    current_user: CurrentAdmin,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
    search: str | None = Query(default=None, description="Search by title"),
    user_id: UUID | None = Query(default=None, description="Filter by user ID"),
    include_archived: bool = Query(False, description="Include archived conversations"),
) -> Any:
    """List all conversations across all users (admin only)."""
    from sqlalchemy import func, select
    from app.db.models.conversation import Conversation, Message
    from app.db.models.user import User

    db = service.db
    query = select(
        Conversation,
        func.count(Message.id).label("message_count"),
        User.email.label("user_email"),
    ).outerjoin(Message, Message.conversation_id == Conversation.id).outerjoin(
        User, User.id == Conversation.user_id
    ).group_by(Conversation.id, User.email)

    if search:
        query = query.where(Conversation.title.ilike(f"%{search}%"))
    if user_id:
        query = query.where(Conversation.user_id == user_id)
    if not include_archived:
        query = query.where(Conversation.is_archived.is_(False))

    # Count
    count_query = select(func.count()).select_from(Conversation)
    if search:
        count_query = count_query.where(Conversation.title.ilike(f"%{search}%"))
    if user_id:
        count_query = count_query.where(Conversation.user_id == user_id)
    if not include_archived:
        count_query = count_query.where(Conversation.is_archived.is_(False))
    total = await db.scalar(count_query) or 0

    query = query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    items = [
        AdminConversationRead(
            id=conv.id,
            user_id=conv.user_id,
{%- if cookiecutter.use_pydantic_deep %}
            project_id=getattr(conv, "project_id", None),
{%- endif %}
            title=conv.title,
            is_archived=conv.is_archived,
            message_count=msg_count,
            user_email=email,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )
        for conv, msg_count, email in rows
    ]
    return AdminConversationList(items=items, total=total)


@router.get("/users", response_model=AdminUserList)
async def admin_list_users(
    service: ConversationSvc,
    current_user: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = Query(default=None, description="Search by email or name"),
) -> Any:
    """List all users with conversation counts (admin only)."""
    from sqlalchemy import func, select
    from app.db.models.conversation import Conversation
    from app.db.models.user import User
    from app.schemas.conversation_share import AdminUserRead

    db = service.db
    query = select(
        User,
        func.count(Conversation.id).label("conversation_count"),
    ).outerjoin(Conversation, Conversation.user_id == User.id).group_by(User.id)

    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )

    count_query = select(func.count()).select_from(User)
    if search:
        count_query = count_query.where(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )
    total = await db.scalar(count_query) or 0

    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    items = [
        AdminUserRead(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            conversation_count=conv_count,
            created_at=user.created_at,
        )
        for user, conv_count in rows
    ]
    return AdminUserList(items=items, total=total)


@router.get("/{conversation_id}", response_model=ConversationReadWithMessages)
async def admin_get_conversation(
    conversation_id: UUID,
    service: ConversationSvc,
    current_user: CurrentAdmin,
) -> Any:
    """Get any conversation with messages (admin read-only access)."""
    return await service.get_conversation_with_messages(conversation_id)


{%- elif cookiecutter.use_sqlite %}


@router.get("", response_model=AdminConversationList)
def admin_list_conversations(
    service: ConversationSvc,
    current_user: CurrentAdmin,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
    search: str | None = Query(default=None, description="Search by title"),
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    include_archived: bool = Query(False, description="Include archived conversations"),
) -> Any:
    """List all conversations across all users (admin only)."""
    from sqlalchemy import func, select
    from app.db.models.conversation import Conversation, Message
    from app.db.models.user import User

    db = service.db
    query = select(
        Conversation,
        func.count(Message.id).label("message_count"),
        User.email.label("user_email"),
    ).outerjoin(Message, Message.conversation_id == Conversation.id).outerjoin(
        User, User.id == Conversation.user_id
    ).group_by(Conversation.id, User.email)

    if search:
        query = query.where(Conversation.title.ilike(f"%{search}%"))
    if user_id:
        query = query.where(Conversation.user_id == user_id)
    if not include_archived:
        query = query.where(Conversation.is_archived.is_(False))

    count_query = select(func.count()).select_from(Conversation)
    if search:
        count_query = count_query.where(Conversation.title.ilike(f"%{search}%"))
    if user_id:
        count_query = count_query.where(Conversation.user_id == user_id)
    if not include_archived:
        count_query = count_query.where(Conversation.is_archived.is_(False))
    total = db.scalar(count_query) or 0

    query = query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit)
    result = db.execute(query)
    rows = result.all()

    items = [
        AdminConversationRead(
            id=conv.id,
            user_id=conv.user_id,
{%- if cookiecutter.use_pydantic_deep %}
            project_id=getattr(conv, "project_id", None),
{%- endif %}
            title=conv.title,
            is_archived=conv.is_archived,
            message_count=msg_count,
            user_email=email,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )
        for conv, msg_count, email in rows
    ]
    return AdminConversationList(items=items, total=total)


@router.get("/users", response_model=AdminUserList)
def admin_list_users(
    service: ConversationSvc,
    current_user: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = Query(default=None, description="Search by email or name"),
) -> Any:
    """List all users with conversation counts (admin only)."""
    from sqlalchemy import func, select
    from app.db.models.conversation import Conversation
    from app.db.models.user import User
    from app.schemas.conversation_share import AdminUserRead

    db = service.db
    query = select(
        User,
        func.count(Conversation.id).label("conversation_count"),
    ).outerjoin(Conversation, Conversation.user_id == User.id).group_by(User.id)

    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )

    count_query = select(func.count()).select_from(User)
    if search:
        count_query = count_query.where(
            User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%")
        )
    total = db.scalar(count_query) or 0

    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = db.execute(query)
    rows = result.all()

    items = [
        AdminUserRead(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            conversation_count=conv_count,
            created_at=user.created_at,
        )
        for user, conv_count in rows
    ]
    return AdminUserList(items=items, total=total)


@router.get("/{conversation_id}", response_model=ConversationReadWithMessages)
def admin_get_conversation(
    conversation_id: str,
    service: ConversationSvc,
    current_user: CurrentAdmin,
) -> Any:
    """Get any conversation with messages (admin read-only access)."""
    return service.get_conversation_with_messages(conversation_id)


{%- elif cookiecutter.use_mongodb %}


@router.get("", response_model=AdminConversationList)
async def admin_list_conversations(
    service: ConversationSvc,
    current_user: CurrentAdmin,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
    search: str | None = Query(default=None, description="Search by title"),
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    include_archived: bool = Query(False, description="Include archived conversations"),
) -> Any:
    """List all conversations across all users (admin only)."""
    from app.db.models.conversation import Conversation, Message
    from app.db.models.user import User

    query_filter: dict = {}
    if search:
        import re
        query_filter["title"] = {"$regex": re.escape(search), "$options": "i"}
    if user_id:
        query_filter["user_id"] = user_id
    if not include_archived:
        query_filter["is_archived"] = False

    total = await Conversation.find(query_filter).count()
    conversations = (
        await Conversation.find(query_filter)
        .sort("-updated_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    items = []
    for conv in conversations:
        msg_count = await Message.find(Message.conversation_id == str(conv.id)).count()
        user_email = None
        if conv.user_id:
            user = await User.get(conv.user_id)
            user_email = user.email if user else None
        items.append(
            AdminConversationRead(
                id=str(conv.id),
                user_id=conv.user_id,
{%- if cookiecutter.use_pydantic_deep %}
                project_id=getattr(conv, "project_id", None),
{%- endif %}
                title=conv.title,
                is_archived=conv.is_archived,
                message_count=msg_count,
                user_email=user_email,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
        )
    return AdminConversationList(items=items, total=total)


@router.get("/users", response_model=AdminUserList)
async def admin_list_users(
    current_user: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = Query(default=None, description="Search by email or name"),
) -> Any:
    """List all users with conversation counts (admin only)."""
    from app.db.models.conversation import Conversation
    from app.db.models.user import User
    from app.schemas.conversation_share import AdminUserRead

    query_filter: dict = {}
    if search:
        import re
        escaped = re.escape(search)
        query_filter["$or"] = [
            {"email": {"$regex": escaped, "$options": "i"}},
            {"full_name": {"$regex": escaped, "$options": "i"}},
        ]

    total = await User.find(query_filter).count()
    users = (
        await User.find(query_filter)
        .sort("-created_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    items = []
    for user in users:
        conv_count = await Conversation.find(Conversation.user_id == str(user.id)).count()
        items.append(
            AdminUserRead(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                conversation_count=conv_count,
                created_at=user.created_at,
            )
        )
    return AdminUserList(items=items, total=total)


@router.get("/{conversation_id}", response_model=ConversationReadWithMessages)
async def admin_get_conversation(
    conversation_id: str,
    service: ConversationSvc,
    current_user: CurrentAdmin,
) -> Any:
    """Get any conversation with messages (admin read-only access)."""
    return await service.get_conversation_with_messages(conversation_id)


{%- endif %}
{%- else %}
"""Admin conversation routes — requires JWT authentication (use_jwt)."""
{%- endif %}
