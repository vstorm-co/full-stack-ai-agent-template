{%- if cookiecutter.enable_admin_panel and cookiecutter.use_sqlalchemy %}
"""SQLAdmin configuration with automatic model discovery."""

import types
from typing import Any, ClassVar

from fastapi import FastAPI
from sqlalchemy import String, create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase
from sqladmin import Admin, ModelView
{%- if cookiecutter.admin_require_auth %}
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy.orm import Session as DBSession
from starlette.requests import Request
{%- endif %}

from app.core.config import settings
{%- if cookiecutter.admin_require_auth %}
from app.core.security import verify_password
{%- endif %}
from app.db.base import Base
from app.db.models.user import User, UserRole
{%- if cookiecutter.enable_session_management %}
from app.db.models.session import Session
{%- endif %}
{%- if cookiecutter.use_ai %}
from app.db.models.conversation import Conversation, Message, ToolCall
{%- endif %}
{%- if cookiecutter.enable_webhooks %}
from app.db.models.webhook import Webhook, WebhookDelivery
{%- endif %}


SENSITIVE_COLUMN_PATTERNS: list[str] = [
    "password",
    "hashed_password",
    "secret",
    "token",
    "api_key",
    "refresh_token",
]

SEARCHABLE_COLUMN_TYPES: tuple[type, ...] = (String,)

AUTO_GENERATED_COLUMNS: list[str] = [
    "created_at",
    "updated_at",
]

MODEL_ICONS: dict[str, str] = {
    "User": "fa-solid fa-user",
    "Session": "fa-solid fa-key",
    "Conversation": "fa-solid fa-comments",
    "Message": "fa-solid fa-message",
    "ToolCall": "fa-solid fa-wrench",
    "Webhook": "fa-solid fa-link",
    "WebhookDelivery": "fa-solid fa-paper-plane",
}


def discover_models(base: type[DeclarativeBase]) -> list[type]:
    """Discover all SQLAlchemy models registered with the given Base.

    Args:
        base: The SQLAlchemy DeclarativeBase class.

    Returns:
        List of model classes that inherit from the Base.
    """
    return [mapper.class_ for mapper in base.registry.mappers]


def get_model_columns(model: type) -> list[str]:
    """Get all column names from a SQLAlchemy model.

    Args:
        model: The SQLAlchemy model class.

    Returns:
        List of column names.
    """
    mapper: Any = inspect(model)
    return [column.key for column in mapper.columns]


def get_searchable_columns(model: type) -> list[str]:
    """Get columns suitable for searching (String type columns).

    Args:
        model: The SQLAlchemy model class.

    Returns:
        List of searchable column names.
    """
    mapper: Any = inspect(model)
    searchable = []
    for column in mapper.columns:
        is_searchable_type = isinstance(column.type, SEARCHABLE_COLUMN_TYPES)
        is_sensitive = any(pattern in column.key.lower() for pattern in SENSITIVE_COLUMN_PATTERNS)
        if is_searchable_type and not is_sensitive:
            searchable.append(column.key)
    return searchable


def get_sortable_columns(model: type) -> list[str]:
    """Get columns suitable for sorting.

    Args:
        model: The SQLAlchemy model class.

    Returns:
        List of sortable column names.
    """
    mapper: Any = inspect(model)
    return [column.key for column in mapper.columns]


def get_form_excluded_columns(model: type) -> list[str]:
    """Get columns that should be excluded from create/edit forms.

    Excludes sensitive columns and auto-generated columns.

    Args:
        model: The SQLAlchemy model class.

    Returns:
        List of column names to exclude from forms.
    """
    excluded = []
    for column_name in get_model_columns(model):
        if any(pattern in column_name.lower() for pattern in SENSITIVE_COLUMN_PATTERNS):
            excluded.append(column_name)
        elif column_name in AUTO_GENERATED_COLUMNS:
            excluded.append(column_name)
    return excluded


