# Manual setup steps for {{ cookiecutter.project_name }}

The generator created the code. These are the **one-time external setup steps**
that can't be automated — accounts to create, keys to copy, services to provision.

> Skip ahead to "After every deploy" at the bottom for things you'll re-do
> regularly. Items above are one-time per environment.

---

## Secrets

```bash
cp backend/.env.example backend/.env
```

Then in `backend/.env`:

- [ ] **`SECRET_KEY`** — replace with a fresh value: `openssl rand -hex 32`
- [ ] **`API_KEY`** — replace with a fresh value: `openssl rand -hex 32`

These are used to sign JWTs and authenticate service-to-service calls. Rotate at every environment promotion (dev → staging → prod each get their own).

## PostgreSQL

- [ ] Provision a PostgreSQL ≥ 14 instance (local: `docker compose up -d db`; managed: Neon / Supabase / RDS / Cloud SQL).
- [ ] Set `DATABASE_URL` in `.env` to the **async** connection string: `postgresql+asyncpg://user:pass@host:5432/dbname`.
- [ ] Run migrations: `cd backend && uv run alembic upgrade head`.

{%- if cookiecutter.use_openai %}

## OpenAI

- [ ] Create API key at https://platform.openai.com/api-keys.
- [ ] Set `OPENAI_API_KEY` in `.env`.
- [ ] (Optional) Set spending limit on OpenAI dashboard to avoid surprise bills.
{%- endif %}

{%- if cookiecutter.use_anthropic %}

## Anthropic

- [ ] Create API key at https://console.anthropic.com/.
- [ ] Set `ANTHROPIC_API_KEY` in `.env`.
{%- endif %}

{%- if cookiecutter.use_google %}

## Google AI Studio

- [ ] Create API key at https://aistudio.google.com/.
- [ ] Set `GOOGLE_API_KEY` in `.env`.
{%- endif %}

{%- if cookiecutter.use_openrouter %}

## OpenRouter

- [ ] Create API key at https://openrouter.ai/keys.
- [ ] Set `OPENROUTER_API_KEY` in `.env`.
{%- endif %}

{%- if cookiecutter.enable_oauth_google %}

## Google OAuth

- [ ] Go to https://console.cloud.google.com/ → APIs & Services → Credentials → Create OAuth client ID.
- [ ] Application type: **Web application**.
- [ ] Authorized redirect URIs: `{{ cookiecutter.frontend_port and "http://localhost:" + cookiecutter.frontend_port|string or "http://localhost:3000" }}/auth/callback`. Add prod URL when deploying.
- [ ] Copy **Client ID** + **Client secret** → set `GOOGLE_OAUTH_CLIENT_ID` + `GOOGLE_OAUTH_CLIENT_SECRET` in `.env`.
{%- endif %}

{%- if cookiecutter.enable_rag %}

## RAG ({{ cookiecutter.vector_store }})
{% if cookiecutter.use_milvus %}
- [ ] Local: `docker compose up -d milvus etcd minio` (already in `docker-compose.yml`).
- [ ] Cloud: provision via Zilliz Cloud, set `MILVUS_URI` + `MILVUS_TOKEN`.
{%- elif cookiecutter.use_qdrant %}
- [ ] Local: `docker compose up -d qdrant`.
- [ ] Cloud: provision Qdrant Cloud, set `QDRANT_URL` + `QDRANT_API_KEY`.
{%- elif cookiecutter.use_chromadb %}
- [ ] Local: `docker compose up -d chroma` (or run embedded mode — set `CHROMA_HOST=localhost`).
- [ ] No managed cloud service for Chroma; use Milvus or Qdrant in production.
{%- elif cookiecutter.use_pgvector %}
- [ ] Run `CREATE EXTENSION vector;` against your Postgres database (already added to migration `0007`).
{%- endif %}

- [ ] (Optional) Ingest seed documents: `uv run {{ cookiecutter.project_slug }} rag-ingest /path/to/file.pdf --collection docs`.
{%- if cookiecutter.enable_google_drive_ingestion %}

### Google Drive sync source

- [ ] Create a service account at https://console.cloud.google.com/iam-admin/serviceaccounts.
- [ ] Download the JSON credentials → save to `secrets/gdrive-service-account.json`.
- [ ] Share the target Drive folder with the service-account email.
- [ ] Set `GOOGLE_DRIVE_CREDENTIALS_FILE` in `.env`.
{%- endif %}
{%- if cookiecutter.enable_s3_ingestion %}

### S3 / MinIO sync source

