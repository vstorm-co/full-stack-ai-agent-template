"""Resend email provider."""

import asyncio
import logging
import uuid

from app.services.email.providers.base import EmailMessage, SendResult

logger = logging.getLogger(__name__)


class ResendProvider:
    def __init__(self, api_key: str) -> None:
        import resend as resend_sdk

        resend_sdk.api_key = api_key
        self._resend = resend_sdk

    async def send(self, message: EmailMessage) -> SendResult:
        from_addr = (
            f"{message.from_name} <{message.from_email}>"
            if message.from_name
            else message.from_email
        )
        params = {
            "from": from_addr,
            "to": message.to,
            "subject": message.subject,
            "html": message.html,
            "text": message.text,
        }
        if message.cc:
            params["cc"] = message.cc
        if message.bcc:
            params["bcc"] = message.bcc
        if message.reply_to:
            params["reply_to"] = message.reply_to
        if message.tags:
            params["tags"] = [{"name": "type", "value": t} for t in message.tags]

        try:
            resp = await asyncio.to_thread(self._resend.Emails.send, params)
            msg_id = resp.get("id", str(uuid.uuid4()))
            logger.info(
                "resend_email_sent",
                extra={
                    "message_id": msg_id,
                    "to": message.to,
                    "subject": message.subject,
                },
            )
            return SendResult(provider_message_id=msg_id, accepted=True)
        except Exception as exc:
            logger.error(
                "resend_email_failed",
                extra={"error": str(exc), "to": message.to},
            )
            return SendResult(provider_message_id="", accepted=False, error=str(exc))
