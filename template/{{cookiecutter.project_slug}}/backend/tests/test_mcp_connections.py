"""Tests for MCP connections: agents/mcp toolset building + the service layer."""

import contextlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from mcp.shared.auth import OAuthToken

from app.agents import mcp_oauth
from app.agents.mcp import (
    McpServerSpec,
    McpToolInfo,
    _make_toolset,
    _mcp_transport,
    _tool_prefix,
    build_mcp_toolsets,
    static_server_specs,
)
from app.agents.mcp_oauth import McpOAuthPayload
from app.core.config import McpServerConfig, settings
from app.core.crypto import decrypt_value, encrypt_value
from app.core.exceptions import NotFoundError
from app.core.sanitize import SSRFBlockedError
from app.db.models.mcp_connection import McpConnection
from app.schemas.mcp_connection import (
    McpConnectionCreate,
    McpConnectionRead,
    McpConnectionUpdate,
)
from app.services import mcp_connection as mcp_connection_service
from app.services.mcp_connection import (
    McpConnectionService,
    _apply_token,
    _resolve_auth_headers,
)


@contextlib.asynccontextmanager
async def _acm(value):
    """Minimal async context manager yielding *value* (fakes a transport client)."""
    yield value


def _connection(**overrides) -> McpConnection:
    defaults: dict = {
        "id": uuid4(),
        "user_id": uuid4(),
        "name": "github",
        "url": "https://example.com/mcp",
        "auth_token": None,
        "allowed_tools": None,
        "is_enabled": True,
        "auth_type": "bearer",
        "oauth_state": None,
        "oauth_payload": None,
        "last_status": None,
        "last_error": None,
        "last_checked_at": None,
        "created_at": datetime.now(UTC),
        "updated_at": None,
    }
    defaults.update(overrides)
    conn = McpConnection()
    for key, value in defaults.items():
        setattr(conn, key, value)
    return conn


class TestToolPrefix:
    def test_hyphens_become_underscores(self):
        assert _tool_prefix("github-work") == "github_work"

    def test_uppercase_and_specials_are_sanitized(self):
        assert _tool_prefix("My Server!") == "my_server"

    def test_empty_falls_back(self):
        assert _tool_prefix("!!!") == "mcp"


class TestTransportSelection:
    """`_mcp_transport` must pick SSE vs streamable HTTP from the URL alone."""

    @pytest.mark.anyio
    async def test_sse_url_uses_sse_client(self, monkeypatch):
        calls: list = []
        import mcp.client.sse as sse_mod

        def sse_client(url, headers=None):
            calls.append(("sse", url, headers))
            return _acm(("sse-read", "sse-write"))

        monkeypatch.setattr(sse_mod, "sse_client", sse_client)
        async with _mcp_transport("https://mcp.atlassian.com/v1/sse", {"h": "1"}) as (r, w):
            assert (r, w) == ("sse-read", "sse-write")
        assert calls == [("sse", "https://mcp.atlassian.com/v1/sse", {"h": "1"})]

    @pytest.mark.anyio
    async def test_http_url_uses_streamable_client(self, monkeypatch):
        calls: list = []
        import mcp.client.streamable_http as http_mod

        def streamablehttp_client(url, headers=None):
            calls.append(("http", url, headers))
            return _acm(("http-read", "http-write", lambda: None))

        monkeypatch.setattr(http_mod, "streamablehttp_client", streamablehttp_client)
        async with _mcp_transport("https://example.com/mcp", None) as (r, w):
            assert (r, w) == ("http-read", "http-write")
        assert calls == [("http", "https://example.com/mcp", None)]


