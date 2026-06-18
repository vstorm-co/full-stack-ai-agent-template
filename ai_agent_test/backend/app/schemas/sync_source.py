"""Sync source configuration schemas."""

from typing import Any

from pydantic import BaseModel


class ConnectorConfigField(BaseModel):
    """Describes a single configuration field for a connector."""

    type: str
    required: bool = False
    label: str = ""
    help: str | None = None
    default: Any = None
    secret: bool = False


class ConnectorInfo(BaseModel):
    """Metadata about an available connector type."""

    type: str
    name: str
    config_schema: dict[str, ConnectorConfigField]
    enabled: bool


class SyncSourceCreate(BaseModel):
    """Schema for creating a new sync source."""

    name: str
    connector_type: str
    collection_name: str
    config: dict[str, object]
    sync_mode: str = "new_only"
    schedule_minutes: int | None = None


class SyncSourceUpdate(BaseModel):
    """Schema for updating an existing sync source."""

    name: str | None = None
    config: dict[str, object] | None = None
    sync_mode: str | None = None
    schedule_minutes: int | None = None
    is_active: bool | None = None
    collection_name: str | None = None


class SyncSourceRead(BaseModel):
    """Schema for reading a sync source."""

    id: str
    name: str
    connector_type: str
    collection_name: str
    config: dict[str, object]
    sync_mode: str
    schedule_minutes: int | None
    is_active: bool
    last_sync_at: str | None
    last_sync_status: str | None
    last_error: str | None
    created_at: str | None


class SyncSourceList(BaseModel):
    """Paginated list of sync sources."""

    items: list[SyncSourceRead]
    total: int


class ConnectorList(BaseModel):
    """List of available connectors."""

    items: list[ConnectorInfo]
