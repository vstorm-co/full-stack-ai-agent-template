{%- if cookiecutter.enable_rag %}
"""Sync source configuration schemas."""

from typing import Any

from app.schemas.base import BaseSchema


class ConnectorConfigField(BaseSchema):
    """Describes a single configuration field for a connector."""

    type: str
    required: bool = False
    label: str = ""
    help: str | None = None
    default: Any = None
    secret: bool = False


class ConnectorInfo(BaseSchema):
    """Metadata about an available connector type."""

    type: str
    name: str
    config_schema: dict[str, ConnectorConfigField]
    enabled: bool


class SyncSourceCreate(BaseSchema):
    """Schema for creating a new sync source."""

    name: str
    connector_type: str
    collection_name: str
    config: dict[str, object]
    sync_mode: str = "new_only"
    schedule_minutes: int | None = None


class SyncSourceUpdate(BaseSchema):
    """Schema for updating an existing sync source."""

    name: str | None = None
    config: dict[str, object] | None = None
    sync_mode: str | None = None
    schedule_minutes: int | None = None
    is_active: bool | None = None
    collection_name: str | None = None


class SyncSourceRead(BaseSchema):
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


class SyncSourceList(BaseSchema):
    """Paginated list of sync sources."""

    items: list[SyncSourceRead]
    total: int


class ConnectorList(BaseSchema):
    """List of available connectors."""

    items: list[ConnectorInfo]
{%- endif %}
