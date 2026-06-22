"""Public demo conversation routes (no authentication).

Serves conversations an admin has flagged ``is_demo=True`` so unauthenticated
visitors can browse and replay curated agent runs on the public demo page.
Only demo-flagged conversations are ever exposed here — regular user conversations
are never reachable through these endpoints.

Endpoints:
    GET /demos          — List demo conversations (gallery cards)
    GET /demos/{id}     — Get one demo conversation with messages + tool calls
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import ConversationSvc
from app.schemas.conversation import ConversationReadWithMessages, DemoConversationList

router = APIRouter()


@router.get("", response_model=DemoConversationList)
async def list_demo_conversations(
    service: ConversationSvc,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
) -> Any:
    """List admin-curated demo conversations (public, no auth)."""
    items, total = await service.list_demo_conversations(skip=skip, limit=limit)
    return DemoConversationList(items=items, total=total)


@router.get("/{conversation_id}", response_model=ConversationReadWithMessages)
async def get_demo_conversation(
    conversation_id: UUID,
    service: ConversationSvc,
) -> Any:
    """Get a single demo conversation with all messages (public, no auth)."""
    return await service.get_demo_conversation(conversation_id)
