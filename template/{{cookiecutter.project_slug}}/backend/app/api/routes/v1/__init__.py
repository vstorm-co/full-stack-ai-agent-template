"""API v1 router aggregation."""
{%- if cookiecutter.use_jwt or cookiecutter.enable_oauth or cookiecutter.enable_webhooks or cookiecutter.use_pydantic_deep or cookiecutter.use_telegram or cookiecutter.use_slack %}
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
{%- endif %}

from fastapi import APIRouter

from app.api.routes.v1 import health
{%- if cookiecutter.use_jwt %}
from app.api.routes.v1 import admin_users, auth, users
{%- endif %}
{%- if cookiecutter.use_jwt and cookiecutter.use_ai %}
from app.api.routes.v1 import admin_ratings
{%- endif %}
{%- if cookiecutter.enable_oauth %}
from app.api.routes.v1 import oauth
{%- endif %}
{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}
from app.api.routes.v1 import sessions
{%- endif %}
{%- if cookiecutter.use_ai %}
from app.api.routes.v1 import conversations
{%- endif %}
{%- if cookiecutter.use_jwt and cookiecutter.use_ai %}
from app.api.routes.v1 import admin_conversations
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
from app.api.routes.v1 import projects
{%- endif %}
{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}
from app.api.routes.v1 import webhooks
{%- endif %}
{%- if cookiecutter.use_ai %}
from app.api.routes.v1 import agent
{%- endif %}
{%- if cookiecutter.enable_rag %}
from app.api.routes.v1 import rag
{%- endif %}
{%- if cookiecutter.use_jwt %}
from app.api.routes.v1 import files
{%- endif %}
{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}
from app.api.routes.v1 import channels
{%- endif %}
{%- if cookiecutter.use_telegram %}
from app.api.routes.v1 import telegram_webhook
{%- endif %}
{%- if cookiecutter.use_slack %}
from app.api.routes.v1 import slack_webhook
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
from app.api.routes.v1 import members, organizations
from app.api.routes.v1.invitations import org_router as invitations_org_router, token_router as invitations_token_router
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
from app.api.routes.v1 import knowledge_bases
{%- endif %}
{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
from app.api.routes.v1 import billing
{%- endif %}
{%- if cookiecutter.enable_newsletter_signup %}
from app.api.routes.v1 import marketing
{%- endif %}
{%- if cookiecutter.enable_marketing_site %}
from app.api.routes.v1 import contact
{%- endif %}
{%- if cookiecutter.use_auth and cookiecutter.use_ai %}
from app.api.routes.v1 import me_slash_commands
{%- endif %}
{%- if cookiecutter.include_example_crud %}
from app.api.routes.v1 import items
{%- endif %}
{%- if cookiecutter.use_jwt %}
from app.api.routes.v1 import admin_stats
{%- endif %}
{%- if cookiecutter.enable_rag and cookiecutter.enable_teams and cookiecutter.use_jwt %}
from app.api.routes.v1 import org_integrations
{%- endif %}

v1_router = APIRouter()

v1_router.include_router(health.router, tags=["health"])

{%- if cookiecutter.use_jwt %}

v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
v1_router.include_router(users.router, prefix="/users", tags=["users"])
{%- endif %}
{%- if cookiecutter.use_jwt and cookiecutter.use_ai %}

v1_router.include_router(admin_ratings.router, prefix="/admin/ratings", tags=["admin:ratings"])
{%- endif %}

{%- if cookiecutter.enable_oauth %}

v1_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
{%- endif %}

{%- if cookiecutter.enable_session_management and cookiecutter.use_jwt %}

v1_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
{%- endif %}

{%- if cookiecutter.use_ai %}

v1_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
{%- endif %}

{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}

v1_router.include_router(projects.router, prefix="/projects", tags=["projects"])
{%- endif %}

{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}

v1_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
{%- endif %}

{%- if cookiecutter.use_ai %}

v1_router.include_router(agent.router, tags=["agent"])
{%- endif %}

{%- if cookiecutter.enable_rag %}

v1_router.include_router(rag.router, prefix="/rag", tags=["rag"])
{%- endif %}

{%- if cookiecutter.use_jwt %}

v1_router.include_router(files.router, tags=["files"])
{%- endif %}

{%- if cookiecutter.use_jwt and cookiecutter.use_ai %}

v1_router.include_router(admin_conversations.router, prefix="/admin/conversations", tags=["admin-conversations"])
{%- endif %}
{%- if cookiecutter.use_jwt %}

v1_router.include_router(admin_users.router, prefix="/admin/users", tags=["admin:users"])
{%- endif %}

{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}

v1_router.include_router(channels.router, prefix="/channels", tags=["channels"])
{%- endif %}

{%- if cookiecutter.use_telegram %}

v1_router.include_router(telegram_webhook.router, prefix="/telegram", tags=["telegram"])
{%- endif %}

{%- if cookiecutter.use_slack %}

v1_router.include_router(slack_webhook.router, prefix="/slack", tags=["slack"])
{%- endif %}

{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}

v1_router.include_router(organizations.router, prefix="/orgs", tags=["organizations"])
v1_router.include_router(members.router, prefix="/orgs", tags=["members"])
v1_router.include_router(invitations_org_router, prefix="/orgs", tags=["invitations"])
v1_router.include_router(invitations_token_router, tags=["invitations"])
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}

v1_router.include_router(knowledge_bases.router, prefix="/kb", tags=["knowledge-bases"])
{%- endif %}
{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}

v1_router.include_router(billing.router, prefix="/billing", tags=["billing"])
{%- endif %}
{%- if cookiecutter.enable_newsletter_signup %}
v1_router.include_router(marketing.router, tags=["marketing"])
{%- endif %}
{%- if cookiecutter.enable_marketing_site %}
v1_router.include_router(contact.router, tags=["contact"])
{%- endif %}
{%- if cookiecutter.use_auth and cookiecutter.use_ai %}
v1_router.include_router(
    me_slash_commands.router, prefix="/me/slash-commands", tags=["me:slash-commands"]
)
{%- endif %}
{%- if cookiecutter.use_jwt %}
v1_router.include_router(admin_stats.router, prefix="/admin", tags=["admin:stats"])
{%- endif %}
{%- if cookiecutter.enable_rag and cookiecutter.enable_teams and cookiecutter.use_jwt %}
v1_router.include_router(org_integrations.router, prefix="/org/integrations", tags=["org:integrations"])
{%- endif %}

{%- if cookiecutter.include_example_crud %}

# Example Item CRUD (reference scaffold — safe to delete once you've added your own domain)
v1_router.include_router(items.router, prefix="/items", tags=["items"])
{%- endif %}
