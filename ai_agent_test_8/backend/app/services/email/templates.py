"""Template loader — reads pre-rendered HTML/text from emails/dist/."""

from pathlib import Path

from app.services.email.exceptions import EmailTemplateError

# Emails compiled directory sits alongside `backend/` at the project root
_DIST_DIR = Path(__file__).parent.parent.parent.parent / "emails" / "compiled"


def _load_raw(key: str, ext: str) -> str:
    path = _DIST_DIR / f"{key}.{ext}"
    if not path.exists():
        raise EmailTemplateError(
            message=f"Email template '{key}.{ext}' not found",
            details={"path": str(path)},
        )
    return path.read_text(encoding="utf-8")


def _render(template: str, context: dict) -> str:
    """Replace [[variable]] placeholders with context values."""
    for k, v in context.items():
        template = template.replace(f"[[{k}]]", str(v) if v is not None else "")
    return template


def render_email(key: str, context: dict) -> tuple[str, str, str]:
    """Return (subject, html, text) for the given template key and context."""
    try:
        html_raw = _load_raw(key, "html")
        text_raw = _load_raw(key, "txt")
    except EmailTemplateError:
        raise

    # Subject is stored in the first line of .txt as "Subject: ..."
    lines = text_raw.splitlines()
    subject_line = lines[0] if lines else ""
    subject_raw = (
        subject_line.removeprefix("Subject:").strip()
        if subject_line.startswith("Subject:")
        else key
    )
    text_body = "\n".join(lines[1:]).strip()

    subject = _render(subject_raw, context)
    html = _render(html_raw, context)
    text = _render(text_body, context)
    return subject, html, text
