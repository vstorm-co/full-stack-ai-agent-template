{%- if cookiecutter.use_jwt %}
"""Tests for service layer."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import AlreadyExistsError, AuthenticationError, NotFoundError
{%- if cookiecutter.enable_email %}
from app.core.security import get_password_hash
{%- endif %}
from app.schemas.user import UserCreate, UserUpdate
from app.services.user import UserService


class MockUser:
    """Mock user for testing."""

    def __init__(
        self,
        id=None,
        email="test@example.com",
        full_name="Test User",
        hashed_password="$2b$12$hashedpassword",
        is_active=True,
        role="user",
    ):
        self.id = id or uuid4()
        self.email = email
        self.full_name = full_name
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.role = role




class TestUserServicePostgresql:
    """Tests for UserService with PostgreSQL."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def user_service(self, mock_db: AsyncMock) -> UserService:
        """Create UserService instance with mock db."""
        return UserService(mock_db)

    @pytest.fixture
    def mock_user(self) -> MockUser:
        """Create a mock user."""
        return MockUser()

    @pytest.mark.anyio
    async def test_get_by_id_success(self, user_service: UserService, mock_user: MockUser):
        """Test getting user by ID successfully."""
        with patch("app.services.user.user_repo") as mock_repo:
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)

            result = await user_service.get_by_id(mock_user.id)

            assert result == mock_user
            mock_repo.get_by_id.assert_called_once()

    @pytest.mark.anyio
    async def test_get_by_id_not_found(self, user_service: UserService):
        """Test getting non-existent user raises NotFoundError."""
        with patch("app.services.user.user_repo") as mock_repo:
            mock_repo.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await user_service.get_by_id(uuid4())

    @pytest.mark.anyio
    async def test_get_by_email(self, user_service: UserService, mock_user: MockUser):
        """Test getting user by email."""
        with patch("app.services.user.user_repo") as mock_repo:
            mock_repo.get_by_email = AsyncMock(return_value=mock_user)

            result = await user_service.get_by_email("test@example.com")

            assert result == mock_user

    @pytest.mark.anyio
    async def test_get_multi(self, user_service: UserService, mock_user: MockUser):
        """Test getting multiple users."""
        with patch("app.services.user.user_repo") as mock_repo:
            mock_repo.get_multi = AsyncMock(return_value=[mock_user])

            result = await user_service.get_multi(skip=0, limit=10)

            assert len(result) == 1
            assert result[0] == mock_user

    @pytest.mark.anyio
    async def test_register_success(self, user_service: UserService, mock_user: MockUser):
        """Test registering a new user."""
        # Stub the count-of-users SELECT used by the first-user → app-admin
        # promotion. Side effects we don't care about (welcome email, personal
        # org creation, count query) are mocked out so the test stays focused
        # on user_repo.create being invoked.
        scalar_one_result = MagicMock()
        scalar_one_result.scalar_one.return_value = 1
        user_service.db.execute = AsyncMock(return_value=scalar_one_result)

        with (
            patch("app.services.user.user_repo") as mock_repo,
{%- if cookiecutter.enable_teams %}
            patch("app.services.user.OrganizationService") as mock_org_svc,
{%- endif %}
{%- if cookiecutter.enable_email %}
            patch("app.services.user.get_email_service") as mock_email,
{%- endif %}
        ):
            mock_repo.get_by_email = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=mock_user)
{%- if cookiecutter.enable_teams %}
            mock_org_svc.return_value.create_personal_org = AsyncMock()
{%- endif %}
{%- if cookiecutter.enable_email %}
            mock_email.return_value.send_welcome = AsyncMock()
{%- endif %}

            user_in = UserCreate(
                email="new@example.com",
                password="password123",
                full_name="New User",
            )
            result = await user_service.register(user_in)

            assert result == mock_user
            mock_repo.create.assert_called_once()

    @pytest.mark.anyio
    async def test_register_duplicate_email(self, user_service: UserService, mock_user: MockUser):
        """Test registering with existing email raises AlreadyExistsError."""
        with patch("app.services.user.user_repo") as mock_repo:
            mock_repo.get_by_email = AsyncMock(return_value=mock_user)

            user_in = UserCreate(
                email="existing@example.com",
                password="password123",
                full_name="Test",
            )

            with pytest.raises(AlreadyExistsError):
                await user_service.register(user_in)

    @pytest.mark.anyio
    async def test_authenticate_success(self, user_service: UserService, mock_user: MockUser):
        """Test successful authentication."""
        with (
            patch("app.services.user.user_repo") as mock_repo,
            patch("app.services.user.verify_password", return_value=True),
        ):
            mock_repo.get_by_email = AsyncMock(return_value=mock_user)

            result = await user_service.authenticate("test@example.com", "password123")

            assert result == mock_user

    @pytest.mark.anyio
    async def test_authenticate_invalid_password(self, user_service: UserService, mock_user: MockUser):
        """Test authentication with wrong password."""
        with (
            patch("app.services.user.user_repo") as mock_repo,
            patch("app.services.user.verify_password", return_value=False),
        ):
            mock_repo.get_by_email = AsyncMock(return_value=mock_user)

            with pytest.raises(AuthenticationError):
                await user_service.authenticate("test@example.com", "wrongpassword")

    @pytest.mark.anyio
    async def test_authenticate_user_not_found(self, user_service: UserService):
        """Test authentication with non-existent user."""
        with patch("app.services.user.user_repo") as mock_repo:
            mock_repo.get_by_email = AsyncMock(return_value=None)

            with pytest.raises(AuthenticationError):
                await user_service.authenticate("unknown@example.com", "password")

    @pytest.mark.anyio
    async def test_authenticate_inactive_user(self, user_service: UserService):
        """Test authentication with inactive user."""
        inactive_user = MockUser(is_active=False)
        with (
            patch("app.services.user.user_repo") as mock_repo,
            patch("app.services.user.verify_password", return_value=True),
        ):
            mock_repo.get_by_email = AsyncMock(return_value=inactive_user)

            with pytest.raises(AuthenticationError):
                await user_service.authenticate("test@example.com", "password")

    @pytest.mark.anyio
    async def test_update_success(self, user_service: UserService, mock_user: MockUser):
        """Test updating user."""
        with patch("app.services.user.user_repo") as mock_repo:
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_repo.update = AsyncMock(return_value=mock_user)

            user_update = UserUpdate(full_name="Updated Name")
            result = await user_service.update(mock_user.id, user_update)

            assert result == mock_user

    @pytest.mark.anyio
    async def test_update_with_password(self, user_service: UserService, mock_user: MockUser):
        """Test updating user with password change."""
        with patch("app.services.user.user_repo") as mock_repo:
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_repo.update = AsyncMock(return_value=mock_user)

            user_update = UserUpdate(password="newpassword123")
            result = await user_service.update(mock_user.id, user_update)

            assert result == mock_user
            # Verify hashed_password was passed to update
            call_args = mock_repo.update.call_args
            assert "hashed_password" in call_args[1]["update_data"]

    @pytest.mark.anyio
    async def test_delete_success(self, user_service: UserService, mock_user: MockUser):
        """Test deleting user."""
        with patch("app.services.user.user_repo") as mock_repo:
            mock_repo.delete = AsyncMock(return_value=mock_user)

            result = await user_service.delete(mock_user.id)

            assert result == mock_user

    @pytest.mark.anyio
    async def test_delete_not_found(self, user_service: UserService):
        """Test deleting non-existent user."""
        with patch("app.services.user.user_repo") as mock_repo:
            mock_repo.delete = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await user_service.delete(uuid4())

