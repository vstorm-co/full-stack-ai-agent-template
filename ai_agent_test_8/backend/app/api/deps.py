"""API dependencies.

Dependency injection factories for services, repositories, and authentication.
"""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from typing import Annotated

from fastapi import Depends
from fastapi import Header
from fastapi import WebSocket, Cookie, WebSocketException
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session

DBSession = Annotated[AsyncSession, Depends(get_db_session)]
from uuid import UUID

from app.db.session import get_db_context
from fastapi import Request

from app.clients.redis import RedisClient


async def get_redis(request: Request) -> RedisClient:
    """Get Redis client from lifespan state."""
    return request.state.redis  # type: ignore[no-any-return]


Redis = Annotated[RedisClient, Depends(get_redis)]


from app.services.user import UserService
from app.services.session import SessionService
from app.services.conversation import ConversationService
from app.services.conversation_share import ConversationShareService


def get_user_service(db: DBSession) -> UserService:
    """Create UserService instance with database session."""
    return UserService(db)


def get_session_service(db: DBSession) -> SessionService:
    """Create SessionService instance with database session."""
    return SessionService(db)


UserSvc = Annotated[UserService, Depends(get_user_service)]
SessionSvc = Annotated[SessionService, Depends(get_session_service)]


def get_conversation_service(db: DBSession) -> ConversationService:
    """Create ConversationService instance with database session."""
    return ConversationService(db)


ConversationSvc = Annotated[ConversationService, Depends(get_conversation_service)]


def get_conversation_share_service(db: DBSession) -> ConversationShareService:
    """Create ConversationShareService instance with database session."""
    return ConversationShareService(db)


ConversationShareSvc = Annotated[ConversationShareService, Depends(get_conversation_share_service)]
from app.services.channel_bot import ChannelBotService


def get_channel_bot_service(db: DBSession) -> ChannelBotService:
    """Create ChannelBotService instance with database session."""
    return ChannelBotService(db)


ChannelBotSvc = Annotated[ChannelBotService, Depends(get_channel_bot_service)]

from app.services.message_rating import MessageRatingService


def get_rating_service(db: DBSession) -> MessageRatingService:
    """Create MessageRatingService instance with database session."""
    return MessageRatingService(db)


MessageRatingSvc = Annotated[MessageRatingService, Depends(get_rating_service)]
from app.services.rag_document import RAGDocumentService
from app.services.rag_sync import RAGSyncService
from app.services.sync_source import SyncSourceService


def get_rag_document_service(db: DBSession) -> RAGDocumentService:
    """Create RAGDocumentService instance with database session."""
    return RAGDocumentService(db)


def get_rag_sync_service(db: DBSession) -> RAGSyncService:
    """Create RAGSyncService instance with database session."""
    return RAGSyncService(db)


def get_sync_source_service(db: DBSession) -> SyncSourceService:
    """Create SyncSourceService instance with database session."""
    return SyncSourceService(db)


RAGDocumentSvc = Annotated[RAGDocumentService, Depends(get_rag_document_service)]
RAGSyncSvc = Annotated[RAGSyncService, Depends(get_rag_sync_service)]
SyncSourceSvc = Annotated[SyncSourceService, Depends(get_sync_source_service)]
from app.services.rag_status import RAGStatusService


def get_rag_status_service() -> RAGStatusService:
    """Create RAGStatusService instance (no DB)."""
    return RAGStatusService()


RAGStatusSvc = Annotated[RAGStatusService, Depends(get_rag_status_service)]
from app.services.knowledge_base import KnowledgeBaseService


def get_knowledge_base_service(db: DBSession) -> KnowledgeBaseService:
    """Create KnowledgeBaseService instance with database session."""
    return KnowledgeBaseService(db)


KnowledgeBaseSvc = Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)]
from app.services.file_upload import FileUploadService


def get_file_upload_service(db: DBSession) -> FileUploadService:
    """Create FileUploadService instance with database session."""
    return FileUploadService(db)