- [ ] Provision an S3 bucket (or run MinIO locally: `docker compose up -d minio`).
- [ ] Create an IAM user with `s3:GetObject` + `s3:ListBucket` on the source bucket.
- [ ] Set `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `RAG_S3_BUCKET` / `RAG_S3_PREFIX` in `.env`.
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_redis %}

## Redis

- [ ] Local: `docker compose up -d redis` (already in compose file).
- [ ] Managed: Upstash / Redis Cloud / ElastiCache. Set `REDIS_URL` in `.env`.
{%- endif %}

{%- if cookiecutter.enable_billing %}

## Stripe billing

- [ ] Create account at https://dashboard.stripe.com/.
- [ ] Get API keys (Developers → API keys): set `STRIPE_SECRET_KEY` + `STRIPE_PUBLISHABLE_KEY` in `.env`.
- [ ] Create products + prices in Stripe Dashboard, then sync IDs to seed migration or your `plans` table.
- [ ] Set up webhook endpoint:
  - Endpoint URL: `https://your-backend/api/v1/billing/webhook`
  - Events: `checkout.session.completed`, `customer.subscription.{created,updated,deleted}`, `invoice.{paid,payment_failed}`, `payment_intent.succeeded`
  - Copy signing secret → set `STRIPE_WEBHOOK_SECRET` in `.env`.
- [ ] Test via Stripe CLI: `stripe listen --forward-to localhost:{{ cookiecutter.backend_port }}/api/v1/billing/webhook`.
{%- endif %}

{%- if cookiecutter.enable_email %}

## Transactional email
{% if cookiecutter.email_provider == "resend" %}
- [ ] Sign up at https://resend.com.
- [ ] Verify your sending domain (DNS DKIM/SPF records).
- [ ] Create API key → set `RESEND_API_KEY` in `.env`.
- [ ] Set `EMAIL_FROM=noreply@yourdomain.com` (must be on verified domain).
{%- elif cookiecutter.email_provider == "smtp" %}
- [ ] Pick provider (SendGrid / Mailgun / Postmark / SES). Set up DNS records they require.
- [ ] Create SMTP credentials → set `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` in `.env`.
- [ ] Set `EMAIL_FROM=noreply@yourdomain.com`.
{%- else %}
- [ ] No external provider — emails written to stdout (`log` provider). Useful for dev only.
- [ ] Switch to `resend` or `smtp` for staging/prod.
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_sentry %}

## Sentry

- [ ] Create project at https://sentry.io/.
- [ ] Copy DSN → set `SENTRY_DSN` in `.env`.
- [ ] (Optional) Configure release tracking in CI by setting `SENTRY_RELEASE` to git SHA before deploy.
{%- endif %}

{%- if cookiecutter.enable_logfire %}

## Logfire (Pydantic observability)

- [ ] Create account at https://logfire.pydantic.dev.
- [ ] Run `uv run logfire auth` once locally to bootstrap.
- [ ] Get write token → set `LOGFIRE_TOKEN` in `.env` for non-local environments.
{%- endif %}

{%- if cookiecutter.enable_langsmith %}

## LangSmith

- [ ] Create account at https://smith.langchain.com.
- [ ] Get API key → set `LANGSMITH_API_KEY` + `LANGSMITH_PROJECT={{ cookiecutter.project_slug }}` in `.env`.
{%- endif %}

{%- if cookiecutter.enable_kubernetes %}

## Kubernetes deploy

- [ ] Build + push images: see `docs/deploy.md` → Kubernetes section.
- [ ] Create cluster secret from `.env`: `kubectl create secret generic app-secrets --from-env-file=backend/.env`.
- [ ] Update image tags in `k8s/deployment.yaml`.
- [ ] Apply: `kubectl apply -f k8s/`.
{%- endif %}

---

## After every deploy

- [ ] Run database migrations: `alembic upgrade head` (CI step or post-deploy job).
- [ ] Smoke test `/api/v1/health` returns `{"status": "ok"}`.
{% if cookiecutter.use_frontend %}- [ ] Frontend loads, login → dashboard flow works.
{% endif %}{% if cookiecutter.enable_billing %}- [ ] Stripe webhook delivers (check Stripe Dashboard → Developers → Webhooks → recent deliveries).
{% endif %}- [ ] Logs flowing to your aggregator.

---

## Where to find more

- `ENV_VARS.md` — exhaustive env var reference
- `docs/deploy.md` — platform-specific deployment recipes
- `SECURITY.md` — security model + production hardening checklist
- `CONTRIBUTING.md` — dev environment setup
- `docs/architecture.md` — codebase layered architecture rules
