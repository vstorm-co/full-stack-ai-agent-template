"""Tests for security module."""

from datetime import timedelta

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
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
