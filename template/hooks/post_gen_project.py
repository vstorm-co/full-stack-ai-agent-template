#!/usr/bin/env python
"""Post-generation hook for cookiecutter template."""

import os
import shutil
import subprocess
import sys

# Get cookiecutter variables
use_frontend = "{{ cookiecutter.use_frontend }}" == "True"
generate_env = "{{ cookiecutter.generate_env }}" == "True"

# Feature flags
use_database = "{{ cookiecutter.use_database }}" == "True"
use_postgresql = "{{ cookiecutter.use_postgresql }}" == "True"
use_sqlite = "{{ cookiecutter.use_sqlite }}" == "True"
use_mongodb = "{{ cookiecutter.use_mongodb }}" == "True"
use_sqlalchemy = "{{ cookiecutter.use_sqlalchemy }}" == "True"
use_sqlmodel = "{{ cookiecutter.use_sqlmodel }}" == "True"
use_pydantic_ai = "{{ cookiecutter.use_pydantic_ai }}" == "True"
use_langchain = "{{ cookiecutter.use_langchain }}" == "True"
use_langgraph = "{{ cookiecutter.use_langgraph }}" == "True"
use_crewai = "{{ cookiecutter.use_crewai }}" == "True"
use_deepagents = "{{ cookiecutter.use_deepagents }}" == "True"
enable_admin_panel = "{{ cookiecutter.enable_admin_panel }}" == "True"
enable_websockets = "{{ cookiecutter.enable_websockets }}" == "True"
enable_redis = "{{ cookiecutter.enable_redis }}" == "True"
enable_caching = "{{ cookiecutter.enable_caching }}" == "True"
enable_rate_limiting = "{{ cookiecutter.enable_rate_limiting }}" == "True"
enable_session_management = "{{ cookiecutter.enable_session_management }}" == "True"
enable_webhooks = "{{ cookiecutter.enable_webhooks }}" == "True"
enable_oauth = "{{ cookiecutter.enable_oauth }}" == "True"
use_auth = "{{ cookiecutter.use_auth }}" == "True"
use_celery = "{{ cookiecutter.use_celery }}" == "True"
use_taskiq = "{{ cookiecutter.use_taskiq }}" == "True"
use_arq = "{{ cookiecutter.use_arq }}" == "True"
use_github_actions = "{{ cookiecutter.use_github_actions }}" == "True"
use_gitlab_ci = "{{ cookiecutter.use_gitlab_ci }}" == "True"
enable_kubernetes = "{{ cookiecutter.enable_kubernetes }}" == "True"
use_nginx = "{{ cookiecutter.use_nginx }}" == "True"
enable_logfire = "{{ cookiecutter.enable_logfire }}" == "True"
enable_langsmith = "{{ cookiecutter.enable_langsmith }}" == "True"
enable_rag = "{{ cookiecutter.enable_rag }}" == "True"
enable_rag_image_description = "{{ cookiecutter.enable_rag_image_description }}" == "True"
enable_google_drive_ingestion = "{{ cookiecutter.enable_google_drive_ingestion }}" == "True"
enable_s3_ingestion = "{{ cookiecutter.enable_s3_ingestion }}" == "True"
enable_web_search = "{{ cookiecutter.enable_web_search }}" == "True"
web_fetch_tool = "{{ cookiecutter.web_fetch_tool }}" == "True"
enable_charts = "{{ cookiecutter.enable_charts }}" == "True"
charts_channel_png = "{{ cookiecutter.charts_channel_png }}" == "True"
enable_antv_charts = "{{ cookiecutter.enable_antv_charts }}" == "True"
enable_code_execution = "{{ cookiecutter.enable_code_execution }}" == "True"
enable_deep_research = "{{ cookiecutter.enable_deep_research }}" == "True"
use_pydantic_deep = "{{ cookiecutter.use_pydantic_deep }}" == "True"
use_telegram = "{{ cookiecutter.use_telegram }}" == "True"
use_slack = "{{ cookiecutter.use_slack }}" == "True"
enable_docker = "{{ cookiecutter.enable_docker }}" == "True"
enable_teams = "{{ cookiecutter.enable_teams }}" == "True"
enable_billing = "{{ cookiecutter.enable_billing }}" == "True"
enable_credits_system = "{{ cookiecutter.enable_credits_system }}" == "True"
enable_usage_dashboard = "{{ cookiecutter.enable_usage_dashboard }}" == "True"
enable_usage_anomaly_detection = "{{ cookiecutter.enable_usage_anomaly_detection }}" == "True"
enable_email = "{{ cookiecutter.enable_email }}" == "True"
enable_newsletter_signup = "{{ cookiecutter.enable_newsletter_signup }}" == "True"
enable_marketing_site = "{{ cookiecutter.enable_marketing_site }}" == "True"
enable_changelog = "{{ cookiecutter.enable_changelog }}" == "True"
enable_i18n = "{{ cookiecutter.enable_i18n }}" == "True"
use_delegated_auth = "{{ cookiecutter.use_delegated_auth }}" == "True"
use_external_user_id_in_conversations = (
    "{{ cookiecutter.use_external_user_id_in_conversations }}" == "True"
)
include_example_crud = "{{ cookiecutter.include_example_crud }}" == "True"
use_ai = "{{ cookiecutter.use_ai }}" == "True"
enable_storybook = "{{ cookiecutter.enable_storybook }}" == "True"


def remove_file(path: str) -> None:
    """Remove a file if it exists."""
    if os.path.exists(path):
        os.remove(path)
        print(f"  Removed: {os.path.relpath(path)}")


def is_stub_file(filepath: str) -> bool:
    """Return True if the file has no real code — empty or docstring-only."""
    if not os.path.exists(filepath):
        return False
    with open(filepath) as f:
        content = f.read().strip()
    if not content:
        return True
    # Single triple-quoted docstring, no real code
    if content.startswith('"""') and content.endswith('"""'):
        inner = content[3:-3].strip()
        # No nested docstrings, no functions/classes
        if '"""' not in inner and "def " not in content and "class " not in content:
            return True
    # Only comment lines + optional shebang/encoding — no code
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    code_lines = [
        l for l in lines
        if not l.startswith("#") and l not in ("pass", "...")
    ]
    return len(code_lines) == 0


def remove_dir(path: str) -> None:
    """Remove a directory if it exists."""
    if os.path.exists(path):
        shutil.rmtree(path)
        print(f"  Removed: {os.path.relpath(path)}/")


# Base directories
backend_app = os.path.join(os.getcwd(), "backend", "app")

# Cleanup stub files based on disabled features
print("Cleaning up unused files...")

# --- AI Agent files (remove unused framework-specific files) ---
if not use_pydantic_ai:
    remove_file(os.path.join(backend_app, "agents", "assistant.py"))
    remove_file(os.path.join(backend_app, "agents", "tools", "ask_user_tool.py"))
