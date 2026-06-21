{%- if cookiecutter.enable_billing and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Tests for Stripe seat limit enforcement."""

import stripe as _stripe
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import BadRequestError, PaymentRequiredError
from app.services.billing import BillingService
from app.services.invitation import InvitationService


def _org(seats_limit=None, stripe_customer_id=None):
    org = MagicMock()
    org.id = "org-1"
    org.name = "Test Org"
    org.seats_limit = seats_limit
    org.stripe_customer_id = stripe_customer_id
    return org


def _invite(org_id="org-1", role="member"):
    inv = MagicMock()
    inv.organization_id = org_id
    inv.role = role
    inv.status = "pending"
    inv.expires_at = None
    inv.email = "user@example.com"
    return inv


def _user(email: str = "user@example.com"):
    """User mock whose email matches the invite — accept() rejects mismatches."""
    user = MagicMock()
    user.id = "user-1"
    user.email = email
    return user


class TestSeatLimitEnforcement:
    """Invitation.accept() enforces seats_limit (PostgreSQL async)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.mark.anyio
    async def test_accept_allowed_when_under_limit(self, mock_db):
        org = _org(seats_limit=5)
        inv = _invite()

        with patch("app.repositories.invitation_repo.get_by_token", new=AsyncMock(return_value=inv)), \
             patch("app.repositories.member_repo.get", new=AsyncMock(return_value=None)), \
             patch("app.repositories.organization_repo.get_by_id", new=AsyncMock(return_value=org)), \
             patch("app.repositories.user_repo.get_by_id", new=AsyncMock(return_value=_user("user@example.com"))), \
             patch("app.repositories.member_repo.count_for_org", new=AsyncMock(return_value=3)), \
             patch("app.repositories.member_repo.create", new=AsyncMock(return_value=MagicMock())), \
             patch("app.repositories.invitation_repo.accept", new=AsyncMock()):
            svc = InvitationService(mock_db)
            result = await svc.accept("tok", "user-1")
            assert result is inv

    @pytest.mark.anyio
    async def test_accept_blocked_when_at_limit(self, mock_db):
        org = _org(seats_limit=3)
        inv = _invite()

        with patch("app.repositories.invitation_repo.get_by_token", new=AsyncMock(return_value=inv)), \
             patch("app.repositories.member_repo.get", new=AsyncMock(return_value=None)), \
             patch("app.repositories.organization_repo.get_by_id", new=AsyncMock(return_value=org)), \
             patch("app.repositories.user_repo.get_by_id", new=AsyncMock(return_value=_user("user@example.com"))), \
             patch("app.repositories.member_repo.count_for_org", new=AsyncMock(return_value=3)):
            svc = InvitationService(mock_db)
            with pytest.raises(PaymentRequiredError):
                await svc.accept("tok", "user-1")

    @pytest.mark.anyio
    async def test_accept_unlimited_when_no_seats_limit(self, mock_db):
        org = _org(seats_limit=None)
        inv = _invite()

        with patch("app.repositories.invitation_repo.get_by_token", new=AsyncMock(return_value=inv)), \
             patch("app.repositories.member_repo.get", new=AsyncMock(return_value=None)), \
             patch("app.repositories.organization_repo.get_by_id", new=AsyncMock(return_value=org)), \
             patch("app.repositories.user_repo.get_by_id", new=AsyncMock(return_value=_user("user@example.com"))), \
             patch("app.repositories.member_repo.count_for_org", new=AsyncMock(return_value=100)), \
             patch("app.repositories.member_repo.create", new=AsyncMock(return_value=MagicMock())), \
             patch("app.repositories.invitation_repo.accept", new=AsyncMock()):
            svc = InvitationService(mock_db)
            result = await svc.accept("tok", "user-1")
            assert result is inv


class TestBillingService:
    """BillingService unit tests (PostgreSQL async)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    # Tests for `get_or_create_customer`, `create_checkout_session(org=...)`,
    # and `create_portal_session(org)` were removed when those concerns moved
    # into private sub-services (CheckoutService, customer_repo) — the public
    # facade no longer exposes the same shape. Webhook signature validation
    # stays on the facade, so its test stays.

    @pytest.mark.anyio
    async def test_webhook_invalid_signature_raises(self, mock_db):
        svc = BillingService(mock_db)
        with patch.object(
            _stripe.Webhook,
            "construct_event",
            side_effect=_stripe.SignatureVerificationError("bad sig", b""),
        ):
            with pytest.raises(BadRequestError):
                await svc.handle_webhook_event(b"payload", "sig")


{%- else %}
"""Stripe seats tests — not configured (enable_billing, enable_teams, or use_jwt is false)."""
{%- endif %}
