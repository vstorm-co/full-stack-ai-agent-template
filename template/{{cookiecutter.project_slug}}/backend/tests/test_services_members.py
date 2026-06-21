{%- if cookiecutter.enable_teams %}
"""Tests for MemberService and InvitationService."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AlreadyExistsError, AuthorizationError, BadRequestError, NotFoundError
from app.services.invitation import InvitationService
from app.services.member import MemberService


class TestMemberService:
    """Tests for MemberService (PostgreSQL async)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.get = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.delete = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        return MemberService(mock_db)

    @pytest.mark.anyio
    async def test_list_for_org_raises_if_not_member(self, service):
        with (
            patch("app.services.member.member_repo.get", new=AsyncMock(return_value=None)),
            pytest.raises(NotFoundError),
        ):
            await service.list_for_org(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.anyio
    async def test_change_role_raises_if_requester_not_admin_or_owner(self, service):
        mock_member = MagicMock()
        mock_member.role = "member"

        with (
            patch("app.services.member.member_repo.get", new=AsyncMock(return_value=mock_member)),
            pytest.raises(AuthorizationError),
        ):
            await service.change_role(uuid.uuid4(), uuid.uuid4(), "viewer", requester_id=uuid.uuid4())

    @pytest.mark.anyio
    async def test_change_role_raises_if_target_is_owner(self, service):
        mock_requester = MagicMock()
        mock_requester.role = "owner"
        mock_target = MagicMock()
        mock_target.role = "owner"

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_requester if call_count == 1 else mock_target

        with (
            patch("app.services.member.member_repo.get", new=mock_get),
            pytest.raises(BadRequestError),
        ):
            await service.change_role(uuid.uuid4(), uuid.uuid4(), "admin", requester_id=uuid.uuid4())

    @pytest.mark.anyio
    async def test_change_role_admin_cannot_assign_admin_role(self, service):
        mock_requester = MagicMock()
        mock_requester.role = "admin"
        mock_target = MagicMock()
        mock_target.role = "member"

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_requester if call_count == 1 else mock_target

        with (
            patch("app.services.member.member_repo.get", new=mock_get),
            pytest.raises(AuthorizationError),
        ):
            await service.change_role(uuid.uuid4(), uuid.uuid4(), "admin", requester_id=uuid.uuid4())

    @pytest.mark.anyio
    async def test_remove_raises_if_not_authorized(self, service):
        mock_member = MagicMock()
        mock_member.role = "viewer"

        with (
            patch("app.services.member.member_repo.get", new=AsyncMock(return_value=mock_member)),
            pytest.raises(AuthorizationError),
        ):
            await service.remove(uuid.uuid4(), uuid.uuid4(), requester_id=uuid.uuid4())

    @pytest.mark.anyio
    async def test_remove_admin_cannot_remove_admin(self, service):
        mock_requester = MagicMock()
        mock_requester.role = "admin"
        mock_target = MagicMock()
        mock_target.role = "admin"

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_requester if call_count == 1 else mock_target

        with (
            patch("app.services.member.member_repo.get", new=mock_get),
            pytest.raises(AuthorizationError),
        ):
            await service.remove(uuid.uuid4(), uuid.uuid4(), requester_id=uuid.uuid4())

    @pytest.mark.anyio
    async def test_leave_owner_blocked_if_others_exist(self, service):
        mock_membership = MagicMock()
        mock_membership.role = "owner"

        with (
            patch("app.services.member.member_repo.get", new=AsyncMock(return_value=mock_membership)),
            patch("app.services.member.member_repo.count_for_org", new=AsyncMock(return_value=3)),
            pytest.raises(BadRequestError),
        ):
            await service.leave(uuid.uuid4(), requester_id=uuid.uuid4())

    @pytest.mark.anyio
    async def test_transfer_ownership_only_owner_can_call(self, service):
        mock_requester = MagicMock()
        mock_requester.role = "admin"

        with (
            patch("app.services.member.member_repo.get", new=AsyncMock(return_value=mock_requester)),
            pytest.raises(AuthorizationError),
        ):
            await service.transfer_ownership(uuid.uuid4(), uuid.uuid4(), requester_id=uuid.uuid4())

    @pytest.mark.anyio
    async def test_transfer_ownership_to_self_raises(self, service):
        uid = uuid.uuid4()
        mock_requester = MagicMock()
        mock_requester.role = "owner"

        with (
            patch("app.services.member.member_repo.get", new=AsyncMock(return_value=mock_requester)),
            pytest.raises(BadRequestError),
        ):
            await service.transfer_ownership(uuid.uuid4(), uid, requester_id=uid)


class TestInvitationService:
    """Tests for InvitationService (PostgreSQL async)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        return InvitationService(mock_db)

    @pytest.mark.anyio
    async def test_invite_raises_if_not_admin_or_owner(self, service):
        mock_member = MagicMock()
        mock_member.role = "member"

        with (
            patch("app.services.invitation.member_repo.get", new=AsyncMock(return_value=mock_member)),
            pytest.raises(AuthorizationError),
        ):
            await service.invite(uuid.uuid4(), "user@example.com", "member", requester_id=uuid.uuid4())

    @pytest.mark.anyio
    async def test_invite_admin_cannot_invite_as_admin(self, service):
        mock_requester = MagicMock()
        mock_requester.role = "admin"

        with (
            patch("app.services.invitation.member_repo.get", new=AsyncMock(return_value=mock_requester)),
            pytest.raises(AuthorizationError),
        ):
            await service.invite(uuid.uuid4(), "user@example.com", "admin", requester_id=uuid.uuid4())

    @pytest.mark.anyio
    async def test_invite_raises_on_duplicate_pending(self, service):
        mock_requester = MagicMock()
        mock_requester.role = "owner"
        mock_pending = MagicMock()

        with (
            patch("app.services.invitation.member_repo.get", new=AsyncMock(return_value=mock_requester)),
            patch("app.services.invitation.user_repo.get_by_email", new=AsyncMock(return_value=None)),
            patch("app.services.invitation.invitation_repo.get_pending_for_org_email", new=AsyncMock(return_value=mock_pending)),
            pytest.raises(AlreadyExistsError),
        ):
            await service.invite(uuid.uuid4(), "user@example.com", "member", requester_id=uuid.uuid4())

    @pytest.mark.anyio
    async def test_accept_raises_on_missing_token(self, service):
        with (
            patch("app.services.invitation.invitation_repo.get_by_token", new=AsyncMock(return_value=None)),
            pytest.raises(NotFoundError),
        ):
            await service.accept("bad-token", accepting_user_id=uuid.uuid4())

    @pytest.mark.anyio
    async def test_accept_raises_on_non_pending_invite(self, service):
        mock_invite = MagicMock()
        mock_invite.status = "accepted"

        with (
            patch("app.services.invitation.invitation_repo.get_by_token", new=AsyncMock(return_value=mock_invite)),
            pytest.raises(BadRequestError),
        ):
            await service.accept("some-token", accepting_user_id=uuid.uuid4())

    @pytest.mark.anyio
    async def test_revoke_raises_if_not_pending(self, service):
        mock_invite = MagicMock()
        mock_invite.status = "expired"

        with (
            patch("app.services.invitation.invitation_repo.get_by_token", new=AsyncMock(return_value=mock_invite)),
            pytest.raises(BadRequestError),
        ):
            await service.revoke("some-token", requester_id=uuid.uuid4())


{%- else %}
"""Member/Invitation service tests — not configured (enable_teams=false)."""
{%- endif %}
