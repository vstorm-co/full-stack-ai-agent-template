{%- if cookiecutter.enable_admin_panel %}
"""Tests for admin panel with automatic model discovery."""

from typing import ClassVar
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from sqlalchemy import Boolean, Integer, String, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

import app.admin as admin_module

from sqladmin import ModelView

from app.admin import (
    SENSITIVE_COLUMN_PATTERNS,
    AUTO_GENERATED_COLUMNS,
    MODEL_ICONS,
    discover_models,
    get_model_columns,
    get_searchable_columns,
    get_sortable_columns,
    get_form_excluded_columns,
    pluralize,
    create_model_admin,
    register_models_auto,
    get_sync_engine,
    setup_admin,
)
{%- if cookiecutter.admin_require_auth %}
from app.admin import AdminAuth
{%- endif %}


class MockBase(DeclarativeBase):
    """Mock base class for testing."""

    pass


class MockUser(MockBase):
    """Mock user model for testing."""

    __tablename__ = "mock_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[str] = mapped_column(DateTime, nullable=True)


class MockItem(MockBase):
    """Mock item model for testing."""

    __tablename__ = "mock_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=True)


class MockSession(MockBase):
    """Mock session model with sensitive columns."""

    __tablename__ = "mock_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    api_key: Mapped[str] = mapped_column(String(255), nullable=True)
    secret: Mapped[str] = mapped_column(String(255), nullable=True)


class TestConstants:
    """Tests for module constants."""

    def test_sensitive_column_patterns_exist(self):
        """Test sensitive column patterns are defined."""
        assert isinstance(SENSITIVE_COLUMN_PATTERNS, list)
        assert "password" in SENSITIVE_COLUMN_PATTERNS
        assert "hashed_password" in SENSITIVE_COLUMN_PATTERNS
        assert "secret" in SENSITIVE_COLUMN_PATTERNS
        assert "token" in SENSITIVE_COLUMN_PATTERNS
        assert "api_key" in SENSITIVE_COLUMN_PATTERNS

    def test_auto_generated_columns_exist(self):
        """Test auto-generated columns are defined."""
        assert isinstance(AUTO_GENERATED_COLUMNS, list)
        assert "created_at" in AUTO_GENERATED_COLUMNS
        assert "updated_at" in AUTO_GENERATED_COLUMNS

    def test_model_icons_exist(self):
        """Test model icons mapping is defined."""
        assert isinstance(MODEL_ICONS, dict)
        assert "User" in MODEL_ICONS
        assert MODEL_ICONS["User"] == "fa-solid fa-user"


class TestDiscoverModels:
    """Tests for discover_models function."""

    def test_discovers_all_registered_models(self):
        """Test that discover_models finds all models in the registry."""
        models = discover_models(MockBase)
        model_names = [m.__name__ for m in models]

        assert "MockUser" in model_names
        assert "MockItem" in model_names
        assert "MockSession" in model_names

    def test_returns_list(self):
        """Test that discover_models returns a list."""
        models = discover_models(MockBase)
        assert isinstance(models, list)

    def test_returns_model_classes(self):
        """Test that discovered items are model classes."""
        models = discover_models(MockBase)
        for model in models:
            assert hasattr(model, "__tablename__")


class TestGetModelColumns:
    """Tests for get_model_columns function."""

    def test_returns_all_columns(self):
        """Test that all columns are returned."""
        columns = get_model_columns(MockUser)

        assert "id" in columns
        assert "email" in columns
        assert "full_name" in columns
        assert "hashed_password" in columns
        assert "is_active" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_returns_list_of_strings(self):
        """Test that column names are strings."""
        columns = get_model_columns(MockItem)

        assert isinstance(columns, list)
        for col in columns:
            assert isinstance(col, str)


class TestGetSearchableColumns:
    """Tests for get_searchable_columns function."""

    def test_returns_string_columns(self):
        """Test that string columns are included."""
        columns = get_searchable_columns(MockUser)

        assert "email" in columns
        assert "full_name" in columns

    def test_excludes_sensitive_columns(self):
        """Test that sensitive columns are excluded."""
        columns = get_searchable_columns(MockUser)

        assert "hashed_password" not in columns

    def test_excludes_non_string_columns(self):
        """Test that non-string columns are excluded."""
        columns = get_searchable_columns(MockUser)

        assert "id" not in columns
        assert "is_active" not in columns

    def test_excludes_multiple_sensitive_patterns(self):
        """Test that all sensitive patterns are excluded."""
        columns = get_searchable_columns(MockSession)

        assert "refresh_token_hash" not in columns
        assert "api_key" not in columns
        assert "secret" not in columns


