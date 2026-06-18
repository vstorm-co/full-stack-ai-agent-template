"""Input sanitization utilities.

This module provides security-focused input sanitization functions:
- HTML sanitization to prevent XSS attacks
- Path traversal prevention for file operations
- Webhook URL validation to prevent SSRF attacks
- Common input cleaning utilities

Note: SQL injection is prevented by using SQLAlchemy ORM with parameterized queries.
"""

import html
import ipaddress
import os
import re
import socket
import unicodedata
from pathlib import Path
from typing import TypeVar
from urllib.parse import urlparse

# Default allowed HTML tags for rich text content
DEFAULT_ALLOWED_TAGS = frozenset(
    {
        "a",
        "abbr",
        "acronym",
        "b",
        "blockquote",
        "br",
        "code",
        "em",
        "i",
        "li",
        "ol",
        "p",
        "pre",
        "strong",
        "ul",
    }
)

# Default allowed HTML attributes
DEFAULT_ALLOWED_ATTRIBUTES = {
    "a": frozenset({"href", "title", "rel"}),
    "abbr": frozenset({"title"}),
    "acronym": frozenset({"title"}),
}

# Allowed URL schemes for webhook URLs
WEBHOOK_ALLOWED_SCHEMES = frozenset({"http", "https"})

# Shared Address Space (RFC 6598) — CGNAT range.
# Python 3.11+ no longer classifies 100.64.0.0/10 as private or reserved,
# so we block it explicitly. Covers cloud metadata endpoints like
# Alibaba Cloud's 100.100.100.200.
_CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")


class SSRFBlockedError(ValueError):
    """Raised when a URL is blocked by SSRF protection.

    Dedicated exception type to avoid fragile string matching when
    distinguishing SSRF blocks from other ValueErrors.
    """


def sanitize_html(
    content: str,
    allowed_tags: frozenset[str] | None = None,
    strip: bool = True,
) -> str:
    """Sanitize HTML content to prevent XSS attacks.

    This is a simple implementation that escapes all HTML.
    For rich text support, consider using the `bleach` library.

    Args:
        content: The HTML content to sanitize.
        allowed_tags: Not used in simple mode (for bleach compatibility).
        strip: Not used in simple mode (for bleach compatibility).

    Returns:
        Escaped HTML-safe string.

    Example:
        >>> sanitize_html("<script>alert('xss')</script>")
        "&lt;script&gt;alert('xss')&lt;/script&gt;"
    """
    if not content:
        return ""

    return html.escape(content)


def sanitize_filename(filename: str, allow_unicode: bool = False) -> str:
    """Sanitize a filename to prevent path traversal and unsafe characters.

    Args:
        filename: The filename to sanitize.
        allow_unicode: Whether to allow unicode characters.

    Returns:
        A safe filename string.

    Example:
        >>> sanitize_filename("../../../etc/passwd")
        "etc_passwd"
        >>> sanitize_filename("hello world.txt")
        "hello_world.txt"
    """
    if not filename:
        return ""

    # Normalize unicode
    if allow_unicode:
        filename = unicodedata.normalize("NFKC", filename)
    else:
        filename = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")

    # Get just the filename (remove any path components)
    filename = os.path.basename(filename)

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Replace path separators and special characters
    filename = re.sub(r"[/\\:*?\"<>|]", "_", filename)

    # Replace multiple underscores/spaces with single underscore
    filename = re.sub(r"[\s_]+", "_", filename)

    # Remove leading/trailing underscores and dots
    filename = filename.strip("._")

    # Ensure we have a valid filename
    if not filename:
        return "unnamed"

    return filename


def validate_safe_path(
    base_dir: Path | str,
    user_path: str,
) -> Path:
    """Validate that a user-provided path is within the allowed base directory.

    Prevents path traversal attacks by ensuring the resolved path
    is within the expected directory.

    Args:
        base_dir: The base directory that all paths must be within.
        user_path: The user-provided path to validate.

    Returns:
        The resolved, safe path.

    Raises:
        ValueError: If the path would escape the base directory.

    Example:
        >>> validate_safe_path("/uploads", "../../../etc/passwd")
        Raises ValueError
        >>> validate_safe_path("/uploads", "images/photo.jpg")
        Path("/uploads/images/photo.jpg")
    """
    base_path = Path(base_dir).resolve()
    user_path_sanitized = sanitize_filename(user_path.lstrip("/\\"))

    # Resolve the full path
    full_path = (base_path / user_path_sanitized).resolve()

    # Check if the resolved path is within the base directory
    try:
        full_path.relative_to(base_path)
    except ValueError as err:
        raise ValueError(
            f"Path traversal detected: {user_path!r} would escape {base_dir!r}"
        ) from err

    return full_path


