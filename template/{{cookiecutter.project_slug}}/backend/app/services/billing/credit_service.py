{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
"""CreditService — atomic credit ledger operations."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.billing.exceptions import InsufficientCreditsError
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.db.models.organization import Organization
from app.db.models.credit_transaction import CreditTransaction, CreditTransactionType
import app.repositories.credit_transaction as credit_tx_repo
import app.repositories.organization as org_repo

logger = logging.getLogger(__name__)


class CreditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def grant_subscription_credits(
        self,
        *,
        organization_id: uuid.UUID,
        amount: int,
        description: str,
        stripe_reference: str | None = None,
    ) -> CreditTransaction:
        org = await self._lock_org(organization_id)
        org.credits_balance += amount
        return await credit_tx_repo.create(
            self.db,
            organization_id=organization_id,
            delta=amount,
            balance_after=org.credits_balance,
            type=CreditTransactionType.GRANT_SUBSCRIPTION,
            description=description,
            stripe_reference=stripe_reference,
        )

    async def add_topup_credits(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
        amount: int,
        stripe_payment_intent_id: str,
    ) -> CreditTransaction:
        org = await self._lock_org(organization_id)
        org.credits_balance += amount
        return await credit_tx_repo.create(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            delta=amount,
            balance_after=org.credits_balance,
            type=CreditTransactionType.PURCHASE_TOPUP,
            description=f"Credit top-up ({amount} credits)",
            stripe_reference=stripe_payment_intent_id,
        )

    async def grant_signup_bonus(self, *, organization_id: uuid.UUID) -> CreditTransaction:
        amount = settings.CREDITS_FREE_TIER_GRANT
        org = await self._lock_org(organization_id)
        org.credits_balance += amount
        return await credit_tx_repo.create(
            self.db,
            organization_id=organization_id,
            delta=amount,
            balance_after=org.credits_balance,
            type=CreditTransactionType.GRANT_TRIAL,
            description=f"Sign-up bonus ({amount} credits)",
        )

    # Hot path — keep fast, minimize lock duration.
    async def debit(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
        amount: int,
        type: CreditTransactionType,
        description: str,
        usage_event_id: uuid.UUID | None = None,
    ) -> CreditTransaction:
        if amount <= 0:
            raise ValueError("Amount must be positive")

        org = await self._lock_org(organization_id)

        if org.credits_balance < amount:
            raise InsufficientCreditsError(
                message=f"Need {amount} credits, have {org.credits_balance}",
                details={"required": amount, "available": org.credits_balance},
            )

        org.credits_balance -= amount

        tx = await credit_tx_repo.create(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            delta=-amount,
            balance_after=org.credits_balance,
            type=type,
            description=description,
            usage_event_id=usage_event_id,
        )

        if org.credits_balance < settings.CREDITS_LOW_THRESHOLD and (org.credits_balance + amount) >= settings.CREDITS_LOW_THRESHOLD:
            logger.warning(
                "credits_low_threshold_crossed",
                extra={"org_id": str(organization_id), "balance": org.credits_balance},
            )

        return tx

    async def get_balance(self, organization_id: uuid.UUID) -> int:
        org = await self.db.get(Organization, organization_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": str(organization_id)})
        return org.credits_balance

    async def get_history(
        self,
        organization_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[CreditTransaction], int]:
        return await credit_tx_repo.list_for_org(self.db, organization_id, skip=skip, limit=limit)

    async def _lock_org(self, organization_id: uuid.UUID) -> Organization:
        org = await org_repo.get_by_id_for_update(self.db, organization_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": str(organization_id)})
        return org

{%- else %}
"""credit_service — not enabled (enable_billing=false or enable_credits_system=false)."""
{%- endif %}