class TestGetSortableColumns:
    """Tests for get_sortable_columns function."""

    def test_returns_all_columns(self):
        """Test that all columns are returned as sortable."""
        columns = get_sortable_columns(MockItem)

        assert "id" in columns
        assert "title" in columns
        assert "description" in columns
        assert "price" in columns

    def test_returns_list(self):
        """Test that a list is returned."""
        columns = get_sortable_columns(MockUser)

        assert isinstance(columns, list)


# Tests for get_form_excluded_columns


class TestGetFormExcludedColumns:
    """Tests for get_form_excluded_columns function."""

    def test_excludes_sensitive_columns(self):
        """Test that sensitive columns are excluded from forms."""
        columns = get_form_excluded_columns(MockUser)

        assert "hashed_password" in columns

    def test_excludes_auto_generated_columns(self):
        """Test that auto-generated columns are excluded from forms."""
        columns = get_form_excluded_columns(MockUser)

        assert "created_at" in columns
        assert "updated_at" in columns

    def test_does_not_exclude_regular_columns(self):
        """Test that regular columns are not excluded."""
        columns = get_form_excluded_columns(MockUser)

        assert "email" not in columns
        assert "full_name" not in columns
        assert "is_active" not in columns

    def test_excludes_all_sensitive_patterns(self):
        """Test that all sensitive patterns are matched."""
        columns = get_form_excluded_columns(MockSession)

        assert "refresh_token_hash" in columns
        assert "api_key" in columns
        assert "secret" in columns


# Tests for pluralize


class TestPluralize:
    """Tests for pluralize function."""

    def test_regular_pluralization(self):
        """Test regular word pluralization (add 's')."""
        assert pluralize("User") == "Users"
        assert pluralize("Conversation") == "Conversations"
        assert pluralize("Model") == "Models"

    def test_words_ending_in_y(self):
        """Test words ending in 'y' (change to 'ies')."""
        assert pluralize("Category") == "Categories"
        assert pluralize("Delivery") == "Deliveries"
        assert pluralize("Entry") == "Entries"

    def test_words_ending_in_s(self):
        """Test words ending in 's' (add 'es')."""
        assert pluralize("Address") == "Addresses"
        assert pluralize("Class") == "Classes"

    def test_words_ending_in_x(self):
        """Test words ending in 'x' (add 'es')."""
        assert pluralize("Box") == "Boxes"
        assert pluralize("Tax") == "Taxes"

    def test_words_ending_in_ch(self):
        """Test words ending in 'ch' (add 'es')."""
        assert pluralize("Match") == "Matches"
        assert pluralize("Batch") == "Batches"

    def test_words_ending_in_sh(self):
        """Test words ending in 'sh' (add 'es')."""
        assert pluralize("Dish") == "Dishes"
        assert pluralize("Wish") == "Wishes"


# Tests for create_model_admin


