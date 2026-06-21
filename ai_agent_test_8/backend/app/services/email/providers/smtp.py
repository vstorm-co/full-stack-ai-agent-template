"""SMTP email provider using aiosmtplib."""

import logging
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.services.email.providers.base import EmailMessage, SendResult

logger = logging.getLogger(__name__)


class SMTPProvider:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    async def send(self, message: EmailMessage) -> SendResult:
        import aiosmtplib

        from_addr = (
            f"{message.from_name} <{message.from_email}>"
            if message.from_name
            else message.from_email
        )
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = from_addr
        msg["To"] = ", ".join(message.to)
        if message.cc:
            msg["Cc"] = ", ".join(message.cc)
        if message.reply_to:
            msg["Reply-To"] = message.reply_to

        msg.attach(MIMEText(message.text, "plain"))
        msg.attach(MIMEText(message.html, "html"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                use_tls=self.use_tls,
            )
            msg_id = f"smtp_{uuid.uuid4()}"
            logger.info(
                "smtp_email_sent",
                extra={
                    "message_id": msg_id,
                    "to": message.to,
                    "subject": message.subject,
                },
            )
            return SendResult(provider_message_id=msg_id, accepted=True)
        except Exception as exc:
            logger.error(
                "smtp_email_failed",
                extra={"error": str(exc), "to": message.to},
            )
            return SendResult(provider_message_id="", accepted=False, error=str(exc))
