# Deployment

This project was generated with the following deployment-related flags:

{% if cookiecutter.enable_docker %}- ✅ Docker / `docker-compose.yml`{% else %}- ❌ No Docker (manual deploy){% endif %}
{% if cookiecutter.enable_kubernetes %}- ✅ Kubernetes manifests in `k8s/`{% else %}- ❌ No Kubernetes manifests{% endif %}
- CI: `{{ cookiecutter.ci_type }}`
{% if cookiecutter.use_nginx %}- Reverse proxy: Nginx{% endif %}
{% if cookiecutter.use_traefik %}- Reverse proxy: Traefik{% endif %}

---

{% if cookiecutter.enable_docker %}
## Docker Compose (single host)

For staging or small production:

```bash
# 1. Configure
cp backend/.env.example backend/.env
# Edit backend/.env with production values (see ENV_VARS.md)

# 2. Build + start
docker compose up -d --build

# 3. Apply migrations
docker compose exec app uv run alembic upgrade head


# 4. Verify
curl http://localhost:{{ cookiecutter.backend_port }}/api/v1/health
{% if cookiecutter.use_frontend %}# Frontend: http://localhost:{{ cookiecutter.frontend_port }}{% endif %}
```

### Reverse proxy

{%- if cookiecutter.use_nginx %}
Nginx config in `nginx/` proxies `/` → frontend, `/api` → backend, `/ws` → backend WebSocket. Update `server_name` and TLS cert paths in `nginx/conf.d/app.conf`.
{%- elif cookiecutter.use_traefik %}
Traefik labels in `docker-compose.yml` route based on `Host()`. Set `DOMAIN` env var, then point your DNS at the host. ACME / Let's Encrypt configured via labels — uncomment in `docker-compose.yml` and set `ACME_EMAIL`.
{%- else %}
Front this with your own reverse proxy (Caddy / Nginx / ALB). The backend listens on `:{{ cookiecutter.backend_port }}` and frontend on `:{{ cookiecutter.frontend_port }}`.
{%- endif %}
{% endif %}

{% if cookiecutter.enable_kubernetes %}

## Kubernetes

Manifests in `k8s/` cover: Deployment, Service, ConfigMap, Secret stub, Ingress, optional HPA.

```bash
# Build + push images
docker build -t your-registry/{{ cookiecutter.project_slug }}-backend:latest backend/
{% if cookiecutter.use_frontend %}docker build -t your-registry/{{ cookiecutter.project_slug }}-frontend:latest frontend/
{% endif %}docker push your-registry/{{ cookiecutter.project_slug }}-backend:latest

# Update image tags in k8s/deployment.yaml, then:
kubectl create namespace {{ cookiecutter.project_slug }}
kubectl -n {{ cookiecutter.project_slug }} create secret generic app-secrets --from-env-file=backend/.env
kubectl apply -n {{ cookiecutter.project_slug }} -f k8s/

# Migrations as a Job
kubectl -n {{ cookiecutter.project_slug }} apply -f k8s/migration-job.yaml
```

### Tuning

- **Replicas:** edit `k8s/deployment.yaml`. Backend is async — start with 2 replicas.
- **HPA:** if `k8s/hpa.yaml` is present, scales on CPU. Adjust thresholds.
- **Resources:** request/limit set conservatively. Scale up RAM if you process large files{% if cookiecutter.enable_rag %} or have many concurrent RAG queries{% endif %}.
{% endif %}

## Platform-specific quickstarts

### Fly.io

```bash
fly launch --name {{ cookiecutter.project_slug }}-backend --region waw
{% if cookiecutter.use_postgresql %}fly postgres create --name {{ cookiecutter.project_slug }}-db
fly postgres attach {{ cookiecutter.project_slug }}-db
{% endif %}{% if cookiecutter.enable_redis %}# Redis: use Upstash (`fly redis create`) or Fly's Tigris{% endif %}
fly secrets set $(cat backend/.env | grep -v '^#' | xargs)
fly deploy
```

### Railway

1. Connect repo, pick Dockerfile-based deploy.
2. Add env vars from `backend/.env` to Railway service.
{% if cookiecutter.use_postgresql %}3. Provision PostgreSQL plugin → `DATABASE_URL` auto-injected.
{% endif %}{% if cookiecutter.enable_redis %}4. Provision Redis plugin → `REDIS_URL` auto-injected.
{% endif %}5. Deploy.

### Render

1. Create Web Service → docker, point at `backend/Dockerfile`.
{% if cookiecutter.use_frontend %}2. Create Static Site for frontend (build cmd: `bun install && bun run build`, output dir: `.next`).
{% endif %}{% if cookiecutter.use_postgresql %}3. Create PostgreSQL → copy DATABASE_URL.
{% endif %}4. Add env vars; deploy.

### Vercel (frontend only)
{% if cookiecutter.use_frontend %}
The frontend is a Next.js app — works on Vercel out of the box.

```bash
cd frontend
vercel
```

Set `BACKEND_URL` and `NEXT_PUBLIC_API_URL` env vars in Vercel dashboard pointing to your backend host.
{% else %}
Not applicable — this project doesn't generate a frontend.
{% endif %}

---

## Environment validation in production

Before promoting to prod, run:

```bash
docker compose exec app uv run python -c "from app.core.config import settings; print('OK')"
```

Catches missing required env vars early. See `ENV_VARS.md` for the full list.

## Post-deploy checks

- [ ] `/api/v1/health` returns `{"status": "ok"}`
- [ ] `alembic current` matches expected revision
{% if cookiecutter.use_frontend %}- [ ] Frontend renders, login flow works end-to-end
{% endif %}{% if cookiecutter.enable_billing %}- [ ] Stripe test webhook delivers (use Stripe CLI: `stripe listen --forward-to https://your-domain/api/v1/billing/webhook`)
{% endif %}{% if cookiecutter.enable_email %}- [ ] Test email sends (trigger password-reset flow)
{% endif %}- [ ] Logs flowing to your aggregator{% if cookiecutter.enable_sentry %} + Sentry capturing errors{% endif %}{% if cookiecutter.enable_logfire %} + Logfire receiving traces{% endif %}
- [ ] Reverse proxy enforces HTTPS

## Rollback

- **Schema:** `alembic downgrade -1` rolls back one migration. Test on staging first.
- **Code:** redeploy previous image tag. Pin tags (`v1.2.3`), never deploy `latest` to prod.
- **Data:** restore from your most recent backup; verify `alembic current` matches the data version.