class TestCreateModelAdmin:
    """Tests for create_model_admin function."""

    def test_creates_model_view_class(self):
        """Test that a ModelView subclass is created."""
        admin_class = create_model_admin(MockItem)

        assert admin_class is not None
        assert issubclass(admin_class, ModelView)

    def test_binds_model_via_metaclass(self):
        """Test that the model is properly bound via the metaclass."""
        admin_class = create_model_admin(MockItem)

        # The model should be accessible after metaclass processing
        assert hasattr(admin_class, "model")
        assert admin_class.model == MockItem

    def test_generates_class_name(self):
        """Test that the class name is generated correctly."""
        admin_class = create_model_admin(MockItem)

        assert admin_class.__name__ == "MockItemAdmin"

    def test_sets_display_name(self):
        """Test that the display name is set."""
        admin_class = create_model_admin(MockItem)

        assert admin_class.name == "MockItem"

    def test_sets_plural_name(self):
        """Test that the plural name is set."""
        admin_class = create_model_admin(MockItem)

        assert admin_class.name_plural == "MockItems"

    def test_custom_name_override(self):
        """Test that custom name can be provided."""
        admin_class = create_model_admin(MockItem, name="Product")

        assert admin_class.name == "Product"

    def test_custom_name_plural_override(self):
        """Test that custom plural name can be provided."""
        admin_class = create_model_admin(MockItem, name_plural="Products")

        assert admin_class.name_plural == "Products"

    def test_sets_icon_from_mapping(self):
        """Test that icon is set from MODEL_ICONS mapping."""
        admin_class = create_model_admin(MockUser)

        # MockUser won't be in MODEL_ICONS, so it should get default
        assert admin_class.icon == "fa-solid fa-database"

    def test_custom_icon_override(self):
        """Test that custom icon can be provided."""
        admin_class = create_model_admin(MockItem, icon="fa-solid fa-star")

        assert admin_class.icon == "fa-solid fa-star"

    def test_sets_column_list(self):
        """Test that column_list is populated."""
        admin_class = create_model_admin(MockItem)

        assert admin_class.column_list is not None
        assert len(admin_class.column_list) > 0

    def test_custom_column_list(self):
        """Test that custom column_list can be provided."""
        admin_class = create_model_admin(
            MockItem, column_list=[MockItem.id, MockItem.title]
        )

        assert len(admin_class.column_list) == 2

    def test_sets_searchable_columns(self):
        """Test that searchable columns are set."""
        admin_class = create_model_admin(MockItem)

        assert admin_class.column_searchable_list is not None

    def test_sets_sortable_columns(self):
        """Test that sortable columns are set."""
        admin_class = create_model_admin(MockItem)

        assert admin_class.column_sortable_list is not None

    def test_sets_form_excluded_columns(self):
        """Test that form excluded columns are set."""
        admin_class = create_model_admin(MockUser)

        assert admin_class.form_excluded_columns is not None

    def test_crud_permissions_default_true(self):
        """Test that CRUD permissions default to True."""
        admin_class = create_model_admin(MockItem)

        assert admin_class.can_create is True
        assert admin_class.can_edit is True
        assert admin_class.can_delete is True
        assert admin_class.can_view_details is True

    def test_crud_permissions_can_be_disabled(self):
        """Test that CRUD permissions can be disabled."""
        admin_class = create_model_admin(
            MockItem,
            can_create=False,
            can_edit=False,
            can_delete=False,
            can_view_details=False,
        )

        assert admin_class.can_create is False
        assert admin_class.can_edit is False
        assert admin_class.can_delete is False
        assert admin_class.can_view_details is False


# Tests for register_models_auto


class TestRegisterModelsAuto:
    """Tests for register_models_auto function."""

    def test_registers_all_models(self):
        """Test that all models are registered."""
        mock_admin = MagicMock()

        registered = register_models_auto(mock_admin, MockBase)

        assert len(registered) >= 3  # MockUser, MockItem, MockSession
        assert mock_admin.add_view.call_count >= 3

    def test_excludes_specified_models(self):
        """Test that excluded models are not registered."""
        mock_admin = MagicMock()

        registered = register_models_auto(
            mock_admin, MockBase, exclude_models=[MockSession]
        )

        registered_names = [r.__name__ for r in registered]
        assert "MockSessionAdmin" not in registered_names

    def test_applies_custom_configs(self):
        """Test that custom configs are applied."""
        mock_admin = MagicMock()
        custom_configs = {
            MockItem: {
                "can_create": False,
                "icon": "fa-solid fa-custom",
            }
        }

        registered = register_models_auto(
            mock_admin, MockBase, custom_configs=custom_configs
        )

        # Find the MockItem admin class
        item_admin = next(r for r in registered if r.model == MockItem)
        assert item_admin.can_create is False
        assert item_admin.icon == "fa-solid fa-custom"

    def test_returns_list_of_model_views(self):
        """Test that a list of ModelView classes is returned."""
        mock_admin = MagicMock()

        registered = register_models_auto(mock_admin, MockBase)

        assert isinstance(registered, list)
        for admin_class in registered:
            assert issubclass(admin_class, ModelView)


# Tests for get_sync_engine


class TestGetSyncEngine:
    """Tests for get_sync_engine function."""

    @patch("app.admin.create_engine")
    @patch("app.admin.settings")
    def test_creates_engine_with_settings(self, mock_settings, mock_create_engine):
        """Test that engine is created with correct settings."""
        # Reset the cached engine
        admin_module._sync_engine = None

        mock_settings.DATABASE_URL_SYNC = "postgresql://test"
        mock_settings.DEBUG = False
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engine = get_sync_engine()

        mock_create_engine.assert_called_once_with(
            "postgresql://test", echo=False
        )
        assert engine == mock_engine

        # Reset for other tests
        admin_module._sync_engine = None

    @patch("app.admin.create_engine")
    @patch("app.admin.settings")
    def test_returns_cached_engine(self, mock_settings, mock_create_engine):
        """Test that engine is cached and reused."""
        # Reset the cached engine
        admin_module._sync_engine = None

        mock_settings.DATABASE_URL_SYNC = "postgresql://test"
        mock_settings.DEBUG = False
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engine1 = get_sync_engine()
        engine2 = get_sync_engine()

        # Should only create once
        mock_create_engine.assert_called_once()
        assert engine1 is engine2

        # Reset for other tests
        admin_module._sync_engine = None


