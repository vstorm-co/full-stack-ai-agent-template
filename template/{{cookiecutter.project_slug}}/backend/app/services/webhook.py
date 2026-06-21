{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}
"""Webhook service (PostgreSQL async)."""

import hashlib
import hmac
import json
import logging
import secrets
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.sanitize import SSRFBlockedError, validate_webhook_url
from app.db.models.webhook import Webhook, WebhookDelivery
from app.repositories import webhook_repo
from app.schemas.webhook import WebhookCreate, WebhookUpdate

logger = logging.getLogger(__name__)


def _validate_url_or_raise_422(url: str) -> str:
    """Validate a webhook URL; convert SSRF/ValueError into ValidationError (422)."""
    try:
        return validate_webhook_url(url)
    except (SSRFBlockedError, ValueError) as exc:
        raise ValidationError(message=str(exc)) from exc


class WebhookService:
    """Service for webhook management and delivery."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_webhook(
        self,
        data: WebhookCreate,
        user_id: UUID | None = None,
    ) -> Webhook:
        """Create a new webhook subscription."""
        _validate_url_or_raise_422(str(data.url))
        secret = secrets.token_urlsafe(32)

        return await webhook_repo.create(
            self.db,
            name=data.name,
            url=str(data.url),
            secret=secret,
            events=data.events,
            description=data.description,
            user_id=user_id,
        )

    async def get_webhook(self, webhook_id: UUID) -> Webhook:
        """Get a webhook by ID."""
        webhook = await webhook_repo.get_by_id(self.db, webhook_id)
        if not webhook:
            raise NotFoundError(message="Webhook not found")
        return webhook

    async def list_webhooks(
        self,
        user_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Webhook], int]:
        """List webhooks, optionally filtered by user."""
        return await webhook_repo.get_list(
            self.db, user_id=user_id, skip=skip, limit=limit
        )

    async def update_webhook(
        self,
        webhook_id: UUID,
        data: WebhookUpdate,
    ) -> Webhook:
        """Update a webhook."""
        if data.url is not None:
            _validate_url_or_raise_422(str(data.url))

        webhook = await self.get_webhook(webhook_id)
        return await webhook_repo.update(self.db, webhook, data)

    async def delete_webhook(self, webhook_id: UUID) -> None:
        """Delete a webhook."""
        webhook = await self.get_webhook(webhook_id)
        await webhook_repo.delete(self.db, webhook)

    async def regenerate_secret(self, webhook_id: UUID) -> str:
        """Regenerate the webhook secret."""
        webhook = await self.get_webhook(webhook_id)
        new_secret = secrets.token_urlsafe(32)
        await webhook_repo.update_secret(self.db, webhook, new_secret)
        return new_secret

    async def test_webhook(self, webhook_id: UUID) -> dict:
        """Send a test event to the webhook."""
        webhook = await self.get_webhook(webhook_id)

        test_payload = {
            "event": "webhook.test",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {"message": "This is a test webhook delivery"},
        }

        result = await self._deliver(webhook, "webhook.test", test_payload)
        return result

    async def dispatch_event(
        self,
        event_type: str,
        data: dict,
    ) -> None:
        """Dispatch an event to all subscribed webhooks."""
        webhooks = await webhook_repo.get_by_event(self.db, event_type)

        payload = {
            "event": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": data,
        }

        for webhook in webhooks:
            try:
                await self._deliver(webhook, event_type, payload)
            except Exception as e:
                logger.error(
                    "Webhook delivery failed: webhook_id=%s event=%s error=%s",
                    webhook.id, event_type, e,
                )

    async def _deliver(
        self,
        webhook: Webhook,
        event_type: str,
        payload: dict,
    ) -> dict:
        """Deliver a payload to a webhook with HMAC signature."""
        # Re-validate URL at delivery time to prevent DNS rebinding attacks
        _validate_url_or_raise_422(webhook.url)

        payload_json = json.dumps(payload, default=str)

        signature = self._create_signature(webhook.secret, payload_json)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": event_type,
        }

        delivery = await webhook_repo.create_delivery(
            self.db,
            webhook_id=webhook.id,
            event_type=event_type,
            payload=payload_json,
        )

        try:
            # SECURITY: follow_redirects defaults to False in httpx.
            # Do NOT enable it — redirects could bypass SSRF validation
            # by redirecting to an internal IP after the URL check passes.
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    webhook.url,
                    content=payload_json,
                    headers=headers,
                )

            delivery.response_status = response.status_code
            delivery.response_body = response.text[:10000]  # Limit size
            delivery.success = 200 <= response.status_code < 300
            delivery.delivered_at = datetime.now(UTC)

            logger.info(
                "Webhook delivered: webhook_id=%s event=%s status=%s",
                webhook.id, event_type, response.status_code,
            )

        except Exception as e:
            delivery.error_message = str(e)
            delivery.success = False

            logger.error(
                "Webhook delivery error: webhook_id=%s event=%s error=%s",
                webhook.id, event_type, e,
            )

        await webhook_repo.save_delivery(self.db, delivery)

        return {
            "success": delivery.success,
            "status_code": delivery.response_status,
            "message": delivery.error_message or "Delivered successfully",
        }

    @staticmethod
    def _create_signature(secret: str, payload: str) -> str:
        """Create HMAC-SHA256 signature for the payload."""
        digest = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={digest}"

    async def get_deliveries(
        self,
        webhook_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[WebhookDelivery], int]:
        """Get delivery history for a webhook."""
        await self.get_webhook(webhook_id)
        return await webhook_repo.get_deliveries(self.db, webhook_id, skip=skip, limit=limit)

    @staticmethod
    def verify_signature(secret: str, payload: str, signature: str) -> bool:
        """Verify a webhook signature."""
        expected = WebhookService._create_signature(secret, payload)
        return hmac.compare_digest(expected, signature)


{%- else %}
"""Webhook service - not configured."""
{%- endif %}
