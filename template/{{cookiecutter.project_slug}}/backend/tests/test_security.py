{%- if cookiecutter.use_jwt %}
"""Tests for security module."""

from datetime import timedelta

from app.core.security import (
    create_access_token,
{%- if cookiecutter.enable_email %}
    create_magic_link_token,
    create_password_reset_token,
{%- endif %}
    create_refresh_token,
    get_password_hash,
{%- if cookiecutter.enable_email %}
    password_epoch,
{%- endif %}
    verify_password,
{%- if cookiecutter.enable_email %}
    verify_special_token,
{%- endif %}
    verify_token,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "mysecretpassword"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False


class TestAccessToken:
    """Tests for access token functions."""

    def test_create_access_token(self):
        """Test creating access token."""
        subject = "user123"
        token = create_access_token(subject)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expires_delta(self):
        """Test creating access token with custom expiration."""
        subject = "user123"
        expires = timedelta(hours=2)
        token = create_access_token(subject, expires_delta=expires)

        assert isinstance(token, str)
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == subject
        assert payload["type"] == "access"

    def test_verify_access_token(self):
        """Test verifying access token."""
        subject = "user123"
        token = create_access_token(subject)
        payload = verify_token(token)

        assert payload is not None
        assert payload["sub"] == subject
        assert payload["type"] == "access"

    def test_verify_invalid_token(self):
        """Test verifying invalid token."""
        payload = verify_token("invalid.token.here")

        assert payload is None

    def test_verify_expired_token(self):
        """Test verifying expired token."""
        subject = "user123"
        # Create token that expires immediately
        token = create_access_token(subject, expires_delta=timedelta(seconds=-1))
        payload = verify_token(token)

        assert payload is None


class TestRefreshToken:
    """Tests for refresh token functions."""

    def test_create_refresh_token(self):
        """Test creating refresh token."""
        subject = "user123"
        token = create_refresh_token(subject)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token_with_expires_delta(self):
        """Test creating refresh token with custom expiration."""
        subject = "user123"
        expires = timedelta(days=7)
        token = create_refresh_token(subject, expires_delta=expires)

        assert isinstance(token, str)
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == subject
        assert payload["type"] == "refresh"

    def test_verify_refresh_token(self):
        """Test verifying refresh token."""
        subject = "user123"
        token = create_refresh_token(subject)
        payload = verify_token(token)

        assert payload is not None
        assert payload["sub"] == subject
        assert payload["type"] == "refresh"

{%- if cookiecutter.enable_email %}


class TestSingleUseTokens:
    """A JWT cannot be revoked, so single use has to be encoded in a claim.

    These tests pin the *mechanism*; the service-level checks that act on it
    live in tests/test_services.py.
    """

    def test_reset_token_is_bound_to_the_password_it_was_issued_against(self):
        """The pwe claim changes with the hash, which is what expires the link."""
        old_hash = get_password_hash("old-password")
        token = create_password_reset_token("user123", current_password_hash=old_hash)

        payload = verify_special_token(token, expected_type="password_reset")
        assert payload is not None
        assert payload["pwe"] == password_epoch(old_hash)

        # After the reset the hash is different, so the token no longer matches.
        new_hash = get_password_hash("new-password")
        assert payload["pwe"] != password_epoch(new_hash)

    def test_reset_token_rejects_a_wrong_type(self):
        """A reset token must not be usable where another type is expected."""
        token = create_password_reset_token("user123", current_password_hash="hash")
        assert verify_special_token(token, expected_type="magic_link") is None

    def test_magic_link_token_carries_the_epoch_it_was_issued_at(self):
        """Redeeming bumps the epoch, which is what invalidates the link."""
        token = create_magic_link_token("user123", magic_link_epoch=3)

        payload = verify_special_token(token, expected_type="magic_link")
        assert payload is not None
        assert payload["mle"] == 3
{%- endif %}
{%- endif %}