# Tests for setup_admin


class TestSetupAdmin:
    """Tests for setup_admin function."""

    @patch("app.admin.register_models_auto")
    @patch("app.admin.get_sync_engine")
    @patch("app.admin.Admin")
    def test_creates_admin_instance(
        self, mock_admin_class, mock_get_engine, mock_register
    ):
        """Test that Admin instance is created."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_admin_instance = MagicMock()
        mock_admin_class.return_value = mock_admin_instance
        mock_app = MagicMock()

        result = setup_admin(mock_app)

        mock_admin_class.assert_called_once()
        assert result == mock_admin_instance

    @patch("app.admin.register_models_auto")
    @patch("app.admin.get_sync_engine")
    @patch("app.admin.Admin")
    def test_calls_register_models_auto(
        self, mock_admin_class, mock_get_engine, mock_register
    ):
        """Test that register_models_auto is called."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_admin_instance = MagicMock()
        mock_admin_class.return_value = mock_admin_instance
        mock_app = MagicMock()

        setup_admin(mock_app)

        mock_register.assert_called_once()

    @patch("app.admin.register_models_auto")
    @patch("app.admin.get_sync_engine")
    @patch("app.admin.Admin")
    def test_uses_correct_engine(
        self, mock_admin_class, mock_get_engine, mock_register
    ):
        """Test that the sync engine is used."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_admin_instance = MagicMock()
        mock_admin_class.return_value = mock_admin_instance
        mock_app = MagicMock()

        setup_admin(mock_app)

        # Check that Admin was called with the engine
        call_args = mock_admin_class.call_args
        assert call_args[0][1] == mock_engine


{%- if cookiecutter.admin_require_auth %}


# Tests for AdminAuth


class TestAdminAuth:
    """Tests for AdminAuth authentication backend."""

    @pytest.fixture
    def auth_backend(self):
        """Create an AdminAuth instance for testing."""
        return AdminAuth(secret_key="test-secret-key")

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = MagicMock()
        request.session = {}
        return request

    @pytest.mark.anyio
    async def test_login_returns_false_for_empty_credentials(
        self, auth_backend, mock_request
    ):
        """Test that login fails with empty credentials."""
        mock_request.form = AsyncMock(return_value={"username": "", "password": ""})

        result = await auth_backend.login(mock_request)

        assert result is False

    @pytest.mark.anyio
    async def test_login_returns_false_for_missing_email(
        self, auth_backend, mock_request
    ):
        """Test that login fails with missing email."""
        mock_request.form = AsyncMock(return_value={"username": None, "password": "pass"})

        result = await auth_backend.login(mock_request)

        assert result is False

    @pytest.mark.anyio
    async def test_login_returns_false_for_missing_password(
        self, auth_backend, mock_request
    ):
        """Test that login fails with missing password."""
        mock_request.form = AsyncMock(return_value={"username": "test@test.com", "password": None})

        result = await auth_backend.login(mock_request)

        assert result is False

    @pytest.mark.anyio
    @patch("app.admin.get_sync_engine")
    @patch("app.admin.verify_password")
    async def test_login_returns_false_for_nonexistent_user(
        self, mock_verify, mock_get_engine, auth_backend, mock_request
    ):
        """Test that login fails for non-existent user."""
        mock_request.form = AsyncMock(
            return_value={"username": "nonexistent@test.com", "password": "password"}
        )

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        with patch("app.admin.DBSession") as mock_session_class:
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            result = await auth_backend.login(mock_request)

        assert result is False

    @pytest.mark.anyio
    @patch("app.admin.get_sync_engine")
    @patch("app.admin.verify_password")
    async def test_login_returns_false_for_wrong_password(
        self, mock_verify, mock_get_engine, auth_backend, mock_request
    ):
        """Test that login fails for wrong password."""
        mock_request.form = AsyncMock(
            return_value={"username": "test@test.com", "password": "wrongpassword"}
        )
        mock_verify.return_value = False

        mock_user = MagicMock()
        mock_user.has_role.return_value = True
        mock_user.hashed_password = "hashed"

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        with patch("app.admin.DBSession") as mock_session_class:
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            result = await auth_backend.login(mock_request)

        assert result is False

    @pytest.mark.anyio
    @patch("app.admin.get_sync_engine")
    @patch("app.admin.verify_password")
    async def test_login_returns_false_for_non_superuser(
        self, mock_verify, mock_get_engine, auth_backend, mock_request
    ):
        """Test that login fails for non-superuser."""
        mock_request.form = AsyncMock(
            return_value={"username": "test@test.com", "password": "password"}
        )
        mock_verify.return_value = True

        mock_user = MagicMock()
        mock_user.has_role.return_value = False
        mock_user.hashed_password = "hashed"

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        with patch("app.admin.DBSession") as mock_session_class:
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            result = await auth_backend.login(mock_request)

        assert result is False

    @pytest.mark.anyio
    @patch("app.admin.get_sync_engine")
    @patch("app.admin.verify_password")
    async def test_login_success_for_valid_superuser(
        self, mock_verify, mock_get_engine, auth_backend, mock_request
    ):
        """Test that login succeeds for valid superuser."""
        mock_request.form = AsyncMock(
            return_value={"username": "admin@test.com", "password": "password"}
        )
        mock_verify.return_value = True

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.email = "admin@test.com"
        mock_user.has_role.return_value = True
        mock_user.hashed_password = "hashed"

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        with patch("app.admin.DBSession") as mock_session_class:
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            result = await auth_backend.login(mock_request)

        assert result is True
        assert mock_request.session["admin_user_id"] == "user-123"
        assert mock_request.session["admin_email"] == "admin@test.com"

    @pytest.mark.anyio
    async def test_logout_clears_session(self, auth_backend, mock_request):
        """Test that logout clears the session."""
        mock_request.session["admin_user_id"] = "user-123"
        mock_request.session["admin_email"] = "test@test.com"

        result = await auth_backend.logout(mock_request)

        assert result is True
        assert len(mock_request.session) == 0

    @pytest.mark.anyio
    async def test_authenticate_returns_false_without_session(
        self, auth_backend, mock_request
    ):
        """Test that authenticate fails without session."""
        mock_request.session = {}

        result = await auth_backend.authenticate(mock_request)

        assert result is False

    @pytest.mark.anyio
    @patch("app.admin.get_sync_engine")
    async def test_authenticate_returns_false_for_invalid_user(
        self, mock_get_engine, auth_backend, mock_request
    ):
        """Test that authenticate fails for invalid user."""
        mock_request.session = {"admin_user_id": "user-123"}

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        with patch("app.admin.DBSession") as mock_session_class:
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            result = await auth_backend.authenticate(mock_request)

        assert result is False

    @pytest.mark.anyio
    @patch("app.admin.get_sync_engine")
    async def test_authenticate_returns_false_for_inactive_user(
        self, mock_get_engine, auth_backend, mock_request
    ):
        """Test that authenticate fails for inactive user."""
        mock_request.session = {"admin_user_id": "user-123"}

        mock_user = MagicMock()
        mock_user.has_role.return_value = True
        mock_user.is_active = False

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        with patch("app.admin.DBSession") as mock_session_class:
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            result = await auth_backend.authenticate(mock_request)

        assert result is False

    @pytest.mark.anyio
    @patch("app.admin.get_sync_engine")
    async def test_authenticate_returns_false_for_non_superuser(
        self, mock_get_engine, auth_backend, mock_request
    ):
        """Test that authenticate fails for non-superuser."""
        mock_request.session = {"admin_user_id": "user-123"}

        mock_user = MagicMock()
        mock_user.has_role.return_value = False
        mock_user.is_active = True

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        with patch("app.admin.DBSession") as mock_session_class:
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            result = await auth_backend.authenticate(mock_request)

        assert result is False

    @pytest.mark.anyio
    @patch("app.admin.get_sync_engine")
    async def test_authenticate_success_for_valid_superuser(
        self, mock_get_engine, auth_backend, mock_request
    ):
        """Test that authenticate succeeds for valid superuser."""
        mock_request.session = {"admin_user_id": "user-123"}

        mock_user = MagicMock()
        mock_user.has_role.return_value = True
        mock_user.is_active = True

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        with patch("app.admin.DBSession") as mock_session_class:
            mock_session_class.return_value.__enter__ = MagicMock(
                return_value=mock_session
            )
            mock_session_class.return_value.__exit__ = MagicMock(return_value=False)

            result = await auth_backend.authenticate(mock_request)

        assert result is True
{%- endif %}
{%- else %}
"""Admin panel tests - not configured."""
{%- endif %}