if not use_langchain:
    remove_file(os.path.join(backend_app, "agents", "langchain_assistant.py"))
if not use_langgraph:
    remove_file(os.path.join(backend_app, "agents", "langgraph_assistant.py"))
if not use_crewai:
    remove_file(os.path.join(backend_app, "agents", "crewai_assistant.py"))
if not use_deepagents:
    remove_file(os.path.join(backend_app, "agents", "deepagents_assistant.py"))
if not use_pydantic_deep:
    remove_file(os.path.join(backend_app, "agents", "pydantic_deep_assistant.py"))
if not enable_web_search:
    remove_file(os.path.join(backend_app, "agents", "tools", "web_search.py"))
    remove_file(os.path.join(os.getcwd(), "backend", "tests", "test_web_search.py"))
if not web_fetch_tool:
    remove_file(os.path.join(backend_app, "agents", "tools", "fetch_url.py"))
    remove_file(os.path.join(os.getcwd(), "backend", "tests", "test_fetch_url.py"))
if not enable_charts:
    remove_file(os.path.join(backend_app, "agents", "tools", "chart_tool.py"))
    remove_file(os.path.join(backend_app, "agents", "tools", "chart_render.py"))
    remove_file(os.path.join(os.getcwd(), "backend", "tests", "test_chart_tool.py"))
    if use_frontend:
        frontend_src = os.path.join(os.getcwd(), "frontend", "src")
        remove_file(os.path.join(frontend_src, "components", "chat", "chart-message.tsx"))
elif not charts_channel_png:
    # Chart tool enabled but no Slack/Telegram — PNG renderer not needed.
    remove_file(os.path.join(backend_app, "agents", "tools", "chart_render.py"))
if not enable_antv_charts:
    # AntV diagram MCP client + the create_map tool + its Leaflet renderer.
    remove_file(os.path.join(backend_app, "agents", "tools", "antv_chart.py"))
    remove_file(os.path.join(backend_app, "agents", "tools", "map_tool.py"))
    if use_frontend:
        frontend_src = os.path.join(os.getcwd(), "frontend", "src")
        remove_file(os.path.join(frontend_src, "components", "chat", "map-leaflet.tsx"))
        remove_file(os.path.join(frontend_src, "components", "chat", "map-message.tsx"))
if not enable_code_execution:
    remove_file(os.path.join(backend_app, "agents", "tools", "code_execution.py"))
if not enable_deep_research:
    remove_file(os.path.join(backend_app, "services", "research.py"))
    remove_file(os.path.join(backend_app, "db", "todo_pool.py"))
    if use_frontend:
        frontend_src = os.path.join(os.getcwd(), "frontend", "src")
        remove_file(os.path.join(frontend_src, "components", "chat", "research-panel.tsx"))
        remove_file(os.path.join(frontend_src, "stores", "research-store.ts"))
        remove_file(os.path.join(frontend_src, "stores", "chat-mode-store.ts"))

# --- No-AI mode: remove all AI/chat/conversation files ---
if not use_ai:
    # Entire agents folder
    remove_dir(os.path.join(backend_app, "agents"))
    # Agent & conversation services
    remove_file(os.path.join(backend_app, "services", "agent.py"))
    remove_file(os.path.join(backend_app, "services", "agent_session.py"))
    remove_file(os.path.join(backend_app, "services", "agent_invocation.py"))
    remove_file(os.path.join(backend_app, "services", "conversation.py"))
    # Conversation model / repo / schema
    remove_file(os.path.join(backend_app, "db", "models", "conversation.py"))
    remove_file(os.path.join(backend_app, "repositories", "conversation.py"))
    remove_file(os.path.join(backend_app, "schemas", "conversation.py"))
    remove_file(os.path.join(backend_app, "schemas", "message_rating.py"))
    # Conversation sharing — model + repo + service. The *schema* module
    # (schemas/conversation_share.py) is intentionally KEPT: it also defines
    # AdminUserRead/AdminUserList, consumed by the always-on admin_users
    # route. Its conversation-specific schemas are Jinja-guarded by use_ai.
    remove_file(os.path.join(backend_app, "db", "models", "conversation_share.py"))
    remove_file(os.path.join(backend_app, "repositories", "conversation_share.py"))
    remove_file(os.path.join(backend_app, "services", "conversation_share.py"))
    # Message ratings — model + repo + service (AI-only)
    remove_file(os.path.join(backend_app, "db", "models", "message_rating.py"))
    remove_file(os.path.join(backend_app, "repositories", "message_rating.py"))
    remove_file(os.path.join(backend_app, "services", "message_rating.py"))
    # Chat & conversation routes
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "chat.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "conversations.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "message_ratings.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "me_slash_commands.py"))
    # AI agent route + admin conversation/rating browsers — AI-only and
    # import-broken without the conversation/message_rating models.
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "agent.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "admin_conversations.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "admin_ratings.py"))
    # Slash commands model / repo / schema / service
    remove_file(os.path.join(backend_app, "db", "models", "user_slash_command.py"))
    remove_file(os.path.join(backend_app, "repositories", "user_slash_command.py"))
    remove_file(os.path.join(backend_app, "schemas", "user_slash_command.py"))
    remove_file(os.path.join(backend_app, "services", "user_slash_command.py"))
    # Logfire (AI observability) — only remove if no other use
    # Keep logfire_setup.py if logfire is enabled for non-AI tracing (FastAPI/DB)
    # Frontend chat UI + AI-only admin pages / API proxies / data hooks
    if use_frontend:
        frontend_src = os.path.join(os.getcwd(), "frontend", "src")
        remove_dir(os.path.join(frontend_src, "app", "[locale]", "(dashboard)", "chat"))
        remove_dir(os.path.join(frontend_src, "components", "chat"))
        remove_file(os.path.join(frontend_src, "components", "dashboard", "conversation-list.tsx"))
        # Admin conversations / ratings pages — route group is "(dashboard)"
        remove_dir(
            os.path.join(
                frontend_src, "app", "[locale]", "(dashboard)", "admin", "conversations"
            )
        )
        remove_dir(
            os.path.join(frontend_src, "app", "[locale]", "(dashboard)", "admin", "ratings")
        )
        # Next.js API proxies for the removed admin endpoints
        remove_dir(os.path.join(frontend_src, "app", "api", "admin", "conversations"))
        remove_dir(os.path.join(frontend_src, "app", "api", "admin", "ratings"))
        # Conversation / rating data hooks
        remove_file(os.path.join(frontend_src, "hooks", "use-conversations.ts"))
        remove_file(os.path.join(frontend_src, "hooks", "use-conversation-shares.ts"))
        remove_file(os.path.join(frontend_src, "hooks", "use-admin-conversations.ts"))
        # Slash-commands frontend feature — AI/chat only; its hook/manager
        # import from the (now-removed) components/chat module. (Also removed
        # by the no-auth block, but that doesn't fire when only AI is off.)
        remove_dir(os.path.join(frontend_src, "app", "api", "me", "slash-commands"))
        remove_file(os.path.join(frontend_src, "lib", "slash-commands-api.ts"))
        remove_file(os.path.join(frontend_src, "hooks", "use-slash-commands.ts"))
        remove_file(
            os.path.join(frontend_src, "components", "settings", "slash-commands-manager.tsx")
        )
        remove_dir(
            os.path.join(
                frontend_src,
                "app",
                "[locale]",
                "(dashboard)",
                "settings",
                "slash-commands",
            )
        )

