{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Tests for RBAC dependencies and org-role permission matrix."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.deps import RequireOrgRole, _require_app_admin
from app.core.exceptions import AuthorizationError


class TestRequireOrgRole:
    """Tests for RequireOrgRole dependency (PostgreSQL async)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.get = AsyncMock()
        return db

    @pytest.fixture
    def mock_org(self):
        org = MagicMock()
        org.id = uuid.uuid4()
        return org

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = uuid.uuid4()
        user.is_app_admin = False
        return user

    @pytest.mark.anyio
    async def test_owner_passes_require_owner(self, mock_db, mock_org, mock_user):
        mock_membership = MagicMock()
        mock_membership.role = "owner"

        checker = RequireOrgRole("owner")
        with patch("app.api.deps._member_repo.get", new=AsyncMock(return_value=mock_membership)):
            result = await checker(org=mock_org, user=mock_user, db=mock_db)
        assert result is mock_org

    @pytest.mark.anyio
    async def test_admin_fails_require_owner(self, mock_db, mock_org, mock_user):
        mock_membership = MagicMock()
        mock_membership.role = "admin"

        checker = RequireOrgRole("owner")
        with (
            patch("app.api.deps._member_repo.get", new=AsyncMock(return_value=mock_membership)),
            pytest.raises(AuthorizationError),
        ):
            await checker(org=mock_org, user=mock_user, db=mock_db)

    @pytest.mark.anyio
    async def test_owner_passes_require_admin_plus(self, mock_db, mock_org, mock_user):
        mock_membership = MagicMock()
        mock_membership.role = "owner"

        checker = RequireOrgRole("owner", "admin")
        with patch("app.api.deps._member_repo.get", new=AsyncMock(return_value=mock_membership)):
            result = await checker(org=mock_org, user=mock_user, db=mock_db)
        assert result is mock_org

    @pytest.mark.anyio
    async def test_member_fails_require_admin_plus(self, mock_db, mock_org, mock_user):
        mock_membership = MagicMock()
        mock_membership.role = "member"

        checker = RequireOrgRole("owner", "admin")
        with (
            patch("app.api.deps._member_repo.get", new=AsyncMock(return_value=mock_membership)),
            pytest.raises(AuthorizationError),
        ):
            await checker(org=mock_org, user=mock_user, db=mock_db)

    @pytest.mark.anyio
    async def test_non_member_fails(self, mock_db, mock_org, mock_user):
        checker = RequireOrgRole("owner", "admin", "member")
        with (
            patch("app.api.deps._member_repo.get", new=AsyncMock(return_value=None)),
            pytest.raises(AuthorizationError),
        ):
            await checker(org=mock_org, user=mock_user, db=mock_db)

    @pytest.mark.anyio
    async def test_viewer_passes_require_any_role(self, mock_db, mock_org, mock_user):
        mock_membership = MagicMock()
        mock_membership.role = "viewer"

        checker = RequireOrgRole("owner", "admin", "member", "viewer")
        with patch("app.api.deps._member_repo.get", new=AsyncMock(return_value=mock_membership)):
            result = await checker(org=mock_org, user=mock_user, db=mock_db)
        assert result is mock_org


class TestCurrentAppAdmin:
    """Tests for CurrentAppAdmin dependency."""

    @pytest.mark.anyio
    async def test_app_admin_passes(self):
        mock_user = MagicMock()
        mock_user.is_app_admin = True

        result = await _require_app_admin(user=mock_user)
        assert result is mock_user

    @pytest.mark.anyio
    async def test_non_app_admin_fails(self):
        mock_user = MagicMock()
        mock_user.is_app_admin = False

        with pytest.raises(AuthorizationError):
            await _require_app_admin(user=mock_user)


class TestOrgRolePermissionMatrix:
    """Parametrised tests covering the full role x action permission matrix."""

    _ROLES = ["owner", "admin", "member", "viewer"]

    @pytest.mark.parametrize("role,should_pass", [
        ("owner", True),
        ("admin", False),
        ("member", False),
        ("viewer", False),
    ])
    @pytest.mark.anyio
    async def test_require_owner(self, role: str, should_pass: bool):
        mock_db = MagicMock()
        mock_org = MagicMock()
        mock_org.id = uuid.uuid4()
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_membership = MagicMock()
        mock_membership.role = role

        checker = RequireOrgRole("owner")
        with patch("app.api.deps._member_repo.get", new=AsyncMock(return_value=mock_membership)):
            if should_pass:
                await checker(org=mock_org, user=mock_user, db=mock_db)
            else:
                with pytest.raises(AuthorizationError):
                    await checker(org=mock_org, user=mock_user, db=mock_db)

    @pytest.mark.parametrize("role,should_pass", [
        ("owner", True),
        ("admin", True),
        ("member", False),
        ("viewer", False),
    ])
    @pytest.mark.anyio
    async def test_require_admin_plus(self, role: str, should_pass: bool):
        mock_db = MagicMock()
        mock_org = MagicMock()
        mock_org.id = uuid.uuid4()
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_membership = MagicMock()
        mock_membership.role = role

        checker = RequireOrgRole("owner", "admin")
        with patch("app.api.deps._member_repo.get", new=AsyncMock(return_value=mock_membership)):
            if should_pass:
                await checker(org=mock_org, user=mock_user, db=mock_db)
            else:
                with pytest.raises(AuthorizationError):
                    await checker(org=mock_org, user=mock_user, db=mock_db)

    @pytest.mark.parametrize("role,should_pass", [
        ("owner", True),
        ("admin", True),
        ("member", True),
        ("viewer", False),
    ])
    @pytest.mark.anyio
    async def test_require_member_plus(self, role: str, should_pass: bool):
        mock_db = MagicMock()
        mock_org = MagicMock()
        mock_org.id = uuid.uuid4()
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_membership = MagicMock()
        mock_membership.role = role

        checker = RequireOrgRole("owner", "admin", "member")
        with patch("app.api.deps._member_repo.get", new=AsyncMock(return_value=mock_membership)):
            if should_pass:
                await checker(org=mock_org, user=mock_user, db=mock_db)
            else:
                with pytest.raises(AuthorizationError):
                    await checker(org=mock_org, user=mock_user, db=mock_db)


{%- else %}
"""RBAC tests — not configured (enable_teams=false or no JWT)."""
{%- endif %}
