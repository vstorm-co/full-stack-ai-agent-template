"""Log email provider — for development. Prints to stdout, optionally writes HTML to disk."""

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.services.email.providers.base import EmailMessage, SendResult

logger = logging.getLogger(__name__)


class LogProvider:
    def __init__(self, write_to_disk: bool = False, output_dir: str = "/tmp/emails") -> None:
        self._write_to_disk = write_to_disk
        self._output_dir = Path(output_dir)

    async def send(self, message: EmailMessage) -> SendResult:
        msg_id = f"log_{uuid.uuid4()}"
        logger.info(
            "email_send_simulated",
            extra={
                "message_id": msg_id,
                "to": message.to,
                "subject": message.subject,
                "preview": message.text[:200] if message.text else "",
            },
        )

        if self._write_to_disk:
            try:
                self._output_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                fname = self._output_dir / f"{ts}_{message.subject[:40].replace(' ', '_')}.html"
                fname.write_text(message.html, encoding="utf-8")
                logger.info("email_written_to_disk", extra={"path": str(fname)})
            except Exception as exc:
                logger.warning("email_write_failed", extra={"error": str(exc)})

        return SendResult(provider_message_id=msg_id, accepted=True)
