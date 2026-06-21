"""Email module — transactional email via Resend, SMTP, or log (dev)."""

from app.core.config import settings
from app.services.email.providers.base import EmailProvider


def get_email_provider() -> EmailProvider:
    match settings.EMAIL_PROVIDER:
        case "resend":
            from app.services.email.providers.resend import ResendProvider

            return ResendProvider(api_key=settings.RESEND_API_KEY)
        case "log" | _:
            from app.services.email.providers.log import LogProvider

            return LogProvider()
