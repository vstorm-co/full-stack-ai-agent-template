"""Email-specific exceptions."""

from app.core.exceptions import AppException


class EmailError(AppException):
    status_code = 500
    code = "EMAIL_ERROR"


class EmailProviderError(EmailError):
    status_code = 502
    code = "EMAIL_PROVIDER_ERROR"


class EmailUnsubscribedError(EmailError):
    status_code = 422
    code = "EMAIL_UNSUBSCRIBED"


class EmailSuppressedError(EmailError):
    status_code = 422
    code = "EMAIL_SUPPRESSED"


class EmailTemplateError(EmailError):
    status_code = 500
    code = "EMAIL_TEMPLATE_ERROR"
