"""Telegram webhook receiver endpoint."""

import asyncio
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response

from app.api.deps import ChannelBotSvc
from app.services.channels import get_adapter
from app.worker.background.channel import process_channel_event

logger = logging.getLogger(__name__)

router = APIRouter()

_background_tasks: set[asyncio.Task[None]] = set()


@router.post("/{bot_id}/webhook", status_code=200)
async def telegram_webhook(
    bot_id: UUID,
    request: Request,
    bot_service: ChannelBotSvc,
) -> Response:
    """Receive Telegram webhook updates.

    Immediately returns HTTP 200 to Telegram, then processes the update
    asynchronously in the background so Telegram does not time out.
    """
    adapter = get_adapter("telegram")
    headers: dict[str, str] = dict(request.headers)
    payload: dict[str, Any] = await request.json()

    bot = await bot_service.find_active(bot_id)
    if bot is None:
        return Response(status_code=200)

    if bot.webhook_secret and not adapter.verify_webhook_signature(headers, bot.webhook_secret):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    incoming = adapter.parse_incoming(payload, str(bot_id))
    if incoming is None:
        return Response(status_code=200)

    task = asyncio.create_task(process_channel_event(incoming))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return Response(status_code=200)