def pluralize(name: str) -> str:
    """Simple pluralization for model names.

    Args:
        name: Singular name.

    Returns:
        Pluralized name.
    """
    if name.endswith("y"):
        return name[:-1] + "ies"
    elif name.endswith("s") or name.endswith("x") or name.endswith("ch") or name.endswith("sh"):
        return name + "es"
    return name + "s"


def create_model_admin(
    model: type,
    *,
    name: str | None = None,
    name_plural: str | None = None,
    icon: str | None = None,
    column_list: list[Any] | None = None,
    column_searchable_list: list[Any] | None = None,
    column_sortable_list: list[Any] | None = None,
    form_excluded_columns: list[Any] | None = None,
    can_create: bool = True,
    can_edit: bool = True,
    can_delete: bool = True,
    can_view_details: bool = True,
) -> type[ModelView]:
    """Dynamically create a ModelView class for a SQLAlchemy model.

    Args:
        model: The SQLAlchemy model class.
        name: Display name (defaults to model class name).
        name_plural: Plural display name (defaults to auto-pluralized name).
        icon: Font Awesome icon class.
        column_list: Columns to display in list view.
        column_searchable_list: Columns to enable search on.
        column_sortable_list: Columns to enable sorting on.
        form_excluded_columns: Columns to exclude from forms.
        can_create: Allow creating new records.
        can_edit: Allow editing records.
        can_delete: Allow deleting records.
        can_view_details: Allow viewing record details.

    Returns:
        A dynamically created ModelView subclass.
    """
    model_name = model.__name__

    _name = name or model_name
    _name_plural = name_plural or pluralize(_name)
    _icon = icon or MODEL_ICONS.get(model_name, "fa-solid fa-database")

    _column_list = column_list
    if _column_list is None:
        columns = get_model_columns(model)
        _column_list = [getattr(model, col) for col in columns if hasattr(model, col)]

    _column_searchable_list = column_searchable_list
    if _column_searchable_list is None:
        searchable = get_searchable_columns(model)
        _column_searchable_list = [getattr(model, col) for col in searchable if hasattr(model, col)]

    _column_sortable_list = column_sortable_list
    if _column_sortable_list is None:
        sortable = get_sortable_columns(model)
        _column_sortable_list = [getattr(model, col) for col in sortable if hasattr(model, col)]

    _form_excluded_columns = form_excluded_columns
    if _form_excluded_columns is None:
        excluded = get_form_excluded_columns(model)
        _form_excluded_columns = [getattr(model, col) for col in excluded if hasattr(model, col)]

    def exec_body(ns: dict[str, Any]) -> None:
        ns["name"] = _name
        ns["name_plural"] = _name_plural
        ns["icon"] = _icon
        ns["column_list"] = _column_list
        ns["column_searchable_list"] = _column_searchable_list
        ns["column_sortable_list"] = _column_sortable_list
        ns["form_excluded_columns"] = _form_excluded_columns
        ns["can_create"] = can_create
        ns["can_edit"] = can_edit
        ns["can_delete"] = can_delete
        ns["can_view_details"] = can_view_details
        # Add ClassVar type hints for sqladmin compatibility
        ns["__annotations__"] = {
            "column_list": ClassVar,
            "column_searchable_list": ClassVar,
            "column_sortable_list": ClassVar,
            "form_excluded_columns": ClassVar,
            "can_create": ClassVar,
            "can_edit": ClassVar,
            "can_delete": ClassVar,
            "can_view_details": ClassVar,
        }

    # Create the class using types.new_class to properly pass model kwarg to metaclass
    class_name = f"{model_name}Admin"
    admin_class = types.new_class(
        class_name,
        (ModelView,),
        {"model": model},  # Pass model to metaclass
        exec_body,
    )

    return admin_class


