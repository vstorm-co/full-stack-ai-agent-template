"""API v1 router aggregation."""
{%- if cookiecutter.use_jwt or cookiecutter.enable_oauth or cookiecutter.include_example_crud or cookiecutter.enable_conversation_persistence or cookiecutter.enable_webhooks or cookiecutter.enable_websockets or cookiecutter.enable_ai_agent %}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
{%- endif %}

from fastapi import APIRouter

from app.api.routes.v1 import health
{%- if cookiecutter.use_jwt %}
from app.api.routes.v1 import auth, users
{%- endif %}
{%- if cookiecutter.enable_oauth %}
from app.api.routes.v1 import oauth
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
from app.api.routes.v1 import sessions
{%- endif %}
{%- if cookiecutter.include_example_crud and cookiecutter.use_database %}
from app.api.routes.v1 import items
{%- endif %}
{%- if cookiecutter.enable_conversation_persistence and cookiecutter.use_database %}
from app.api.routes.v1 import conversations
{%- endif %}
{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}
from app.api.routes.v1 import webhooks
{%- endif %}
{%- if cookiecutter.enable_websockets %}
from app.api.routes.v1 import ws
{%- endif %}
{%- if cookiecutter.enable_ai_agent %}
from app.api.routes.v1 import agent
{%- endif %}
{%- if cookiecutter.enable_rag %}
from app.api.routes.v1 import rag
{%- endif %}

v1_router = APIRouter()

# Health check routes (no auth required)
v1_router.include_router(health.router, tags=["health"])

{%- if cookiecutter.use_jwt %}

# Authentication routes
v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# User routes
v1_router.include_router(users.router, prefix="/users", tags=["users"])
{%- endif %}

{%- if cookiecutter.enable_oauth %}

# OAuth2 routes
v1_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
{%- endif %}

{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}

# Session management routes
v1_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
{%- endif %}

{%- if cookiecutter.include_example_crud and cookiecutter.use_database %}

# Example CRUD routes (items)
v1_router.include_router(items.router, prefix="/items", tags=["items"])
{%- endif %}

{%- if cookiecutter.enable_conversation_persistence and cookiecutter.use_database %}

# Conversation routes (AI chat persistence)
v1_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
{%- endif %}

{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}

# Webhook routes
v1_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
{%- endif %}

{%- if cookiecutter.enable_websockets %}

# WebSocket routes
v1_router.include_router(ws.router, tags=["websocket"])
{%- endif %}
{%- if cookiecutter.enable_ai_agent %}

# AI Agent routes
v1_router.include_router(agent.router, tags=["agent"])
{%- endif %}

{%- if cookiecutter.enable_rag %}

# RAG routes
v1_router.include_router(rag.router, prefix="/rag", tags=["rag"])
{%- endif %}
