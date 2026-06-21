# Environment variables

Reference for `{{ cookiecutter.project_name }}` runtime configuration. The
authoritative source is `backend/.env.example` — this doc explains what each
group is for and which are required vs optional.

> Quick start: copy `backend/.env.example` to `backend/.env` and fill in the
> blanks marked **Required**. Defaults are sensible for local development.

## Project

| Variable | Required | Default | Description |
|---|---|---|---|
| `PROJECT_NAME` | optional | `{{ cookiecutter.project_name }}` | Used in logs, OpenAPI title, email templates |
| `DEBUG` | optional | `true` | When `true`, FastAPI returns full tracebacks |
| `ENVIRONMENT` | optional | `local` | Free-form tag: `local` / `staging` / `production` |
| `TIMEZONE` | optional | `{{ cookiecutter.timezone }}` | IANA TZ name (e.g. `Europe/Warsaw`) |
| `BACKEND_URL` | optional | `http://localhost:{{ cookiecutter.backend_port }}` | Used by frontend BFF + email link generation |
| `FRONTEND_URL` | optional | `http://localhost:{{ cookiecutter.frontend_port }}` | Used by password-reset / magic-link emails |

## Auth & secrets

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **required in prod** | (generated) | JWT signing key. Rotating invalidates all tokens |
| `API_KEY` | **required in prod** | (generated) | Static admin/service-to-service key for `X-API-Key` header |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | optional | `30` | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | optional | `10080` | JWT refresh token lifetime (7 days) |
{%- if cookiecutter.enable_oauth_google %}
| `GOOGLE_OAUTH_CLIENT_ID` | required | — | From Google Cloud Console → OAuth credentials |
| `GOOGLE_OAUTH_CLIENT_SECRET` | required | — | jw |
{%- endif %}

## Database
| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | **required** | `postgresql+asyncpg://...` | Full async connection string |
| `DB_POOL_SIZE` | optional | `{{ cookiecutter.db_pool_size }}` | Number of long-lived connections |
| `DB_MAX_OVERFLOW` | optional | `{{ cookiecutter.db_max_overflow }}` | Burst capacity above pool size |

## LLM / AI
{% if cookiecutter.use_openai %}
| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | **required** | — | From platform.openai.com |
| `AI_MODEL` | optional | `gpt-5.5` | Default model used by agent (provider-specific) |
{%- endif %}
{%- if cookiecutter.use_anthropic %}
| `ANTHROPIC_API_KEY` | **required** | — | From console.anthropic.com |
{%- endif %}
{%- if cookiecutter.use_google %}
| `GOOGLE_API_KEY` | **required** | — | From aistudio.google.com |
{%- endif %}
{%- if cookiecutter.use_openrouter %}
| `OPENROUTER_API_KEY` | **required** | — | From openrouter.ai |
{%- endif %}
{%- if cookiecutter.enable_logfire %}
| `LOGFIRE_TOKEN` | optional | — | When set, ships traces to Logfire (logfire.pydantic.dev) |
{%- endif %}
{%- if cookiecutter.enable_langsmith %}
| `LANGSMITH_API_KEY` | optional | — | When set, sends traces to smith.langchain.com |
| `LANGSMITH_PROJECT` | optional | `{{ cookiecutter.project_slug }}` | Project bucket in LangSmith |
{%- endif %}

{%- if cookiecutter.enable_rag %}

## RAG ({{ cookiecutter.vector_store }})

| Variable | Required | Default | Description |
|---|---|---|---|
{%- if cookiecutter.use_milvus %}
| `MILVUS_URI` | **required** | `http://localhost:19530` | Milvus gRPC endpoint |
| `MILVUS_TOKEN` | optional | — | Auth token (cloud Milvus) |
{%- elif cookiecutter.use_qdrant %}
| `QDRANT_URL` | **required** | `http://localhost:6333` | Qdrant REST endpoint |
| `QDRANT_API_KEY` | optional | — | Auth (cloud Qdrant) |
{%- elif cookiecutter.use_chromadb %}
| `CHROMA_HOST` | optional | `localhost` | Chroma server host |
| `CHROMA_PORT` | optional | `8000` | Chroma server port |
{%- endif %}
{%- if cookiecutter.use_voyage_embeddings %}
| `VOYAGE_API_KEY` | **required** | — | From voyageai.com |
{%- endif %}
{%- if cookiecutter.use_llamaparse %}
| `LLAMA_CLOUD_API_KEY` | required for PDF parsing | — | From cloud.llamaindex.ai |
{%- endif %}
{%- if cookiecutter.enable_google_drive_ingestion %}
| `GOOGLE_DRIVE_CREDENTIALS_FILE` | required | — | Path to service-account JSON |
{%- endif %}
{%- if cookiecutter.enable_s3_ingestion %}
| `RAG_S3_BUCKET` | required | — | Source bucket for ingestion |
| `RAG_S3_PREFIX` | optional | `""` | Path prefix to scan |
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_redis %}

