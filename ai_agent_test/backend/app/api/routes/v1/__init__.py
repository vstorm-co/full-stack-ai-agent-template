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
from app.api.routes.v1 import contact
from app.api.routes.v1 import me_slash_commands
from app.api.routes.v1 import admin_stats

v1_router = APIRouter()

# Health check routes (no auth required)
v1_router.include_router(health.router, tags=["health"])

# Authentication routes
v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# User routes
v1_router.include_router(users.router, prefix="/users", tags=["users"])

# Admin: message-rating analytics
v1_router.include_router(admin_ratings.router, prefix="/admin/ratings", tags=["admin:ratings"])

# OAuth2 routes
v1_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])

# Session management routes
v1_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])

# Conversation routes (AI chat persistence)
v1_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])

# AI Agent routes
v1_router.include_router(agent.router, tags=["agent"])

# RAG routes
v1_router.include_router(rag.router, prefix="/rag", tags=["rag"])

# File upload/download routes
v1_router.include_router(files.router, tags=["files"])

# Admin: conversation browser
v1_router.include_router(
    admin_conversations.router, prefix="/admin/conversations", tags=["admin-conversations"]
)

# Admin: user management + impersonation
v1_router.include_router(admin_users.router, prefix="/admin/users", tags=["admin:users"])

# Messaging channel admin routes (shared across Telegram, Slack)
v1_router.include_router(channels.router, prefix="/channels", tags=["channels"])

# Telegram webhook endpoint
v1_router.include_router(telegram_webhook.router, prefix="/telegram", tags=["telegram"])

# Slack Events API endpoint
v1_router.include_router(slack_webhook.router, prefix="/slack", tags=["slack"])
v1_router.include_router(contact.router, tags=["contact"])
v1_router.include_router(
    me_slash_commands.router, prefix="/me/slash-commands", tags=["me:slash-commands"]
)
v1_router.include_router(admin_stats.router, prefix="/admin", tags=["admin:stats"])