# --- Webhook files ---
if not enable_webhooks or not use_database:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "webhooks.py"))
    remove_file(os.path.join(backend_app, "db", "models", "webhook.py"))
    remove_file(os.path.join(backend_app, "repositories", "webhook.py"))
    remove_file(os.path.join(backend_app, "services", "webhook.py"))
    remove_file(os.path.join(backend_app, "schemas", "webhook.py"))

# --- Session management files ---
if not enable_session_management:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "sessions.py"))
    remove_file(os.path.join(backend_app, "db", "models", "session.py"))
    remove_file(os.path.join(backend_app, "repositories", "session.py"))
    remove_file(os.path.join(backend_app, "services", "session.py"))
    remove_file(os.path.join(backend_app, "schemas", "session.py"))
    if use_frontend:
        frontend_src = os.path.join(os.getcwd(), "frontend", "src")
        remove_dir(os.path.join(frontend_src, "app", "api", "sessions"))
        remove_file(os.path.join(frontend_src, "components", "dashboard", "active-sessions.tsx"))


# --- Admin panel: SQLAdmin UI (requires SQLAlchemy, not SQLModel) ---
# This gates ONLY the SQLAdmin integration (`admin.py`). The core admin REST
# routes (`admin_users.py`, `admin_stats.py`) and their dashboard pages stay
# regardless — they're always useful for the workspace admin role. The AI
# admin routes (`admin_conversations.py`, `admin_ratings.py`) are removed in
# the no-AI block above; `admin_stats.py` keeps working because its
# conversation/message metrics are Jinja-guarded by use_ai.
if not enable_admin_panel or (not use_postgresql and not use_sqlite) or not use_sqlalchemy:
    remove_file(os.path.join(backend_app, "admin.py"))

# Stripe events listing requires the StripeEvent model — drop it (and the
# proxy) when billing is off. The /admin/stripe-events page itself is removed
# in the billing-off block elsewhere.
if not enable_billing and use_frontend:
    frontend_src_for_admin = os.path.join(os.getcwd(), "frontend", "src")
    remove_dir(os.path.join(frontend_src_for_admin, "app", "api", "admin", "stripe-events"))

# --- Redis/Cache files ---
if not enable_redis:
    remove_file(os.path.join(backend_app, "clients", "redis.py"))

if not enable_caching:
    remove_file(os.path.join(backend_app, "core", "cache.py"))

# --- Rate limiting ---
if not enable_rate_limiting:
    remove_file(os.path.join(backend_app, "core", "rate_limit.py"))
    remove_dir(os.path.join(backend_app, "services", "rate_limit"))

# --- OAuth ---
if not enable_oauth:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "oauth.py"))
    remove_file(os.path.join(backend_app, "core", "oauth.py"))


# --- Logfire setup file (when logfire is disabled) ---
if not enable_logfire:
    remove_file(os.path.join(backend_app, "core", "logfire_setup.py"))

# --- RAG files ---
if not enable_rag:
    # Remove entire rag directory when RAG is disabled
    remove_dir(os.path.join(backend_app, "services", "rag"))
    # Remove RAG-related API route
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "rag.py"))
    # Remove RAG schema
    remove_file(os.path.join(backend_app, "schemas", "rag.py"))
    # Remove RAG commands
    remove_file(os.path.join(backend_app, "commands", "rag.py"))
    # Remove RAG worker tasks
    remove_file(os.path.join(backend_app, "worker", "tasks", "rag_ingestion.py"))
    # Remove RAG agent tool
    remove_file(os.path.join(backend_app, "agents", "tools", "rag_tool.py"))
    # Remove RAG document repository/service/model stubs
    remove_file(os.path.join(backend_app, "repositories", "rag_document.py"))
    remove_file(os.path.join(backend_app, "services", "rag_document.py"))
    remove_file(os.path.join(backend_app, "services", "rag_sync.py"))
    remove_file(os.path.join(backend_app, "db", "models", "rag_document.py"))
    # Remove sync source/log artifacts (they only exist for RAG)
    remove_file(os.path.join(backend_app, "db", "models", "sync_source.py"))
    remove_file(os.path.join(backend_app, "db", "models", "sync_log.py"))
    remove_file(os.path.join(backend_app, "schemas", "sync_source.py"))
    remove_file(os.path.join(backend_app, "repositories", "sync_source.py"))
    remove_file(os.path.join(backend_app, "repositories", "sync_log.py"))
    remove_file(os.path.join(backend_app, "services", "sync_source.py"))
    # Remove frontend RAG files
    if use_frontend:
        frontend_src = os.path.join(os.getcwd(), "frontend", "src")
        remove_file(os.path.join(frontend_src, "lib", "rag-api.ts"))
        remove_dir(os.path.join(frontend_src, "app", "api", "v1", "rag"))
        # Remove RAG management page (both paths - i18n variant may be moved later)
        remove_dir(os.path.join(frontend_src, "app", "[locale]", "(dashboard)", "rag"))
        remove_dir(os.path.join(frontend_src, "app", "(dashboard)", "rag"))
        # RAG-only chat / KB / sync components — no fallback when rag-api.ts
        # is gone, so drop them entirely.
        remove_dir(os.path.join(frontend_src, "components", "rag"))
        remove_file(os.path.join(frontend_src, "components", "chat", "kb-panel.tsx"))
        # Knowledge-base UI is a RAG feature — its page/hook/components import
        # @/lib/rag-api + @/components/rag (just removed). The KB nav entries
        # are already gated `enable_teams and enable_rag`, so drop the files
        # too (otherwise `next build` type-checks orphaned, broken imports).
        # Mirrors the teams-off KB removal block.
        remove_dir(os.path.join(frontend_src, "components", "kb"))
        remove_dir(os.path.join(frontend_src, "app", "api", "kb"))
        remove_dir(os.path.join(frontend_src, "app", "[locale]", "(dashboard)", "kb"))
        remove_file(os.path.join(frontend_src, "hooks", "use-knowledge-bases.ts"))
        remove_file(os.path.join(frontend_src, "types", "knowledge-base.ts"))
