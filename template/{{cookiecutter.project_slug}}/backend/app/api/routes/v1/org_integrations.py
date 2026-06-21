{%- if cookiecutter.enable_rag and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Org-level sync source (integration) management.

Accessible to org owners and admins — no app-admin required.
These endpoints manage sync sources at the organisation level:
an integration without a ``collection_name`` is a "template" that can
later be cloned into one or more knowledge bases.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import (
    DBSession,
    RequireAdminPlus,
    SyncSourceSvc,
)
from app.repositories import sync_log as sync_log_repo
from app.schemas.rag import RAGSyncLogList, RAGSyncLogItem, RAGSyncResponse
from app.schemas.sync_source import (
    ConnectorList,
    SyncSourceCreate,
    SyncSourceList,
    SyncSourceRead,
)

router = APIRouter()


@router.get("", response_model=SyncSourceList)
async def list_org_integrations(
    sync_source_svc: SyncSourceSvc,
    active_org: RequireAdminPlus,
) -> Any:
    """List all sync source integrations for the active organisation.

    Returns both unassigned (org-level) and KB-assigned sources so the
    admin gets a full picture of what's configured.
    """
    return await sync_source_svc.list_sources(organization_id=active_org.id)


@router.get("/connectors", response_model=ConnectorList)
async def list_org_connectors(
    sync_source_svc: SyncSourceSvc,
    _: RequireAdminPlus,
) -> Any:
    """List available connector types (Google Drive, S3, …)."""
    return sync_source_svc.list_connectors()


@router.post("", response_model=SyncSourceRead, status_code=status.HTTP_201_CREATED)
async def create_org_integration(
    data: SyncSourceCreate,
    sync_source_svc: SyncSourceSvc,
    active_org: RequireAdminPlus,
) -> Any:
    """Create an org-level integration.

    Omit ``collection_name`` to keep it unassigned — it can be cloned
    into multiple knowledge bases later.  Pass a ``collection_name`` to
    immediately wire it to a specific KB collection.
    """
    return await sync_source_svc.create_source(data, organization_id=active_org.id)


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_org_integration(
    source_id: UUID,
    sync_source_svc: SyncSourceSvc,
    _: RequireAdminPlus,
) -> None:
    """Delete an org integration by ID."""
    await sync_source_svc.delete_source(str(source_id))


@router.post("/{source_id}/trigger", response_model=RAGSyncResponse)
async def trigger_org_integration(
    source_id: UUID,
    sync_source_svc: SyncSourceSvc,
    _: RequireAdminPlus,
) -> Any:
    """Manually trigger a sync run for an org integration."""
    sync_log = await sync_source_svc.trigger_sync(str(source_id))
    return RAGSyncResponse(
        id=str(sync_log.id),
        status="running",
        message=f"Sync triggered for integration '{source_id}'",
    )


@router.get("/{source_id}/logs", response_model=RAGSyncLogList)
async def list_org_integration_logs(
    source_id: UUID,
    db: DBSession,
    _: RequireAdminPlus,
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    """List sync run history for a specific org integration."""
    logs = await sync_log_repo.get_all(db, sync_source_id=source_id, limit=limit)
    items = [
        RAGSyncLogItem(
            id=str(log.id),
            source=log.source,
            collection_name=log.collection_name,
            status=log.status,
            mode=log.mode,
            total_files=log.total_files,
            ingested=log.ingested,
            updated=log.updated,
            skipped=log.skipped,
            failed=log.failed,
            error_message=log.error_message,
            started_at=log.started_at,
            completed_at=log.completed_at,
        )
        for log in logs
    ]
    return RAGSyncLogList(items=items, total=len(items))
{%- else %}
"""Org integrations routes — not configured."""
{%- endif %}