FileUploadSvc = Annotated[FileUploadService, Depends(get_file_upload_service)]
from app.repositories import member_repo, organization_repo
from app.services.organization import OrganizationService
from app.services.member import MemberService
from app.services.invitation import InvitationService


def get_organization_service(db: DBSession) -> OrganizationService:
    """Create OrganizationService instance with database session."""
    return OrganizationService(db)


def get_member_service(db: DBSession) -> MemberService:
    """Create MemberService instance with database session."""
    return MemberService(db)


def get_invitation_service(db: DBSession) -> InvitationService:
    """Create InvitationService instance with database session."""
    return InvitationService(db)


OrganizationSvc = Annotated[OrganizationService, Depends(get_organization_service)]
MemberSvc = Annotated[MemberService, Depends(get_member_service)]
InvitationSvc = Annotated[InvitationService, Depends(get_invitation_service)]
from app.services.billing import BillingService


def get_billing_service(db: DBSession) -> BillingService:
    """Create BillingService instance with database session."""
    return BillingService(db)


BillingSvc = Annotated[BillingService, Depends(get_billing_service)]
from app.core.exceptions import AuthenticationError, AuthorizationError, NotFoundError
from app.core.security import verify_token
from app.db.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_service: UserSvc,
) -> User:
    """Get current authenticated user from JWT token.

    Returns the full User object including role information.

    Raises:
        AuthenticationError: If token is invalid or user not found.
    """

    payload = verify_token(token)
    if payload is None:
        raise AuthenticationError(message="Invalid or expired token")

    # Ensure this is an access token, not a refresh token
    if payload.get("type") != "access":
        raise AuthenticationError(message="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(message="Invalid token payload")

    user = await user_service.get_by_id(UUID(user_id))
    if not user.is_active:
        raise AuthenticationError(message="User account is disabled")

    return user


class RoleChecker:
    """Dependency class for role-based access control.

    Usage:
        # Require admin role
        @router.get("/admin-only")
        async def admin_endpoint(
            user: Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]
        ):
            ...

        # Require any authenticated user
        @router.get("/users")
        async def users_endpoint(
            user: Annotated[User, Depends(get_current_user)]
        ):
            ...
    """

    def __init__(self, required_role: UserRole) -> None:
        self.required_role = required_role

    async def __call__(
        self,
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        """Check if user has the required role.

        Raises:
            AuthorizationError: If user doesn't have the required role.
        """
        if not user.has_role(self.required_role):
            raise AuthorizationError(
                message=f"Role '{self.required_role.value}' required for this action"
            )
        return user


async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user and verify they are a superuser.

    Raises:
        AuthorizationError: If user is not a superuser.
    """
    if not current_user.has_role(UserRole.ADMIN):
        raise AuthorizationError(message="Admin privileges required")
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_active_superuser)]
CurrentAdmin = Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]
from app.db.models.organization import Organization, OrgRole

# Module-level alias so tests can patch via `app.api.deps._member_repo`.
# RequireOrgRole methods reference this alias instead of importing the repo
# inline; routes using member_repo continue to import via the canonical path.
from app.repositories import member_repo as _member_repo


async def get_active_organization(
    user: CurrentUser,
    db: DBSession,
    x_organization_id: UUID | None = Header(None),
) -> Organization:
    """Resolve the active Organization for the current request.

    Reads ``X-Organization-Id`` header. Falls back to the user's Personal Org
    when the header is absent. Raises 404 if the user is not a member.
    """

    if x_organization_id is None:
        org = await organization_repo.get_personal_for_user(db, user.id)
        if not org:
            raise NotFoundError(message="Personal organization not found — please re-register")
        return org

    membership = await member_repo.get(db, organization_id=x_organization_id, user_id=user.id)
    if not membership:
        raise NotFoundError(
            message="Organization not found or access denied",
            details={"org_id": str(x_organization_id)},
        )
    org = await organization_repo.get_by_id(db, x_organization_id)
    if not org:
        raise NotFoundError(
            message="Organization not found", details={"org_id": str(x_organization_id)}
        )
    return org


ActiveOrg = Annotated[Organization, Depends(get_active_organization)]


class RequireOrgRole:
    """Dependency that verifies the requester has one of the allowed roles in the active org.

    Usage::

        @router.delete("/{org_id}")
        async def delete(org: RequireOwner, ...) -> None: ...
    """

    def __init__(self, *allowed_roles: str) -> None:
        self.allowed_roles = set(allowed_roles)

    async def __call__(self, org: ActiveOrg, user: CurrentUser, db: DBSession) -> Organization:
        membership = await _member_repo.get(db, organization_id=org.id, user_id=user.id)
        if not membership or membership.role not in self.allowed_roles:
            raise AuthorizationError(
                message="Insufficient organization role",
                details={"required": list(self.allowed_roles), "org_id": str(org.id)},
            )
        return org


RequireOwner = Annotated[Organization, Depends(RequireOrgRole(OrgRole.OWNER.value))]
RequireAdminPlus = Annotated[
    Organization, Depends(RequireOrgRole(OrgRole.OWNER.value, OrgRole.ADMIN.value))
]
RequireMemberPlus = Annotated[
    Organization,
    Depends(RequireOrgRole(OrgRole.OWNER.value, OrgRole.ADMIN.value, OrgRole.MEMBER.value)),
]


# is_app_admin is a global flag on the User model — independent of team
# membership. Routes guarded by this dep (e.g. /admin/users) stay reachable
# even when teams are disabled, so the dep itself must not be gated.
async def _require_app_admin(user: CurrentUser) -> User:
    """Raises 403 unless the user has the is_app_admin flag set."""
    if not getattr(user, "is_app_admin", False):
        raise AuthorizationError(message="App admin privileges required")
    return user


CurrentAppAdmin = Annotated[User, Depends(_require_app_admin)]


_WS_TOKEN_PROTOCOL_PREFIX = "access_token."


def _extract_ws_auth(websocket: WebSocket) -> tuple[str | None, str | None]:
    """Parse Sec-WebSocket-Protocol header for an auth token + app subprotocol.

    Clients pass the token as a subprotocol of the form
    ``access_token.<JWT>`` alongside an optional application subprotocol
    (e.g. ``chat``). Returns (token, app_subprotocol) — either may be None.
    """
    raw = websocket.headers.get("sec-websocket-protocol") or ""
    token: str | None = None
    app_subprotocol: str | None = None
    for proto in (p.strip() for p in raw.split(",") if p.strip()):
        if proto.startswith(_WS_TOKEN_PROTOCOL_PREFIX):
            token = proto[len(_WS_TOKEN_PROTOCOL_PREFIX) :]
        elif app_subprotocol is None:
            app_subprotocol = proto
    return token, app_subprotocol


async def get_current_user_ws(
    websocket: WebSocket,
    access_token: str | None = Cookie(None),
) -> User:
    """Authenticate a WebSocket connection.

    Token sources, checked in order:
    1. ``Sec-WebSocket-Protocol`` header, in the form ``access_token.<JWT>``.
       The chosen application subprotocol (e.g. ``chat``) is echoed back on
       ``accept()`` via ``websocket.state.accept_subprotocol``.
    2. Same-origin ``access_token`` cookie (fallback for same-origin clients).

    Tokens in query strings are NOT accepted — they leak into logs and
    Referer headers.

    Raises:
        WebSocketException: If token is invalid or user not found. Raising the
            WebSocket-native exception lets Starlette close the handshake cleanly
            (close code 4001) — raising an HTTP-domain exception here instead
            bubbles up unhandled and yields an HTTP 500 on the WS upgrade.
    """

    subprotocol_token, app_subprotocol = _extract_ws_auth(websocket)
    websocket.state.accept_subprotocol = app_subprotocol

    auth_token = subprotocol_token or access_token

    if not auth_token:
        raise WebSocketException(code=4001, reason="Missing authentication token")

    payload = verify_token(auth_token)
    if payload is None:
        raise WebSocketException(code=4001, reason="Invalid or expired token")

    if payload.get("type") != "access":
        raise WebSocketException(code=4001, reason="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise WebSocketException(code=4001, reason="Invalid token payload")

    async with get_db_context() as db:
        user_service = UserService(db)
        try:
            user = await user_service.get_by_id(UUID(user_id))
        except NotFoundError:
            raise WebSocketException(code=4001, reason="User not found") from None

        if not user.is_active:
            raise WebSocketException(code=4001, reason="User account is disabled")

        # Eagerly load all columns, then detach from session to avoid
        # "instance not bound to a Session" errors after the context manager exits
        await db.refresh(user)
        db.expunge(user)
        return user


CurrentUserWS = Annotated[User, Depends(get_current_user_ws)]

import secrets

from fastapi.security import APIKeyHeader


api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def verify_api_key(
    api_key: Annotated[str | None, Depends(api_key_header)],
) -> str:
    """Verify API key from header.

    Uses constant-time comparison to prevent timing attacks.

    Raises:
        AuthenticationError: If API key is missing.
        AuthorizationError: If API key is invalid.
    """
    if api_key is None:
        raise AuthenticationError(message="API Key header missing")
    if not secrets.compare_digest(api_key, settings.API_KEY):
        raise AuthorizationError(message="Invalid API Key")
    return api_key


ValidAPIKey = Annotated[str, Depends(verify_api_key)]


from fastapi import Request

from app.core.config import settings
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.ingestion import IngestionService
from app.services.rag.documents import DocumentProcessor
from app.services.rag.retrieval import RetrievalService
from app.services.rag.vectorstore import MilvusVectorStore
from app.services.rag.vectorstore import BaseVectorStore


def get_embedding_service(request: Request) -> EmbeddingService:
    """Get embedding service from lifespan state or create new if not available."""
    if hasattr(request.state, "embedding_service"):
        return request.state.embedding_service  # type: ignore[no-any-return]
    return EmbeddingService(settings=settings.rag)


EmbeddingSvc = Annotated[EmbeddingService, Depends(get_embedding_service)]


def get_vectorstore(request: Request, embedder: EmbeddingSvc) -> BaseVectorStore:
    """Get vector store client from lifespan state or create new."""
    if hasattr(request.state, "vector_store"):
        return request.state.vector_store  # type: ignore[no-any-return]
    return MilvusVectorStore(settings=settings.rag, embedding_service=embedder)


VectorStoreSvc = Annotated[BaseVectorStore, Depends(get_vectorstore)]


def get_retrieval_service(vector_store: VectorStoreSvc) -> RetrievalService:
    """Create RetrievalService instance."""
    return RetrievalService(vector_store=vector_store, settings=settings.rag)


RetrievalSvc = Annotated[RetrievalService, Depends(get_retrieval_service)]


def get_document_processor() -> DocumentProcessor:
    """Create DocumentProcessor instance."""
    return DocumentProcessor(settings=settings.rag)


DocumentProcessorSvc = Annotated[DocumentProcessor, Depends(get_document_processor)]


def get_ingestion_service(
    processor: DocumentProcessorSvc,
    vector_store: VectorStoreSvc,
) -> IngestionService:
    """Create IngestionService instance."""
    return IngestionService(processor=processor, vector_store=vector_store)


IngestionSvc = Annotated[IngestionService, Depends(get_ingestion_service)]
from app.services.contact import ContactService


def get_contact_service() -> ContactService:
    """Create ContactService instance."""
    return ContactService()


ContactSvc = Annotated[ContactService, Depends(get_contact_service)]
from app.services.user_slash_command import UserSlashCommandService


def get_user_slash_command_service(db: DBSession) -> UserSlashCommandService:
    return UserSlashCommandService(db)


UserSlashCommandSvc = Annotated[UserSlashCommandService, Depends(get_user_slash_command_service)]
from app.services.admin import AdminService


def get_admin_service(db: DBSession) -> AdminService:
    """Create AdminService instance — used by admin REST routes (always
    available, independent of the optional SQLAdmin UI)."""
    return AdminService(db)


AdminSvc = Annotated[AdminService, Depends(get_admin_service)]
