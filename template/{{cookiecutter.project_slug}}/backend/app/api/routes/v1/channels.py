{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
"""Channel bot management routes (admin only).

Endpoints:
    GET    /channels/bots                           — List all bots
    POST   /channels/bots                           — Create bot
    GET    /channels/bots/{bot_id}                  — Get bot
    PATCH  /channels/bots/{bot_id}                  — Update bot
    DELETE /channels/bots/{bot_id}                  — Delete bot
    POST   /channels/bots/{bot_id}/activate         — Activate bot
    POST   /channels/bots/{bot_id}/deactivate       — Deactivate bot
    POST   /channels/bots/{bot_id}/webhook/register — Register webhook
    POST   /channels/bots/{bot_id}/webhook/delete   — Delete webhook
    GET    /channels/bots/{bot_id}/sessions         — List sessions for bot
"""

from typing import Any

{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

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


{%- if cookiecutter.use_postgresql %}


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


@router.post("/bots/{bot_id}/webhook/register")
async def register_webhook(
    bot_id: UUID,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Register webhook URL with Telegram for this bot."""
    from app.channels import get_adapter
    from app.core.config import settings

    bot = await service.get(bot_id)
    adapter = get_adapter("telegram")
    decrypted_token = service.get_decrypted_token(bot)

    webhook_url = (
        f"{settings.TELEGRAM_WEBHOOK_BASE_URL}/api/v1/channels/telegram/{bot_id}/webhook"
    )
    success = await adapter.register_webhook(
        decrypted_token,
        url=webhook_url,
        secret=bot.webhook_secret,
    )
    return {"success": success, "webhook_url": webhook_url}


@router.post("/bots/{bot_id}/webhook/delete")
async def delete_webhook(
    bot_id: UUID,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Remove the webhook from Telegram (switches bot to polling mode)."""
    from app.channels import get_adapter

    bot = await service.get(bot_id)
    adapter = get_adapter("telegram")
    decrypted_token = service.get_decrypted_token(bot)

    success = await adapter.delete_webhook(decrypted_token)
    return {"success": success}


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


{%- elif cookiecutter.use_sqlite %}


@router.get("/bots", response_model=ChannelBotList)
def list_bots(
    service: ChannelBotSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
) -> Any:
    """List all registered channel bots."""
    items, total = service.list_all(skip=skip, limit=limit)
    return ChannelBotList(items=items, total=total)


@router.post("/bots", response_model=ChannelBotRead, status_code=status.HTTP_201_CREATED)
def create_bot(
    data: ChannelBotCreate,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Create a new channel bot. The bot token is encrypted before storage."""
    return service.create(data)


@router.get("/bots/{bot_id}", response_model=ChannelBotRead)
def get_bot(
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Get a channel bot by ID."""
    return service.get(bot_id)


@router.patch("/bots/{bot_id}", response_model=ChannelBotRead)
def update_bot(
    bot_id: str,
    data: ChannelBotUpdate,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Update a channel bot."""
    return service.update(bot_id, data)


@router.delete("/bots/{bot_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_bot(
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> None:
    """Delete a channel bot."""
    service.delete(bot_id)


@router.post("/bots/{bot_id}/activate", response_model=ChannelBotRead)
def activate_bot(
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Activate a channel bot."""
    return service.activate(bot_id)


@router.post("/bots/{bot_id}/deactivate", response_model=ChannelBotRead)
def deactivate_bot(
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Deactivate a channel bot."""
    return service.deactivate(bot_id)


@router.post("/bots/{bot_id}/webhook/register")
async def register_webhook(
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Register webhook URL with Telegram for this bot."""
    from app.channels import get_adapter
    from app.core.config import settings

    bot = service.get(bot_id)
    adapter = get_adapter("telegram")
    decrypted_token = service.get_decrypted_token(bot)

    webhook_url = (
        f"{settings.TELEGRAM_WEBHOOK_BASE_URL}/api/v1/channels/telegram/{bot_id}/webhook"
    )
    success = await adapter.register_webhook(
        decrypted_token,
        url=webhook_url,
        secret=bot.webhook_secret,
    )
    return {"success": success, "webhook_url": webhook_url}


@router.post("/bots/{bot_id}/webhook/delete")
async def delete_webhook(
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Remove the webhook from Telegram."""
    from app.channels import get_adapter

    bot = service.get(bot_id)
    adapter = get_adapter("telegram")
    decrypted_token = service.get_decrypted_token(bot)

    success = await adapter.delete_webhook(decrypted_token)
    return {"success": success}


@router.get("/bots/{bot_id}/sessions", response_model=ChannelSessionList)
def list_sessions(
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List channel sessions for this bot."""
    items, total = service.list_sessions(bot_id, skip=skip, limit=limit)
    return ChannelSessionList(items=items, total=total)


{%- elif cookiecutter.use_mongodb %}


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
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Get a channel bot by ID."""
    return await service.get(bot_id)


@router.patch("/bots/{bot_id}", response_model=ChannelBotRead)
async def update_bot(
    bot_id: str,
    data: ChannelBotUpdate,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Update a channel bot."""
    return await service.update(bot_id, data)


@router.delete("/bots/{bot_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_bot(
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> None:
    """Delete a channel bot and stop any active polling."""
    await service.delete(bot_id)


@router.post("/bots/{bot_id}/activate", response_model=ChannelBotRead)
async def activate_bot(
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Activate a channel bot."""
    return await service.activate(bot_id)


@router.post("/bots/{bot_id}/deactivate", response_model=ChannelBotRead)
async def deactivate_bot(
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Deactivate a channel bot."""
    return await service.deactivate(bot_id)


@router.post("/bots/{bot_id}/webhook/register")
async def register_webhook(
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Register webhook URL with Telegram for this bot."""
    from app.channels import get_adapter
    from app.core.config import settings

    bot = await service.get(bot_id)
    adapter = get_adapter("telegram")
    decrypted_token = service.get_decrypted_token(bot)

    webhook_url = (
        f"{settings.TELEGRAM_WEBHOOK_BASE_URL}/api/v1/channels/telegram/{bot_id}/webhook"
    )
    success = await adapter.register_webhook(
        decrypted_token,
        url=webhook_url,
        secret=bot.webhook_secret,
    )
    return {"success": success, "webhook_url": webhook_url}


@router.post("/bots/{bot_id}/webhook/delete")
async def delete_webhook(
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
) -> Any:
    """Remove the webhook from Telegram (switches bot to polling mode)."""
    from app.channels import get_adapter

    bot = await service.get(bot_id)
    adapter = get_adapter("telegram")
    decrypted_token = service.get_decrypted_token(bot)

    success = await adapter.delete_webhook(decrypted_token)
    return {"success": success}


@router.get("/bots/{bot_id}/sessions", response_model=ChannelSessionList)
async def list_sessions(
    bot_id: str,
    service: ChannelBotSvc,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    """List channel sessions for this bot."""
    items, total = await service.list_sessions(bot_id, skip=skip, limit=limit)
    return ChannelSessionList(items=items, total=total)


{%- endif %}
{%- endif %}