def _is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address is private, reserved, loopback, or link-local.

    Args:
        ip_str: The IP address string to check.

    Returns:
        True if the address should be blocked, False if it's safe.
    """
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        # If we can't parse it, block it to be safe
        return True

    return (
        addr.is_private
        or addr.is_reserved
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_unspecified
        or addr in _CGNAT_NETWORK
    )


def validate_webhook_url(
    url: str,
    allowed_schemes: frozenset[str] | None = None,
) -> str:
    """Validate a webhook URL to prevent SSRF attacks.

    Checks that the URL:
    - Uses an allowed scheme (http/https only by default)
    - Does not contain userinfo (credentials in the URL)
    - Does not point to private, reserved, loopback, or link-local IP addresses
    - Resolves via DNS to a public IP (prevents DNS rebinding attacks)

    Args:
        url: The webhook URL to validate.
        allowed_schemes: Allowed URL schemes. Defaults to {"http", "https"}.

    Returns:
        The validated URL string.

    Raises:
        SSRFBlockedError: If the URL is blocked by SSRF protection.
        ValueError: If the URL is malformed.

    Example:
        >>> validate_webhook_url("https://example.com/webhook")
        "https://example.com/webhook"
        >>> validate_webhook_url("http://169.254.169.254/latest/meta-data/")
        Raises SSRFBlockedError
    """
    if allowed_schemes is None:
        allowed_schemes = WEBHOOK_ALLOWED_SCHEMES

    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception as err:
        raise ValueError(f"Invalid webhook URL: {url!r}") from err

    # Validate scheme
    if parsed.scheme not in allowed_schemes:
        raise SSRFBlockedError(
            f"URL scheme {parsed.scheme!r} is not allowed. "
            f"Allowed schemes: {', '.join(sorted(allowed_schemes))}"
        )

    # Extract hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"Invalid webhook URL: no hostname found in {url!r}")

    # Reject URLs with userinfo (credentials) to prevent URL parsing ambiguities
    # e.g. http://user:pass@host/ or http://foo@169.254.169.254%00@public.com/
    if parsed.username is not None or parsed.password is not None:
        raise SSRFBlockedError(
            "Webhook URL must not contain credentials (userinfo). "
            "Remove the user:password@ portion from the URL."
        )

    # Try to parse hostname directly as an IP address
    try:
        addr = ipaddress.ip_address(hostname)
        if _is_ip_blocked(str(addr)):
            raise SSRFBlockedError(
                f"Webhook URL blocked: {hostname!r} resolves to a private/internal "
                f"address. SSRF protection does not allow requests to internal networks."
            )
        return url
    except SSRFBlockedError:
        raise
    except ValueError:
        # Not an IP literal — continue to DNS resolution below
        pass

    # Determine the correct default port based on the scheme
    default_port = 443 if parsed.scheme == "https" else 80
    port = parsed.port or default_port

    # Resolve hostname via DNS and check all returned addresses
    # TODO: socket.getaddrinfo() is blocking I/O — in async code paths
    # (PostgreSQL, MongoDB) consider using loop.getaddrinfo() or run_in_executor.
    try:
        addr_infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as err:
        raise SSRFBlockedError(
            f"Webhook URL blocked: unable to resolve hostname {hostname!r}"
        ) from err

    if not addr_infos:
        raise SSRFBlockedError(
            f"Webhook URL blocked: hostname {hostname!r} did not resolve to any address"
        )

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip_str = str(sockaddr[0])
        if _is_ip_blocked(ip_str):
            raise SSRFBlockedError(
                f"Webhook URL blocked: {hostname!r} resolves to private/internal "
                f"address {ip_str!r}. SSRF protection does not allow requests to "
                f"internal networks."
            )

    return url


def sanitize_string(
    value: str,
    max_length: int | None = None,
    allow_newlines: bool = True,
    strip_whitespace: bool = True,
) -> str:
    """Sanitize a string input with various options.

    Args:
        value: The string to sanitize.
        max_length: Maximum allowed length (truncates if exceeded).
        allow_newlines: Whether to preserve newlines.
        strip_whitespace: Whether to strip leading/trailing whitespace.

    Returns:
        Sanitized string.
    """
    if not value:
        return ""

    # Strip null bytes and other control characters (except newlines if allowed)
    if allow_newlines:
        value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
    else:
        value = re.sub(r"[\x00-\x1f\x7f]", "", value)

    # Strip whitespace if requested
    if strip_whitespace:
        value = value.strip()

    # Truncate if needed
    if max_length is not None and len(value) > max_length:
        value = value[:max_length]

    return value


def sanitize_email(email: str) -> str:
    """Basic email sanitization.

    Note: For proper email validation, use Pydantic's EmailStr type.
    This function only performs basic cleaning.

    Args:
        email: The email address to sanitize.

    Returns:
        Lowercased, stripped email.
    """
    if not email:
        return ""

    return email.strip().lower()


T = TypeVar("T", int, float)


def sanitize_numeric(
    value: str | int | float,
    value_type: type[T],
    min_value: T | None = None,
    max_value: T | None = None,
    default: T | None = None,
) -> T | None:
    """Sanitize and validate a numeric value.

    Args:
        value: The value to sanitize (can be string or numeric).
        value_type: The expected type (int or float).
        min_value: Minimum allowed value.
        max_value: Maximum allowed value.
        default: Default value if conversion fails.

    Returns:
        The sanitized numeric value, or default if invalid.

    Example:
        >>> sanitize_numeric("100", int, min_value=0, max_value=1000)
        100
        >>> sanitize_numeric("abc", int, default=0)
        0
    """
    try:
        result = value_type(value)

        if min_value is not None and result < min_value:
            result = min_value
        if max_value is not None and result > max_value:
            result = max_value

        return result
    except (ValueError, TypeError):
        return default


def escape_sql_like(pattern: str, escape_char: str = "\\") -> str:
    """Escape special characters in a LIKE pattern.

    Use this when building LIKE queries with user input.

    Args:
        pattern: The pattern to escape.
        escape_char: The escape character to use.

    Returns:
        Escaped pattern safe for use in LIKE queries.

    Example:
        >>> escape_sql_like("100%")
        "100\\%"
        >>> escape_sql_like("under_score")
        "under\\_score"
    """
    # Escape the escape character first, then special chars
    pattern = pattern.replace(escape_char, escape_char + escape_char)
    pattern = pattern.replace("%", escape_char + "%")
    pattern = pattern.replace("_", escape_char + "_")
    return pattern
