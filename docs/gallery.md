# Screenshots

A tour of what a generated project looks like out of the box — chat, marketing site, dashboard, billing, admin, and orchestration.

!!! tip "Light / dark"
    Many screenshots ship in **both themes**. Use the brightness toggle in the top bar (☀️ / 🌙) and the images below switch with it automatically.

## AI Chat

The chat UI streams over WebSocket and renders each tool call as a purpose-built card instead of a raw JSON dump.

**Plan & tasks** — a sticky plan/task checklist above the composer updates live as the agent works, with an inline reasoning indicator.

![Chat plan and tasks](screenshots/chat_tasks.png){.shot}

**Subagents** — when work is delegated, a live feed and side panel show each subagent's status, streamed messages, and final result.

![Chat subagents](screenshots/chat_subagents.png){.shot}

**Charts** — the `create_chart` tool renders interactive, theme-aware bar / area / line / pie / scatter charts inline.

![Chat charts](screenshots/chat_graphs.png){.shot}

**Code execution** — the optional `run_python` tool shows the executed code alongside its output (or error) in a collapsible card.

![Chat Python code execution](screenshots/chat_python_code.png){.shot}

**Ask user** — the agent can pause to ask clarifying questions and resume once you answer.

![Chat ask-user tool](screenshots/chat_ask_user.png){.shot}

**Reasoning & answered questions** — a clean thinking view plus answered-question history keeps long turns readable.

![Chat reasoning and answered questions](screenshots/chat_answered_questions_and_thinking.png){.shot}

## Marketing Site

Generated with the `enable_marketing_site` option — a full public site you can ship as-is.

**Hero**

![Landing hero](screenshots/landing_hero.png){.shot}

**Full landing page**

![Landing page](screenshots/landing_full.png){.shot}

**Pricing** — monthly/annual toggle; pulls live plan data from Stripe when connected.

![Pricing](screenshots/landing_pricing.png){.shot}

**Blog** — MDX posts in the repo, no CMS needed.

![Blog](screenshots/blogs.png){.shot}

## Auth

**Login** — split-screen with Google OAuth and email/password.

![Login](screenshots/login.png){.shot}

**Register**

![Register](screenshots/register.png){.shot}

**Reset password**

![Reset password](screenshots/reset_password.png){.shot}

## Dashboard

Workspace overview with sparkline stat cards, a usage timeline, recent activity, and team info.

![Dashboard — light](screenshots/dashboard_light.png#only-light){.shot}
![Dashboard — dark](screenshots/dashboard_dark.png#only-dark){.shot}

## Teams & Organizations

**Workspaces** — every organization you belong to, with plan tier and role.

![Organizations — light](screenshots/organizations_light.png#only-light){.shot}
![Organizations — dark](screenshots/organizations_dark.png#only-dark){.shot}

**Team management** — members, roles, and invites.

![Organization — light](screenshots/organization_light.png#only-light){.shot}
![Organization — dark](screenshots/organization_dark.png#only-dark){.shot}

## Knowledge Bases

**Knowledge bases** — RAG collections scoped to the workspace; toggle which are active in chat.

![Knowledge bases — light](screenshots/knowledge_bases_light.png#only-light){.shot}
![Knowledge bases — dark](screenshots/knowledge_bases_dark.png#only-dark){.shot}

**Documents & sync sources** — preview or download any file, and manage connected sync sources (Google Drive, S3/MinIO) with manual triggers and per-run logs.

![Knowledge base source — light](screenshots/knowledge_base_source_light.png#only-light){.shot}
![Knowledge base source — dark](screenshots/knowledge_base_source_dark.png#only-dark){.shot}

## Billing & Usage

**Overview** — plan, seats, storage usage, and quick links. "Manage in Stripe" opens the Customer Portal.

![Billing overview — light](screenshots/billing_and_usage_light.png#only-light){.shot}
![Billing overview — dark](screenshots/billing_and_usage_dark.png#only-dark){.shot}

**Usage** — daily credits-spent and call-count charts plus a by-model token breakdown.

![Billing usage — light](screenshots/billing_usage_light.png#only-light){.shot}
![Billing usage — dark](screenshots/billing_usage_dark.png#only-dark){.shot}

**Credits** — balance and an immutable transaction ledger.

![Billing credits — light](screenshots/billing_credits_light.png#only-light){.shot}
![Billing credits — dark](screenshots/billing_credits_dark.png#only-dark){.shot}

**Subscription & invoices**

![Billing subscription — light](screenshots/billing_subscription_light.png#only-light){.shot}
![Billing subscription — dark](screenshots/billing_subscription_dark.png#only-dark){.shot}
![Billing invoices — light](screenshots/billing_invoices_light.png#only-light){.shot}
![Billing invoices — dark](screenshots/billing_invoices_dark.png#only-dark){.shot}

## Profile & Settings

**Profile**

![Profile — light](screenshots/profile_light.png#only-light){.shot}
![Profile — dark](screenshots/profile_dark.png#only-dark){.shot}

**Account & security**

![Account — light](screenshots/account_light.png#only-light){.shot}
![Account — dark](screenshots/account_dark.png#only-dark){.shot}

**Slash commands** — customize the `/command` palette in chat.

![Slash commands — light](screenshots/commands_light.png#only-light){.shot}
![Slash commands — dark](screenshots/commands_dark.png#only-dark){.shot}

**Appearance** — theme switcher and brand-color presets.

![Appearance — light](screenshots/appearance_light.png#only-light){.shot}
![Appearance — dark](screenshots/appearance_dark.png#only-dark){.shot}

**Notifications**

![Notifications — light](screenshots/notifications_light.png#only-light){.shot}
![Notifications — dark](screenshots/notifications_dark.png#only-dark){.shot}

## Admin Panel

Requires the `admin` role.

**Overview** — users, active sessions, conversations, MRR, and a recent-activity feed.

![Admin overview — light](screenshots/admin_overview_light.png#only-light){.shot}
![Admin overview — dark](screenshots/admin_overview_dark.png#only-dark){.shot}

**User management**

![Admin users — light](screenshots/admin_users_light.png#only-light){.shot}
![Admin users — dark](screenshots/admin_users_dark.png#only-dark){.shot}

**Conversation browser**

![Admin conversations — light](screenshots/admin_conversations_light.png#only-light){.shot}
![Admin conversations — dark](screenshots/admin_conversations_dark.png#only-dark){.shot}

**Message quality & ratings**

![Admin ratings — light](screenshots/admin_ratings_light.png#only-light){.shot}
![Admin ratings — dark](screenshots/admin_ratings_dark.png#only-dark){.shot}

**Stripe events log**

![Stripe events — light](screenshots/admin_stripe_events_light.png#only-light){.shot}
![Stripe events — dark](screenshots/admin_stripe_events_dark.png#only-dark){.shot}

**System health**

![System health — light](screenshots/admin_system_light.png#only-light){.shot}
![System health — dark](screenshots/admin_system_dark.png#only-dark){.shot}

## Background Tasks & Orchestration

Choose Prefect as your task queue (in the interactive wizard) and the project ships a self-hosted Prefect server and runner with scheduled flows for RAG sync, billing/email reminders, and credits maintenance.

![Prefect dashboard](screenshots/prefect_dashboard.png){.shot}

![Prefect flow runs](screenshots/prefect_runs.png){.shot}

![Prefect task timeline](screenshots/prefect_task_timeline.png){.shot}
