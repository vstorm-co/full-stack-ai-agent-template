"""Contact-form service — accepts inbound inquiries from the marketing site.

The current implementation is intentionally minimal: it structured-logs the
submission and returns success. Production deployments typically swap in:

  - persistence (write to a `contact_messages` table for admin review),
  - an email notification to the support inbox,
  - a CRM webhook (HubSpot / Pipedrive / Plain).

Adding any of those is a service-level change — the route stays as is.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ContactService:
    """Handle inbound contact-form submissions.

    Stateless — holds no DB session. Routing decisions (which inbox to forward
    to per `topic`) live here, not in the route or schema.
    """

    async def submit(
        self,
        *,
        name: str,
        email: str,
        topic: str,
        message: str,
    ) -> None:
        """Record a contact-form submission.

        We log first, side-effect last — that way a downstream failure (CRM
        outage, email provider hiccup) doesn't make us lose the submission.
        """
        logger.info(
            "contact_submission",
            extra={
                "topic": topic,
                "email": email,
                "name": name,
                # Preview to avoid putting PII-heavy bodies in the main log line.
                "message_preview": message[:120] + ("…" if len(message) > 120 else ""),
                "message_length": len(message),
            },
        )
        # Future: notify support inbox / push to CRM. Best-effort, don't fail
        # the user-facing submission for downstream issues.
