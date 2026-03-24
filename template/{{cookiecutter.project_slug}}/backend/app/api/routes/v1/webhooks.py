{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}
"""Webhook management routes."""

from fastapi import APIRouter, Query, status
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from app.api.deps import WebhookSvc
{%- if cookiecutter.use_jwt %}
from app.api.deps import CurrentAdmin
{%- endif %}
from app.schemas.webhook import (
    WebhookCreate,
    WebhookDeliveryListResponse,
    WebhookListResponse,
    WebhookRead,
    WebhookSecretResponse,
    WebhookTestResponse,
    WebhookUpdate,
)

router = APIRouter()


{%- if cookiecutter.use_postgresql %}


@router.post("", response_model=WebhookRead, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    data: WebhookCreate,
    webhook_service: WebhookSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentAdmin,
{%- endif %}
):
    """Create a new webhook subscription."""
    webhook = await webhook_service.create_webhook(
        data,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )
    return WebhookRead(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        description=webhook.description,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    webhook_service: WebhookSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentAdmin,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all webhooks."""
    webhooks, total = await webhook_service.list_webhooks(
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
        skip=skip,
        limit=limit,
    )
    return WebhookListResponse(
        items=[
            WebhookRead(
                id=w.id,
                name=w.name,
                url=w.url,
                events=w.events,
                is_active=w.is_active,
                description=w.description,
                created_at=w.created_at,
                updated_at=w.updated_at,
            )
            for w in webhooks
        ],
        total=total,
    )


@router.get("/{webhook_id}", response_model=WebhookRead)
async def get_webhook(
    webhook_id: UUID,
    webhook_service: WebhookSvc,
):
    """Get a webhook by ID."""
    webhook = await webhook_service.get_webhook(webhook_id)
    return WebhookRead(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        description=webhook.description,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


@router.patch("/{webhook_id}", response_model=WebhookRead)
async def update_webhook(
    webhook_id: UUID,
    data: WebhookUpdate,
    webhook_service: WebhookSvc,
):
    """Update a webhook."""
    webhook = await webhook_service.update_webhook(webhook_id, data)
    return WebhookRead(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        description=webhook.description,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_webhook(
    webhook_id: UUID,
    webhook_service: WebhookSvc,
):
    """Delete a webhook."""
    await webhook_service.delete_webhook(webhook_id)


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: UUID,
    webhook_service: WebhookSvc,
):
    """Send a test event to the webhook."""
    result = await webhook_service.test_webhook(webhook_id)
    return WebhookTestResponse(**result)


@router.post("/{webhook_id}/regenerate-secret", response_model=WebhookSecretResponse)
async def regenerate_webhook_secret(
    webhook_id: UUID,
    webhook_service: WebhookSvc,
):
    """Regenerate the webhook secret."""
    new_secret = await webhook_service.regenerate_secret(webhook_id)
    return WebhookSecretResponse(secret=new_secret)


@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListResponse)
async def list_webhook_deliveries(
    webhook_id: UUID,
    webhook_service: WebhookSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Get delivery history for a webhook."""
    from app.schemas.webhook import WebhookDeliveryRead

    deliveries, total = await webhook_service.get_deliveries(webhook_id, skip=skip, limit=limit)
    return WebhookDeliveryListResponse(
        items=[
            WebhookDeliveryRead(
                id=d.id,
                webhook_id=d.webhook_id,
                event_type=d.event_type,
                response_status=d.response_status,
                error_message=d.error_message,
                attempt_count=d.attempt_count,
                success=d.success,
                created_at=d.created_at,
                delivered_at=d.delivered_at,
            )
            for d in deliveries
        ],
        total=total,
    )


{%- elif cookiecutter.use_sqlite %}


@router.post("", response_model=WebhookRead, status_code=status.HTTP_201_CREATED)
def create_webhook(
    data: WebhookCreate,
    webhook_service: WebhookSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentAdmin,
{%- endif %}
):
    """Create a new webhook subscription."""
    webhook = webhook_service.create_webhook(
        data,
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
    )
    return WebhookRead(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        description=webhook.description,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


@router.get("", response_model=WebhookListResponse)
def list_webhooks(
    webhook_service: WebhookSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentAdmin,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all webhooks."""
    webhooks, total = webhook_service.list_webhooks(
{%- if cookiecutter.use_jwt %}
        user_id=current_user.id,
{%- endif %}
        skip=skip,
        limit=limit,
    )
    return WebhookListResponse(
        items=[
            WebhookRead(
                id=w.id,
                name=w.name,
                url=w.url,
                events=w.events,
                is_active=w.is_active,
                description=w.description,
                created_at=w.created_at,
                updated_at=w.updated_at,
            )
            for w in webhooks
        ],
        total=total,
    )


@router.get("/{webhook_id}", response_model=WebhookRead)
def get_webhook(
    webhook_id: str,
    webhook_service: WebhookSvc,
):
    """Get a webhook by ID."""
    webhook = webhook_service.get_webhook(webhook_id)
    return WebhookRead(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        description=webhook.description,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


@router.patch("/{webhook_id}", response_model=WebhookRead)
def update_webhook(
    webhook_id: str,
    data: WebhookUpdate,
    webhook_service: WebhookSvc,
):
    """Update a webhook."""
    webhook = webhook_service.update_webhook(webhook_id, data)
    return WebhookRead(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        description=webhook.description,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_webhook(
    webhook_id: str,
    webhook_service: WebhookSvc,
):
    """Delete a webhook."""
    webhook_service.delete_webhook(webhook_id)


@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListResponse)
def list_webhook_deliveries(
    webhook_id: str,
    webhook_service: WebhookSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Get delivery history for a webhook."""
    from app.schemas.webhook import WebhookDeliveryRead

    deliveries, total = webhook_service.get_deliveries(webhook_id, skip=skip, limit=limit)
    return WebhookDeliveryListResponse(
        items=[
            WebhookDeliveryRead(
                id=d.id,
                webhook_id=d.webhook_id,
                event_type=d.event_type,
                response_status=d.response_status,
                error_message=d.error_message,
                attempt_count=d.attempt_count,
                success=d.success,
                created_at=d.created_at,
                delivered_at=d.delivered_at,
            )
            for d in deliveries
        ],
        total=total,
    )


{%- elif cookiecutter.use_mongodb %}


@router.post("", response_model=WebhookRead, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    data: WebhookCreate,
    webhook_service: WebhookSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentAdmin,
{%- endif %}
):
    """Create a new webhook subscription."""
    webhook = await webhook_service.create_webhook(
        data,
{%- if cookiecutter.use_jwt %}
        user_id=str(current_user.id),
{%- endif %}
    )
    return WebhookRead(
        id=str(webhook.id),
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        description=webhook.description,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at or webhook.created_at,
    )


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    webhook_service: WebhookSvc,
{%- if cookiecutter.use_jwt %}
    current_user: CurrentAdmin,
{%- endif %}
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all webhooks."""
    webhooks, total = await webhook_service.list_webhooks(
{%- if cookiecutter.use_jwt %}
        user_id=str(current_user.id),
{%- endif %}
        skip=skip,
        limit=limit,
    )
    return WebhookListResponse(
        items=[
            WebhookRead(
                id=str(w.id),
                name=w.name,
                url=w.url,
                events=w.events,
                is_active=w.is_active,
                description=w.description,
                created_at=w.created_at,
                updated_at=w.updated_at or w.created_at,
            )
            for w in webhooks
        ],
        total=total,
    )


@router.get("/{webhook_id}", response_model=WebhookRead)
async def get_webhook(
    webhook_id: str,
    webhook_service: WebhookSvc,
):
    """Get a webhook by ID."""
    webhook = await webhook_service.get_webhook(webhook_id)
    return WebhookRead(
        id=str(webhook.id),
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        description=webhook.description,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at or webhook.created_at,
    )


@router.patch("/{webhook_id}", response_model=WebhookRead)
async def update_webhook(
    webhook_id: str,
    data: WebhookUpdate,
    webhook_service: WebhookSvc,
):
    """Update a webhook."""
    webhook = await webhook_service.update_webhook(webhook_id, data)
    return WebhookRead(
        id=str(webhook.id),
        name=webhook.name,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        description=webhook.description,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at or webhook.created_at,
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_webhook(
    webhook_id: str,
    webhook_service: WebhookSvc,
):
    """Delete a webhook."""
    await webhook_service.delete_webhook(webhook_id)


@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListResponse)
async def list_webhook_deliveries(
    webhook_id: str,
    webhook_service: WebhookSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Get delivery history for a webhook."""
    from app.schemas.webhook import WebhookDeliveryRead

    deliveries, total = await webhook_service.get_deliveries(webhook_id, skip=skip, limit=limit)
    return WebhookDeliveryListResponse(
        items=[
            WebhookDeliveryRead(
                id=str(d.id),
                webhook_id=d.webhook_id,
                event_type=d.event_type,
                response_status=d.response_status,
                error_message=d.error_message,
                attempt_count=d.attempt_count,
                success=d.success,
                created_at=d.created_at,
                delivered_at=d.delivered_at,
            )
            for d in deliveries
        ],
        total=total,
    )


{%- endif %}
{%- else %}
"""Webhook routes - not configured."""
{%- endif %}
