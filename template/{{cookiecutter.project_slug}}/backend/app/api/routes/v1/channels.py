{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
"""Channel bot management routes (admin only)."""

from typing import Any

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import ChannelBotSvc, CurrentAdmin
from app.schemas.channel_bot import (
    ChannelBotCreate,
    ChannelBotList,
    ChannelBotRead,
    ChannelBotUpdate,
    ChannelSessionList,
)

router = APIRouter()


@router.get("/bots", response_model=ChannelBotList)
async def list_bots(
    service: ChannelBotSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
) -> Any:
    """List all registered channel bots."""
    items, total = await service.list_all(skip=skip, limit=limit)
    return ChannelBotList(items=items, total=total)


@router.post("/bots", response_model=ChannelBotRead, status_code=status.HTTP_201_CREATED)
async def create_bot(
    data: ChannelBotCreate,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Create a new channel bot. The bot token is encrypted before storage."""
    return await service.create(data)


@router.get("/bots/{bot_id}", response_model=ChannelBotRead)
async def get_bot(
    bot_id: UUID,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Get a channel bot by ID."""
    return await service.get(bot_id)


@router.patch("/bots/{bot_id}", response_model=ChannelBotRead)
async def update_bot(
    bot_id: UUID,
    data: ChannelBotUpdate,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Update a channel bot."""
    return await service.update(bot_id, data)


@router.delete("/bots/{bot_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_bot(
    bot_id: UUID,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> None:
    """Delete a channel bot and stop any active polling."""
    await service.delete(bot_id)


@router.post("/bots/{bot_id}/activate", response_model=ChannelBotRead)
async def activate_bot(
    bot_id: UUID,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Activate a channel bot."""
    return await service.activate(bot_id)


@router.post("/bots/{bot_id}/deactivate", response_model=ChannelBotRead)
async def deactivate_bot(
    bot_id: UUID,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Deactivate a channel bot."""
    return await service.deactivate(bot_id)


@router.post("/bots/{bot_id}/webhook/register", response_model=None)
async def register_webhook(
    bot_id: UUID,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Register a webhook URL with the bot's platform."""
    return await service.register_webhook(bot_id)


@router.post("/bots/{bot_id}/webhook/delete", response_model=None)
async def delete_webhook(
    bot_id: UUID,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Remove the webhook from the bot's platform (switches to polling mode)."""
    return await service.delete_webhook(bot_id)


@router.get("/bots/{bot_id}/sessions", response_model=ChannelSessionList)
async def list_sessions(
    bot_id: UUID,
    service: ChannelBotSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List channel sessions for this bot."""
    items, total = await service.list_sessions(bot_id, skip=skip, limit=limit)
    return ChannelSessionList(items=items, total=total)


{%- endif %}
