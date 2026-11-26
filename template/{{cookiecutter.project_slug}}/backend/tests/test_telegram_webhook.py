{%- if cookiecutter.use_telegram %}
"""Telegram webhook requests are authenticated before parsing their body."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.v1.telegram_webhook import telegram_webhook
from app.services.channels.telegram import TelegramAdapter

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def telegram_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = TelegramAdapter()
    monkeypatch.setattr("app.api.routes.v1.telegram_webhook.get_adapter", lambda platform: adapter)


async def test_polling_mode_never_parses_webhook_requests() -> None:
    bot = SimpleNamespace(platform="telegram", webhook_mode=False, webhook_secret=None)
    service = SimpleNamespace(find_active=AsyncMock(return_value=bot))
    request = MagicMock(json=AsyncMock())

    response = await telegram_webhook(uuid4(), request, service)

    assert response.status_code == 200
    request.json.assert_not_awaited()


@pytest.mark.parametrize("secret", [None, "configured-secret"])
async def test_webhook_requires_a_valid_signature(secret: str | None) -> None:
    bot = SimpleNamespace(platform="telegram", webhook_mode=True, webhook_secret=secret)
    service = SimpleNamespace(find_active=AsyncMock(return_value=bot))
    request = MagicMock(headers={}, json=AsyncMock())

    with pytest.raises(HTTPException) as error:
        await telegram_webhook(uuid4(), request, service)

    assert error.value.status_code == 403
    request.json.assert_not_awaited()


async def test_authenticated_webhook_reads_the_body() -> None:
    secret = "configured-secret"
    bot = SimpleNamespace(platform="telegram", webhook_mode=True, webhook_secret=secret)
    service = SimpleNamespace(find_active=AsyncMock(return_value=bot))
    request = MagicMock(headers={"x-telegram-bot-api-secret-token": secret}, json=AsyncMock(return_value={}))

    response = await telegram_webhook(uuid4(), request, service)

    assert response.status_code == 200
    request.json.assert_awaited_once()
{%- endif %}
