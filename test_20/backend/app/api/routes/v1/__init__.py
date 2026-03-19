"""API v1 router aggregation."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

from fastapi import APIRouter

from app.api.routes.v1 import health
from app.api.routes.v1 import auth, users
from app.api.routes.v1 import oauth
from app.api.routes.v1 import sessions
from app.api.routes.v1 import items
from app.api.routes.v1 import conversations
from app.api.routes.v1 import webhooks
from app.api.routes.v1 import ws
from app.api.routes.v1 import agent
from app.api.routes.v1 import rag
from app.api.routes.v1 import files

v1_router = APIRouter()

# Health check routes (no auth required)
v1_router.include_router(health.router, tags=["health"])

# Authentication routes
v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# User routes
v1_router.include_router(users.router, prefix="/users", tags=["users"])

# OAuth2 routes
v1_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])

# Session management routes
v1_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])

# Example CRUD routes (items)
v1_router.include_router(items.router, prefix="/items", tags=["items"])

# Conversation routes (AI chat persistence)
v1_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])

# Webhook routes
v1_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

# WebSocket routes
v1_router.include_router(ws.router, tags=["websocket"])

# AI Agent routes
v1_router.include_router(agent.router, tags=["agent"])

# RAG routes
v1_router.include_router(rag.router, prefix="/rag", tags=["rag"])

# File upload/download routes
v1_router.include_router(files.router, tags=["files"])