else:
    # RAG enabled — remove optional components if not enabled
    rag_dir = os.path.join(backend_app, "services", "rag")
    if not enable_rag_image_description:
        remove_file(os.path.join(rag_dir, "image_describer.py"))
    if not enable_google_drive_ingestion:
        remove_file(os.path.join(rag_dir, "sources", "google_drive.py"))
        remove_file(os.path.join(rag_dir, "connectors", "google_drive.py"))
    if not enable_s3_ingestion:
        remove_file(os.path.join(rag_dir, "sources", "s3.py"))
        remove_file(os.path.join(rag_dir, "connectors", "s3.py"))
    if not enable_google_drive_ingestion and not enable_s3_ingestion:
        remove_dir(os.path.join(rag_dir, "sources"))
        # Keep rag/connectors/ — its __init__.py defines CONNECTOR_REGISTRY which
        # sync_source.py imports unconditionally even when no connectors are configured.

# --- Messaging channels (Slack / Telegram) ---
# Per-channel adapters & webhook routes
if not use_telegram:
    remove_file(os.path.join(backend_app, "services", "channels", "telegram.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "telegram_webhook.py"))
if not use_slack:
    remove_file(os.path.join(backend_app, "services", "channels", "slack.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "slack_webhook.py"))

# Shared channel infrastructure — only present when at least one channel is enabled
if not use_telegram and not use_slack:
    remove_dir(os.path.join(backend_app, "services", "channels"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "channels.py"))
    remove_file(os.path.join(backend_app, "core", "channel_crypto.py"))
    remove_file(os.path.join(backend_app, "commands", "channel.py"))
    remove_file(os.path.join(backend_app, "services", "channel_bot.py"))
    remove_file(os.path.join(backend_app, "services", "agent_invocation.py"))
    remove_file(os.path.join(backend_app, "repositories", "channel_bot.py"))
    remove_file(os.path.join(backend_app, "repositories", "channel_identity.py"))
    remove_file(os.path.join(backend_app, "repositories", "channel_session.py"))
    remove_file(os.path.join(backend_app, "schemas", "channel_bot.py"))
    remove_file(os.path.join(backend_app, "db", "models", "channel_bot.py"))
    remove_file(os.path.join(backend_app, "db", "models", "channel_identity.py"))
    remove_file(os.path.join(backend_app, "db", "models", "channel_session.py"))

# --- DeepAgents project files (only when use_pydantic_deep is enabled) ---
if not use_pydantic_deep:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "projects.py"))
    remove_file(os.path.join(backend_app, "db", "models", "project.py"))
    remove_file(os.path.join(backend_app, "schemas", "project.py"))
    remove_file(os.path.join(backend_app, "services", "project.py"))
    remove_file(os.path.join(backend_app, "repositories", "project.py"))

# --- Test stubs that depend on disabled features ---
backend_tests = os.path.join(os.getcwd(), "backend", "tests")
if not enable_redis:
    remove_file(os.path.join(backend_tests, "test_clients.py"))
if not (use_postgresql and use_sqlalchemy):
    remove_file(os.path.join(backend_tests, "test_services_conversation.py"))
if not (enable_admin_panel and use_postgresql):
    remove_file(os.path.join(backend_tests, "test_admin.py"))

# --- Empty docker-compose placeholders ---
if not enable_docker:
    project_root = os.getcwd()
    for compose_file in (
        "docker-compose.yml",
        "docker-compose.dev.yml",
        "docker-compose.prod.yml",
        "docker-compose.frontend.yml",
    ):
        remove_file(os.path.join(project_root, compose_file))

# --- Cleanup stub files (files with only docstring, no code) ---
# Scan all .py files under backend/app — catches any template that rendered to
# a stub docstring because its feature gate was disabled.
for root, _dirs, files in os.walk(backend_app):
    for fname in files:
        if not fname.endswith(".py"):
            continue
        filepath = os.path.join(root, fname)
        if is_stub_file(filepath):
            remove_file(filepath)

# --- Worker/Background tasks ---
# worker/background/ holds in-process handlers (FastAPI BackgroundTasks fallback)
# and stays regardless of distributed queue selection. worker/tasks/ holds
# distributed Celery/Taskiq/ARQ tasks and is only kept when one is selected.
use_any_background_tasks = use_celery or use_taskiq or use_arq
worker_dir = os.path.join(backend_app, "worker")
if not use_any_background_tasks:
    remove_file(os.path.join(worker_dir, "celery_app.py"))
    remove_file(os.path.join(worker_dir, "taskiq_app.py"))
    remove_file(os.path.join(worker_dir, "arq_app.py"))
    remove_dir(os.path.join(worker_dir, "tasks"))
    remove_file(os.path.join(backend_tests, "test_worker_taskiq.py"))
else:
    if not use_celery:
        remove_file(os.path.join(worker_dir, "celery_app.py"))
    if not use_taskiq:
        remove_file(os.path.join(worker_dir, "taskiq_app.py"))
        remove_file(os.path.join(worker_dir, "tasks", "schedules.py"))
        remove_file(os.path.join(backend_tests, "test_worker_taskiq.py"))
    if not use_arq:
        remove_file(os.path.join(worker_dir, "arq_app.py"))


# --- Cleanup empty directories ---
def remove_empty_dirs(path: str) -> None:
    """Recursively remove empty directories.

    A directory is considered "empty" when it contains nothing, OR when it
    only contains an __init__.py file that is itself empty (whitespace-only).
    A non-trivial __init__.py (with imports, registries, public API) is kept
    even when its siblings are gone — removing it would silently break code
    that imports from the package (e.g. CONNECTOR_REGISTRY in
    services/rag/connectors).
    """
    if not os.path.isdir(path):
        return
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            remove_empty_dirs(item_path)
    remaining = os.listdir(path)
    if not remaining:
        os.rmdir(path)
        print(f"  Removed empty: {os.path.relpath(path)}/")
    elif remaining == ["__init__.py"]:
        init_path = os.path.join(path, "__init__.py")
        try:
            init_text = open(init_path).read().strip()
        except OSError:
            init_text = ""
        if init_text == "":
            os.remove(init_path)
            os.rmdir(path)
            print(f"  Removed empty: {os.path.relpath(path)}/")


# Clean up empty directories in key locations
for subdir in [
    "clients",
    "agents",
    "worker",
    "worker/tasks",
    "worker/background",
    "services/billing",
    "services/billing/handlers",
    "services/channels",
    "services/email",
    "services/email/providers",
    "services/rag",
    # NOTE: services/rag/connectors intentionally excluded — its __init__.py
    # defines CONNECTOR_REGISTRY which sync_source.py imports unconditionally.
    # Removing the dir (even when no connectors are configured) breaks startup.
    "services/rag/sources",
    "services/rate_limit",
]:
    dir_path = os.path.join(backend_app, subdir)
    if os.path.exists(dir_path):
        remove_empty_dirs(dir_path)

print("File cleanup complete.")

# --- CI/CD files cleanup ---
if not use_github_actions:
    github_dir = os.path.join(os.getcwd(), ".github")
    if os.path.exists(github_dir):
        shutil.rmtree(github_dir)
        print("Removed .github/ directory (GitHub Actions not enabled)")

if not use_gitlab_ci:
    gitlab_ci_file = os.path.join(os.getcwd(), ".gitlab-ci.yml")
    if os.path.exists(gitlab_ci_file):
        os.remove(gitlab_ci_file)
        print("Removed .gitlab-ci.yml (GitLab CI not enabled)")

if not enable_kubernetes:
    kubernetes_dir = os.path.join(os.getcwd(), "kubernetes")
    if os.path.exists(kubernetes_dir):
        shutil.rmtree(kubernetes_dir)
        print("Removed kubernetes/ directory (Kubernetes not enabled)")

if not use_nginx:
    nginx_dir = os.path.join(os.getcwd(), "nginx")
    if os.path.exists(nginx_dir):
        shutil.rmtree(nginx_dir)
        print("Removed nginx/ directory (Nginx not enabled)")

# Remove frontend folder if not using frontend
if not use_frontend:
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    if os.path.exists(frontend_dir):
        shutil.rmtree(frontend_dir)
        print("Removed frontend/ directory (frontend not enabled)")
    # Remove frontend-specific Claude rule
    remove_file(os.path.join(os.getcwd(), ".claude", "rules", "frontend.md"))


# Remove .env files if generate_env is false
if not generate_env:
    backend_env = os.path.join(os.getcwd(), "backend", ".env")
    if os.path.exists(backend_env):
        os.remove(backend_env)
        print("Removed backend/.env (generate_env disabled)")

    frontend_env = os.path.join(os.getcwd(), "frontend", ".env.local")
    if os.path.exists(frontend_env):
        os.remove(frontend_env)
        print("Removed frontend/.env.local (generate_env disabled)")
else:
    # Generate frontend/.env.local with necessary Next.js public variables
    if use_frontend:
        frontend_env_local = os.path.join(os.getcwd(), "frontend", ".env.local")
        if not os.path.exists(frontend_env_local):
            env_lines = [
                "# Backend API URL (server-side only - not exposed to browser)",
                "BACKEND_URL=http://localhost:{{ cookiecutter.backend_port }}",
                "",
                "# WebSocket URL for real-time features",
                "BACKEND_WS_URL=ws://localhost:{{ cookiecutter.backend_port }}",
                "",
                "# Canonical site URL — used for SEO metadata, OG tags, sitemap.xml,",
                "# robots.txt, schema.org organization. Override in production with",
                "# the real https origin.",
                "NEXT_PUBLIC_SITE_URL=http://localhost:{{ cookiecutter.frontend_port }}",
            ]
            env_lines.extend([
                "",
                "# Authentication (always enabled)",
                "NEXT_PUBLIC_AUTH_ENABLED=true",
            ])
            if enable_oauth:
                # Build the comma-separated provider list the OAuth buttons read.
                # Currently only Google has full backend wiring; expand here when
                # GitHub / Microsoft are added.
                providers = []
                if "{{ cookiecutter.enable_oauth_google }}" == "True":
                    providers.append("google")
                env_lines.extend([
                    "",
                    "# Public API URL for OAuth redirects (exposed to browser)",
                    "NEXT_PUBLIC_API_URL=http://localhost:{{ cookiecutter.backend_port }}",
                    "",
                    "# OAuth providers shown on /login + /register (comma-separated).",
                    "# Drives the <OAuthButtons> component — must include only providers",
                    "# whose backend credentials are configured in backend/.env.",
                    "NEXT_PUBLIC_OAUTH_PROVIDERS=" + ",".join(providers),
                ])
            if enable_rag:
                env_lines.extend([
                    "",
                    "# RAG (Retrieval Augmented Generation)",
                    "NEXT_PUBLIC_RAG_ENABLED=true",
                ])
            if enable_logfire:
                env_lines.extend([
                    "",
                    "# Logfire/OpenTelemetry (server-side instrumentation)",
                    "# Get your write token from: https://logfire.pydantic.dev",
                    "OTEL_EXPORTER_OTLP_ENDPOINT=https://logfire-api.pydantic.dev",
                    "OTEL_EXPORTER_OTLP_HEADERS=Authorization=your-logfire-write-token",
                ])
            if "{{ cookiecutter.enable_brand_from_config }}" == "True":
                env_lines.extend([
                    "",
                    "# Runtime brand override (white-label)",
                    "# Set NEXT_PUBLIC_BRAND_COLOR to one of: blue, green, red, violet, orange",
                    "NEXT_PUBLIC_BRAND_COLOR={{ cookiecutter.brand_color }}",
                    "NEXT_PUBLIC_BRAND_LOGO_URL=",
                ])

            with open(frontend_env_local, "w") as f:
                f.write("\n".join(env_lines) + "\n")
            print("Generated frontend/.env.local")

# Generate uv.lock for backend (required for Docker builds)
backend_dir = os.path.join(os.getcwd(), "backend")
if os.path.exists(backend_dir):
    uv_cmd = shutil.which("uv")
    if uv_cmd:
        print("Generating uv.lock for backend...")
        result = subprocess.run(
            [uv_cmd, "lock"],
            cwd=backend_dir,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            print("uv.lock generated successfully.")
        else:
            print("Warning: Failed to generate uv.lock. Run 'uv lock' in backend/ directory.")
    else:
        print("Warning: uv not found. Run 'uv lock' in backend/ to generate lock file.")

# Run ruff to auto-fix import sorting and other linting issues
if os.path.exists(backend_dir):
    ruff_cmd = None

    # Try multiple methods to find/run ruff
    # 1. Check if ruff is in PATH
    ruff_path = shutil.which("ruff")
    if ruff_path:
        ruff_cmd = [ruff_path]
    # 2. Try uvx ruff (if uv is installed)
    elif shutil.which("uvx"):
        ruff_cmd = ["uvx", "ruff"]
    # 3. Try python -m ruff
    else:
        # Test if ruff is available as a module
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "--version"],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            ruff_cmd = [sys.executable, "-m", "ruff"]

    if ruff_cmd:
        print(f"Running ruff to format code (using: {' '.join(ruff_cmd)})...")
        # Run ruff check --fix to auto-fix issues (suppress output)
        subprocess.run(
            [*ruff_cmd, "check", "--fix", "--quiet", backend_dir],
            check=False,
            capture_output=True,
        )
        # Run ruff format for consistent formatting (suppress output)
        subprocess.run(
            [*ruff_cmd, "format", "--quiet", backend_dir],
            check=False,
            capture_output=True,
        )
        print("Code formatting complete.")
    else:
        print("Warning: ruff not found. Run 'ruff format .' in backend/ to format code.")

# Format frontend with prettier if it exists
frontend_dir = os.path.join(os.getcwd(), "frontend")
if use_frontend and os.path.exists(frontend_dir):
    # Try to find bun or npx for running prettier
    bun_cmd = shutil.which("bun")
    npx_cmd = shutil.which("npx")

    if bun_cmd:
        print("Installing frontend dependencies and formatting with Prettier...")
        # Install dependencies first (prettier is a devDependency)
        result = subprocess.run(
            [bun_cmd, "install"],
            cwd=frontend_dir,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            # Format with prettier
            subprocess.run(
                [bun_cmd, "run", "format"],
                cwd=frontend_dir,
                capture_output=True,
                check=False,
            )
            print("Frontend formatting complete.")
        else:
            print("Warning: Failed to install frontend dependencies.")
    elif npx_cmd:
        print("Formatting frontend with Prettier...")
        subprocess.run(
            [npx_cmd, "prettier", "--write", "."],
            cwd=frontend_dir,
            capture_output=True,
            check=False,
        )
        print("Frontend formatting complete.")
    else:
        print("Warning: bun/npx not found. Run 'bun run format' in frontend/ to format code.")

# --- Teams: remove teams-specific files if enable_teams is false ---
if not enable_teams:
    remove_file(os.path.join(backend_app, "db", "models", "organization.py"))
    remove_file(os.path.join(backend_app, "db", "models", "audit_log.py"))
    remove_file(os.path.join(backend_app, "schemas", "organization.py"))
    remove_file(os.path.join(backend_app, "repositories", "organization.py"))
    remove_file(os.path.join(backend_app, "repositories", "member.py"))
    remove_file(os.path.join(backend_app, "repositories", "invitation.py"))
    remove_file(os.path.join(backend_app, "services", "organization.py"))
    remove_file(os.path.join(backend_app, "services", "member.py"))
    remove_file(os.path.join(backend_app, "services", "invitation.py"))
    remove_file(os.path.join(backend_app, "core", "audit.py"))
    remove_file(os.path.join(backend_app, "commands", "create_app_admin.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "organizations.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "members.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "invitations.py"))
    remove_file(os.path.join(backend_tests, "test_rbac_teams.py"))
    remove_file(os.path.join(backend_tests, "test_services_members.py"))
    remove_file(os.path.join(backend_tests, "test_tenant_isolation.py"))
    remove_file(os.path.join(backend_app, "db", "models", "knowledge_base.py"))
    remove_file(os.path.join(backend_app, "schemas", "knowledge_base.py"))
    remove_file(os.path.join(backend_app, "repositories", "knowledge_base.py"))
    remove_file(os.path.join(backend_app, "services", "knowledge_base.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "knowledge_bases.py"))
    remove_file(os.path.join(backend_tests, "test_kb_scoping.py"))
    remove_file(os.path.join(backend_tests, "test_conversation_kb_toggle.py"))
    remove_file(os.path.join(backend_app, "services", "billing.py"))
    remove_file(os.path.join(backend_app, "schemas", "billing.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "billing.py"))
    remove_file(os.path.join(backend_tests, "test_stripe_seats.py"))
    # Frontend teams files
    if use_frontend:
        frontend_src = os.path.join(os.getcwd(), "frontend", "src")
        remove_dir(os.path.join(frontend_src, "components", "teams"))
        remove_dir(os.path.join(frontend_src, "app", "api", "orgs"))
        remove_dir(os.path.join(frontend_src, "app", "api", "invitations"))
        remove_dir(os.path.join(frontend_src, "app", "[locale]", "(dashboard)", "orgs"))
        remove_dir(os.path.join(frontend_src, "app", "[locale]", "(dashboard)", "invitations"))
        remove_file(os.path.join(frontend_src, "hooks", "use-organizations.ts"))
        remove_file(os.path.join(frontend_src, "hooks", "use-members.ts"))
        remove_file(os.path.join(frontend_src, "hooks", "use-invitations.ts"))
        remove_file(os.path.join(frontend_src, "stores", "org-store.ts"))
        remove_file(os.path.join(frontend_src, "types", "organization.ts"))
        # Also remove KB/billing frontend since they depend on teams
        remove_dir(os.path.join(frontend_src, "components", "kb"))
        remove_dir(os.path.join(frontend_src, "app", "api", "kb"))
        remove_dir(os.path.join(frontend_src, "app", "[locale]", "(dashboard)", "kb"))
        remove_file(os.path.join(frontend_src, "hooks", "use-knowledge-bases.ts"))
        remove_file(os.path.join(frontend_src, "types", "knowledge-base.ts"))
        remove_dir(os.path.join(frontend_src, "components", "billing"))
        remove_dir(os.path.join(frontend_src, "app", "api", "billing"))
        remove_dir(os.path.join(frontend_src, "app", "[locale]", "(dashboard)", "billing"))
        remove_file(os.path.join(frontend_src, "hooks", "use-billing.ts"))
        remove_file(os.path.join(frontend_src, "types", "billing.ts"))
        # Keep lib/teaser-plans.ts — it's pure static fallback data with no
        # billing dependencies. The /pricing landing page imports it and
        # gracefully renders teaser cards when the live `/billing/plans`
        # endpoint is unavailable (which is exactly the case here).
        remove_dir(
            os.path.join(frontend_src, "app", "[locale]", "(dashboard)", "admin", "stripe-events"),
        )
        # Dashboard widgets that depend on teams/orgs.
        remove_file(os.path.join(frontend_src, "components", "dashboard", "team-summary.tsx"))

# --- Billing: remove billing-specific files if enable_billing is false ---
if not enable_billing:
    remove_file(os.path.join(backend_app, "schemas", "billing.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "billing.py"))
    remove_file(os.path.join(backend_tests, "test_stripe_seats.py"))
    # Remove the entire billing services subpackage (facade + Stripe client + handlers)
    remove_dir(os.path.join(backend_app, "services", "billing"))
    # Remove billing repositories and models
    remove_file(os.path.join(backend_app, "repositories", "plan.py"))
    remove_file(os.path.join(backend_app, "repositories", "subscription.py"))
    remove_file(os.path.join(backend_app, "repositories", "stripe_event.py"))
    remove_file(os.path.join(backend_app, "repositories", "credit_transaction.py"))
    remove_file(os.path.join(backend_app, "repositories", "usage_event.py"))
    remove_file(os.path.join(backend_app, "db", "models", "plan.py"))
    remove_file(os.path.join(backend_app, "db", "models", "subscription.py"))
    remove_file(os.path.join(backend_app, "db", "models", "stripe_event.py"))
    remove_file(os.path.join(backend_app, "db", "models", "credit_transaction.py"))
    remove_file(os.path.join(backend_app, "commands", "sync_stripe_plans.py"))
    if use_frontend:
        frontend_src = os.path.join(os.getcwd(), "frontend", "src")
        remove_dir(os.path.join(frontend_src, "components", "billing"))
        remove_dir(os.path.join(frontend_src, "app", "api", "billing"))
        remove_dir(os.path.join(frontend_src, "app", "[locale]", "(dashboard)", "billing"))
        remove_file(os.path.join(frontend_src, "hooks", "use-billing.ts"))
        remove_file(os.path.join(frontend_src, "types", "billing.ts"))
        # teaser-plans.ts stays — it's the fallback data for /pricing when
        # there is no live billing backend. /pricing imports it directly.
        # Admin Stripe events page is billing-specific
        remove_dir(
            os.path.join(frontend_src, "app", "[locale]", "(dashboard)", "admin", "stripe-events"),
        )
        # Dashboard widgets that depend on billing data.
        remove_file(os.path.join(frontend_src, "components", "dashboard", "subscription-chip.tsx"))
        remove_file(os.path.join(frontend_src, "components", "dashboard", "tool-usage.tsx"))
        remove_file(os.path.join(frontend_src, "components", "dashboard", "top-models.tsx"))
        # billing/me/* proxy depends on the billing backend
        remove_dir(os.path.join(frontend_src, "app", "api", "billing", "me"))
        # Settings → Integrations tab depends on useBilling for the Stripe
        # portal link. Drop the page when billing is off; the settings index
        # auto-skips it because the layout reads the directory.
        remove_dir(
            os.path.join(
                frontend_src, "app", "[locale]", "(dashboard)", "settings", "integrations",
            ),
        )

# --- Credits system: per-org balance, usage events, top-up purchases ---
# Backend-only cleanup. Frontend usage UI (usage-gauge, usage-timeline,
# /billing/usage page) STAYS regardless — these are imported by the dashboard
# and pricing flows and gracefully degrade when the API returns no data.
if not enable_credits_system:
    remove_file(os.path.join(backend_app, "repositories", "credit_transaction.py"))
    remove_file(os.path.join(backend_app, "repositories", "usage_event.py"))
    remove_file(os.path.join(backend_app, "db", "models", "credit_transaction.py"))

# --- Usage spike detection: cron job that compares hourly usage vs rolling avg ---
if not enable_usage_anomaly_detection:
    remove_file(os.path.join(backend_app, "services", "anomaly_detection.py"))
    # Worker task imports the service — remove together to avoid an import error
    # at app boot. Schedule entries in celery_app are already feature-gated.
    remove_file(os.path.join(backend_app, "worker", "tasks", "anomaly_tasks.py"))

# --- Email: lifecycle + notification emails (welcome, invitation, billing) ---
if not enable_email:
    remove_dir(os.path.join(backend_app, "services", "email"))
    # Newsletter is gated by enable_email AND enable_newsletter_signup —
    # if the email service is gone, the newsletter route can't function either.
    remove_file(os.path.join(backend_app, "services", "newsletter.py"))

# --- Newsletter signup: POST /newsletter/signup endpoint + landing form ---
if not enable_newsletter_signup:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "marketing.py"))
    remove_file(os.path.join(backend_app, "schemas", "marketing.py"))
    remove_file(os.path.join(backend_app, "services", "newsletter.py"))
    if use_frontend:
        frontend_src = os.path.join(os.getcwd(), "frontend", "src")
        remove_file(
            os.path.join(frontend_src, "components", "marketing", "newsletter-signup.tsx"),
        )

# --- Marketing site: remove blog / about / contact / help / security / community / legal ---
# Onboarding, settings, dashboard chrome stay regardless — they're core product UI.
# Landing (/) and pricing stay — they're entry points even for non-marketing setups.
if not enable_marketing_site:
    # Backend: contact endpoint is part of marketing surface
    remove_file(os.path.join(backend_app, "schemas", "contact.py"))
    remove_file(os.path.join(backend_app, "services", "contact.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "contact.py"))

# --- API keys + password reset + magic link: all require auth ---
if not use_auth:
    # API keys
    remove_file(os.path.join(backend_app, "db", "models", "api_key.py"))
    remove_file(os.path.join(backend_app, "schemas", "api_key.py"))
    remove_file(os.path.join(backend_app, "repositories", "api_key.py"))
    remove_file(os.path.join(backend_app, "services", "api_key.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "api_keys.py"))
    # User slash commands (per-user, so auth-required)
    remove_file(os.path.join(backend_app, "db", "models", "user_slash_command.py"))
    remove_file(os.path.join(backend_app, "schemas", "user_slash_command.py"))
    remove_file(os.path.join(backend_app, "repositories", "user_slash_command.py"))
    remove_file(os.path.join(backend_app, "services", "user_slash_command.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "me_slash_commands.py"))
    # Password reset + magic link schemas (auth-only flows)
    remove_file(os.path.join(backend_app, "schemas", "password_reset.py"))
    if use_frontend:
        frontend_src_for_api_keys = os.path.join(os.getcwd(), "frontend", "src")
        remove_dir(os.path.join(frontend_src_for_api_keys, "app", "api", "api-keys"))
        remove_file(
            os.path.join(
                frontend_src_for_api_keys, "components", "settings", "api-key-manager.tsx"
            ),
        )
        # User slash commands frontend (BFF proxies, hook, manager, settings page)
        remove_dir(
            os.path.join(frontend_src_for_api_keys, "app", "api", "me", "slash-commands")
        )
        remove_file(
            os.path.join(frontend_src_for_api_keys, "lib", "slash-commands-api.ts")
        )
        remove_file(
            os.path.join(frontend_src_for_api_keys, "hooks", "use-slash-commands.ts")
        )
        remove_file(
            os.path.join(
                frontend_src_for_api_keys,
                "components",
                "settings",
                "slash-commands-manager.tsx",
            ),
        )
        remove_dir(
            os.path.join(
                frontend_src_for_api_keys,
                "app",
                "[locale]",
                "(dashboard)",
                "settings",
                "slash-commands",
            )
        )
        # Frontend proxies for password reset + magic link
        remove_dir(
            os.path.join(frontend_src_for_api_keys, "app", "api", "auth", "password-reset")
        )
        remove_dir(
            os.path.join(frontend_src_for_api_keys, "app", "api", "auth", "magic-link")
        )
        # Frontend pages
        remove_dir(
            os.path.join(
                frontend_src_for_api_keys,
                "app",
                "[locale]",
                "(auth)",
                "reset-password",
            )
        )
        remove_dir(
            os.path.join(
                frontend_src_for_api_keys, "app", "[locale]", "auth", "magic-link"
            )
        )
        remove_file(
            os.path.join(
                frontend_src_for_api_keys, "components", "auth", "reset-password-form.tsx"
            )
        )

if not enable_marketing_site and use_frontend:
    frontend_root = os.path.join(os.getcwd(), "frontend")
    frontend_src = os.path.join(frontend_root, "src")
    locale_app = os.path.join(frontend_src, "app", "[locale]")

    # Frontend proxy for backend /contact
    remove_dir(os.path.join(frontend_src, "app", "api", "contact"))

    # Marketing route pages
    for d in ("about", "blog", "community", "contact", "help", "legal", "security"):
        remove_dir(os.path.join(locale_app, d))

    # Sitemap is genuinely marketing-specific — it walks blog posts and lists
    # public landing pages we just removed. Drop only this; favicon, apple
    # icon, manifest, robots, and the OG image are universally useful (browser
    # tab icon, PWA install, shared-link previews on Slack/Twitter, search
    # engine crawl rules) so they stay even when the marketing site is off.
    remove_file(os.path.join(frontend_src, "app", "sitemap.ts"))

    # Marketing-only sub-trees: only the ones used exclusively by the
    # blog / legal / SEO routes that we just removed. The shared marketing
    # components (hero, section, pricing-teaser, footer, etc.) STAY because
    # the landing page (/) and pricing (/pricing) still depend on them — see
    # the comment at the top of this block.
    remove_dir(os.path.join(frontend_src, "components", "blog"))
    remove_dir(os.path.join(frontend_src, "components", "legal"))
    # Only files that have no callers outside removed routes can go:
    # NOTE: cookie-banner.tsx STAYS — it's rendered by [locale]/layout.tsx for
    # every page (auth, dashboard, marketing). EU cookie consent applies even
    # without a marketing site.
    for f in (
        "legal-page.tsx",         # used by legal pages
        "contact-form.tsx",       # used by /contact
    ):
        remove_file(os.path.join(frontend_src, "components", "marketing", f))

    # Marketing-only lib helpers. NOTE: `seo.ts` and `schema-org.ts` STAY —
    # they're imported by app/layout.tsx, [locale]/layout.tsx, and every auth /
    # onboarding / dashboard page for `<head>` metadata + structured data.
    # `blog.ts` and `contact-info.ts` ride with the marketing routes that just
    # got removed. `changelog.ts` is removed only when the changelog page also
    # goes (see the changelog block below).
    remove_file(os.path.join(frontend_src, "lib", "blog.ts"))
    remove_file(os.path.join(frontend_src, "lib", "contact-info.ts"))

    # MDX content directory
    remove_dir(os.path.join(frontend_root, "content"))

# Changelog: page + its data file ride together. The page is not in the
# marketing block above (it's pseudo-marketing — a public release log) so it
# has its own flag.
if not enable_changelog and use_frontend:
    frontend_root = os.path.join(os.getcwd(), "frontend")
    frontend_src = os.path.join(frontend_root, "src")
    remove_dir(os.path.join(frontend_src, "app", "[locale]", "changelog"))
    remove_file(os.path.join(frontend_src, "lib", "changelog.ts"))

# Delegated auth: external IdP issues JWTs. Strip the local password/email
# auth surface — register, password reset, magic link have no meaning when
# the IdP owns the user identity.
if use_delegated_auth:
    backend_root = os.path.join(os.getcwd(), "backend")
    backend_app = os.path.join(backend_root, "app")
    # Email-based auth recovery flows are dead in delegated mode.
    remove_file(os.path.join(backend_app, "schemas", "password_reset.py"))
    remove_file(os.path.join(backend_app, "schemas", "magic_link.py"))
    if use_frontend:
        frontend_root = os.path.join(os.getcwd(), "frontend")
        frontend_src = os.path.join(frontend_root, "src")
        # Public auth pages — IdP owns these UIs now.
        for d in ("login", "register", "forgot-password", "reset-password", "magic-link-sent"):
            remove_dir(os.path.join(frontend_src, "app", "[locale]", "(auth)", d))
        for f in ("login-form.tsx", "register-form.tsx", "forgot-password-form.tsx", "reset-password-form.tsx"):
            remove_file(os.path.join(frontend_src, "components", "auth", f))

else:
    # Local-auth mode: the delegated-auth migration is dead weight.
    backend_root = os.path.join(os.getcwd(), "backend")
    remove_file(
        os.path.join(backend_root, "alembic", "versions", "0019_user_external_id.py")
    )

# Example Item CRUD scaffold — remove all 6 files when not requested.
if not include_example_crud:
    backend_root = os.path.join(os.getcwd(), "backend")
    remove_file(os.path.join(backend_app, "db", "models", "item.py"))
    remove_file(os.path.join(backend_app, "schemas", "item.py"))
    remove_file(os.path.join(backend_app, "repositories", "item.py"))
    remove_file(os.path.join(backend_app, "services", "item.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "items.py"))
    remove_file(
        os.path.join(backend_root, "alembic", "versions", "0021_create_items.py")
    )

# Conversations.external_user_id is opt-in even within delegated mode.
if not use_external_user_id_in_conversations:
    backend_root = os.path.join(os.getcwd(), "backend")
    remove_file(
        os.path.join(
            backend_root,
            "alembic",
            "versions",
            "0020_conversation_external_user_id.py",
        )
    )

# i18n: when single-locale (English-only), drop:
#   - Polish translations (`messages/pl.json`)
#   - Per-locale Polish legal/marketing TSX (e.g. `legal/pl/*`)
#   - Language switcher component (no longer rendered by header.tsx, so the
#     file is dead code — strip to keep `bun build` lean).
# The next-intl provider stays — it still works with one locale and any
# `useTranslations()` call keeps reading from `messages/en.json`. Re-enabling
# multi-language later means putting the files back + extending `i18n.ts`.
if not enable_i18n and use_frontend:
    frontend_root = os.path.join(os.getcwd(), "frontend")
    frontend_src = os.path.join(frontend_root, "src")
    remove_file(os.path.join(frontend_root, "messages", "pl.json"))
    remove_file(os.path.join(frontend_src, "components", "language-switcher.tsx"))
    # Per-locale Polish copies — the en/ counterparts stay.
    legal_dir = os.path.join(frontend_src, "components", "legal")
    if os.path.isdir(legal_dir):
        for entry in os.listdir(legal_dir):
            if entry.startswith("pl") or entry.endswith("-pl.tsx"):
                target = os.path.join(legal_dir, entry)
                if os.path.isfile(target):
                    remove_file(target)
                elif os.path.isdir(target):
                    remove_dir(target)

# Storybook: remove .storybook/ when not requested
if not enable_storybook and use_frontend:
    frontend_root = os.path.join(os.getcwd(), "frontend")
    storybook_dir = os.path.join(frontend_root, ".storybook")
    if os.path.exists(storybook_dir):
        shutil.rmtree(storybook_dir)
        print("Removed frontend/.storybook/ (storybook not enabled)")

print("Project generated successfully!")
