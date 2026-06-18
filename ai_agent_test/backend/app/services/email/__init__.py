"""Email module — transactional email via Resend, SMTP, or log (dev)."""

from app.services.email.providers.base import EmailProvider


def get_email_provider() -> EmailProvider:
    from app.core.config import settings

    match settings.EMAIL_PROVIDER:
        case "smtp":
            from app.services.email.providers.smtp import SMTPProvider

            return SMTPProvider(
                host=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_TLS,
            )
        case "log" | _:
            from app.services.email.providers.log import LogProvider

            return LogProvider()
