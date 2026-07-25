"""Tests for MCP connections: agents/mcp toolset building + the service layer."""

import contextlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from mcp.shared.auth import OAuthToken
from pydantic import ValidationError

from app.agents import mcp_oauth
from app.agents.mcp import (
    McpProbeError,
    McpServerSpec,
    McpToolInfo,
    _make_toolset,
    _mcp_transport,
    _tool_prefix,
    build_mcp_toolsets,
    probe_mcp_server,
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


def _allow_any_url(monkeypatch) -> None:
    """Skip SSRF validation for tests that are about something else (it resolves
    DNS, so it must not run against made-up hostnames)."""

    async def _passthrough(url: str) -> str:
        return url

    monkeypatch.setattr(mcp_connection_service, "validate_mcp_url", _passthrough)


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
        "oauth_pending_payload": None,
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

    @pytest.mark.anyio
    async def test_colliding_tool_prefix_is_dropped(self, monkeypatch):
        """Two servers sharing a prefix would make pydantic-ai raise on
        duplicate tool names and kill the turn — the later one is skipped."""
        probed: list[str] = []

        async def ok_probe(url, headers=None, timeout=None):
            probed.append(url)
            return [McpToolInfo(name="t", description="")]

        monkeypatch.setattr("app.agents.mcp.probe_mcp_server", ok_probe)
        specs = [
            # Workspace server first — it wins over the user's connection.
            McpServerSpec(name="github", url="https://workspace.example/mcp"),
            McpServerSpec(name="GitHub", url="https://user.example/mcp"),
        ]
        toolsets = await build_mcp_toolsets(specs)
        assert len(toolsets) == 1
        assert probed == ["https://workspace.example/mcp"]


class TestProbeErrors:
    """A dead server must never abort the turn — including when the failure
    arrives as an exception group out of the anyio task group."""

    @pytest.mark.anyio
    async def test_exception_group_becomes_probe_error(self, monkeypatch):
        @contextlib.asynccontextmanager
        async def failing_transport(url, headers):
            raise BaseExceptionGroup("unhandled errors in a TaskGroup", [ConnectionError("boom")])
            yield  # pragma: no cover

        monkeypatch.setattr("app.agents.mcp._mcp_transport", failing_transport)
        # McpProbeError is an Exception, so `except Exception` callers catch it.
        with pytest.raises(McpProbeError, match="boom"):
            await probe_mcp_server("https://example.com/mcp")

    @pytest.mark.anyio
    async def test_cancellation_is_not_swallowed(self, monkeypatch):
        import asyncio

        @contextlib.asynccontextmanager
        async def cancelled_transport(url, headers):
            raise BaseExceptionGroup("cancelled", [asyncio.CancelledError()])
            yield  # pragma: no cover

        monkeypatch.setattr("app.agents.mcp._mcp_transport", cancelled_transport)
        with pytest.raises(BaseExceptionGroup):
            await probe_mcp_server("https://example.com/mcp")


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

    def test_name_must_be_a_slug(self):
        """The name becomes the tool prefix, so anything outside the slug rule
        would silently collapse two servers onto one prefix."""
        with pytest.raises(ValidationError):
            McpServerConfig(name="My Server!", url="https://example.com/mcp")

    def test_duplicate_names_are_rejected_at_startup(self):
        """Two servers with one name means one of them never reaches a chat
        turn. Fail at boot rather than at runtime, where nobody would see it."""
        with pytest.raises(ValidationError, match="duplicate server names"):
            type(settings)(
                MCP_SERVERS=[
                    McpServerConfig(name="github", url="https://a.example/mcp"),
                    McpServerConfig(name="github", url="https://b.example/mcp"),
                ]
            )


class TestToolsetsForUser:
    @pytest.mark.anyio
    async def test_no_user_still_gets_workspace_servers(self, monkeypatch):
        """Channel traffic that isn't mapped to an account: the deployment's
        MCP_SERVERS still apply, and no database session is opened for the
        per-user connections that can't exist."""

        def _no_db():  # pragma: no cover - only called if the guard regresses
            raise AssertionError("build_toolsets_for_user(None) must not open a session")

        monkeypatch.setattr(
            mcp_connection_service,
            "static_server_specs",
            lambda: [McpServerSpec(name="workspace", url="https://example.com/mcp")],
        )
        monkeypatch.setattr(mcp_connection_service, "get_db_context", _no_db)
        seen: list[list[McpServerSpec]] = []

        async def fake_build(specs: list[McpServerSpec]) -> list[str]:
            seen.append(specs)
            return ["toolset"]

        monkeypatch.setattr(mcp_connection_service, "build_mcp_toolsets", fake_build)

        assert await mcp_connection_service.build_toolsets_for_user(None) == ["toolset"]
        assert [spec.name for spec in seen[0]] == ["workspace"]


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
        "server_url": "https://srv/mcp",
        "started_at": datetime.now(UTC).timestamp(),
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
        lock_mock = AsyncMock(return_value=conn)
        monkeypatch.setattr(
            mcp_connection_service.mcp_connection_repo, "get_by_id_for_update", lock_mock
        )
        update_mock = AsyncMock()
        monkeypatch.setattr(mcp_connection_service.mcp_connection_repo, "update", update_mock)

        headers = await _resolve_auth_headers(AsyncMock(), conn)
        assert headers == {"Authorization": "Bearer fresh-token"}
        refresh_mock.assert_awaited_once()
        # The refresh token is only ever spent while holding the row lock.
        lock_mock.assert_awaited_once()
        # The refreshed token was persisted back (re-encrypted).
        stored = update_mock.call_args.kwargs["update_data"]["oauth_payload"]
        assert (
            McpOAuthPayload.model_validate_json(
                decrypt_value(stored, settings.SECRET_KEY)
            ).access_token
            == "fresh-token"
        )

    @pytest.mark.anyio
    async def test_concurrent_turn_reuses_the_token_the_winner_stored(self, monkeypatch):
        """Two turns can hit an expired token at once. The one that loses the
        row lock must re-read the row and use the fresh token, not spend the
        refresh token a second time — providers that rotate it would invalidate
        the winner's copy and quietly kill the connection."""
        stale = _oauth_connection(
            _base_payload(access_token="stale", refresh_token="rt", expires_at=0.0)
        )
        # What the winner committed while we waited on the lock.
        refreshed = _oauth_connection(
            _base_payload(
                access_token="fresh-token",
                refresh_token="rt2",
                expires_at=datetime.now(UTC).timestamp() + 3600,
            )
        )
        refresh_mock = AsyncMock()
        monkeypatch.setattr(mcp_oauth, "refresh_tokens", refresh_mock)
        monkeypatch.setattr(
            mcp_connection_service.mcp_connection_repo,
            "get_by_id_for_update",
            AsyncMock(return_value=refreshed),
        )
        update_mock = AsyncMock()
        monkeypatch.setattr(mcp_connection_service.mcp_connection_repo, "update", update_mock)

        headers = await _resolve_auth_headers(AsyncMock(), stale)

        assert headers == {"Authorization": "Bearer fresh-token"}
        refresh_mock.assert_not_awaited()
        update_mock.assert_not_awaited()

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
        _allow_any_url(monkeypatch)
        data = McpConnectionCreate(
            name="github", url="https://example.com/mcp", auth_token="secret"
        )
        await service.create(user_id=uuid4(), data=data)

        stored = repo.create.call_args.kwargs["auth_token"]
        assert stored != "secret"
        assert decrypt_value(stored, settings.SECRET_KEY) == "secret"

    @pytest.mark.anyio
    async def test_create_without_token_stores_none(self, service, repo, monkeypatch):
        _allow_any_url(monkeypatch)
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
        _allow_any_url(monkeypatch)
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
        assert kwargs["oauth_state"] and kwargs["oauth_pending_payload"]
        # Nothing lands in the live payload until the callback succeeds.
        assert kwargs.get("oauth_payload") is None
        # The persisted payload holds the PKCE verifier but no tokens yet.
        payload = McpOAuthPayload.model_validate_json(
            decrypt_value(kwargs["oauth_pending_payload"], settings.SECRET_KEY)
        )
        assert payload.code_verifier and payload.access_token is None
        assert payload.client_id == "cid"
        # Stamped so the callback can refuse a flow the user never finished.
        assert datetime.now(UTC).timestamp() - payload.started_at < mcp_oauth.FLOW_TTL_SECS

    @pytest.mark.anyio
    async def test_oauth_start_keeps_working_tokens_until_consent(
        self, service, repo, monkeypatch
    ):
        """Re-authorizing must not break the connection if the user closes the
        consent tab — the live tokens (and the URL) stay put until it lands."""
        _allow_any_url(monkeypatch)
        live = _oauth_connection(
            _base_payload(access_token="live-token"), name="linear", url="https://srv/mcp"
        )
        repo.get_by_name.return_value = live
        discovered = mcp_oauth.DiscoveredServer(
            authorization_endpoint="https://srv/authorize",
            token_endpoint="https://srv/token",
            registration_endpoint=None,
            resource="https://other/mcp",
            scope=None,
            metadata=MagicMock(),
        )
        monkeypatch.setattr(mcp_oauth, "discover", AsyncMock(return_value=discovered))
        monkeypatch.setattr(mcp_oauth, "register_client", AsyncMock(return_value=("cid", None)))

        await service.oauth_start(user_id=uuid4(), name="linear", url="https://other/mcp")

        update_data = repo.update.call_args.kwargs["update_data"]
        assert update_data["oauth_pending_payload"]
        assert "oauth_payload" not in update_data  # the working tokens survive
        assert "url" not in update_data  # and so does the URL they belong to

    @pytest.mark.anyio
    async def test_oauth_start_rejects_internal_urls(self, service, repo):
        with pytest.raises(SSRFBlockedError):
            await service.oauth_start(
                user_id=uuid4(), name="evil", url="http://169.254.169.254/mcp"
            )
        repo.create.assert_not_called()

    @pytest.mark.anyio
    async def test_oauth_callback_exchanges_and_clears_state(self, service, repo, monkeypatch):
        pending = _connection(
            auth_type="oauth",
            url="https://srv/mcp",
            oauth_state="state-xyz",
            oauth_pending_payload=encrypt_value(
                _base_payload(
                    code_verifier="verifier", server_url="https://moved/mcp"
                ).model_dump_json(),
                settings.SECRET_KEY,
            ),
        )
        repo.get_by_oauth_state = AsyncMock(return_value=pending)
        repo.update.return_value = pending
        token = OAuthToken(access_token="AT", refresh_token="RT", expires_in=3600)
        monkeypatch.setattr(mcp_oauth, "exchange_code", AsyncMock(return_value=token))

        await service.oauth_callback(state="state-xyz", code="the-code")

        update_data = repo.update.call_args.kwargs["update_data"]
        assert update_data["oauth_state"] is None  # no longer pending
        assert update_data["oauth_pending_payload"] is None
        assert update_data["last_status"] == "ok"
        # The URL the tokens were issued for is applied together with them.
        assert update_data["url"] == "https://moved/mcp"
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

    @pytest.mark.anyio
    async def test_oauth_callback_rejects_an_expired_flow(self, service, repo, monkeypatch):
        """The state token is the only thing authenticating this endpoint, and
        it travels through the provider and the browser's history — a consent
        redirect the user never finished must stop being redeemable."""
        started = datetime.now(UTC).timestamp() - mcp_oauth.FLOW_TTL_SECS - 1
        stale = _connection(
            auth_type="oauth",
            oauth_state="state-old",
            oauth_pending_payload=encrypt_value(
                _base_payload(code_verifier="verifier", started_at=started).model_dump_json(),
                settings.SECRET_KEY,
            ),
        )
        repo.get_by_oauth_state = AsyncMock(return_value=stale)
        exchange_mock = AsyncMock()
        monkeypatch.setattr(mcp_oauth, "exchange_code", exchange_mock)

        with pytest.raises(mcp_oauth.OAuthError, match="expired"):
            await service.oauth_callback(state="state-old", code="the-code")

        exchange_mock.assert_not_awaited()
        repo.update.assert_not_called()

    @pytest.mark.anyio
    async def test_oauth_callback_on_unreadable_payload_asks_to_start_again(self, service, repo):
        """A rotated SECRET_KEY makes the pending payload undecryptable. That's
        a dead flow the user restarts, not a 500."""
        stale = _connection(
            auth_type="oauth",
            oauth_state="state-broken",
            oauth_pending_payload="enc:not-valid-ciphertext",
        )
        repo.get_by_oauth_state = AsyncMock(return_value=stale)

        with pytest.raises(mcp_oauth.OAuthError, match="no longer valid"):
            await service.oauth_callback(state="state-broken", code="the-code")

    @pytest.mark.anyio
    async def test_update_url_drops_oauth_tokens(self, service, repo, monkeypatch):
        """Tokens are bound to the host they were issued for — moving the URL
        must not send a provider's access token to a different server."""
        _allow_any_url(monkeypatch)
        user_id = uuid4()
        conn = _oauth_connection(
            _base_payload(access_token="AT"), user_id=user_id, oauth_state=None
        )
        repo.get_by_id.return_value = conn

        await service.update(
            user_id=user_id,
            connection_id=conn.id,
            data=McpConnectionUpdate(url="https://elsewhere.example/mcp"),
        )

        update_data = repo.update.call_args.kwargs["update_data"]
        assert update_data["oauth_payload"] is None
        assert update_data["oauth_pending_payload"] is None
        assert update_data["oauth_state"] is None


class TestOAuthRequestSafety:
    """Discovery lets the remote server choose most of the URLs we call, so
    every hop — redirects included — goes through the SSRF policy.

    IP literals are used throughout: the validator short-circuits on those, so
    the tests never touch DNS.
    """

    @staticmethod
    def _client(handler) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=False
        )

    @pytest.mark.anyio
    async def test_redirect_to_internal_host_is_blocked(self):
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(str(request.url))
            return httpx.Response(
                302, headers={"Location": "http://169.254.169.254/latest/meta-data/"}
            )

        async with self._client(handler) as client:
            request = client.build_request("GET", "https://93.184.216.34/.well-known/x")
            with pytest.raises(mcp_oauth.OAuthError):
                await mcp_oauth._send(client, request)

        # The first hop was allowed; the metadata address was never requested.
        assert seen == ["https://93.184.216.34/.well-known/x"]

    @pytest.mark.anyio
    async def test_redirect_to_public_host_is_followed(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "93.184.216.34":
                return httpx.Response(302, headers={"Location": "https://93.184.216.35/moved"})
            return httpx.Response(200, text="ok")

        async with self._client(handler) as client:
            request = client.build_request("GET", "https://93.184.216.34/start")
            response = await mcp_oauth._send(client, request)

        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_redirect_loop_gives_up(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(302, headers={"Location": "https://93.184.216.34/loop"})

        async with self._client(handler) as client:
            request = client.build_request("GET", "https://93.184.216.34/loop")
            with pytest.raises(mcp_oauth.OAuthError, match="redirects"):
                await mcp_oauth._send(client, request)

    @pytest.mark.anyio
    async def test_token_endpoint_body_is_not_surfaced(self, monkeypatch):
        """The OAuth error text reaches the user's browser — an internal
        service's reply must not ride along with it."""

        async def fake_send(client, request):
            return httpx.Response(500, text="redis: NOAUTH Authentication required", request=request)

        monkeypatch.setattr(mcp_oauth, "_send", fake_send)
        with pytest.raises(mcp_oauth.OAuthError) as exc_info:
            await mcp_oauth._token_request("https://93.184.216.34/token", {"grant_type": "x"})

        assert "redis" not in str(exc_info.value)
        assert "500" in str(exc_info.value)


class TestReadSchema:
    def test_token_never_leaves_backend(self):
        conn = _connection(auth_token=encrypt_value("secret", settings.SECRET_KEY))
        read = McpConnectionRead.from_model(conn)
        assert read.has_auth_token is True
        assert "secret" not in read.model_dump_json()

    def test_oauth_authorized_reflects_tokens_and_pending_state(self):
        # First-time consent not completed: only a pending flow → not authorized.
        pending = _connection(
            auth_type="oauth",
            oauth_state="s",
            oauth_pending_payload=encrypt_value(
                _base_payload(code_verifier="v").model_dump_json(), settings.SECRET_KEY
            ),
        )
        assert McpConnectionRead.from_model(pending).oauth_authorized is False
        # Completed: tokens present → authorized.
        done = _oauth_connection(_base_payload(access_token="AT"), oauth_state=None)
        read = McpConnectionRead.from_model(done)
        assert read.oauth_authorized is True
        assert read.auth_type == "oauth"
        # The encrypted payload (with tokens) never appears in the response.
        assert "AT" not in read.model_dump_json()

    def test_reauthorizing_a_live_connection_still_reads_as_connected(self):
        """A re-authorization in flight must not flash "not connected" in the UI
        for a connection whose tokens still work."""
        conn = _oauth_connection(
            _base_payload(access_token="AT"),
            oauth_state="new-flow",
            oauth_pending_payload=encrypt_value(
                _base_payload(code_verifier="v").model_dump_json(), settings.SECRET_KEY
            ),
        )
        assert McpConnectionRead.from_model(conn).oauth_authorized is True
