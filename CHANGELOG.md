# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.14] - 2026-06-23

### Added

- **Public demo gallery & live replay** — any conversation can be flagged as a demo by an admin (`PATCH /api/v1/admin/conversations/{id}/demo`), after which it appears on a public gallery page (`/{locale}/demo`) and can be played back frame-by-frame at `/{locale}/demo/{id}`. The gallery shows a deterministic waveform-trace visualisation (WaveTrace) unique to each demo UUID alongside a message-count, title, and preview quote. The replay page streams every message turn in real time, including tool calls and their results, at a configurable speed — exactly as the original session unfolded. No auth required; the public endpoints (`GET /api/v1/demos`, `GET /api/v1/demos/{id}`) return only flagged conversations (#106)
- **Conversation replay engine** — `useConversationReplay` hook drives step-by-step playback: reveals committed messages one turn at a time with character-by-character streaming on the active turn, emits a `tick` on every visual update, and exposes `start / stop / isReplaying / displayMessages / progress`. `useStepReplay` handles the per-turn streaming loop with configurable char-rate and inter-message delay. Tool calls animate in the same pass, with human-readable captions mapped from tool names via `agent-step-captions.ts` (#106)
- **`is_demo` conversation flag** — Alembic migration `0023`, `Conversation.is_demo: bool = False` column, repository helpers (`list_demos`, `get_public_demo`), and service methods (`mark_as_demo`, `list_public_demos`, `get_public_demo`). Admin conversations endpoint extended with a toggle action and `is_demo` field in the response schema (#106)
- **Admin conversations panel update** — the admin conversations table gains a "Demo" toggle button that calls the new action endpoint and reflects the current state with an optimistic UI update and toast feedback (#106)
- **Demo UI** — cinematic pre-play overlay (pulsing branded play button with radial glow, backdrop blur), sticky progress bar, "Jump to active" re-engage button, and "Watch again" reset. Gallery uses a dark hero with ambient glow blobs, live-indicator pill, and a two-column card grid with per-card hover gradient reveal (#106)

### Fixed

- **Demo replay auto-scroll** — replaced `window.scrollBy` (which has no effect when the page's scroll container is not `window`) with an inner `overflow-y-auto` container that the replay hook scrolls directly via `container.scrollBy`. The outer wrapper uses `h-[calc(100vh-3.5rem)]` (fixed height) so `flex-1` on the messages pane actually constrains its height and triggers overflow — previously `min-h` let the container grow unbounded, making `overflow-y-auto` a no-op (#106)
- **Jinja2 parse error on demo pages** — JSX inline style objects (`style={{ ... }}`) conflicted with Jinja2's `{{ }}` delimiter, causing "expected token 'end of print statement', got ':'" at generation time. Both demo template files are now wrapped in `{% raw %}...{% endraw %}`, with the single `{{ cookiecutter.backend_port }}` substitution broken out of the raw block. Inline style objects are also extracted to named constants to eliminate all `style={{` occurrences (#106)

### Changed

- **Demo replay scrollbar** — replaced the browser-default scrollbar on the replay container with a 4 px thin variant: transparent track, `border`-coloured thumb at rest, brand-coloured thumb on hover. Applied via Tailwind arbitrary-variant selectors (webkit) and `scrollbar-width: thin` / `scrollbar-color` (Firefox) (#106)

## [0.2.13] - 2026-06-22

### Added

- **Prefect background-task option** (`--background-tasks prefect`, `use_prefect`) — a fourth task backend alongside Celery, Taskiq, and ARQ. Unlike the Redis-backed queues, Prefect runs its own orchestrator: a `prefect-server` container (UI on `:4200`) plus a `prefect-runner` that registers deployments from `app/worker/prefect_app.py` and polls for work. Ships flows for RAG (on-demand ingest/sync + a scheduled `check_scheduled_syncs`), billing/email reminders (trial-ending, low-credits), and credits maintenance (ledger cleanup, `mv_usage_daily` refresh) on cron/interval schedules. Self-hosted by default (`PREFECT_API_URL`); set `PREFECT_API_KEY` for Prefect Cloud (#105)
- **Organization integrations / sync sources UI** — manage RAG connectors per organization from the dashboard (`/orgs/[id]/integrations`). Add a Google Drive or S3/MinIO source, assign it to a knowledge base, trigger a sync manually, and inspect per-run logs (status, mode, duration, and ingested/updated/skipped/failed counts). Sources can live at the org level as reusable templates or be wired to a specific collection. Connector credentials are encrypted at rest with Fernet (`app/core/crypto.py`) and masked in API responses. Endpoints under `/api/v1/org/integrations` (admin/owner only) (#105)
- **Billing, credits & usage metering** — a full Stripe billing stack: plans/prices mirrored locally, seat-based subscriptions with trials and end-of-period cancellation, an idempotent Stripe webhook event log, a Customer Portal link, and invoices. Adds a credits ledger (`credit_transaction`) and per-message usage events (`usage_event`: input/output/cached tokens, model, provider, credits charged) rolled up into a `mv_usage_daily` materialized view. New billing dashboard pages: subscription, payment methods, invoices, credits balance/ledger, and usage with daily credits/calls and by-model token charts (#105)
- **File view & download** — preview knowledge-base documents and chat attachments in-app via a modal viewer supporting 20+ types (PDF, images, audio/video, CSV tables, HTML sandbox, JSON, Markdown, syntax-highlighted code, plain text) with a download/open-external fallback for anything else. Backed by document/file download routes on the API (#105)
- **Standalone TODO planner and subagents** (`enable_todo`, `enable_subagents`) — the planner and multi-agent delegation that previously only shipped with Deep Research are now independent opt-in toggles. Enabling `enable_deep_research` still turns both on automatically (#105)
- **Chat UI overhaul** — specialized tool-result cards replace generic JSON dumps: numbered web-search results, knowledge-base chunks grouped by source file with relevance scores, `run_python` code + stdout/result, skill cards, `ask_user` question/answer transcripts, and datetime cards. Adds a live **subagent feed and side panel** (status, messages, results per delegated agent), a **sources panel** that collects every citation (knowledge base + web) with clickable `[N]` badges in Markdown, a sticky **task/plan checklist** above the composer, inline **chart rendering** (bar/area/line/pie/scatter, theme-aware), file-preview cards for attachments, and a reasoning/"thinking" view (#105)
- **Multi-provider embeddings** — the embedding provider is now selected automatically from the chosen LLM provider: OpenAI → `text-embedding-3-small`, Anthropic → Voyage, Google → Gemini (multimodal text + image) (#105)
- **Marketing & dashboard polish** — new marketing sections (feature bento, comparison table, integrations grid, enterprise-security band, outcomes band, case study, smooth scroll), dashboard sparkline stat cards and a usage timeline chart, an admin message-ratings chart, and a `/dev/components` showcase page. New shared UI primitives: data table, confirm dialog, form field, icon button, section heading (#105)
- **Claude Code skills in generated projects** — a feature-gated `.claude/skills/` toolkit of model-invoked playbooks grounded in the project's conventions: `alembic-migration`, `pytest-suite`, `agent-tool` (adapts to the chosen AI framework), `frontend-feature`, `rag-knowledge`, `background-task` (adapts to the chosen queue), `billing-stripe`, and `channel-bot`. Only the skills matching the selected stack are emitted (e.g. no `frontend-feature` for backend-only projects). Complements the existing `.claude/commands/` and `.claude/rules/`

### Changed

- **Database simplified to PostgreSQL** — PostgreSQL (async) is now the single supported database. The migration history, seed command, and Makefile targets are PostgreSQL-only; SQLModel and the example-CRUD scaffold simply require PostgreSQL now (#105)
- **Charts consolidated** — the separate `enable_antv_charts` option is gone; charting is covered by `enable_charts` (native chart tool + web rendering) (#105)

### Removed

- **CrewAI framework** — the generator now offers **5** AI frameworks (PydanticAI, PydanticDeep, LangChain, LangGraph, DeepAgents). CrewAI's older `opentelemetry-sdk` pin conflicted with current Logfire, and the option is dropped (#105)
- **MongoDB and SQLite database backends** — `--database` now accepts `postgresql` or `none`. Projects needing those engines should pin a generator ≤ 0.2.12 (#105)
- **`enable_antv_charts`** flag (folded into `enable_charts`) (#105)

### Fixed

- **Frontend Docker build (`make dev-frontend`) failed with `"/app/public": not found`** — the standalone runner stage copies `frontend/public`, but Next.js never created the directory when there were no static assets. Ship `frontend/public/.gitkeep` so the directory always exists in the build context (#103, #105)

## [0.2.12] - 2026-06-17

### Added

- **Deep Research mode** (`enable_deep_research`, `--deep-research`, PydanticAI only) — turns the assistant into a deep-research agent: a TODO planner (`pydantic-ai-todo`), parallel researcher/analyst/writer subagents (`subagents-pydantic-ai`), and an automatic context manager (`summarization-pydantic-ai`). The planner clarifies scope, plans the work, delegates web research to subagents, and composes a cited report; progress streams to a dedicated live research panel (plan checklist, subagent status cards, context-usage meter) while the final report streams back as a normal message. TODO state persists in PostgreSQL when available, else in memory. Activated at runtime with `ENABLE_DEEP_RESEARCH=true`; a client can opt a single turn out with `deep_research=false`. Gated behind the new flag and PydanticAI-only by a config validator — when off, the template generates exactly as before. Ships with a stop control and a per-turn research store in the web chat (#90)

### Fixed

- **`make install` failed with `Failed to spawn: pre-commit`** — dev tools (`pytest`, `ruff`, `ty`, `pre-commit`, …) lived under `[project.optional-dependencies].dev`, which uv only installs via its deprecated `dev`-extra special-casing; on uv versions where `uv sync --dev` targets the PEP 735 group instead, they were skipped entirely. Moved them to `[dependency-groups]` so `uv sync` / `uv sync --dev` install them deterministically and `--no-dev` (prod Dockerfile) still excludes them (#95, #101)
- **`make docker-db` (and the other `docker-*` / `docker-prod-*` / `docker-redis` targets) errored `docker-compose: No such file or directory`** — those recipes shelled out to the legacy Compose v1 binary while the dev/quickstart targets already used Compose v2. Every recipe now invokes `docker compose`; the `docker-compose.*.yml` filenames are unchanged (#96, #100)
- **Frontend Docker build (`make dev-frontend`) failed to build the image** — the Dockerfile copied a `bun.lockb*` glob that never matched the current text `bun.lock` (so `bun install --frozen-lockfile` had no lockfile and errored), the healthcheck shelled out to a `curl` the `oven/bun` image doesn't ship, and the `NEXT_PUBLIC_*` client vars were never passed as build args. Copies `bun.lock*`, passes the public env vars as build args (Dockerfile + compose), probes the healthcheck with bun's `fetch`, chowns the copied `public/`, and guards `parseLoadSkillResult` so `bun run build` type-checks (#97, #99)
- **PydanticDeep OpenAI models** are now routed to the OpenAI Responses API (#93)
- **Taskiq worker and scheduler containers stay healthy**; the taskiq-only worker regression test is removed from celery/arq/none projects so it doesn't linger as an empty file (#94)
- **`ty check` on generated projects** — the admin/user routes for SQLite were sync `def`s that never `await`ed the always-async `UserService`, so they returned un-awaited coroutines (real bug); they are now `async`. The service's id parameters are typed per database (`UUID` for Postgres, `str` for SQLite/MongoDB) via a `UserId` alias, the agent's capability list is typed `list[Any]`, the admin-stats best-effort model imports are feature-gated instead of importing absent modules, and the `AdminService` session is typed `Any` so one implementation serves async/sync. A minimal SQLite project now type-checks clean (0 diagnostics)

### Dependencies

- Pinned `fastapi>=0.135.3,<0.137` in generated backends — FastAPI 0.137 made prefix-less `include_router` reject the documented `@router.get("")` empty-path idiom, breaking every generated project at import (#90)
- Added `pydantic-ai-todo`, `subagents-pydantic-ai`, and `summarization-pydantic-ai` to generated backends when `enable_deep_research` is on (#90)
- Bumped `codecov/codecov-action` 6 → 7 in the CI actions group (#89)

## [0.2.11] - 2026-06-12

### Added

- **AntV advanced-diagram tools + interactive maps** (`enable_antv_charts`, `--antv-charts`) — adds an `mcp-server-chart` Docker sidecar exposing AntV diagram tools (flowchart, mind-map, org-chart, sankey, waterfall, funnel, treemap, radar, histogram, boxplot, dual-axes) and a native `create_map` tool (Leaflet/OpenStreetMap) with a typed `MapMarker` schema that prevents empty-marker validation errors from weaker models. `create_map` is wired into all 6 agent frameworks; the AntV diagrams render server-side via the sidecar. Web chat renders maps with `react-leaflet` (`MapMessage`/`MapLeaflet`) and AntV diagrams as images in the tool-call card. Opt-in and profile-gated — `ENABLE_ANTV_CHARTS=false` by default, sidecar started with `docker compose --profile antv up -d`; for prod self-host GPT-Vis-SSR via `ANTV_VIS_REQUEST_SERVER` instead of AntV's public render backend (#83)
- **`ask_user` tool** (PydanticAI) — the agent can pause a run to put one or more questions to the user and resume with their answers, for intake/setup flows and mid-run clarifications. Backed by a WebSocket pause/resume in `AgentSession` and an interactive multi-step `QuestionPrompt` card in the frontend (numbered options, free-form answers, skip). System-prompt guidance steers the model to use it only when a missing detail would genuinely change what it does next (#88)
- **`run_python` code execution** (`enable_code_execution`, `--code-execution`, PydanticAI only) — a `run_python` tool backed by the `pydantic-monty` sandboxed interpreter. In one tool turn the model can compute projections/aggregations and call `create_chart`/`create_map`/`current_datetime` directly from inside the sandbox; visualizations created in-code stream to the session as live, persisted interactive cards (the same `tool_call`/`tool_result` pair as a direct call). Restricted stdlib (`math`, `asyncio`, `json`, `datetime`, `re`); activated at runtime with `ENABLE_CODE_EXECUTION=true`. Temporary shim until PydanticAI's official `CodeExecutionToolset` ships (#88)
- **Skills system** (`enable_skills`, `--skills`, PydanticAI only) — a `pydantic-ai-skills` `SkillsToolset` that loads `SKILL.md` files from `backend/skills/` as agent tools (the model picks a skill, then follows its instructions). Ships the loader only — drop your own skills in; the toolset no-ops when the directory is empty. Frontend renders `load_skill`/`list_skills` tool calls as clean skill cards. Pairs with code execution for skills that compute (#88)

### Fixed

- **MCP connection leak in CrewAI** — `get_antv_crewai_tools` now memoizes the started MCP adapter so it's started once per process, not once per request (#83)
- **Per-request event-loop blocking in LangChain/LangGraph/DeepAgents** — AntV tool discovery is memoized so `_run_sync` only blocks on the first request (#83)
- **antvis-chart Docker healthcheck** — plain `wget` was rejected by the streamable-HTTP endpoint; replaced with a `node` one-liner. Added coordinate-bounds validation to `MapSpec._validate_center` (matching per-marker validation) and removed the dead `parse_map_spec` export (#83)
- **Streamed tool-call args could be a raw string** — `agent_session` now uses `args_as_dict(raise_if_invalid=False)` so tool-call cards always receive a dict; a stray/duplicate `ask_user_response` frame (e.g. after a reconnect) is dropped instead of surfacing a spurious "Empty message" error (#88)

### Changed

- **Generated-project ruff tests run via `uvx`** — `test_template_integration.py` / `test_message_ratings.py` invoke `uvx ruff` from the project's `backend/` dir (matching the post-gen hook) instead of `uv run ruff`, avoiding a stray `VIRTUAL_ENV` breaking local runs. New matrix configs `pydantic_ai_code_execution` and `pydantic_ai_skills` so both new paths are linted + type-checked in CI (#88)

### Removed

- **`ai_agent_test/` generated snapshot** — removed the 710-file generated project that was committed to the repo root; it only served to confuse Renovate and tooling (the `template/` source is the durable artifact). Added to `.gitignore`

### Dependencies

- `pydantic-monty>=0.0.18` and `pydantic-ai-skills>=0.11.0` added to generated backends when `enable_code_execution` / `enable_skills` are on; `react-leaflet` added to the template frontend and an `mcp-server-chart` sidecar to the compose files when `enable_antv_charts` is on

## [0.2.10] - 2026-05-27

### Added

- **Frontend `PageHero` component** — shared `components/dashboard/page-hero.tsx` (151 lines) used by admin, billing, settings, KB, organizations, and dashboard pages so headers share a single typographic rhythm and breadcrumb pattern instead of each page hand-rolling its own
- **Chat controls panel** — new `components/chat/chat-controls.tsx` (586 lines) consolidates model picker, knowledge-base toggles, and conversation settings into one panel. Replaces the split `chat-settings.tsx` (deleted) and `kb-selector.tsx` (deleted) — fewer UI surfaces, no more duplicate KB lookups
- **Auth screens redesigned** — login, register, reset-password, and forgot-password forms now use a split-screen layout (product pitch on the right, form on the left), proper OAuth divider, and consistent form spacing. Generated `(auth)/layout.tsx` + `magic-link-sent/page.tsx` updated to match

### Changed

- **Marketing site refreshed** — hero, pricing teaser, final CTA, marketing footer rebuilt with cleaner typography, monthly/annual toggle on pricing, and configurable footer columns (`footer-config.ts`)
- **Knowledge bases page redesigned** — `kb/kb-list.tsx` rewritten (266-line refactor) with card layout, per-base actions, and clearer empty-state copy
- **Dashboard / admin / settings / billing pages** — every page header migrated to the new `PageHero`; layout, sidebar, and command palette tightened. Globals CSS adjusted for the new spacing scale
- **README** — banner image at the top replaced with the live chat demo video so the first thing a visitor sees is the product running; merged the separate "web search" and "chart generation" demos into one (the new demo covers both); refreshed every product screenshot from `assets/new2/`; pruned ~40 unused assets (`assets/new/`, `assets/chat/`, old marketing PNGs, button SVGs)

### Fixed

- **No-AI projects (`use_ai=False`) failed to build** — generator now removes every AI-only surface that previously leaked through and broke imports: `conversation` / `conversation_share` / `message_rating` / `user_slash_command` models + repos + services, the `agent`, `admin_conversations`, `admin_ratings`, and `me_slash_commands` routes, and the corresponding frontend pages (`chat/`, `admin/conversations`, `admin/ratings`, `settings/slash-commands`), API proxies, and data hooks. RAG-off projects also drop the KB UI (`components/kb`, `app/api/kb`, `(dashboard)/kb`, `use-knowledge-bases.ts`, `types/knowledge-base.ts`) so `next build` no longer fails on orphaned imports
- **Backend modules unconditionally pulled in chat code** — `api/deps.py`, `api/routes/v1/__init__.py`, `db/models/__init__.py`, `repositories/__init__.py`, `schemas/__init__.py`, `services/admin.py`, `repositories/user.py`, and `admin.py` (SQLAdmin) had `use_database`-gated imports of `Conversation`/`Message`/`MessageRating`/etc. that crashed in no-AI projects. Re-gated to `use_ai` and added literal-zero fallbacks for conversation counts in admin stats / user listings (PG, SQLite, MongoDB)
- **CLI: Slack/Telegram channels silently accepted without an AI framework** — `ProjectConfig` validation now rejects `--slack`/`--telegram` when `use_ai` is off (the channel adapters only exist to relay messages to `AgentInvocationService`), with a quick-fix message
- **`temperature` forwarded to reasoning models (gpt-5.5, o1)** — those models reject the parameter entirely, so `AssistantAgent` no longer falls back to `settings.AI_TEMPERATURE`; it stays `None` and is only forwarded to `ModelSettings` when the caller explicitly sets it
- **`reranker.py` Cohere init imported the SDK only to discard it** — replaced the `from cohere import AsyncClient` probe with `importlib.util.find_spec("cohere")` so we check availability without polluting imports
- **Auth components barrel exported password forms in OAuth-only builds** — `components/auth/index.ts` now gates the local-auth form exports behind `use_local_auth`, so OAuth-only projects don't ship dead code that references missing endpoints
- **README demo videos invisible on GitHub** — `<video>` tags from `raw.githubusercontent.com` don't render in the GitHub README viewer (only `<img>` autoplays from raw URLs). Converted both chat and RAG demo `.mp4`s to optimized `.gif`s (960px, 10fps, palette-quantized — 5.8 MB and 3.0 MB respectively, ~80% smaller than source) and switched the README to `<img>` tags. Removed the unused `.mp4` sources
- **Renovate scanned the generated `ai_agent_test/` snapshot** — opened useless PRs against the snapshot's `package.json` / `docker-compose.yml` instead of the actual `template/` source, so every accepted bump would silently revert on the next regeneration. Added `ignorePaths: ["ai_agent_test/**", "**/node_modules/**"]` so future bumps target the template files

### Dependencies

- Generator CI Python pinned to **3.14** (was 3.12) — `.github/workflows/{ci,docs,release}.yml` (#75)
- `aquasecurity/trivy-action` → **v0.36.0** in generated projects' CI (#74)
- `milvusdb/milvus` Docker tag → **v2.6.17** in generated `docker-compose.{dev,prod,}.yml` (#77)
- `qdrant/qdrant` Docker tag → **v1.18.1** in generated `docker-compose.{dev,prod,}.yml` (#78)
- `quay.io/coreos/etcd` Docker tag → **v3.6.11** (Milvus dependency) in generated `docker-compose.{dev,prod,}.yml` (#80)
- `prettier-plugin-tailwindcss` → **^0.8.0** in template frontend `package.json` (#81 bumped only the snapshot; the template source is the durable fix)

## [0.2.9] - 2026-05-17

### Added

- **Chart generation tool** (`enable_charts`) — optional `create_chart` tool letting the agent produce line/bar/pie/area/scatter charts. Returns a validated `ChartSpec` (data, series, custom style/palette/legend/axis) as JSON, so the same payload flows to every surface. Registered in **all 6 agent frameworks** (PydanticAI, LangChain, LangGraph, CrewAI, DeepAgents, PydanticDeep). Web chat renders it interactively with Recharts; Slack/Telegram get a server-side PNG via matplotlib (`charts_channel_png`, gated dep, with a markdown-table fallback). Wizard prompt + `--charts` CLI flag + `enable_charts` cookiecutter var
- **Portable `fetch_url` tool** (`web_fetch_tool`) — SSRF-safe "read this web page" tool for LangChain/LangGraph/CrewAI/DeepAgents (which had no model-native web-fetch). Reuses `app.core.sanitize.validate_webhook_url`, re-validates every redirect hop, caps size/timeout, extracts readable text (BeautifulSoup). PydanticAI/PydanticDeep keep their native `WebFetch`. Closes the gap where `enable_web_fetch` was a silent no-op for those frameworks
- **Web Search & Fetch offered for every agent framework** in the interactive wizard (was PydanticAI-only); CrewAI now actually attaches `search_web`/`fetch_url` to the research agent (they were registered but never used)
- Gated test suites: `test_chart_tool.py`, `test_fetch_url.py`, `test_web_search.py`

### Changed

- **Refreshed default AI models** — OpenAI → `gpt-5.5`, Anthropic → `claude-opus-4-7`, OpenRouter → `anthropic/claude-opus-4-7`, multi-provider → `openai/gpt-5.5` (Google stays `gemini-2.5-flash`). Updated `AI_AVAILABLE_MODELS` (GPT-5.x frontier line; full Claude Opus/Sonnet/Haiku line) and Claude pricing in billing `MODEL_COSTS`; synced `.env`/`.env.example`/docs
- **Rewrote the default agent system prompt** (outcome-first style) — real personality + answering policy + formatting. The RAG variant is no longer a straitjacket: the agent answers general-knowledge questions directly instead of replying "not in the knowledge base", and treats `search_documents` as a tool to use *when relevant* with a retrieval budget and citations
- **`web_search` tool returns structured JSON** (`WebSearchResults`) instead of ad-hoc text, so the chat UI renders clickable titles, domains and snippets (added `parse_web_search`). Fixed stale frontend detection that meant the rich card never showed for LangChain/LangGraph/DeepAgents
- **Removed the `.env.prod` / `.env.prod.example` abstraction** — production now uses the same `backend/.env` as dev (it already contained every variable `.env.prod.example` defined). `docker-compose.prod.yml` reads `env_file: ./backend/.env`; `make prod` checks for `backend/.env` and passes `--env-file backend/.env` to Compose. `.env.prod` removed from `.gitignore`. Migration: move any values from your old `.env.prod` into `backend/.env` (gitignored) on the server
- **Chat UI: ordered message timeline** — a streamed assistant turn now renders as an ordered sequence of parts (thinking → tools → text → …) in true chronological order instead of three fixed slots, so multi-step turns display correctly. Provider-agnostic; CrewAI keeps its multi-message layout
- **Tool-call cards redesigned** — collapsed by default to a clickable bar (tool name + input hint, e.g. the query/URL), expand to the formatted view, `</>` toggle for arguments + raw output. Chart cards auto-expand (they're only useful when visible). New generic fallback renderer displays any newly added backend tool sensibly with no frontend changes; removed the per-tool status icon

### Fixed

- **LangChain/LangGraph/DeepAgents streaming: tool-call arguments were empty in the web UI** — the token-chunk path emitted a premature `tool_call` with `args: {}` and poisoned the shared dedup set, suppressing the complete event. The `updates` stream is now the single source of truth (full args), with no duplicate/empty card
- **Reasoning ("thinking") now streams reliably** — extracted via a shared helper, with a fallback that emits reasoning from the final message for providers that don't stream it as chunks
- **`AIMessageChunk` merge crash** — `Additional kwargs key created_at … unsupported type <class 'float'>` on the OpenAI Responses API. Usage is now summed via `add_usage` instead of merging whole chunks
- **DeepAgents tool calls never fired** — `_stream_update_event` checked the graph node `"agent"`, but `create_deep_agent` (deepagents 0.6.1 → LangChain `create_agent`) names it `"model"`. Tool calls, args and reasoning are now emitted for DeepAgents
- **`KBSelector` infinite `GET /api/kb` request loop** when a workspace has no knowledge bases — a length-based effect re-fired after every empty fetch; replaced with a one-shot ref guard
- **`test_agents.py` was not provider-gated** — it patched OpenAI-only symbols, breaking generation/tests for Anthropic/Google/OpenRouter (and the LangChain branch). PydanticAI now patches the single `_build_model` seam with a real `TestModel`; LangChain patches the provider-correct chat class

## [0.2.8] - 2026-05-11

### Added

- **Email module** (`enable_email`) — Transactional email system with three providers: Resend (async), SMTP (aiosmtplib), and Log (dev/test). Pre-rendered HTML/text templates stored in `emails/compiled/` using `[[variable]]` substitution. `EmailService` facade with convenience wrappers for all email types: welcome, password reset, invitation, payment succeeded/failed, trial ending/expired, subscription canceled/changed, low credits, newsletter welcome
- **Email triggers wired** — `UserService.register()` fires `send_welcome`; `InvitationService.invite()` fires `send_invitation`; billing webhook handlers fire payment/subscription lifecycle emails using Stripe customer data (fail-open — email errors never break webhook processing)
- **Stripe billing — rate limiting per plan** (`enable_rate_limiting`) — Sliding window rate limiter backed by Redis sorted sets (ZADD/ZREMRANGEBYSCORE/ZCARD pipeline) with in-memory fallback. `RateLimitRule` frozen dataclass (per_user, per_org, per_ip, configurable periods); `RateLimitCategory` constants; data-driven plan features override `DEFAULT_RATE_LIMITS`; `make_rate_limit_dep(category)` factory for FastAPI `Depends()`; admin bypass; fail-open on Redis error; HTTP 429 with `Retry-After` header
- **Extended frontend billing dashboard** — `SubscriptionPanel` with 4 states (free/trial/active/canceled), cancel/reactivate dialogs, plan details; `CreditsPanel` with balance display, low-credit alert, top-up button, transaction history with type badges; `/billing/subscription` page with live plan cards; `/billing/credits` page. `useSubscription`, `useCredits`, `usePlans` hooks added to `use-billing.ts`
- **Admin user management** — `GET/PATCH/DELETE /admin/users/{id}` endpoints (requires `is_app_admin` flag). `POST /admin/users/{id}/impersonate` issues a short-lived (1h) JWT token to act as any user — token is returned in the API response. Frontend: `/admin/users` page with search, role toggle, delete, and impersonation-token-to-clipboard button; `/admin/page.tsx` overview with navigation cards; `useAdminUsers` hook
- **UsageService** — `app/services/usage.py` — records `UsageEvent` in DB, computes credits via `usage_to_credits()`, debits org credits via `CreditService.debit()`. All 3 DB variants (PG/SQLite/MongoDB). Wiring point for agent invocations
- **Usage dashboard** — `/billing/usage` frontend page: total credits/tokens/calls KPI cards, recharts bar chart of credits by model, per-model breakdown table, CSV export of credit transaction history
- **Anomaly detection service** (`enable_usage_anomaly_detection`) — `anomaly_detection.py` — spike detection: current-hour credits vs rolling 24h average; alert if ratio > 3×; optional Slack webhook notification (`enable_slack_alerts`, `SLACK_ANOMALY_WEBHOOK_URL` setting)
- **Newsletter signup** (`enable_newsletter_signup`) — `POST /newsletter/signup` endpoint; `NewsletterSignup` React component; sends welcome email via email service
- **Changelog page** (`enable_changelog`) — `/changelog` route with release history, change type badges (feat/fix/improvement/chore)
- **Pricing comparison page** (`enable_comparison_pages`) — `/pricing` route fetches live plans from API; monthly/annual toggle; plan feature list; trial days display; "Get Started" CTA

### Fixed

- **Email templates excluded by `.gitignore`** — Renamed `emails/dist/` → `emails/compiled/` to avoid the generic `dist/` gitignore rule silently stripping all compiled templates from generated projects
- **`billing/facade.py` imports `usage_event_repo` unconditionally** — `app.repositories.usage_event` was imported in both PostgreSQL and SQLite branches regardless of `enable_credits_system`; projects generated with `enable_billing=True` + `enable_credits_system=False` crashed on startup with `ImportError`
- **`func.case()` SQLAlchemy 2.x crash in `message_rating_repo`** — `func.case((condition, value), else_=0)` raised `TypeError: Function.__init__() got an unexpected keyword argument 'else_'`; replaced with `case(...)` imported directly from `sqlalchemy`
- **Credits/usage dashboard widgets shown when `enable_credits_system=False`** — `UsageTimeline` and `TopModels` components were gated on `enable_billing` instead of `enable_credits_system`; they fetch from `/billing/me/credits/usage/...` endpoints that don't exist without the credits system, producing silent 404s and empty charts
- **MongoDB projects: `admin.py` used SQLAlchemy `func.count`** — `AdminService` now has separate `{%- if use_postgresql or use_sqlite %}` / `{%- elif use_mongodb %}` branches; the MongoDB branch uses Beanie `Document.find().count()` and returns `[], 0` for Stripe events (not applicable to MongoDB projects)
- **Admin `GET /conversations/{id}` returned 404 for other users' conversations** — `get_conversation` and `list_messages` route handlers now resolve `uid = None if current_user.role == "admin" else current_user.id`; `user_id=None` in the service layer bypasses the ownership check, allowing admins to read any conversation
- **Frontend `?id=` URL param blocked by ownership guard** — `fetchConversations` removed the `response.items.some(c => c.id === urlId)` check before loading messages; any `?id=` value is now attempted unconditionally and a 404/403 from the server clears the ID silently (non-admins are still protected server-side)
- **Admin conversations page "View" opened an in-page read-only preview** — Replaced the custom preview panel with a `Link` to `/chat?id=<conversation_id>`; admins now land on the full chat UI with the real message history
- **Admin ratings page "Export" returned 404** — `window.open` was targeting `/api/v1/admin/ratings/export` (direct backend path) instead of `/api/admin/ratings/export` (the Next.js proxy route that attaches the auth cookie)
- **CI integration test failures** — `generated_project_full` fixture now sets `frontend=FrontendType.NEXTJS` (required when `oauth_provider=GOOGLE`); MongoDB repository `__init__.py` import guard split so only SQL-only repos (`chat_file_repo`) are excluded from MongoDB projects; SQLite auth test fixed a mock type mismatch (`MagicMock` → `AsyncMock`)

## [0.2.7] - 2026-04-26

### Fixed

- **Disabled features no longer leak generated files** — `post_gen_project.py` now removes channel adapters/routes/services/repos/schemas/models/commands/migrations when `use_telegram` and `use_slack` are both off, RAG sync infrastructure (`sync_log`, `sync_source`, `rag_document` files) when RAG is off, DeepAgents project scaffolding when not selected, leftover test stubs for disabled modules, and empty `docker-compose` placeholders when Docker is disabled
- **`agent.py` (DeepAgents): undefined `file_ids`** — WebSocket payload parsing now extracts `file_ids = raw_data.get("file_ids", [])` before use (previously raised `NameError` at runtime)
- **`agent.py` (CrewAI): missing `ConversationUpdate` import** — Added to imports so title-update path no longer crashes
- **`rag.py`: `complete_sync` called on wrong service** — Was invoked on `SyncSourceService`; now correctly routed to `RAGSyncService`
- **`IngestionService()` instantiated without required args** — Added `IngestionService.from_settings()` classmethod factory; routes/commands/workers now use it
- **`message_rating_repo` not exported** — Added to `app/repositories/__init__.py`; admin ratings flow no longer fails on import
- **`ConversationService.get_conversation_with_messages` missing on SQL backends** — Previously only existed on MongoDB; added to PostgreSQL + SQLite variants
- **`ProjectService.list` / `ChannelBotService.list` shadowed builtin `list`** — Renamed to `list_for_user()` / `list_all()` (with `find_active()` and `list_by_platform()` helpers added)
- **`ModuleNotFoundError: No module named 'app.rag.connectors'`** — `post_gen_project.py` was deleting the entire `rag/connectors/` directory when neither Google Drive nor S3 ingestion was enabled, but `sync_source.py` always imports `CONNECTOR_REGISTRY` from that package. Directory is now preserved; only the individual connector files are removed
- **Empty `tasks/channel.py` generated for projects without Telegram or Slack** — Added removal to the `not use_telegram and not use_slack` post-gen hook block
- **Frontend TypeScript strict mode errors** — Fixed 26 `noUncheckedIndexedAccess` and `undefined`-assignability violations across 7 files: `rag/page.tsx` (array index + file loop guard), `chat-container.tsx` (model selector `useState` type + fallback), `chat-input.tsx` (speech recognition result guard), `tool-approval-dialog.tsx` (`editedArgs` index fallback), `tool-call-card.tsx` (regex capture group fallbacks), `breadcrumb.tsx` (route segment index), `theme-toggle.tsx` (persisted zustand state hydration)

### Changed

- **Strict layered architecture enforced across the template** — Routes call services only (via FastAPI `Depends`); services call repositories only; repositories are the sole layer permitted to talk to the database. Worker tasks, channel adapters, CLI commands, and webhook handlers no longer perform raw DB operations
  - `admin_conversations.py` rewritten to use `ConversationSvc.admin_list_with_users()` and `UserSvc.admin_list_with_counts()`
  - `telegram_webhook.py` / `slack_webhook.py` use `ChannelBotSvc` via `Depends` instead of opening their own DB sessions (`bot_service.find_active(bot_id)`)
  - `agent.py` uses `conv_service.list_attached_files(file_ids)` instead of raw `select(ChatFile)` queries
  - Worker tasks (`rag_tasks._run_ingestion`, `_run_sync`, `_update_status`, `_update_sync_log`) refactored onto the service layer
  - CLI commands (`commands/channel.py`, `seed.py`, `rag.py`) refactored with a `_channel_service()` context-manager helper
  - All `self.db.execute/commit/add` removed from services; sessions auto-commit via `get_db_session`/`get_db_context`/`get_worker_db_context`
- **Repositories expanded with the queries services now need** — `conversation.admin_list_with_users()` + `export_chunk()` (3 backends); `user.list_query()` + `admin_list_with_counts()` + `delete_non_admins()` + `has_any()` (3 backends); `chat_file.get_many()` + `link_to_message()`; `message_rating.get_user_ratings_for_messages()` + `get_rating_counts_for_messages()` + `get_ratings_with_users_for_messages()`; `webhook.create_delivery()` + `save_delivery()`; `sync_log.create(sync_source_id=...)`; `rag_document.delete_by_collection()`
- **Routes thinned to HTTP-only layer** — All response-object construction moved from route handlers into services:
  - `admin_ratings.py`: CSV/JSON export helpers (`_csv_escape`, `_csv_row_values`, `_serialize_csv_row`, `_validate_export_format`, `_export_disposition`, `_json_export_response`, `_stream_csv_sync/async`) and `export_ratings()` moved to `MessageRatingService`. Route reduced to a single `return await rating_service.export_ratings(...)` call
  - `sessions.py`: `SessionRead` construction in `list_sessions` moved to `SessionService.list_sessions()` which now returns `SessionListResponse` directly
  - `rag.py`: `SyncSourceRead(...)` construction moved to `SyncSourceService._to_read()` (used by `list_sources`, `create_source`, `update_source`); `RAGSyncLogItem(...)` moved to `RAGSyncService.list_sync_logs()` → returns `RAGSyncLogList`; `RAGTrackedDocumentItem(...)` moved to `RAGDocumentService.list_documents()` → returns `RAGTrackedDocumentList`; `RAGDocumentItem(...)` moved to `BaseVectorStore.get_document_list()`; `ConnectorInfo/ConnectorList` construction moved to `SyncSourceService.list_connectors()`
  - `oauth.py`: Three-step find/link/create OAuth flow extracted to `UserService.get_or_create_oauth_user()` (all 3 DB variants); `google_callback` reduced to a single service call
  - `users.py`: Raw `Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]` replaced with `CurrentAdmin` alias throughout; `Depends(get_current_user)` replaced with `CurrentUser`
  - Unused `current_user`/`admin_user` route parameters that only provided auth enforcement renamed to `_: CurrentAdmin` / `_: CurrentUser` across all affected routers
- **`agent.py`: inline imports moved to module level** — `from datetime import datetime, UTC`, `import json`, `from pydantic_ai.messages import BinaryContent`, `from app.services.file_storage import get_file_storage`, and pydantic_deep session/project service imports were scattered across WebSocket handler bodies; all moved to the top of their respective framework blocks
- **`conversations.py`**: Direct field mutation `data.user_id = current_user.id` replaced with `data = data.model_copy(update={"user_id": current_user.id})` (Pydantic v2 safe update); inline `ConversationShareSvc` import moved to module level; section-divider comments (`# Message Rating Endpoints`, `# Sharing endpoints`) removed

### Security

- **Generator dependency floors raised** — `pyproject.toml` runtime/dev/docs floors bumped to currently-used versions: `click>=8.3.0`, `cookiecutter>=2.7.0`, `rich>=15.0.0`, `questionary>=2.1.0`, `pydantic>=2.13.0`, `pydantic-settings>=2.13.0`, `email-validator>=2.3.0`, `pytest>=9.0.0`, `pytest-cov>=7.0.0`, `ruff>=0.14.0`, `ty>=0.0.31`, `pre-commit>=4.0.0`, `mkdocs>=1.6.1`, `mkdocs-material>=9.7.0`, `pymdown-extensions>=10.20`. Brings in upstream security/bug fixes
- **`pip-audit` CI: CVE-2026-3219 (pip 26.0.1) added to ignore list** — Vulnerability in `pip` itself with no fix version published yet; documented in the workflow alongside the other ignored CVEs

### Added

- **Config validator: CrewAI + Logfire combination rejected** — Raises `ValueError` at config time; documents an upstream OpenTelemetry/logfire ≥ 4.30 conflict with CrewAI
- **Conditional pydantic pin for CrewAI** — Generated `pyproject.toml` pins `pydantic[email]>=2.11.0,<2.12` when CrewAI is selected (CrewAI is incompatible with pydantic 2.12)
- **Stricter `ty` rules in generated `pyproject.toml`** — `unknown-argument`, `invalid-await`, `invalid-context-manager`, `missing-argument`, `not-iterable`, `invalid-return-type`, `invalid-type-form` promoted to `warn`
- **Integration test matrix** — `TestGeneratedTemplateMatrix` now exercises 14 framework/database/RAG/channel combinations (project names prefixed with `matrix_` to avoid package-name collisions). Suite: **405 passed, 3 skipped**
- **`services/health.py`** — New `build_health_response(status, checks, details)` helper extracted from `health.py` route; `health.py` now imports and calls it instead of defining it inline
- **`services/agent.py`** — New `AgentConnectionManager` class extracted from all 5 AI framework blocks in `agent.py`. Single canonical implementation shared via `from app.services.agent import AgentConnectionManager`
- **`UserService.get_or_create_oauth_user(provider, provider_id, email, full_name)`** — Encapsulates the find-by-oauth-id → find-by-email → link-or-create orchestration that was previously duplicated inline in all three `google_callback` route handlers
- **`SyncSourceService._to_read(source)` / `list_connectors()`** — `_to_read` converts a `SyncSource` ORM model to `SyncSourceRead` (including `json.loads` for SQLite config); `list_connectors()` is a `@staticmethod` that iterates `CONNECTOR_REGISTRY` and returns `ConnectorList` without requiring a DB session
- **`BaseVectorStore.get_document_list(collection_name)`** — Concrete (non-abstract) method on the base class; calls `get_documents()` and maps to `RAGDocumentList`. All vector store implementations (Milvus, Qdrant, ChromaDB, pgvector) inherit it automatically

## [0.2.6] - 2026-04-18

### Added

- **Message rating feature** — Users can rate AI assistant messages with thumbs up/down and optional feedback comments. Toggle behavior: clicking same button removes rating, clicking opposite button changes it. Only assistant messages are rateable
  - **Backend:** `MessageRating` model (PostgreSQL/SQLite/MongoDB, SQLAlchemy/SQLModel), repository + service + schema layers, `POST /conversations/{id}/messages/{messageId}/rate` endpoint. Ratings persisted to `message_ratings` table with unique constraint per user/message and `CHECK` constraint on rating values (1/-1). Optional comment field (up to 2000 chars). Supports all 3 database variants
  - **Admin API:** `GET /admin/ratings` (paginated list with filters), `GET /admin/ratings/summary` (aggregate stats), `GET /admin/ratings/export` (CSV/JSON download). `GET /admin/conversations` (paginated listing). All admin routes require admin role
  - **WebSocket integration:** Ratings data (user's rating, like/dislike counts) included in streaming message events and conversation history loading
  - **Frontend:** `RatingButtons` component with like/dislike icons, comment dialog on dislike, optimistic count updates. Integrated into `message-item.tsx` for assistant messages. Admin pages for ratings management and conversations listing
  - **Frontend proxy routes:** `POST/DELETE /api/conversations/{id}/messages/{messageId}/rate` proxies, `GET /api/v1/admin/ratings`, `/summary`, `/export` routes, `lib/admin-auth.ts` utility for admin API calls
  - **Documentation:** `docs/howto/use-ratings.md` user guide, updated `docs/architecture.md` and `docs/permissions.md`
  - **Tests:** 660+ lines of tests covering config validation, model generation, repository/service/route layers, all database variants

### Security

- **Removed JWT from WebSocket URL query string** — WS auth now uses `Sec-WebSocket-Protocol` (`access_token.<JWT>`) instead of `?token=...`, so tokens no longer leak into access logs or `Referer` headers. Backend echoes the chosen application subprotocol back on `accept()`
- **Removed `/api/auth/token` httpOnly downgrade endpoint** — `access_token` is now returned in the body of `/auth/login`, `/auth/me`, and `/auth/refresh` proxy responses and kept in memory only (never persisted)
- **CSV export injection hardening** — Admin ratings CSV export now prefixes cells starting with `= + - @` (or tab/CR) with a single quote, preventing formula execution when opened in Excel/Sheets
- **Rating comments stored raw** — Dropped `html.escape` from comment sanitization; comments are rendered via React (auto-escaped) and CSV-escaped separately, so the DB stores original text

### Changed

- **Streaming admin ratings CSV export** — `/admin/ratings/export?export_format=csv` now streams row-by-row via an async/sync generator instead of buffering the whole dataset in memory

## [0.2.5] - 2026-04-12

### Added

#### Conversation Sharing + Admin Conversation Browser

- **Conversation sharing** — Share conversations with other users (direct share by user ID) or generate public share links (UUID4 token). Permission levels: `view` (read-only) and `edit` (can add messages). Owner can share, list shares, and revoke access. Recipients can also leave shared conversations
- **`ConversationShare` model** — New DB model across all 5 variants (PG+SQLModel, PG+SQLAlchemy, SQLite+SQLModel, SQLite+SQLAlchemy, MongoDB). Fields: conversation_id, shared_by, shared_with, share_token, permission. Unique constraint on (conversation_id, shared_with)
- **Share endpoints** — `POST /conversations/{id}/shares` (share or generate link), `GET /conversations/{id}/shares` (list shares, owner only), `DELETE /conversations/{id}/shares/{share_id}` (revoke), `GET /conversations/shared-with-me` (list shared with current user), `GET /conversations/shared/{token}` (public access, no auth)
- **Admin conversation browser** — Admin-only endpoints: `GET /admin/conversations` (paginated, searchable by title, filterable by user_id, includes message_count and user_email), `GET /admin/conversations/{id}` (full conversation with messages), `GET /admin/conversations/users` (user list with conversation counts, searchable)
- **Share dialog component** — Frontend dialog to share conversations: user search input, permission dropdown (view/edit), generate share link with copy button, list current shares with revoke
- **Admin conversations page** — `/admin/conversations` page with tabs (Conversations/Users), table views, search, click-to-preview (read-only), user → conversations drill-down
- **Public shared page** — `/shared/[token]` SSR page renders conversation transcript without sidebar or input. Clean read-only view using server-side fetch
- **Frontend hooks** — `useConversationShares` (share, fetch, revoke, shared-with-me) and `useAdminConversations` (admin list, users, detail preview)

#### Slack Multi-Bot Channel Integration

- **Slack adapter** — `SlackAdapter(ChannelAdapter)` supporting both Events API (production webhook) and Socket Mode (development polling). Thread-aware: Slack thread replies fold `thread_ts` into `platform_chat_id` (`{channel}:{thread_ts}`) so each thread gets its own `ChannelSession` and `Conversation`
- **Events API webhook** — `POST /slack/{bot_id}/events` endpoint handles Slack URL verification challenge and event dispatch. Signature verified via HMAC-SHA256 (`v0={timestamp}:{body}`) with 5-minute replay-protection window. Fire-and-forget background dispatch meets Slack's 3s response requirement
- **Socket Mode (dev)** — Supervised polling loop with `slack-sdk`'s `SocketModeClient`. Bot-scoped tasks with 5s back-off restart on crash. Lifecycle managed in app lifespan alongside Telegram polling
- **`use_slack` cookiecutter variable** — Gates all Slack infrastructure. CLI interactive prompt for "Enable Slack integration" added alongside Telegram. Enables: `slack-sdk>=3.35.0`, Slack-specific config vars (`SLACK_SIGNING_SECRET`, `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`), `POST /slack/{bot_id}/events` route
- **Shared channel infrastructure expanded** — All 14 shared files (`ChannelAdapter` base, models, repos, services, router, commands) gated from `use_telegram` → `use_telegram or use_slack` so both platforms share the same session/identity/bot management layer
- **Group chat concurrency control** — Per-chat `asyncio.Lock` (keyed on `{bot_id}:{platform_chat_id}`) in `ChannelMessageRouter.route()`. Serializes concurrent messages from the same group/channel to prevent: duplicate `ChannelSession` creation (DB constraint violation), interleaved agent invocations on the same `Conversation`, and rate-limit counter races. Affects both Telegram groups and Slack channels

#### Telegram Multi-Bot Channel Integration

- **Full Telegram bot integration** — Multi-bot support with polling and webhook delivery modes, encrypted token storage (Fernet), in-memory rate limiting (token-bucket per user per bot), and role-based access policies (open, whitelist, jwt_linked, group_only)
- **Channel adapter architecture** — Abstract `ChannelAdapter` base class with concrete `TelegramAdapter` (aiogram v3). Adapter registry pattern for future platform extensions (Discord, Slack, etc.)
- **Channel message router** — 8-step processing pipeline: load bot, check access, handle commands (/start, /new, /help, /link, /unlink, /project), resolve identity, resolve session, rate-limit, invoke agent, send reply
- **3 new DB models** — `ChannelBot` (encrypted token, access policy, webhook config), `ChannelIdentity` (platform user ↔ app user linking with link codes), `ChannelSession` (bot+chat → conversation mapping)
- **Admin API routes** — Full CRUD for bot management (`/channels/bots`), activate/deactivate, webhook register/delete, session listing. All endpoints require admin role with proper `ChannelBotCreate`/`ChannelBotUpdate`/`ChannelBotRead` schemas
- **Webhook endpoint** — `POST /telegram/{bot_id}/webhook` with signature verification, fire-and-forget async processing to stay within Telegram's 5s timeout
- **Supervised polling** — Per-bot polling loop with 5s back-off restart on crash, managed via lifespan startup/shutdown
- **CLI commands** — `channel-list-bots`, `channel-add-bot`, `channel-webhook-register`, `channel-webhook-delete`, `channel-test-message`
- **`AgentInvocationService`** — Framework-agnostic non-streaming agent invocation for all 6 AI frameworks, used by Telegram channel router
- **`use_telegram` cookiecutter variable** — Gates all Telegram code via Jinja2 conditionals. CLI interactive prompt added

#### PydanticDeep Framework (6th AI Framework)

- **PydanticDeep integration** — Deep agentic coding assistant built on pydantic-ai with filesystem tools (ls, read_file, write_file, edit_file, glob, grep), task management, subagent delegation, skills system, memory persistence, and context discovery
- **Sandbox environment selection in CLI** — New interactive prompt when selecting DeepAgents or PydanticDeep:
  - **PydanticDeep:** Docker sandbox (default), Daytona workspace, State (in-memory)
  - **DeepAgents:** Docker sandbox (default), State (in-memory)
- **`sandbox_backend` cookiecutter variable** — Configures `PYDANTIC_DEEP_BACKEND_TYPE` / `DEEPAGENTS_BACKEND_TYPE` in generated Settings
- **File upload to sandbox workspace** — When users attach files in chat, files are written to the Docker/Daytona sandbox via `docker cp` (or backend API) so the agent can access them with `read_file`. File paths are automatically included in the user message. Falls back to inline content for StateBackend
- **Project-scoped WebSocket endpoint** — `ws/projects/{project_id}/chats/{conversation_id}` for shared Docker containers per project

#### PydanticAI Capabilities

- **WebSearch and WebFetch as default capabilities** — All PydanticAI agents now include `WebSearch()` and `WebFetch()` capabilities. Provider-adaptive: uses builtin when the model supports it natively, falls back to DuckDuckGo (search) and markdownify (fetch)
- **pydantic-ai bumped to >=1.80.0** with `duckduckgo` and `web-fetch` extras for local fallback support

### Changed

- **Removed LocalBackend from PydanticDeep** — Server-side filesystem backends are not appropriate for web apps. Only Docker/Daytona sandbox and StateBackend are supported
- **Removed `PYDANTIC_DEEP_WORKSPACE_DIR` setting** — No longer needed without LocalBackend

### Fixed

- **pgvector `vectorstore.py` f-string SyntaxError** — `metadata JSONB DEFAULT '{}'::jsonb` was rendered inside a Python f-string, causing `SyntaxError: f-string: empty expression not allowed` in generated projects using pgvector. Escaped the braces so the f-string renders `{}` literally. (#65)

#### Telegram Channel Code Review Fixes

- **`channels/router.py`** — Made `route()` always `async def` (was sync for SQLite, causing `asyncio.get_event_loop().run_until_complete()` crash). Removed broken `_handle_command_sync`, `_resolve_identity_sync`, `_resolve_session_sync` methods. Added SQLite branches to all async methods
- **`channels/router.py`** — Fixed `/link` command: replaced non-existent `channel_link_repo.redeem_code()` with `channel_identity_repo.get_by_link_code()`. Code is invalidated after use
- **`channels/router.py`** — Fixed `bot.encrypted_token` → `bot.token_encrypted` in `_send_reply()`. Fixed `bot.system_prompt` → `bot.system_prompt_override` and `bot.model_override` → `bot.ai_model_override`
- **`channels/router.py`** — Fixed MongoDB import paths: `from app.db.models.channel import` → `from app.db.models.channel_identity import` / `from app.db.models.channel_session import`
- **`channels/router.py`** — Added `_parse_policy()` helper to normalize `access_policy` from JSON string (SQLite) or dict (PostgreSQL/MongoDB)
- **`channels/telegram.py`** — Removed module-level singleton that conflicted with lifespan-managed adapter in `main.py`. Fixed SQLite `_handle_update` to `await router.route()`
- **`api/routes/v1/channels.py`** — Fixed all service method names (`service.list_bots()` → `service.list()`, etc.). Replaced `data: Any` with proper `ChannelBotCreate`/`ChannelBotUpdate` schemas. Added `response_model` to all endpoints. Made SQLite webhook routes `async` (was using `asyncio.run()` inside running loop)
- **`api/routes/v1/telegram_webhook.py`** — Fixed SQLite branch to `await router.route()` (route is now always async)
- **`services/channel_bot.py`** — Generate `webhook_secret` via `secrets.token_urlsafe(32)` when `webhook_mode=True` (was always `None`). Added `list_sessions()` method to all 3 backends
- **`repositories/channel_session.py`** — Added `list_by_bot()` and `count_by_bot()` functions to all 3 backends
- **`commands/channel.py`** — Fixed `bot.encrypted_token` → `bot.token_encrypted`. Fixed `channel_bot_repo.list_all(platform=...)` (no such parameter) → conditional `get_by_platform()`. Fixed `encrypted_token=` → `token_encrypted=` in create

### Tooling

- **CI: MongoDB job** — Added missing `ty check` step (was present in minimal and PostgreSQL jobs but absent from MongoDB)
- **Template pre-commit** — Bumped ruff-pre-commit from `v0.8.0` to `v0.15.0` (consistent with `pyproject.toml >=0.15.0`)

### Dependencies

- **pydantic-ai** `>=1.77.0` → `>=1.80.0` (all providers + pydantic-deep)
- **pydantic-ai extras**: Added `duckduckgo` and `web-fetch` extras for WebSearch/WebFetch local fallback
- **aiogram** `>=3.17,<4.0` (new — Telegram adapter)
- **slack-sdk** `>=3.35.0` (new — Slack Web API, Socket Mode, Events API)
- **cryptography** `>=44.0.0` (new — Fernet token encryption, gated under `use_telegram or use_slack`)

## [0.2.4] - 2026-04-09

### Security

- **SSRF protection for webhook URLs (CWE-918)** — Added `validate_webhook_url()` in `app/core/sanitize.py` that blocks private/reserved/loopback/link-local/multicast/CGNAT IPs, validates DNS resolution against internal networks, rejects non-http(s) schemes and URLs with credentials. Validation enforced at webhook create, update, and delivery time across all three database variants (PostgreSQL, SQLite, MongoDB). Includes `SSRFBlockedError` exception with proper 422 responses and 39 unit tests. (PR #62)

## [0.2.3] - 2026-04-05

### Added

- **`.claude/` directory in generated projects** — Full Claude Code project structure so generated projects work as AI-native codebases out of the box
  - **`settings.json`** — Auto-allow permissions for safe operations (Read, Glob, Grep, git, pytest, ruff, ty, alembic)
  - **`rules/architecture.md`** — Layered architecture patterns (Routes → Services → Repositories), DI with `Annotated` aliases, `db.flush()` convention, domain exceptions
  - **`rules/code-style.md`** — Type hints (`str | None`), naming conventions table, import ordering (stdlib → third-party → local), ruff config
  - **`rules/schemas-models.md`** — Pydantic v2 `*Create/*Update/*Read/*List` pattern, `BaseSchema` with `ConfigDict`, SQLAlchemy `Mapped[]` columns, `TimestampMixin`
  - **`rules/exceptions-security.md`** — Domain exception hierarchy (`AppException` → `NotFoundError`, etc.), JWT/bcrypt patterns, `RoleChecker`, API key verification
  - **`rules/api-conventions.md`** — REST design, pagination (`Query(ge=0, le=100)`), auth deps (`CurrentUser`/`CurrentAdmin`/`ValidAPIKey`), response format, file upload
  - **`rules/testing.md`** — Async test patterns, `httpx.AsyncClient`, fixtures, exception testing with `pytest.raises`
  - **`rules/frontend.md`** — Next.js 15 App Router, Server Components, Tailwind conventions (auto-removed when frontend disabled)
  - **`commands/review.md`** — `/project:review` slash command: checks changes against architecture, types, security, and runs linting
  - **`commands/add-endpoint.md`** — `/project:add-endpoint` slash command: scaffolds full CRUD (schema → model → repo → service → deps → route → migration → test)
  - **`commands/fix-issue.md`** — `/project:fix-issue` slash command: traces through layers, fixes, tests, lints
- **Enhanced `CLAUDE.md`** — Rewritten with precise patterns from the actual codebase: architecture layers, DI pattern, schema conventions, exception table, response format examples, key conventions

### Changed

- **Replaced mypy with [ty](https://github.com/astral-sh/ty)** — Astral's Rust-based type checker (from the makers of ruff/uv). Updated across: `pyproject.toml`, Makefile, CI (GitHub Actions + GitLab CI), pre-commit config, `.gitignore`
- **Dependency version bumps** — All generated project dependencies updated to latest stable versions:
  - **Core:** FastAPI 0.135.3, uvicorn 0.43.0, Pydantic 2.12.0, pydantic-settings 2.13.0
  - **Database:** SQLAlchemy 2.0.40, asyncpg 0.31.0, alembic 1.18.0, sqlmodel 0.0.38, motor 3.7.0, beanie 1.29.0
  - **AI Frameworks:** pydantic-ai 1.77.0, langchain 1.2.0, langchain-openai 1.1.0, langgraph 0.4.0, langgraph-checkpoint 4.0.0, crewai 1.13.0
  - **Vector Stores:** pymilvus 2.6.0, qdrant-client 1.14.0, chromadb 1.5.0
  - **Infra:** redis 7.3.0, celery 5.6.0, sentry-sdk 2.53.0, logfire 4.30.0, sqladmin 0.24.0, boto3 1.42.0
  - **Dev:** pytest 9.0.0, ruff 0.15.0, ty 0.0.29

## [0.2.2] - 2026-03-20

### Changed — CLI Simplification (Breaking)

The interactive wizard and CLI have been significantly simplified. Many options that were previously user-configurable are now always enabled or have sensible defaults. This reduces decision fatigue and eliminates invalid configuration combinations.

- **AI Agent always enabled** — Removed `enable_ai_agent` option. AI agent with WebSocket streaming is always included. Stripped `{%- if cookiecutter.enable_ai_agent %}` conditionals from 53 template files.
- **Auth always JWT + API Key** — Removed `AuthType` enum and `--auth` CLI option. JWT (user management, login, roles) + API Key (utility for programmatic access) are always included. Stripped `WebSocketAuthType` — WebSocket always uses JWT.
- **Database always required** — Removed `DatabaseType.NONE` and `--database none`. JWT needs user storage. Minimal preset now uses SQLite.
- **Conversation persistence always on** — Removed `enable_conversation_persistence` option. Chat history always saved to database. Stripped 139 template conditionals.
- **i18n always enabled** — Removed `enable_i18n` option. `next-intl` always included with `[locale]` routing. Stripped 50 template conditionals.
- **Example CRUD removed** — Removed `include_example_crud` option. Item model/routes/tests no longer generated. Post-gen hook always cleans up CRUD files.
- **Session management defaults to enabled** — Changed default from `False` to `True`.
- **Admin panel simplified** — Removed `AdminEnvironmentType` enum and auth config prompts. Admin panel always uses `dev_staging` environment restriction and always requires auth. Checkbox label clarified: "SQL Admin Panel (SQLAdmin) — web UI for browsing/editing database tables".
- **Background tasks default Celery** — Changed default from `None` to `Celery`. Celery is first option in wizard (was last). `None` option kept for projects without Redis.

### Added

#### CLI

- **`--s3-rag` flag** — Enable S3/MinIO document ingestion from CLI (previously only available in interactive mode)
- **S3 ingestion prompt** — Interactive wizard now asks "Enable S3/MinIO document ingestion?"
- **Image description prompt** — Interactive wizard now asks "Enable image description in documents?" for RAG
- **Reranker type selection** — Replaced boolean `--reranker` with proper `RerankerType` enum. User's choice (Cohere vs Cross-Encoder) is now preserved instead of being auto-determined by LLM provider
- **PDF Parser "All" option** — New option installs all 3 parsers (PyMuPDF, LiteParse, LlamaParse). Runtime selection via `PDF_PARSER` and `CHAT_PDF_PARSER` env vars. `PdfParserFactory` creates parser on demand
- **RAG without Celery** — RAG now works with `BackgroundTasks` (no Celery/Taskiq/ARQ required). Ingestion and sync run in-process via FastAPI `BackgroundTasks`. Removed validation that blocked RAG without a task queue
- **Retry, sync logs, cancel endpoints always available** — Previously gated behind Celery/Taskiq/ARQ, now work with any background task backend

#### Backend

- **`CHAT_PDF_PARSER` env var** — Separate parser config for chat file attachments (independent from RAG ingestion). Defaults to `pymupdf` for speed
- **`PdfParserFactory`** — Factory class for runtime PDF parser selection when "All" parsers installed
- **Conversation IDOR protection** — `get_conversation()` now validates `user_id` ownership. Users can only access their own conversations
- **OAuth null password guard** — `authenticate()` checks `user.hashed_password is not None` before `verify_password()`. Prevents crash for OAuth-only users
- **ChatFile cascade delete** — Added `ondelete="CASCADE"` to `user_id` and `message_id` foreign keys in all 4 DB variants
- **SQLite ToolCall args deserialization** — Added `field_validator` on `ToolCallBase.args` that deserializes JSON strings for SQLite compatibility
- **Embedding dimension validation** — Runtime check in `EmbeddingService` that embedding output matches configured `dim`. Raises `ValueError` on mismatch
- **Collection name validation** — Regex check `^[a-zA-Z][a-zA-Z0-9_]{0,63}$` on collection creation. Prevents SQL injection in pgvector and invalid names
- **Vector store connection cleanup** — Qdrant `client.close()` and PgVector `engine.dispose()` in lifespan shutdown

#### RAG

- **ChromaDB async compliance** — All ChromaDB operations wrapped in `asyncio.to_thread()` to avoid blocking the event loop
- **ChromaDB `_ensure_collection()`** — Added missing method. `POST /collections/{name}` now works with ChromaDB
- **ChromaDB filter support** — `search()` now parses `parent_doc_id` filter and passes as ChromaDB `where` clause
- **ChromaDB consistent metadata** — Now uses `_build_chunk_metadata()` (same as Milvus/Qdrant/pgvector)
- **Qdrant filter support** — `search()` now parses filter string and passes as `query_filter` with `FieldCondition`
- **RRF fusion key fix** — Changed merge key from `content[:100]` (collision-prone) to `parent_doc_id:chunk_num`

#### Frontend

- **Refresh token rotation** — `/api/auth/refresh` now updates `refresh_token` cookie when backend returns a new one
- **WebSocket connection guard** — Prevents orphaned WebSocket instances by checking `CONNECTING` state
- **Scroll pagination guard** — Conversation sidebar scroll handler checks `isLoading` + fetch mutex prevents concurrent requests
- **Message deduplication** — Chat messages cleared before loading conversation history, preventing duplicates on switch

### Fixed

- **Port validator** — Returns descriptive error messages ("Port must be between 1024 and 65535") instead of generic `False`
- **Reverse proxy default** — `ReverseProxyType.NONE` when Docker disabled (was `TRAEFIK_INCLUDED`)
- **OpenRouter validation** — Consolidated 4 separate checks into single message: "OpenRouter is only supported with PydanticAI, not {framework}"
- **RAG prompt cancellation** — All questionary calls in `prompt_rag_config()` now wrapped with `_check_cancelled()`. Ctrl+C during RAG config shows "Cancelled." instead of crashing
- **Stale docstring** — Removed bogus `Args: llm_provider` from `prompt_rag_config()` (function has no parameters)
- **Hardcoded `lang="en"`** — Root layout now uses locale from i18n config
- **Milvus version pinned** — Dev compose files use `v2.5.10` (was `latest`), matching production
- **Frontend CI** — Added `bun run lint` and `bun run type-check` steps to CI pipeline
- **Tailwind CSS** — Updated from `^4.0.0-beta.8` to `^4.0.0` (stable)
- **SQLite WebSocket auth** — `contextmanager(get_db_session)()` pattern verified working with mypy
- **`TYPE_CHECKING` import for ChatFile** — Added to SQLAlchemy PG and SQLite conversation model variants
- **Duplicate import** — Removed duplicate `import Image from "next/image"` in `message-item.tsx`
- **RAG search result off-by-one** — Fixed array indexing in expanded view, uses `.find()` by index value
- **Login loading state** — `setLoading(false)` now in `finally` block (was only in `catch`)
- **Refresh cookie clearing** — Cookie options (`httpOnly`, `secure`, `sameSite`) now consistent with logout route
- **Tool call status fallback** — `statusConfig[status]` falls back to `pending` for unknown statuses

### Added

#### Frontend — Landing Page
- **Floating navbar with animated beam border** — Pill-shaped navbar with rotating conic-gradient border in brand color, glass morphism background, adaptive dark/light mode
- **Tech stack marquee** — Infinite scrolling carousel with all project technologies (30+ items), edge fade mask, 60s animation loop
- **Grid background** — 64px grid pattern on hero section with radial gradient mask fade
- **Glass cards** — Frosted glass feature cards with backdrop-blur, hover lift animation, dark/light mode variants
- **Brand color system** — Global `--color-brand` CSS variable (oklch), configurable hue presets (blue, green, red, violet, orange). Changes one value to retheme entire app
- **Footer** — Two-column footer with product links, resources, API docs link, copyright

#### Frontend — Auth
- **Split layout login/register** — Left panel: dark bg with grid, gradient glow, heading, feature pills (AI Chat, KB, Auth, Real-time), quote. Right panel: form with contrasting background. Mobile: form only
- **Auth guard** — Client-side `AuthGuard` component wraps dashboard layout, redirects unauthenticated users to `/login` with loading spinner

#### Frontend — Dashboard
- **Personalized greeting** — "Good morning/afternoon/evening, {name}" based on time of day
- **Stats row** — Compact 4-column cards (API status, Conversations, Knowledge Base, AI Agent)
- **Recent conversations** — Last 5 chats with relative timestamps, skeleton loading
- **Collections overview** — Clickable RAG collection list with vector counts and status badges
- **Quick actions grid** — 2x2 icon grid (New Chat, Upload Docs, API Docs, Profile)
- **Account card** — Avatar with initials, email, role, registration date
- **Environment card** — Status, version, framework, LLM, vector store info

#### Frontend — Chat
- **"Thinking..." indicator** — Animated bounce dots before first content arrives from LLM
- **Copy buttons** — Appear on hover under both user and assistant messages (moved from inside bubble)
- **Message timestamps** — HH:MM format under each message, hidden during streaming
- **File upload system** — Upload images, text, PDF, DOCX via backend API. Thumbnail preview for images, badge for files. Files parsed on backend (PyMuPDF for PDF, python-docx for DOCX)
- **Image support (LLM Vision)** — Images sent as `BinaryContent` to PydanticAI agent for vision analysis. Stored in `media/` directory, linked to messages via `ChatFile` model
- **Microphone (Speech-to-Text)** — Web Speech API voice input button, always visible, toast fallback for unsupported browsers
- **Message queue** — Input not disabled during processing. Messages queued on frontend, auto-sent when bot finishes responding
- **Model selector** — Dropdown in chat status bar (Claude Sonnet 4, Claude 3.5 Sonnet, GPT-4o, GPT-4o Mini, Gemini 2.5 Flash). Backend `get_agent(model_name=...)` accepts override
- **Tool call persistence** — Tool calls (name, args, result, status) saved to database during WebSocket streaming. Visible when loading conversation history

#### Frontend — Knowledge Base (RAG Dashboard)
- **Sidebar layout** — Collections in left sidebar (collapsible), documents/search in main area
- **Create collection** — Inline input in sidebar with "+" button
- **Upload & ingest** — File upload → backend ingestion (parse, chunk, embed, store). Supports PDF, DOCX, TXT, MD. Max 50MB
- **Document tracking** — `RAGDocument` model in database: status (processing/done/error), error message, timestamps, storage path
- **Document list** — Per-collection with filename, type badge, size, date, status icon (spinner/check/error)
- **View original** — Eye icon opens original uploaded file (stored in local storage / S3)
- **Delete document** — AlertDialog confirmation, removes from vector store + file storage + SQL
- **Search** — Full-text vector search with score badges, source document linking ("View source")

#### Frontend — UI Components (shadcn/ui + Radix)
- **Dialog** — `@radix-ui/react-dialog` based modal with overlay, close button, fade+zoom animations
- **AlertDialog** — `@radix-ui/react-alert-dialog` for destructive action confirmations (delete collection, delete document)
- **Avatar** — `@radix-ui/react-avatar` with image support and initial fallback
- **Skeleton** — Pulse animation placeholder for loading states
- **Separator** — `@radix-ui/react-separator` for visual dividers
- **Tooltip** — `@radix-ui/react-tooltip` with TooltipProvider
- **Button `asChild` fix** — `@radix-ui/react-slot` enables proper `asChild` prop on Button component

#### Frontend — Navigation & Layout
- **Nav links in header** — Dashboard, Chat, Knowledge Base, Profile tabs with icons and active state (moved from sidebar)
- **Sidebar → mobile only** — Desktop sidebar removed, kept as Sheet drawer for mobile
- **Language switcher** — Segmented control buttons (EN | PL) with `router.push` locale switching
- **Softer dark theme** — Zinc-inspired tones (14.5% lightness, subtle blue-purple hue 285) replacing pure black (12%)
- **`BACKEND_URL` constant** — API docs links point to backend (`http://localhost:8000/docs`), not frontend
- **Page transition animations** — Fade-in + 6px slide-up animation (250ms ease-out) on dashboard page navigation via `PageTransition` component with `key={pathname}` re-mount
- **Breadcrumbs** — Auto-generated breadcrumb navigation on Profile and Settings pages with `aria-label="Breadcrumb"`, chevron separators, clickable parent links

#### Frontend — Error Handling
- **404 page** — `not-found.tsx` with "Page not found" message, "Go home" and "Dashboard" buttons, brand-colored styling
- **500 error boundary** — `global-error.tsx` with inline styles (no CSS dependency), "Try again" reset button, error digest ID display
- **Page error boundary** — `[locale]/error.tsx` catches errors within layout, preserves header/sidebar, "Try again" + "Go home" buttons

#### Frontend — Accessibility
- **`aria-current="page"`** — Active nav items in header marked for screen readers
- **`aria-live="polite"`** — Loading/status changes announced: auth guard, chat "Thinking..." indicator, RAG upload progress, RAG document status icons
- **`aria-hidden="true"`** — Decorative bounce dots and spinner icons hidden from screen readers
- **`role="status"`** — RAG `StatusIcon` component with descriptive `aria-label` (Completed/Failed/Processing)

#### Backend — File System
- **`ChatFile` model** — Tracks files uploaded in chat (user_id, message_id, filename, mime_type, storage_path, file_type, parsed_content)
- **`LocalFileStorage` service** — Save/load/delete files in `media/{user_id}/` directory. Extensible `BaseFileStorage` ABC for S3/MinIO
- **`POST /files/upload`** — Multipart upload with MIME validation, 10MB limit, auto-parsing (text/PDF/DOCX)
- **`GET /files/{id}`** — Download with owner-only access check
- **File linking** — Files linked to messages via `message_id` FK, loaded with conversation history

#### Backend — RAG Improvements
- **Async Celery ingestion** — `POST /rag/collections/{name}/ingest` returns `202 Accepted` and dispatches `ingest_document_task` to Celery worker. Falls back to synchronous ingestion when Celery is not enabled
- **WebSocket status updates** — `WS /rag/ws/status` endpoint subscribes to Redis pub/sub channel `rag_status`, forwards real-time ingestion status (processing → done/error) to frontend
- **RAG is global** — Removed `user_id` from `RAGDocument` model. All documents, collections, and vectors are shared across users (no per-user isolation)
- **CLI DB tracking** — `rag-ingest` CLI command now creates `RAGDocument` records in SQL for each file. Documents ingested via CLI appear in the Knowledge Base dashboard with status tracking
- **Retry endpoint** — `POST /rag/documents/{id}/retry` resets failed document status to `processing` for re-ingestion
- **`RAGDocument` model** — Tracks ingestion status (processing/done/error), error_message, vector_document_id, storage_path, timestamps
- **`GET /rag/documents`** — List tracked documents with collection filter
- **`GET /rag/documents/{id}/download`** — Download original ingested file
- **`DELETE /rag/documents/{id}`** — Removes from vector store + file storage + SQL (3-way cleanup)
- **Configurable upload size** — `MAX_UPLOAD_SIZE_MB` setting (default 50MB) used in file upload, RAG ingest, and health endpoint. Frontend reads from `NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB` env var
- **Batch upload** — Frontend RAG page supports multi-file upload with progress bar (X/Y files, filename indicator)
- **Filename fix in ingestion** — `document.metadata.filename` set from `source_path` instead of temp file name
- **`EmbeddingsConfig` model validator** — Auto-derives vector dimensions from model name via `EMBEDDING_DIMENSIONS` lookup table
- **`EMBEDDING_MODEL` env var wired** — Settings → RAGSettings → EmbeddingsConfig flow complete

#### Backend — Agent Improvements
- **Tool call persistence** — WebSocket handler collects tool calls during streaming, saves to DB after assistant message
- **Conversation title auto-set** — Backend updates conversation title from first user message when title is empty
- **Model selection** — WebSocket handler accepts `model` field, passes to `get_agent(model_name=...)`
- **File handling in WS** — Parses `file_ids` from WebSocket message, loads files, images → `BinaryContent` for LLM vision, text/PDF/DOCX → parsed content appended to prompt

#### Backend — Security & Compliance
- **PII redaction in logs** — `PiiRedactionFilter` logging filter scrubs emails, JWT tokens, API keys (OpenAI/Anthropic), Bearer tokens, and password-like values from all log output. Prevents PII leaks to log aggregators (Datadog, CloudWatch, Logfire). Activated via `setup_logging()` at app startup
- **Dependency vulnerability scanning** — CI pipeline includes `security` job with `pip-audit` for supply chain risk detection
- **Docker image scanning** — Trivy vulnerability scanner (`aquasecurity/trivy-action@0.28.0`) runs after Docker build in CI, reports CRITICAL and HIGH severity issues

#### Backend — Database & Infrastructure
- **Missing indexes added** — `users.oauth_provider`, `users.oauth_id`, `sessions.user_id`, `webhooks.user_id`, `webhook_deliveries.webhook_id`, `webhook_deliveries.created_at` (all SQL variants)
- **`MEDIA_DIR` config** — New setting for file storage directory
- **`import sqlmodel` in migrations** — Added to `script.py.mako` template for SQLModel projects
- **Graceful RAG startup** — Embedding, reranker, vector store warmup wrapped in try/except, app doesn't crash on failure

### Changed

- **Auth layout theme-aware** — Left hero panel now adapts to light/dark mode (`bg-zinc-100 dark:bg-zinc-950`) instead of hardcoded `bg-zinc-950`
- **`next/image` migration** — Chat file thumbnails and attached images use `next/image` with `unoptimized` for lazy loading and layout stability
- **Consistent loading states** — All `"..."` placeholder text and `"Loading..."` messages replaced with `Skeleton` components (dashboard stats, conversation sidebar, OAuth callback)
- **RAG sidebar responsive** — Sidebar width `w-52 lg:w-64` (narrower on tablets, full width on desktop)
- **Empty search state** — RAG search shows in-UI "No results found" with icon instead of toast-only
- **Profile inline update** — `window.location.reload()` replaced with Zustand `setUser()` for instant state update without page reload
- **Real-time form validation** — Register: email format on blur, password strength bar (Weak/Fair/Good/Strong), confirm password match indicator. Login: email format on blur
- **`TimestampMixin` uses `sa_column_kwargs`** — Fixed SQLModel shared Column object bug (`Column 'created_at' already assigned to Table`)
- **`MessageList` schema** — Changed from `MessageReadSimple` (no tool_calls) to `MessageRead` (with tool_calls + files)
- **`list_messages` endpoint** — Now passes `include_tool_calls=True` to eagerly load tool call relationships
- **RAG proxy routes** — Removed `NEXT_PUBLIC_AUTH_ENABLED` gate, always forward auth cookie if present
- **Removed unused code** — `pipelines/` directory, `repositories/base.py`, `worker/tasks/rag_ingestion.py` (reindex task), `test_pipelines.py`, `docs/howto/add-data-pipeline.md`
- **Removed section dividers** — `# =========` comments removed from `services/conversation.py`, `repositories/conversation.py`, `schemas/conversation.py`
- **`itsdangerous` dependency** — Added when OAuth enabled (required by Starlette `SessionMiddleware`)
- **`logger` added to `main.py`** — `import logging` + `logger = logging.getLogger(__name__)` for RAG startup error logging
- **Document ingestion is CLI-only** - Removed upload API endpoints. Ingestion exclusively via CLI commands (later re-added as `POST /rag/collections/{name}/ingest`)
- **`RetrievalService` renamed** - `MilvusRetrievalService` → `RetrievalService` (now backend-agnostic)
- **Docker validation relaxed** - Docker only required for Milvus and Qdrant vector stores
- **`.env.example` restructured** - RAG section moved from `use_milvus` to `enable_rag` guard
- **README.md rewritten** - Updated for 5 frameworks, 4 providers, RAG section with vector store/embedding tables
- **CLAUDE.md / AGENTS.md updated** - Both project-level and template versions updated with RAG, Gemini, vector stores

### Fixed

- **Language switching** — `usePathname()` with next-intl returns path with locale prefix, original `segments[1] = newLocale` + `router.push` logic restored
- **Conversation "20531d ago"** — `updated_at` null fallback to `created_at` in dashboard
- **RAG stats "..."** — Set `{collections: [], totalVectors: 0}` on error instead of null
- **`callable | None` TypeError** — Changed to `Callable | None` with proper import in `ingestion.py`
- **Tool call card TS error** — `Type 'unknown' not assignable to ReactNode` fixed with ternary
- **Empty args crash** — `json.loads("")` in tool call persistence fixed with `.strip()` check
- **`user_prompt` serialization** — `BinaryContent` not JSON serializable, now sends text-only prompt in WS event
- **File linking FK violation** — ChatFile `message_id` update moved to same DB session as message insert

#### RAG (Retrieval-Augmented Generation) — Pipeline

- **RAG integration** - Full RAG pipeline: document parsing → chunking → embedding → vector store → retrieval. Integrated with all 5 AI frameworks as `search_knowledge_base` tool
- **4 vector store backends** - Milvus (Docker), Qdrant (Docker), ChromaDB (embedded), pgvector (PostgreSQL extension). Selected via `vector_store` config option
- **4 embedding providers** - OpenAI (`text-embedding-3-small`), Voyage (`voyage-3`), Google Gemini (`gemini-embedding-exp-03-07`, multimodal), SentenceTransformers (`all-MiniLM-L6-v2`)
- **Document parsers** - PyMuPDF (PDF text + tables + headers/footers + images + OCR), LlamaParse (130+ formats via cloud API, configurable tier), python-docx (DOCX), native (TXT/MD)
- **Image description** - Optional extraction of images from documents via PyMuPDF + LLM vision API description (OpenAI GPT-4o / Anthropic Claude / Gemini / OpenRouter). Opt-in via `enable_rag_image_description`
- **Chunking strategies** - 3 strategies: `recursive` (default), `markdown` (split by headers), `fixed` (simple fixed-size). Configurable via `RAG_CHUNKING_STRATEGY` env var
- **Hybrid search** - BM25 keyword search + vector similarity search with Reciprocal Rank Fusion (RRF). Enable via `RAG_HYBRID_SEARCH=true`
- **Reranking** - Cohere API or local CrossEncoder for improved search quality
- **Citation/source tracking** - Agent tool returns `[1] Source: filename, page X, chunk Y` format. Agent prompt instructs citation with `[1]`, `[2]` references and source list
- **Document versioning** - `source_path` (local path / `gdrive://id` / `s3://bucket/key`) and `content_hash` (SHA256) in metadata. Automatic deduplication: re-ingest replaces old chunks. CLI: `--replace` / `--no-replace`
- **Multi-collection search** - `RetrievalService.retrieve_multi()` searches across multiple collections. API: `collection_names: list[str]`. Frontend: "All collections" option
- **Document sources** - Local files (CLI `rag-ingest`), Google Drive (service account, CLI `rag-sync-gdrive`), S3/MinIO (CLI `rag-sync-s3`). Extensible `BaseDocumentSource` ABC
- **Ingestion progress** - `tqdm` progress bar in CLI `rag-ingest` with per-file status and replaced count
- **RAG management page** - Frontend `/rag` page: collection list with stats, search preview with results, metadata filters (filetype, min score), multi-collection support, delete collection
- **RAG API endpoints** - `GET/POST/DELETE /rag/collections`, `GET /rag/collections/{name}/info`, `GET /rag/collections/{name}/documents`, `POST /rag/search`, `DELETE /rag/collections/{name}/documents/{id}`
- **RAG CLI commands** - `rag-collections`, `rag-ingest`, `rag-search`, `rag-drop`, `rag-stats`, `rag-sync-gdrive`, `rag-sync-s3`

#### AI / LLM

- **Google Gemini LLM provider** - New `--llm-provider google` option. PydanticAI: `GoogleModel` + `GoogleProvider`. LangChain/LangGraph/CrewAI/DeepAgents: `ChatGoogleGenerativeAI`. Dependencies: `pydantic-ai-slim[google]`, `langchain-google-genai`
- **Gemini multimodal embeddings** - `GeminiEmbeddingProvider` with `embed_image()` for native multimodal (text + images in same vector space). Model: `gemini-embedding-exp-03-07` (3072 dim)

#### Frontend

- **Toast notification system** - `sonner` library with `<Toaster />` in providers. Toast feedback on: login, register, logout, profile save, RAG operations
- **Profile save wired** - "Save Changes" button now calls `PATCH /users/me`. Editable email field, loading state, toast feedback
- **Dashboard redesigned** - Stats cards (API status, account, AI framework, RAG vector count), quick action links (Chat, Knowledge Base, Profile)
- **Settings page** - New `/settings` page with sections: Appearance (theme toggle), Application (project info, AI framework, vector store), Stack (technology badges), Security (auth type, rate limiting)
- **Metadata filtering UI** - RAG search page: filetype dropdown, min score dropdown, "Clear filters" link
- **Specialized tool call cards** - DateTime tool: Calendar/Clock icons with formatted date/time. RAG search: horizontal card carousel with filename, page, score badges, expandable content. Toggle between formatted and raw JSON view
- **Sidebar "Knowledge Base" link** - Navigation item with Database icon, conditional on `enable_rag`

#### DevOps

- **`make quickstart`** - One command to install deps, start Docker services, run migrations, create admin user
- **Vercel deployment** - `frontend/vercel.json` config + `make vercel-deploy` target with env var instructions
- **Qdrant Docker service** - Added to `docker-compose.dev.yml` with health check, volume, and backend env vars

#### PR #50 RAG Bug Fixes (28 issues found and fixed)

- **`schedules.py` regression** - Outer conditional broke Taskiq scheduling for all non-RAG projects. Fixed: restored `use_taskiq` guard, RAG schedule inside nested conditional
- **Duplicate Milvus settings** - `core/config.py` had Milvus settings twice. Fixed: removed duplicate, nested under `use_milvus` inside `enable_rag`
- **Env vars not wired to RAGSettings** - `RAG_CHUNK_SIZE`, `RAG_DEFAULT_COLLECTION` ignored at runtime. Fixed: wired through `Settings.rag` computed property
- **Copy-paste etcd command in prod MinIO** - `docker-compose.prod.yml` minio had etcd command. Fixed: removed
- **Frontend type mismatch** - `RAGSearchResult.text` vs backend `content`. Fixed: renamed to `content`, added `parent_doc_id`
- **Milvus filter injection** - `document_id` interpolated unsanitized. Fixed: strip `"` and `\` before interpolation
- **File upload security** - No filename sanitization, no size limit. Fixed: `_safe_filename()`, `MAX_UPLOAD_SIZE=50MB`, HTTP 413
- **Hardcoded MinIO credentials in prod** - Fixed: env var substitution `${MINIO_ROOT_USER}` / `${MINIO_ROOT_PASSWORD}`
- **`milvusdb/milvus:latest` in prod** - Fixed: pinned to `v2.5.10`
- **`processor.parser.allowed` AttributeError** - Fixed: use `DocumentExtensions` enum directly
- **Inconsistent default collection** - sync wrapper `"default"` vs async `"documents"`. Fixed: both `"documents"`
- **`RerankService` NameError when disabled** - Fixed: `from __future__ import annotations`
- **`print()` in reranker.py** - Fixed: all 13 `print()` → `logger.info()`
- **`console.log` in rag-api.ts** - Fixed: removed debug statements
- **Legacy typing imports in schemas** - Fixed: `List`→`list`, `Dict`→`dict`, `Optional`→`| None`
- **Hardcoded `/tmp/rag_uploads`** - Fixed: `tempfile.gettempdir()`
- **Inconsistent frontend auth** - Fixed: all RAG routes use `NEXT_PUBLIC_AUTH_ENABLED` pattern
- **Inline `import logging` in routes** - Fixed: moved to module level
- **Unconditional PDF parser import** - Fixed: conditional on `not use_llamaparse`
- **Chat page not removed when i18n disabled** - Fixed: remove both `[locale]/` and direct paths
- **`stores/index.ts` unconditional chat exports** - Fixed: previously gated behind `enable_ai_agent` (now always enabled)
- **`types/index.ts` unconditional chat export** - Fixed: previously gated behind `enable_ai_agent` (now always enabled)
- **`chat-sidebar-store.ts` not cleaned up** - Fixed: added to post-gen hook
- **`rag/config.py` gated by `use_milvus`** - Fixed: changed to `enable_rag`
- **Worker tasks gated by `use_milvus`** - Fixed: `rag_ingestion.py`, `celery_app.py`, `arq_app.py` changed to `enable_rag`
- **pgvector SQL injection** - Fixed: `_validate_collection_name()` regex + `_table()` helper in all methods
- **pgvector IVFFlat on empty table** - Fixed: changed to HNSW index
- **Duplicate `logger` in reranker.py** - Fixed: removed duplicate, reordered imports

## [0.2.1] - 2026-03-05

### Added

- **LangSmith observability integration** - New `enable_langsmith` option for LangChain, LangGraph, and DeepAgents frameworks. Adds `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`, `LANGCHAIN_ENDPOINT` settings and `langsmith` dependency when enabled. Includes interactive prompt, `--langsmith` CLI flag, and auto-enable in `ai-agent` preset. Previously LangSmith env vars were hardcoded to appear with LangChain — now requires explicit opt-in and works with all 3 LangChain-ecosystem frameworks.
- **CLI: `--conversation-persistence` flag** - Enable conversation persistence from the command line (previously only available interactively)
- **CLI: `--websocket-auth` option** - Set WebSocket authentication method (`none`, `jwt`, `api_key`) from the command line

### Changed

- **CLI runs interactive wizard by default** - `fastapi-fullstack` now launches the configurator directly without requiring `new` subcommand
- **CLI branding updated** - Banner, descriptions, and prog name updated from "fastapi-gen / FastAPI Project Generator with Logfire" to "Full-Stack AI Agent Template Generator"
- **`templates` command expanded** - Now lists all 5 AI frameworks, LangSmith, ORM options, WebSocket auth, conversation persistence, and port options

### Fixed

#### CLI Fixes

- **`--ai-framework` missing 3 frameworks** - Added `langgraph`, `crewai`, `deepagents` to choices (previously only `pydantic_ai` and `langchain`)

#### Backend Template Fixes

- **Unconditional `import logfire` in `versioning.py`** - Replaced with `logging` module to prevent `ImportError` when Logfire is disabled
- **Unconditional `import logfire` in `webhook.py`** - Replaced `logfire.error()`/`logfire.info()` with `logger.error()`/`logger.info()` in all 3 database sections (PostgreSQL, SQLite, MongoDB) to prevent `ImportError` when Logfire is disabled but webhooks are enabled
- **`backend/.env` LangSmith conditional wrong** - Was gated by `use_langchain` instead of `enable_langsmith` (only `.env.example` was updated, `.env` was missed)
- **`backend/.env` missing sections** - Added OAuth Google, ARQ, and Prometheus sections that were present in `.env.example` but absent from generated `.env`

#### Frontend Template Fixes

- **Sidebar "Chat" link visible without AI agent** - Chat navigation item now always visible (AI agent is always enabled)
- **Frontend chat files not cleaned up** - No longer applicable (AI agent is always enabled, chat files are always present)
- **Chat component exports unconditional** - Chat exports are now always included (AI agent is always enabled)
- **Chat hook exports unconditional** - Hook exports for `useWebSocket`, `useChat`, `useLocalChat` are now always included (AI agent is always enabled)
- **`WS_URL` and `ROUTES.CHAT` always defined** - `constants.ts` now conditionally defines WebSocket URL and chat route only when AI agent is enabled

## [0.2.0] - 2026-02-27

### Changed

- **Repository renamed** from `full-stack-fastapi-nextjs-llm-template` to `full-stack-ai-agent-template` — all internal links, badges, raw.githubusercontent URLs, mkdocs config, and template files updated. Old GitHub URLs redirect automatically.
- **Repository marked as GitHub Template** — users can now click "Use this template" to create a new repo directly from GitHub
- **README CTA section** — replaced "Made with" footer with Vstorm consultancy call-to-action

## [0.1.18] - 2026-02-01

### Fixed

- **Removed macOS `.DS_Store` artifacts** and added `.DS_Store` to `.gitignore` (contributed by [@vladdoster](https://github.com/vladdoster) in [#42](https://github.com/vstorm-co/full-stack-ai-agent-template/pull/42))

## [0.1.17] - 2026-01-24

### Added

- **MkDocs Material documentation site** with pink theme, Inter/JetBrains Mono fonts
- New documentation pages:
  - `docs/index.md` - Landing page with quick start and features overview
  - `docs/installation.md` - Installation guide with uv/pip/pipx options
  - `docs/getting-help.md` - FAQ and support resources
  - `docs/concepts/index.md` - Architecture overview with Mermaid diagrams
  - `docs/guides/quick-start.md` - Step-by-step first project guide
  - `docs/guides/configuration.md` - All configuration options
- GitHub Actions workflow for automatic docs deployment (`docs.yml`)
- Custom styling (`docs/stylesheets/extra.css`) matching pydantic-deep theme
- GitHub announcement bar in docs header

### Changed

- **README.md redesign**:
  - New centered header with "Full-Stack AI Agent Template" title
  - Reorganized badges: AI frameworks (PydanticAI, LangChain, LangGraph, CrewAI, OpenAI, Anthropic, OpenRouter) moved to Features section
  - Added infrastructure badges: FastAPI, Next.js 15, React 19, TypeScript, Tailwind v4, SQLAlchemy, PostgreSQL, MongoDB, Redis, Celery, Logfire, Sentry, Prometheus, Docker, Kubernetes, GitHub Actions, S3
  - New highlights: "🤖 PydanticAI • 🦜 LangChain, LangGraph & DeepAgents • 👥 CrewAI • 🎯 Fully Type-Safe"
- Moved `CHANGELOG.md` from `docs/` to project root (symlinked in docs)
- Added `docs` optional dependency group with mkdocs packages

## [0.1.16] - 2026-01-20

### Fixed

- **Logfire Celery instrumentation prompt** - Celery instrumentation option now only appears when Celery is selected as background task system (previously caused validation error when selecting the option with Taskiq/ARQ)

### Changed

- **Prompt order** - Background tasks prompt now appears before Logfire prompt to enable dynamic feature filtering

### Tests Added

- Test for Celery instrumentation option visibility based on background task selection

## [0.1.15] - 2026-01-18

### Added

#### DeepAgents Framework Support

- **DeepAgents as fifth AI framework option** alongside PydanticAI, LangChain, LangGraph, and CrewAI
- New `--ai-framework deepagents` CLI option for project creation
- Interactive prompt includes "DeepAgents" choice
- **Built-in tools** for file operations, code execution, and task management:
  - `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`
  - `execute` (disabled by default for safety)
  - `write_todos`, `task` (sub-agents)
- **StateBackend** for in-memory file state management
- **Skills support** via `DEEPAGENTS_SKILLS_PATHS` environment variable
- New template files:
  - `app/agents/deepagents_assistant.py` - DeepAgentsAssistant class with run() and stream()
  - WebSocket route implementation with interrupt handling
- New cookiecutter variable: `use_deepagents`
- Dependencies: `deepagents>=0.1.0`

#### Human-in-the-Loop (HITL) Support

- **Tool approval workflow** for DeepAgents allowing users to approve, edit, or reject tool calls
- Configurable via `DEEPAGENTS_INTERRUPT_TOOLS` environment variable:
  - Comma-separated tool names (e.g., `write_file,edit_file,execute`)
  - Or `all` to require approval for all tools
- **Frontend tool approval dialog** (`tool-approval-dialog.tsx`):
  - Shows pending tool calls with JSON args in editable textarea
  - Cancel/Save buttons for editing args
  - Submit button to send decisions
  - Auto-detects changes and sends appropriate decision (approve/edit/reject)
- **WebSocket protocol** for interrupt handling:
  - Backend sends `tool_approval_required` event with action requests
  - Frontend sends `resume` message with user decisions
  - Thread ID management for state persistence across interrupts
- New types in `chat.ts`: `ActionRequest`, `ReviewConfig`, `PendingApproval`, `Decision`
- Updated hooks (`use-chat.ts`, `use-local-chat.ts`) with:
  - `pendingApproval` state
  - `sendResumeDecisions()` function
- Environment variables:
  - `DEEPAGENTS_INTERRUPT_TOOLS` - tools requiring approval
  - `DEEPAGENTS_ALLOWED_DECISIONS` - allowed decision types (approve, edit, reject)

### Fixed

- **OAuth requires JWT authentication** - Added validation that OAuth providers (Google) require JWT auth to be enabled, preventing invalid configuration combinations

### Changed

- **`AIFrameworkType` enum** extended with `DEEPAGENTS` value
- **AI framework prompt** now shows five options: PydanticAI, LangChain, LangGraph, CrewAI, DeepAgents
- **LLM provider validation** - OpenRouter not supported with DeepAgents (uses LangChain providers directly)
- **`VARIABLES.md`** updated with `use_deepagents` documentation
- **Template `CLAUDE.md`** includes DeepAgents in stack section
- **`CONTRIBUTING.md`** updated with correct repository URL

### Tests Added

- Tests for `DEEPAGENTS` enum value
- Tests for DeepAgents + OpenRouter validation (combination is rejected)
- Tests for `use_deepagents` computed field
- Tests for cookiecutter context generation with DeepAgents

## [0.1.14] - 2026-01-16

### Fixed

- **Dynamic version reading** - `fastapi-fullstack --version` now correctly displays the version from `pyproject.toml` using `importlib.metadata` instead of hardcoded value

### Security

- **CVE-2026-22701** - Updated `filelock` to 3.20.3
- **CVE-2026-21441** - Updated `urllib3` to 2.6.3
- **CVE-2026-22702** - Updated `virtualenv` to 20.36.1

## [0.1.13] - 2026-01-06

### Added

#### Comprehensive Configuration Validation

- **New validation rules** to prevent invalid option combinations at config time:
  - WebSocket JWT auth requires main JWT auth to be enabled
  - WebSocket API key auth requires main API key auth to be enabled
  - Admin panel authentication requires JWT auth (for User model)
  - Conversation persistence requires AI agent to be enabled
  - Admin panel requires SQLAlchemy ORM (SQLModel not fully supported by SQLAdmin)
  - Session management requires JWT auth
  - Webhooks require a database to store subscriptions and delivery history
  - Background task queues (Celery/Taskiq/ARQ) require Redis as broker
  - Logfire database instrumentation requires a database
  - Logfire Redis instrumentation requires Redis
  - Logfire Celery instrumentation requires Celery as background task system

#### Improved Post-Generation Instructions

- **Clearer database setup instructions** with warning message:
  ```
  ⚠️  Run all commands in order: db-migrate creates the migration, db-upgrade applies it
  ```
- **README.md** updated with prominent warning about required migration steps
- Commands displayed with aligned descriptions for better readability

#### Dynamic Integration Prompts

- **Context-aware integration options** in interactive wizard:
  - Admin Panel option only shown when SQLAlchemy is selected (not SQLModel)
  - Webhooks option only shown when a database is enabled
  - WebSocket auth options filtered based on main auth type selected
  - Clearer ORM selection labels: "SQLAlchemy — full control, supports admin panel" vs "SQLModel — less boilerplate, no admin panel support"
- **Auto-enable Redis** when caching is selected (with info message)
- **Better descriptions** for all integration options explaining dependencies

#### Template Improvements

- **ARQ worker service** added to `docker-compose.prod.yml`
- **Prometheus labels** added to backend service in `docker-compose.dev.yml`
- **OAuth environment variable** `NEXT_PUBLIC_API_URL` added to frontend `.env.example`
- **Frontend WS_URL** now uses `backend_port` cookiecutter variable instead of hardcoded 8000

### Changed

#### Post-Generation Hook Improvements

- **Stub file cleanup** - removes files containing only docstrings with no actual code
- **Auth file cleanup** - removes auth/user files when JWT is disabled:
  - `auth.py`, `users.py` routes
  - `user.py` model, repository, service, schema
  - `token.py` schema
- **Logfire cleanup** - removes `logfire_setup.py` when Logfire is disabled
- **Security cleanup** - removes `security.py` when no auth is configured at all
- **LangGraph/CrewAI cleanup** - properly removes unused AI framework files

### Fixed

#### Template Fixes

- **LangChain assistant `stream()` method** - changed from sync generator to async generator using `astream()` for proper async streaming
- **OAuth callback** - made fully async, removed sync `asyncio.new_event_loop()` hack
- **Deprecated `datetime.utcnow()`** - replaced with `datetime.now(UTC)` across all services:
  - `cleanup.py` command
  - `session.py` repository and service
  - `conversation.py` service
  - `webhook.py` service
- **Session model** - added missing `default_factory=datetime.utcnow` for `created_at` and `last_used_at` fields
- **Webhook model** - moved `import json` to module level instead of inside properties
- **Admin panel template condition** - now correctly checks for SQLAlchemy ORM requirement
- **Caching setup** - only runs when both caching AND Redis are enabled
- **Config imports** - fixed conditional imports for Redis-only projects (no database)

### Tests Added

- **290+ new test lines** covering all new validation rules
- Tests for WebSocket auth requiring main auth
- Tests for admin panel requiring SQLAlchemy
- Tests for admin authentication requiring JWT
- Tests for conversation persistence requiring AI agent
- Tests for webhooks requiring database
- Tests for Logfire feature dependencies (database, Redis, Celery)
- Tests for background task queues requiring Redis
- Updated CLI tests to include `--redis` flag with task queue options

## [0.1.12] - 2026-01-02

### Added

#### CrewAI Multi-Agent Framework Improvements

- **Full type annotations** for all CrewAI event handlers in `crewai_assistant.py`
- **Comprehensive event queue listener** with handlers for:
  - `crew_started`, `crew_completed`, `crew_failed`
  - `agent_started`, `agent_completed`
  - `task_started`, `task_completed`
  - `tool_started`, `tool_finished`
  - `llm_started`, `llm_completed`
- **Improved stream method** with proper thread and queue handling:
  - Natural completion path when receiving None sentinel
  - Race condition handling for thread death scenarios
  - Defensive code with `# pragma: no cover` for edge cases
- **100% test coverage** for CrewAI assistant module

### Fixed

#### Backend Fixes

- **Type annotations** - All mypy errors fixed across the codebase:
  - Added `Any` types where needed in `logfire_setup.py`
  - Fixed `Callable` types in `commands/__init__.py`
  - Added proper types to versioning middleware
  - Full type coverage for CrewAI event handlers
- **WebSocket disconnect handling** - Proper logging and cleanup when client disconnects during agent processing (lines 241-242 in `agent.py`)
- **Health endpoint edge cases** - Added `# pragma: no cover` for unreachable 503 response path (checks dict is always empty)
- **Abstract method coverage** - Added `# pragma: no cover` for abstract `run()` method in `BasePipeline`

#### Frontend Fixes

- **Timeline connector lines** for grouped messages now display correctly
- **Message grouping** visual indicators properly connect related messages

### Tests Added

- **100% code coverage achieved** (720 statements, 0 missing)
- Tests for all 11 CrewAI event handlers:
  - `test_crew_started_handler`, `test_crew_completed_handler`, `test_crew_failed_handler`
  - `test_agent_started_handler`, `test_agent_completed_handler`
  - `test_task_started_handler`, `test_task_completed_handler`
  - `test_tool_started_handler`, `test_tool_finished_handler`
  - `test_llm_started_handler`, `test_llm_completed_handler`
- Tests for CrewAI stream method edge cases:
  - `test_stream_complete_flow` - natural completion path
  - `test_stream_empty_queue_break` - queue empty handling
  - `test_stream_with_error` - error event handling
- Tests for WebSocket disconnect during processing:
  - `test_websocket_disconnect_during_stream`
  - `test_websocket_disconnect_during_processing`
- Tests for health endpoint edge cases:
  - `test_readiness_probe_503_unit` - 503 response logic

## [0.1.11] - 2026-01-02

### Added

#### LangGraph ReAct Agent Support

- **LangGraph as third AI framework option** alongside PydanticAI and LangChain
- New `--ai-framework langgraph` CLI option for project creation
- Interactive prompt includes "LangGraph (ReAct agent)" choice
- **ReAct (Reasoning + Acting) agent pattern** with graph-based architecture:
  - Agent node for LLM reasoning and tool decision
  - Tools node for executing tool calls
  - Conditional edges for tool execution loop
  - Memory-based checkpointing for conversation continuity
- **Full WebSocket streaming support** using `astream()` with dual modes:
  - `messages` mode for token-level LLM streaming
  - `updates` mode for node state changes (tool calls/results)
- **Tool result correlation** - proper `tool_call_id` matching between calls and results
- New template files:
  - `app/agents/langgraph_assistant.py` - LangGraphAssistant class with run() and stream()
  - WebSocket route implementation in `app/api/routes/v1/agent.py`
- New cookiecutter variable: `use_langgraph`
- Dependencies for LangGraph projects:
  - `langchain-core>=0.3.0`
  - `langchain-openai>=0.3.0` or `langchain-anthropic>=0.3.0`
  - `langgraph>=0.2.0`
  - `langgraph-checkpoint>=2.0.0`

### Changed

- **`AIFrameworkType` enum** extended with `LANGGRAPH` value
- **AI framework prompt** now shows three options: PydanticAI, LangChain, LangGraph
- **LLM provider validation** - OpenRouter not supported with LangGraph (same as LangChain)
- **`VARIABLES.md`** updated with `use_langgraph` documentation
- **Template `CLAUDE.md`** includes LangGraph in stack section

## [0.1.10] - 2025-12-27

### Added

#### Nginx Reverse Proxy Support

- **Nginx as alternative to Traefik** with two configuration modes:
  - `nginx_included`: Full Nginx setup in docker-compose.prod.yml
  - `nginx_external`: Nginx config template only, for external Nginx
- **Nginx configuration template** (`nginx/nginx.conf`) with:
  - Reverse proxy for backend API (api.DOMAIN)
  - Reverse proxy for frontend (DOMAIN) - conditional
  - Reverse proxy for Flower dashboard (flower.DOMAIN) - conditional
  - WebSocket support for `/ws` endpoint
  - Security headers (X-Frame-Options, X-Content-Type-Options, HSTS, etc.)
  - HTTP to HTTPS redirect
  - SSL/TLS configuration with modern cipher suites
  - Let's Encrypt ACME challenge support
- **SSL certificate directory** (`nginx/ssl/`) with setup instructions
- New cookiecutter variables:
  - `include_nginx_service`: Include Nginx container in docker-compose
  - `include_nginx_config`: Generate nginx configuration files
  - `use_nginx`: Using Nginx (included or external)
  - `use_traefik`: Using Traefik (included or external)

### Changed

- **Reverse proxy prompt** now offers 5 options:
  - Traefik (included in docker-compose) - default
  - Traefik (external, shared between projects)
  - Nginx (included in docker-compose)
  - Nginx (external, config template only)
  - None (expose ports directly)
- **`ReverseProxyType` enum** extended with `NGINX_INCLUDED` and `NGINX_EXTERNAL`
- **docker-compose.prod.yml** updated:
  - Added nginx service definition
  - Services use backend-internal network when nginx is selected
  - No ports exposed on backend/frontend when nginx handles traffic
- **`.env.prod.example`** includes DOMAIN variable for nginx configuration
- **`post_gen_project.py`** removes nginx/ folder when nginx is not selected

### Tests Added

- Tests for `NGINX_INCLUDED` and `NGINX_EXTERNAL` enum values
- Tests for cookiecutter context generation with all reverse proxy options
- Tests for `prompt_reverse_proxy()` with nginx choices

## [0.1.9] - 2025-12-26

### Added

#### SQLModel Support

- **Optional SQLModel ORM** as alternative to SQLAlchemy for PostgreSQL and SQLite
- New `--orm` CLI option: `--orm sqlalchemy` (default) or `--orm sqlmodel`
- Interactive prompt for ORM library selection when using `fastapi-fullstack new`
- SQLModel provides simplified syntax combining SQLAlchemy and Pydantic:
  ```python
  from sqlmodel import SQLModel, Field

  class User(SQLModel, table=True):
      id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
      email: str = Field(max_length=255, unique=True)
      is_active: bool = Field(default=True)
  ```
- Full Alembic compatibility maintained with SQLModel
- SQLAdmin works seamlessly with SQLModel models
- All database models updated with SQLModel variants:
  - `User`, `Item`, `Conversation`, `Message`, `Session`, `Webhook`, `WebhookDelivery`
- `VARIABLES.md` updated with new ORM variables: `orm_type`, `use_sqlalchemy`, `use_sqlmodel`

### Changed

- Database model templates now support conditional SQLModel/SQLAlchemy syntax
- `alembic/env.py` uses `SQLModel.metadata` when SQLModel is selected
- Repositories remain unchanged (SQLModel uses same AsyncSession and methods)

### Tests Added

- Tests for `OrmType` enum values
- Tests for `use_sqlalchemy` and `use_sqlmodel` computed fields
- Tests for SQLModel validation (requires PostgreSQL or SQLite)
- Tests for `prompt_orm_type()` function
- Updated `run_interactive_prompts()` tests with `prompt_orm_type` mocks

## [0.1.7] - 2025-12-23

### Added

#### Docker & Production

- **Optional Traefik reverse proxy** with three configuration modes:
  - `traefik_included`: Full Traefik setup in docker-compose.prod.yml (default)
  - `traefik_external`: Traefik labels only, for shared Traefik instances
  - `none`: No reverse proxy, ports exposed directly
- **`.env.prod.example` template** for production secrets management:
  - Conditional sections for PostgreSQL, Redis, JWT, Traefik, Flower
  - Required variable validation using `${VAR:?error}` syntax
  - Setup instructions in docker-compose.prod.yml header
- **Unique Traefik router names** using `project_slug` prefix for multi-tenant support:
  - `{project_slug}-api`, `{project_slug}-frontend`, `{project_slug}-flower`
  - Prevents conflicts when running multiple projects on same server

#### AI Agent Support

- **`AGENTS.md`** file for non-Claude AI agents (Codex, Copilot, Cursor, Zed, OpenCode)
- **Progressive disclosure documentation** in generated projects:
  - `docs/architecture.md` - layered architecture details
  - `docs/adding_features.md` - how to add endpoints, commands, tools
  - `docs/testing.md` - testing guide and examples
  - `docs/patterns.md` - DI, service, repository patterns
- **README.md** updated with "AI-Agent Friendly" section

### Changed

- **Template `CLAUDE.md` refactored** from 384 to ~80 lines following [progressive disclosure best practices](https://humanlayer.dev/blog/writing-a-good-claude-md)
- **Main project `CLAUDE.md`** updated with "Where to Find More Info" section
- **docker-compose.prod.yml** now uses `env_file: .env.prod` instead of inline defaults
- **Removed hardcoded credentials** (`changeme`) from docker-compose.prod.yml

### Security

- Production credentials no longer have insecure defaults
- `.env.prod` added to `.gitignore` to prevent committing secrets
- Required environment variables fail fast with descriptive error messages

## [0.1.6] - 2025-12-22

### Added

#### Multi-LLM Provider Support
- **Multiple LLM providers** for AI agents: OpenAI, Anthropic, and OpenRouter
- PydanticAI supports all three providers (OpenAI, Anthropic, OpenRouter)
- LangChain supports OpenAI and Anthropic
- New `--llm-provider` CLI option and interactive prompt
- Provider-specific API key configuration in `.env` and `config.py`

#### CLI Enhancements
- **`make create-admin` command** for quick admin user creation
- **Comprehensive CLI options** for `fastapi-fullstack create` command:
  - `--redis`, `--caching`, `--rate-limiting`
  - `--admin-panel`, `--websockets`
  - `--task-queue` (none/celery/taskiq/arq)
  - `--oauth-google`, `--session-management`
  - `--kubernetes`, `--ci` (github/gitlab/none)
  - `--sentry`, `--prometheus`
  - `--file-storage`, `--webhooks`
  - `--python-version` (3.11/3.12/3.13)
  - `--i18n`
- **Configuration presets** for common use cases:
  - `--preset production`: Full production setup with Redis, Sentry, K8s, Prometheus
  - `--preset ai-agent`: AI agent with WebSocket streaming and conversation persistence
- **Interactive rate limit configuration** when rate limiting is enabled:
  - Requests per period (default: 100)
  - Period in seconds (default: 60)
  - Storage backend (memory or Redis)

#### Documentation
- **Improved CLI documentation** in README explaining project CLI naming convention (`uv run <project_slug>`)
- **Makefile shortcuts** documented with `make help` command

#### Template Improvements
- **Generator version metadata** in generated projects (`pyproject.toml`):
  ```toml
  [tool.fastapi-fullstack]
  generator_version = "0.1.6"
  generated_at = "2025-12-22T10:30:00+00:00"
  ```
- **Centralized agent prompts** module (`app/agents/prompts.py`) for easier maintenance
- **Template variables documentation** (`template/VARIABLES.md`) with 88+ variables documented

#### Validation
- **Email validation** for `author_email` field using Pydantic's `EmailStr`
- **Tests for OpenRouter + LangChain** validation (combination is rejected)
- **Tests for agents folder** conditional creation

### Changed

#### Configuration Validation
- **Improved option combination validation** in `ProjectConfig`:
  - Admin panel requires PostgreSQL or SQLite (not MongoDB)
  - Caching requires Redis to be enabled
  - Session management requires a database
  - Conversation persistence requires a database
  - Rate limiting with Redis storage requires Redis enabled
  - OpenRouter is only available with PydanticAI (not LangChain)

#### Database Support
- **Admin panel prompt** now appears for both PostgreSQL and SQLite (previously only PostgreSQL)
- **Database-specific post-generation messages**:
  - PostgreSQL: `make docker-db` + migration commands
  - SQLite: Auto-creation note + migration commands (no Docker)
  - MongoDB: `make docker-mongo` (no migrations)
- **Added `close_db()` function** for SQLite database consistency

#### Project Name Handling
- **Unified project name validation** between `prompts.py` and `config.py`
- Extracted validation into `_validate_project_name()` function with clear error messages
- Shows converted project name to user when it differs from input

### Fixed

#### Backend Fixes
- **Conversation list API response format**: Changed `/conversations` and `/conversations/{id}/messages` endpoints to return paginated response `{ items: [...], total: N }` instead of raw array, fixing frontend conversation list not loading after page refresh
- **Database session handling**: Split `get_db_session` into async generator for FastAPI `Depends()` and `@asynccontextmanager` for manual use (WebSocket handlers)
- **WebSocket authentication**:
  - Update `deps.py` to use `get_db_context` for WebSocket auth
  - Add cookie-based authentication support for WebSocket (`access_token` cookie)
  - Now accepts token via query parameter OR cookie for flexibility
- **WebSocket exception handling**: Fix `AttributeError` when exception occurs on WebSocket connection (`request.method` doesn't exist for WebSocket)
- **WebSocket conversation persistence**:
  - Fix `get_db_session` vs `get_db_context` usage (async generator vs async context manager)
  - Fix event name mismatch: backend now sends `conversation_created` to match frontend expectation
- **Docker Compose**: Fix `env_file` path from `.env` to `./backend/.env`
- **ValidationInfo typing**: Add proper type hints to all field validators in `config.py`

#### Frontend Fixes
- **ThemeToggle hydration mismatch**: Add mounted state to prevent SSR/client mismatch
- **Button component**: Extract `asChild` prop to prevent DOM warning
- **ConversationList**: Add default value for conversations to prevent undefined error
- **New Chat button**:
  - Create conversation in database immediately (eager creation)
  - Clear messages properly when switching conversations
  - Fix message appending issue when switching between conversations
- **Conversation store**: Add defensive checks for undefined state

#### CLI Fixes
- **Consistent package name**: Changed from `fastapi-gen` to `fastapi-fullstack` in version option
- **Makefile**: Always generated now (removed from optional dev tools)

#### Template/Generator Fixes
- **Ruff dependency in hooks**: Graceful handling when ruff is not installed:
  - Check PATH for ruff binary
  - Fall back to `uvx ruff` if uv is available
  - Fall back to `python -m ruff` if available as module
  - Show friendly warning if ruff is not available
- **Dynamic generator version**: Replaced hardcoded version with `DYNAMIC` placeholder
- **Unused files cleanup**: Improved post-generation hook to remove:
  - AI agent files based on framework selection
  - Example CRUD files when disabled
  - Conversation, webhook, session files when features disabled
  - Worker directory when no background tasks selected
  - Empty directories automatically
- **`.env` file location**: Move `.env.example` from root to `backend/`

### Tests Added

- Tests for all configuration validation combinations
- Tests for project name validation edge cases
- Tests for `new` command `--output` option
- Tests for OpenRouter + LangChain validation
- Tests for admin panel prompt with SQLite
- Tests for agents folder conditional creation
- Tests for email validation (config and prompts)
- Tests for rate limit configuration prompts