def register_models_auto(
    admin: Admin,
    base: type[DeclarativeBase],
    *,
    exclude_models: list[type] | None = None,
    custom_configs: dict[type, dict[str, Any]] | None = None,
) -> list[type[ModelView]]:
    """Auto-discover and register all models with the admin panel.

    Args:
        admin: The SQLAdmin instance.
        base: The SQLAlchemy DeclarativeBase class.
        exclude_models: Models to exclude from auto-registration.
        custom_configs: Custom configuration overrides per model.

    Returns:
        List of registered ModelView classes.
    """
    exclude_models = exclude_models or []
    custom_configs = custom_configs or {}

    registered_views: list[type[ModelView]] = []
    models = discover_models(base)

    for model in models:
        if model in exclude_models:
            continue

        config = custom_configs.get(model, {})
        admin_class = create_model_admin(model, **config)
        admin.add_view(admin_class)
        registered_views.append(admin_class)

    return registered_views


_sync_engine: Engine | None = None


def get_sync_engine() -> Engine:
    """Get or create the synchronous engine for SQLAdmin."""
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(settings.DATABASE_URL_SYNC, echo=settings.DEBUG)
    return _sync_engine


{%- if cookiecutter.admin_require_auth %}


class AdminAuth(AuthenticationBackend):
    """Admin panel authentication backend.

    Requires superuser credentials to access the admin panel.
    """

    async def login(self, request: Request) -> bool:
        """Validate admin login credentials."""
        form = await request.form()
        email = form.get("username")
        password = form.get("password")

        if not email or not password:
            return False

        assert isinstance(email, str)
        assert isinstance(password, str)

        with DBSession(get_sync_engine()) as session:
            user = session.query(User).filter(User.email == email).first()

            if (
                user
                and user.hashed_password
                and verify_password(password, user.hashed_password)
                and user.has_role(UserRole.ADMIN)
            ):
                request.session["admin_user_id"] = str(user.id)
                request.session["admin_email"] = user.email
                return True

        return False

    async def logout(self, request: Request) -> bool:
        """Clear admin session."""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        """Check if user is authenticated."""
        admin_user_id = request.session.get("admin_user_id")
        if not admin_user_id:
            return False

        with DBSession(get_sync_engine()) as session:
            user = session.query(User).filter(User.id == admin_user_id).first()
            if user and user.has_role(UserRole.ADMIN) and user.is_active:
                return True

        request.session.clear()
        return False
{%- endif %}


CUSTOM_MODEL_CONFIGS: dict[type, dict[str, Any]] = {
    User: {
        "icon": "fa-solid fa-user",
        "form_excluded_columns": [User.hashed_password, User.created_at, User.updated_at],
    },
{%- if cookiecutter.enable_session_management %}
    Session: {
        "icon": "fa-solid fa-key",
        "form_excluded_columns": [Session.refresh_token_hash],
        "can_create": False,  # Sessions are created via login
    },
{%- endif %}
{%- if cookiecutter.use_ai %}
    ToolCall: {
        "icon": "fa-solid fa-wrench",
        "can_create": False,  # Tool calls are created by the agent
    },
{%- endif %}
{%- if cookiecutter.enable_webhooks %}
    Webhook: {
        "icon": "fa-solid fa-link",
        "form_excluded_columns": [Webhook.secret],
    },
    WebhookDelivery: {
        "icon": "fa-solid fa-paper-plane",
        "can_create": False,  # Deliveries are created by webhook dispatch
        "can_edit": False,
    },
{%- endif %}
}


def setup_admin(app: FastAPI) -> Admin:
    """Setup SQLAdmin for the FastAPI app with automatic model discovery.

    Automatically discovers all SQLAlchemy models from the Base registry
    and creates admin views for them with sensible defaults.

    Custom configurations can be provided in CUSTOM_MODEL_CONFIGS to override
    default behavior for specific models.
    """
    sync_engine = get_sync_engine()

    {%- if cookiecutter.admin_require_auth %}
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    admin = Admin(
        app,
        sync_engine,
        title="{{ cookiecutter.project_name }} Admin",
        authentication_backend=authentication_backend,
    )
    {%- else %}
    admin = Admin(
        app,
        sync_engine,
        title="{{ cookiecutter.project_name }} Admin",
    )
    {%- endif %}

    register_models_auto(
        admin,
        Base,
        custom_configs=CUSTOM_MODEL_CONFIGS,
    )

    return admin
{%- else %}
"""Admin panel - not configured."""
{%- endif %}