## Redis

| Variable | Required | Default | Description |
|---|---|---|---|
| `REDIS_URL` | **required** | `redis://localhost:6379/0` | Used by{% if cookiecutter.enable_caching %} cache,{% endif %}{% if cookiecutter.use_celery %} Celery broker,{% endif %}{% if cookiecutter.enable_rate_limiting %} rate-limiter,{% endif %} session store |
{%- endif %}

{%- if cookiecutter.enable_email %}

## Email ({{ cookiecutter.email_provider }})

| Variable | Required | Default | Description |
|---|---|---|---|
{%- if cookiecutter.email_provider == "resend" %}
| `RESEND_API_KEY` | **required** | — | From resend.com |
| `EMAIL_FROM` | **required** | — | Verified sender, e.g. `noreply@yourdomain.com` |
{%- elif cookiecutter.email_provider == "smtp" %}
| `SMTP_HOST` | **required** | — | e.g. `smtp.sendgrid.net` |
| `SMTP_PORT` | optional | `587` | TLS port |
| `SMTP_USERNAME` | **required** | — | SMTP auth user |
| `SMTP_PASSWORD` | **required** | — | SMTP auth password |
| `EMAIL_FROM` | **required** | — | Verified sender |
{%- else %}
| (log provider — no env vars; emails written to stdout) | — | — | — |
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_billing %}

## Stripe billing

| Variable | Required | Default | Description |
|---|---|---|---|
| `STRIPE_SECRET_KEY` | **required** | — | `sk_live_...` (or `sk_test_...` for testing) |
| `STRIPE_WEBHOOK_SECRET` | **required** | — | `whsec_...` from Stripe Dashboard webhook config |
| `STRIPE_PUBLISHABLE_KEY` | **required** | — | `pk_live_...` exposed to frontend |
| `BILLING_DEFAULT_CURRENCY` | optional | `{{ cookiecutter.billing_default_currency }}` | ISO-4217 currency code |
| `BILLING_TRIAL_DAYS` | optional | `{{ cookiecutter.billing_trial_days_default }}` | Default trial length |
{%- if cookiecutter.enable_credits_system %}
| `CREDITS_PER_USD` | optional | `{{ cookiecutter.billing_credits_per_usd }}` | Conversion rate token-cost → credits |
| `CREDITS_LOW_THRESHOLD` | optional | `{{ cookiecutter.billing_credits_low_threshold }}` | Triggers low-credits email |
| `CREDITS_FREE_TIER_GRANT` | optional | `{{ cookiecutter.billing_credits_free_tier_grant }}` | Granted to new orgs on signup |
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_sentry %}

## Sentry

| Variable | Required | Default | Description |
|---|---|---|---|
| `SENTRY_DSN` | optional (off if empty) | — | From sentry.io project settings |
| `SENTRY_ENVIRONMENT` | optional | `local` | Tag for `environment` filter |
| `SENTRY_TRACES_SAMPLE_RATE` | optional | `0.1` | 0.0–1.0 — perf tracing sample |
{%- endif %}

{%- if cookiecutter.enable_prometheus %}

## Prometheus

| Variable | Required | Default | Description |
|---|---|---|---|
| `PROMETHEUS_METRICS_PATH` | optional | `/metrics` | URL path where metrics are exposed |
| `PROMETHEUS_AUTH_TOKEN` | optional (off if empty) | — | When set, `/metrics` requires `Authorization: Bearer <token>` |
{%- endif %}

{%- if cookiecutter.enable_file_storage %}

## File storage (S3/MinIO)

| Variable | Required | Default | Description |
|---|---|---|---|
| `S3_ENDPOINT_URL` | optional | (AWS default) | Set for MinIO/Backblaze/etc. |
| `S3_ACCESS_KEY` | **required** | — | Access key ID |
| `S3_SECRET_KEY` | **required** | — | Secret key |
| `S3_BUCKET` | **required** | — | Default bucket for uploads |
| `S3_REGION` | optional | `us-east-1` | AWS region |
{%- endif %}

## Validation

```bash
# Confirm settings load without errors:
cd backend && uv run python -c "from app.core.config import settings; print(settings.model_dump_json(indent=2))"
```

If any **Required** var is missing, FastAPI raises `pydantic_settings.SettingsError` on startup — check the message for which field.
