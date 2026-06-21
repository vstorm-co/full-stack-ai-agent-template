{%- if cookiecutter.enable_email %}
"""Email module — transactional email via Resend, SMTP, or log (dev)."""

from app.core.config import settings
from app.services.email.providers.base import EmailProvider


def get_email_provider() -> EmailProvider:
    match settings.EMAIL_PROVIDER:
{%- if cookiecutter.email_provider == "resend" %}
        case "resend":
            from app.services.email.providers.resend import ResendProvider
            return ResendProvider(api_key=settings.RESEND_API_KEY)
{%- endif %}
{%- if cookiecutter.email_provider == "smtp" %}
        case "smtp":
            from app.services.email.providers.smtp import SMTPProvider
            return SMTPProvider(
                host=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_TLS,
            )
{%- endif %}
        case "log" | _:
            from app.services.email.providers.log import LogProvider
            return LogProvider()

{%- else %}
"""Email module — not enabled (enable_email=false)."""
{%- endif %}
