# Environment variables

Reference for `ai_agent_test` runtime configuration. The
authoritative source is `backend/.env.example` — this doc explains what each
group is for and which are required vs optional.

> Quick start: copy `backend/.env.example` to `backend/.env` and fill in the
> blanks marked **Required**. Defaults are sensible for local development.

## Project

| Variable | Required | Default | Description |
|---|---|---|---|
| `PROJECT_NAME` | optional | `ai_agent_test` | Used in logs, OpenAPI title, email templates |
| `DEBUG` | optional | `true` | When `true`, FastAPI returns full tracebacks |
| `ENVIRONMENT` | optional | `local` | Free-form tag: `local` / `staging` / `production` |
| `TIMEZONE` | optional | `UTC` | IANA TZ name (e.g. `Europe/Warsaw`) |
| `BACKEND_URL` | optional | `http://localhost:8000` | Used by frontend BFF + email link generation |
| `FRONTEND_URL` | optional | `http://localhost:3000` | Used by password-reset / magic-link emails |

## Auth & secrets

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **required in prod** | (generated) | JWT signing key. Rotating invalidates all tokens |
| `API_KEY` | **required in prod** | (generated) | Static admin/service-to-service key for `X-API-Key` header |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | optional | `30` | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | optional | `10080` | JWT refresh token lifetime (7 days) |
| `GOOGLE_OAUTH_CLIENT_ID` | required | — | From Google Cloud Console → OAuth credentials |
| `GOOGLE_OAUTH_CLIENT_SECRET` | required | — | jw |

## Database

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | **required** | `postgresql+asyncpg://...` | Full async connection string |
| `DB_POOL_SIZE` | optional | `5` | Number of long-lived connections |
| `DB_MAX_OVERFLOW` | optional | `10` | Burst capacity above pool size |

## LLM / AI

| `OPENROUTER_API_KEY` | **required** | — | From openrouter.ai |
| `LOGFIRE_TOKEN` | optional | — | When set, ships traces to Logfire (logfire.pydantic.dev) |

## RAG (milvus)

| Variable | Required | Default | Description |
|---|---|---|---|
| `MILVUS_URI` | **required** | `http://localhost:19530` | Milvus gRPC endpoint |
| `MILVUS_TOKEN` | optional | — | Auth token (cloud Milvus) |
| `LLAMA_CLOUD_API_KEY` | required for PDF parsing | — | From cloud.llamaindex.ai |
| `GOOGLE_DRIVE_CREDENTIALS_FILE` | required | — | Path to service-account JSON |
| `RAG_S3_BUCKET` | required | — | Source bucket for ingestion |
| `RAG_S3_PREFIX` | optional | `""` | Path prefix to scan |

## Redis

| Variable | Required | Default | Description |
|---|---|---|---|
| `REDIS_URL` | **required** | `redis://localhost:6379/0` | Used by cache, Celery broker, rate-limiter, session store |

## Email (smtp)

| Variable | Required | Default | Description |
|---|---|---|---|
| `SMTP_HOST` | **required** | — | e.g. `smtp.sendgrid.net` |
| `SMTP_PORT` | optional | `587` | TLS port |
| `SMTP_USERNAME` | **required** | — | SMTP auth user |
| `SMTP_PASSWORD` | **required** | — | SMTP auth password |
| `EMAIL_FROM` | **required** | — | Verified sender |

## Validation

```bash
# Confirm settings load without errors:
cd backend && uv run python -c "from app.core.config import settings; print(settings.model_dump_json(indent=2))"
```

If any **Required** var is missing, FastAPI raises `pydantic_settings.SettingsError` on startup — check the message for which field.