class TestMakeToolset:
    def test_without_allowlist_returns_prefixed_server(self):
        from pydantic_ai.mcp import MCPToolset
        from pydantic_ai.toolsets import PrefixedToolset

        spec = McpServerSpec(name="github-work", url="https://example.com/mcp")
        toolset = _make_toolset(spec)
        assert isinstance(toolset, PrefixedToolset)
        assert toolset.prefix == "github_work"
        assert isinstance(toolset.wrapped, MCPToolset)

    def test_with_allowlist_filters_before_prefixing(self):
        from pydantic_ai.toolsets import FilteredToolset, PrefixedToolset

        spec = McpServerSpec(
            name="github",
            url="https://example.com/mcp",
            allowed_tools=["search_issues"],
        )
        toolset = _make_toolset(spec)
        assert isinstance(toolset, PrefixedToolset)
        filtered = toolset.wrapped
        assert isinstance(filtered, FilteredToolset)
        # The filter runs before prefixing → unprefixed names.
        allowed_tool = MagicMock()
        allowed_tool.name = "search_issues"
        blocked_tool = MagicMock()
        blocked_tool.name = "delete_repo"
        assert filtered.filter_func(None, allowed_tool) is True
        assert filtered.filter_func(None, blocked_tool) is False


class TestBuildMcpToolsets:
    @pytest.mark.anyio
    async def test_empty_specs_no_probing(self):
        assert await build_mcp_toolsets([]) == []

    @pytest.mark.anyio
    async def test_unreachable_server_is_skipped(self, monkeypatch):
        async def failing_probe(url, headers=None, timeout=None):
            raise TimeoutError("no route")

        monkeypatch.setattr("app.agents.mcp.probe_mcp_server", failing_probe)
        specs = [McpServerSpec(name="dead", url="https://example.com/mcp")]
        assert await build_mcp_toolsets(specs) == []

    @pytest.mark.anyio
    async def test_reachable_server_yields_toolset(self, monkeypatch):
        async def ok_probe(url, headers=None, timeout=None):
            return [McpToolInfo(name="t", description="")]

        monkeypatch.setattr("app.agents.mcp.probe_mcp_server", ok_probe)
        specs = [McpServerSpec(name="live", url="https://example.com/mcp")]
        toolsets = await build_mcp_toolsets(specs)
        assert len(toolsets) == 1


class TestStaticServerSpecs:
    def test_maps_settings_entries(self, monkeypatch):
        monkeypatch.setattr(
            settings,
            "MCP_SERVERS",
            [
                McpServerConfig(
                    name="github",
                    url="https://example.com/mcp",
                    headers={"Authorization": "Bearer x"},
                    allowed_tools=["search"],
                )
            ],
        )
        specs = static_server_specs()
        assert specs == [
            McpServerSpec(
                name="github",
                url="https://example.com/mcp",
                headers={"Authorization": "Bearer x"},
                allowed_tools=["search"],
            )
        ]


class TestAuthHeaders:
    @pytest.mark.anyio
    async def test_no_token_no_headers(self):
        assert await _resolve_auth_headers(AsyncMock(), _connection()) == {}

    @pytest.mark.anyio
    async def test_token_is_decrypted_into_bearer_header(self):
        encrypted = encrypt_value("secret-token", settings.SECRET_KEY)
        conn = _connection(auth_token=encrypted)
        assert await _resolve_auth_headers(AsyncMock(), conn) == {
            "Authorization": "Bearer secret-token"
        }

    @pytest.mark.anyio
    async def test_undecryptable_token_yields_none(self):
        conn = _connection(auth_token="enc:not-valid-ciphertext")
        assert await _resolve_auth_headers(AsyncMock(), conn) is None


def _oauth_connection(payload: McpOAuthPayload, **overrides) -> McpConnection:
    """A connection carrying an encrypted OAuth payload."""
    enc = encrypt_value(payload.model_dump_json(), settings.SECRET_KEY)
    return _connection(auth_type="oauth", oauth_payload=enc, **overrides)


