"""Slack Events API webhook endpoint."""

import asyncio
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response

from app.api.deps import ChannelBotSvc
from app.core.config import settings
from app.services.channels import get_adapter
from app.worker.background.channel import process_channel_event

logger = logging.getLogger(__name__)

router = APIRouter()

_background_tasks: set[asyncio.Task[None]] = set()


@router.post("/{bot_id}/events", status_code=200)
async def slack_events(
    bot_id: UUID,
    request: Request,
    bot_service: ChannelBotSvc,
) -> Any:
    """Receive Slack Events API callbacks.

    Handles URL verification (challenge/response) and event dispatch.
    Returns HTTP 200 immediately to avoid Slack's 3s timeout, then
    processes the event asynchronously.
    """
    raw_body = (await request.body()).decode("utf-8")
    payload: dict[str, Any] = await request.json()

    adapter = get_adapter("slack")
    headers = dict(request.headers)

    if not settings.SLACK_SIGNING_SECRET:
        raise HTTPException(status_code=500, detail="SLACK_SIGNING_SECRET not configured")
    if not adapter.verify_webhook_signature(headers, settings.SLACK_SIGNING_SECRET, body=raw_body):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")

    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge", "")}
    bot = await bot_service.find_active(bot_id)
    if bot is None:
        return Response(status_code=200)

    event = payload.get("event", {})
    if not event:
        return Response(status_code=200)

    incoming = adapter.parse_incoming(payload, str(bot_id))
    if incoming is None:
        return Response(status_code=200)

    task = asyncio.create_task(process_channel_event(incoming))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return Response(status_code=200)
