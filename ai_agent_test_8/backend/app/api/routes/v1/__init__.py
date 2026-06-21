"""API v1 router aggregation."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from fastapi import APIRouter

from app.api.routes.v1 import health
from app.api.routes.v1 import admin_users, auth, users
from app.api.routes.v1 import admin_ratings
from app.api.routes.v1 import oauth
from app.api.routes.v1 import sessions
from app.api.routes.v1 import conversations
from app.api.routes.v1 import admin_conversations
from app.api.routes.v1 import agent
from app.api.routes.v1 import rag
from app.api.routes.v1 import files
from app.api.routes.v1 import channels
from app.api.routes.v1 import telegram_webhook
from app.api.routes.v1 import slack_webhook
from app.api.routes.v1 import members, organizations
from app.api.routes.v1.invitations import (
    org_router as invitations_org_router,
    token_router as invitations_token_router,
)
from app.api.routes.v1 import knowledge_bases
from app.api.routes.v1 import billing
from app.api.routes.v1 import contact
from app.api.routes.v1 import me_slash_commands
from app.api.routes.v1 import admin_stats

v1_router = APIRouter()

v1_router.include_router(health.router, tags=["health"])

v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
v1_router.include_router(users.router, prefix="/users", tags=["users"])

v1_router.include_router(admin_ratings.router, prefix="/admin/ratings", tags=["admin:ratings"])

v1_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])

v1_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])

v1_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])

v1_router.include_router(agent.router, tags=["agent"])

v1_router.include_router(rag.router, prefix="/rag", tags=["rag"])

v1_router.include_router(files.router, tags=["files"])

v1_router.include_router(
    admin_conversations.router, prefix="/admin/conversations", tags=["admin-conversations"]
)

v1_router.include_router(admin_users.router, prefix="/admin/users", tags=["admin:users"])

v1_router.include_router(channels.router, prefix="/channels", tags=["channels"])

v1_router.include_router(telegram_webhook.router, prefix="/telegram", tags=["telegram"])

v1_router.include_router(slack_webhook.router, prefix="/slack", tags=["slack"])

v1_router.include_router(organizations.router, prefix="/orgs", tags=["organizations"])
v1_router.include_router(members.router, prefix="/orgs", tags=["members"])
v1_router.include_router(invitations_org_router, prefix="/orgs", tags=["invitations"])
v1_router.include_router(invitations_token_router, tags=["invitations"])

v1_router.include_router(knowledge_bases.router, prefix="/kb", tags=["knowledge-bases"])

v1_router.include_router(billing.router, prefix="/billing", tags=["billing"])
v1_router.include_router(contact.router, tags=["contact"])
v1_router.include_router(
    me_slash_commands.router, prefix="/me/slash-commands", tags=["me:slash-commands"]
)
v1_router.include_router(admin_stats.router, prefix="/admin", tags=["admin:stats"])