def _base_payload(**overrides) -> McpOAuthPayload:
    data = {
        "authorization_endpoint": "https://srv/authorize",
        "token_endpoint": "https://srv/token",
        "client_id": "cid",
        "client_secret": "csecret",
        "scope": "read",
        "resource": "https://srv/mcp",
        "redirect_uri": "https://app/api/me/mcp-connections/oauth/callback",
    }
    data.update(overrides)
    return McpOAuthPayload(**data)


class TestOAuthTokens:
    def test_apply_token_folds_grant(self):
        payload = _base_payload(code_verifier="verifier", refresh_token="old-refresh")
        token = OAuthToken(access_token="AT", refresh_token="new-refresh", expires_in=3600)
        result = _apply_token(payload, token)
        assert result.access_token == "AT"
        assert result.refresh_token == "new-refresh"
        assert result.code_verifier is None  # cleared once tokens arrive
        assert (
            result.expires_at is not None and result.expires_at > mcp_oauth.TOKEN_EXPIRY_SKEW_SECS
        )

    def test_apply_token_keeps_refresh_when_omitted(self):
        payload = _base_payload(refresh_token="keep-me")
        token = OAuthToken(access_token="AT", expires_in=None)
        result = _apply_token(payload, token)
        assert result.refresh_token == "keep-me"
        assert result.expires_at is None

    @pytest.mark.anyio
    async def test_unauthorized_oauth_yields_none(self):
        # No access_token yet (consent not completed).
        conn = _oauth_connection(_base_payload(code_verifier="v"), oauth_state="state123")
        assert await _resolve_auth_headers(AsyncMock(), conn) is None

    @pytest.mark.anyio
    async def test_valid_oauth_token_becomes_bearer(self):
        payload = _base_payload(access_token="live-token", expires_at=None)
        conn = _oauth_connection(payload)
        assert await _resolve_auth_headers(AsyncMock(), conn) == {
            "Authorization": "Bearer live-token"
        }

    @pytest.mark.anyio
    async def test_expired_token_is_refreshed_and_persisted(self, monkeypatch):
        payload = _base_payload(
            access_token="stale", refresh_token="rt", expires_at=0.0
        )  # long expired
        conn = _oauth_connection(payload)
        fresh = OAuthToken(access_token="fresh-token", refresh_token="rt2", expires_in=3600)
        refresh_mock = AsyncMock(return_value=fresh)
        monkeypatch.setattr(mcp_oauth, "refresh_tokens", refresh_mock)
        update_mock = AsyncMock()
        monkeypatch.setattr(mcp_connection_service.mcp_connection_repo, "update", update_mock)

        headers = await _resolve_auth_headers(AsyncMock(), conn)
        assert headers == {"Authorization": "Bearer fresh-token"}
        refresh_mock.assert_awaited_once()
        # The refreshed token was persisted back (re-encrypted).
        stored = update_mock.call_args.kwargs["update_data"]["oauth_payload"]
        assert (
            McpOAuthPayload.model_validate_json(
                decrypt_value(stored, settings.SECRET_KEY)
            ).access_token
            == "fresh-token"
        )

    @pytest.mark.anyio
    async def test_expired_token_without_refresh_yields_none(self):
        payload = _base_payload(access_token="stale", refresh_token=None, expires_at=0.0)
        conn = _oauth_connection(payload)
        assert await _resolve_auth_headers(AsyncMock(), conn) is None


