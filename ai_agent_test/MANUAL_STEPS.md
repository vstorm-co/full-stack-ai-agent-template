# Manual setup steps for ai_agent_test

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

## OpenRouter

- [ ] Create API key at https://openrouter.ai/keys.
- [ ] Set `OPENROUTER_API_KEY` in `.env`.

## Google OAuth

- [ ] Go to https://console.cloud.google.com/ → APIs & Services → Credentials → Create OAuth client ID.
- [ ] Application type: **Web application**.
- [ ] Authorized redirect URIs: `http://localhost:3000/auth/callback`. Add prod URL when deploying.
- [ ] Copy **Client ID** + **Client secret** → set `GOOGLE_OAUTH_CLIENT_ID` + `GOOGLE_OAUTH_CLIENT_SECRET` in `.env`.

## RAG (milvus)

- [ ] Local: `docker compose up -d milvus etcd minio` (already in `docker-compose.yml`).
- [ ] Cloud: provision via Zilliz Cloud, set `MILVUS_URI` + `MILVUS_TOKEN`.

- [ ] (Optional) Ingest seed documents: `uv run ai_agent_test rag-ingest /path/to/file.pdf --collection docs`.

### Google Drive sync source

- [ ] Create a service account at https://console.cloud.google.com/iam-admin/serviceaccounts.
- [ ] Download the JSON credentials → save to `secrets/gdrive-service-account.json`.
- [ ] Share the target Drive folder with the service-account email.
- [ ] Set `GOOGLE_DRIVE_CREDENTIALS_FILE` in `.env`.

### S3 / MinIO sync source

- [ ] Provision an S3 bucket (or run MinIO locally: `docker compose up -d minio`).
- [ ] Create an IAM user with `s3:GetObject` + `s3:ListBucket` on the source bucket.
- [ ] Set `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `RAG_S3_BUCKET` / `RAG_S3_PREFIX` in `.env`.

## Redis

- [ ] Local: `docker compose up -d redis` (already in compose file).
- [ ] Managed: Upstash / Redis Cloud / ElastiCache. Set `REDIS_URL` in `.env`.

## Transactional email

- [ ] Pick provider (SendGrid / Mailgun / Postmark / SES). Set up DNS records they require.
- [ ] Create SMTP credentials → set `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` in `.env`.
- [ ] Set `EMAIL_FROM=noreply@yourdomain.com`.

## Logfire (Pydantic observability)

- [ ] Create account at https://logfire.pydantic.dev.
- [ ] Run `uv run logfire auth` once locally to bootstrap.
- [ ] Get write token → set `LOGFIRE_TOKEN` in `.env` for non-local environments.

---

## After every deploy

- [ ] Run database migrations: `alembic upgrade head` (CI step or post-deploy job).
- [ ] Smoke test `/api/v1/health` returns `{"status": "ok"}`.
- [ ] Frontend loads, login → dashboard flow works.
- [ ] Logs flowing to your aggregator.

---

## Where to find more

- `ENV_VARS.md` — exhaustive env var reference
- `docs/deploy.md` — platform-specific deployment recipes
- `SECURITY.md` — security model + production hardening checklist
- `CONTRIBUTING.md` — dev environment setup
- `docs/architecture.md` — codebase layered architecture rules