{%- if cookiecutter.enable_email %}


class TestSingleUseLinks:
    """Reset and sign-in links must not survive being redeemed.

    Both are JWTs, so they cannot be revoked — a link that stays valid for its
    whole TTL can be replayed after the legitimate user has already used it,
    which takes over the account.
    """

    @pytest.fixture
    def user_service(self) -> UserService:
        return UserService(AsyncMock())

    @pytest.mark.anyio
    async def test_reset_link_cannot_be_replayed(self, user_service: UserService):
        """Second use of the same reset token is rejected."""
        user = MockUser(hashed_password=get_password_hash("original"))

        with patch("app.services.user.user_repo") as mock_repo:
            mock_repo.get_by_email = AsyncMock(return_value=user)
            issued = await user_service.issue_password_reset_token(user.email)
            assert issued is not None
            _, token = issued

            mock_repo.get_by_id = AsyncMock(return_value=user)

            # Redeeming rotates the hash, which is what expires the token.
            async def _rotate(db, *, db_user, update_data):
                db_user.hashed_password = update_data["hashed_password"]
                return db_user

            mock_repo.update = AsyncMock(side_effect=_rotate)

            await user_service.confirm_password_reset(token, "first-new-password")

            with pytest.raises(AuthenticationError):
                await user_service.confirm_password_reset(token, "attacker-password")

    @pytest.mark.anyio
    async def test_magic_link_cannot_be_replayed(self, user_service: UserService):
        """Second use of the same sign-in link is rejected."""
        user = MockUser()
        user.magic_link_epoch = 0

        with patch("app.services.user.user_repo") as mock_repo:
            mock_repo.get_by_email = AsyncMock(return_value=user)
            issued = await user_service.issue_magic_link_token(user.email)
            assert issued is not None
            _, token = issued

            mock_repo.get_by_id = AsyncMock(return_value=user)

            async def _bump(db, *, db_user, update_data):
                db_user.magic_link_epoch = update_data["magic_link_epoch"]
                return db_user

            mock_repo.update = AsyncMock(side_effect=_bump)

            await user_service.consume_magic_link_token(token)

            with pytest.raises(AuthenticationError):
                await user_service.consume_magic_link_token(token)

    @pytest.mark.anyio
    async def test_redeeming_one_link_invalidates_the_others(
        self, user_service: UserService
    ):
        """Two links outstanding: using the newer one must kill the older one."""
        user = MockUser()
        user.magic_link_epoch = 0

        with patch("app.services.user.user_repo") as mock_repo:
            mock_repo.get_by_email = AsyncMock(return_value=user)
            first = await user_service.issue_magic_link_token(user.email)
            second = await user_service.issue_magic_link_token(user.email)
            assert first is not None and second is not None

            mock_repo.get_by_id = AsyncMock(return_value=user)

            async def _bump(db, *, db_user, update_data):
                db_user.magic_link_epoch = update_data["magic_link_epoch"]
                return db_user

            mock_repo.update = AsyncMock(side_effect=_bump)

            await user_service.consume_magic_link_token(second[1])

            with pytest.raises(AuthenticationError):
                await user_service.consume_magic_link_token(first[1])
{%- endif %}


{%- endif %}