class TestMcpConnectionService:
    @pytest.fixture
    def service(self):
        return McpConnectionService(db=AsyncMock())

    @pytest.fixture
    def repo(self, monkeypatch):
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock()
        mock_repo.get_by_name = AsyncMock(return_value=None)
        mock_repo.list_for_user = AsyncMock(return_value=([], 0))
        mock_repo.create = AsyncMock()
        mock_repo.update = AsyncMock()
        mock_repo.delete = AsyncMock()
        monkeypatch.setattr(mcp_connection_service, "mcp_connection_repo", mock_repo)
        return mock_repo

    @pytest.mark.anyio
    async def test_create_blocks_internal_urls(self, service, repo):
        data = McpConnectionCreate(name="internal", url="http://127.0.0.1:8000/mcp")
        with pytest.raises(SSRFBlockedError):
            await service.create(user_id=uuid4(), data=data)
        repo.create.assert_not_called()

    @pytest.mark.anyio
    async def test_create_encrypts_token(self, service, repo, monkeypatch):
        monkeypatch.setattr(mcp_connection_service, "validate_webhook_url", lambda url: url)
        data = McpConnectionCreate(
            name="github", url="https://example.com/mcp", auth_token="secret"
        )
        await service.create(user_id=uuid4(), data=data)

        stored = repo.create.call_args.kwargs["auth_token"]
        assert stored != "secret"
        assert decrypt_value(stored, settings.SECRET_KEY) == "secret"

    @pytest.mark.anyio
    async def test_create_without_token_stores_none(self, service, repo, monkeypatch):
        monkeypatch.setattr(mcp_connection_service, "validate_webhook_url", lambda url: url)
        data = McpConnectionCreate(name="github", url="https://example.com/mcp")
        await service.create(user_id=uuid4(), data=data)
        assert repo.create.call_args.kwargs["auth_token"] is None

    @pytest.mark.anyio
    async def test_update_empty_token_clears_it(self, service, repo):
        user_id = uuid4()
        conn = _connection(user_id=user_id, auth_token=encrypt_value("old", settings.SECRET_KEY))
        repo.get_by_id.return_value = conn

        await service.update(
            user_id=user_id,
            connection_id=conn.id,
            data=McpConnectionUpdate(auth_token=""),
        )

        update_data = repo.update.call_args.kwargs["update_data"]
        assert update_data["auth_token"] is None
        # Credentials changed → stale check result is reset.
        assert update_data["last_status"] is None

    @pytest.mark.anyio
    async def test_update_url_revalidates_ssrf(self, service, repo):
        user_id = uuid4()
        conn = _connection(user_id=user_id)
        repo.get_by_id.return_value = conn

        with pytest.raises(SSRFBlockedError):
            await service.update(
                user_id=user_id,
                connection_id=conn.id,
                data=McpConnectionUpdate(url="http://169.254.169.254/mcp"),
            )

    @pytest.mark.anyio
    async def test_other_users_connection_is_not_found(self, service, repo):
        repo.get_by_id.return_value = _connection(user_id=uuid4())
        with pytest.raises(NotFoundError):
            await service.delete(user_id=uuid4(), connection_id=uuid4())

    @pytest.mark.anyio
    async def test_test_records_failure(self, service, repo, monkeypatch):
        user_id = uuid4()
        conn = _connection(user_id=user_id)
        repo.get_by_id.return_value = conn
        repo.update.return_value = conn

        async def failing_probe(url, headers=None, timeout=None):
            raise TimeoutError

        monkeypatch.setattr(mcp_connection_service, "probe_mcp_server", failing_probe)

        _, tools, error = await service.test(user_id=user_id, connection_id=conn.id)

        assert tools == []
        assert error is not None and "timed out" in error
        update_data = repo.update.call_args.kwargs["update_data"]
        assert update_data["last_status"] == "error"

    @pytest.mark.anyio
    async def test_test_records_success_and_returns_tools(self, service, repo, monkeypatch):
        user_id = uuid4()
        conn = _connection(user_id=user_id)
        repo.get_by_id.return_value = conn
        repo.update.return_value = conn

        async def ok_probe(url, headers=None, timeout=None):
            return [McpToolInfo(name="search", description="Search things")]

        monkeypatch.setattr(mcp_connection_service, "probe_mcp_server", ok_probe)

        _, tools, error = await service.test(user_id=user_id, connection_id=conn.id)

        assert error is None
        assert [t.name for t in tools] == ["search"]
        assert repo.update.call_args.kwargs["update_data"]["last_status"] == "ok"

    @pytest.mark.anyio
    async def test_oauth_start_registers_and_persists_pending(self, service, repo, monkeypatch):
        monkeypatch.setattr(mcp_connection_service, "validate_webhook_url", lambda url: url)
        discovered = mcp_oauth.DiscoveredServer(
            authorization_endpoint="https://srv/authorize",
            token_endpoint="https://srv/token",
            registration_endpoint="https://srv/register",
            resource="https://srv/mcp",
            scope="read write",
            metadata=MagicMock(),
        )
        monkeypatch.setattr(mcp_oauth, "discover", AsyncMock(return_value=discovered))
        monkeypatch.setattr(mcp_oauth, "register_client", AsyncMock(return_value=("cid", "csec")))

        url = await service.oauth_start(user_id=uuid4(), name="linear", url="https://srv/mcp")

        assert url.startswith("https://srv/authorize?")
        assert "code_challenge=" in url and "state=" in url
        kwargs = repo.create.call_args.kwargs
        assert kwargs["auth_type"] == "oauth"
        assert kwargs["oauth_state"] and kwargs["oauth_payload"]
        # The persisted payload holds the PKCE verifier but no tokens yet.
        payload = McpOAuthPayload.model_validate_json(
            decrypt_value(kwargs["oauth_payload"], settings.SECRET_KEY)
        )
        assert payload.code_verifier and payload.access_token is None
        assert payload.client_id == "cid"

    @pytest.mark.anyio
    async def test_oauth_start_rejects_internal_urls(self, service, repo):
        with pytest.raises(SSRFBlockedError):
            await service.oauth_start(
                user_id=uuid4(), name="evil", url="http://169.254.169.254/mcp"
            )
        repo.create.assert_not_called()

    @pytest.mark.anyio
    async def test_oauth_callback_exchanges_and_clears_state(self, service, repo, monkeypatch):
        pending = _oauth_connection(
            _base_payload(code_verifier="verifier"), oauth_state="state-xyz"
        )
        repo.get_by_oauth_state = AsyncMock(return_value=pending)
        repo.update.return_value = pending
        token = OAuthToken(access_token="AT", refresh_token="RT", expires_in=3600)
        monkeypatch.setattr(mcp_oauth, "exchange_code", AsyncMock(return_value=token))

        await service.oauth_callback(state="state-xyz", code="the-code")

        update_data = repo.update.call_args.kwargs["update_data"]
        assert update_data["oauth_state"] is None  # no longer pending
        assert update_data["last_status"] == "ok"
        payload = McpOAuthPayload.model_validate_json(
            decrypt_value(update_data["oauth_payload"], settings.SECRET_KEY)
        )
        assert payload.access_token == "AT" and payload.refresh_token == "RT"
        assert payload.code_verifier is None

    @pytest.mark.anyio
    async def test_oauth_callback_unknown_state_is_not_found(self, service, repo):
        repo.get_by_oauth_state = AsyncMock(return_value=None)
        with pytest.raises(NotFoundError):
            await service.oauth_callback(state="nope", code="x")


class TestReadSchema:
    def test_token_never_leaves_backend(self):
        conn = _connection(auth_token=encrypt_value("secret", settings.SECRET_KEY))
        read = McpConnectionRead.from_model(conn)
        assert read.has_auth_token is True
        assert "secret" not in read.model_dump_json()

    def test_oauth_authorized_reflects_tokens_and_pending_state(self):
        # Pending (consent not completed): state set → not authorized.
        pending = _oauth_connection(_base_payload(code_verifier="v"), oauth_state="s")
        assert McpConnectionRead.from_model(pending).oauth_authorized is False
        # Completed: tokens present, state cleared → authorized.
        done = _oauth_connection(_base_payload(access_token="AT"), oauth_state=None)
        read = McpConnectionRead.from_model(done)
        assert read.oauth_authorized is True
        assert read.auth_type == "oauth"
        # The encrypted payload (with tokens) never appears in the response.
        assert "AT" not in read.model_dump_json()
