.PHONY: install format lint test run clean help db-init dev dev-down dev-logs dev-rebuild dev-frontend docker-clean stage stage-down prod prod-down

# === Environments ===========================================================
# `make dev`   — local development (docker-compose.dev.yml + bind-mounted source)
# `make stage` — staging (docker-compose.yml — built images, no live reload)
# `make prod`  — production (docker-compose.prod.yml — needs backend/.env + nginx)
# Each env has matching -down / -logs / -rebuild siblings.

{%- if cookiecutter.enable_docker %}

# Wait for postgres to accept connections. Polls pg_isready instead of a
# fixed sleep — handles slow startups and cold-start image pulls.
define _wait_for_db
	@echo "Waiting for PostgreSQL ($(1))..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do \
		if docker compose -f $(1) exec -T db pg_isready -U postgres >/dev/null 2>&1; then \
			echo "  ✅ DB ready"; exit 0; \
		fi; \
		printf '.'; sleep 2; \
	done; \
	echo "  ❌ DB not ready after 30s — check 'make dev-logs'"; exit 1
endef
{%- endif %}

{%- if cookiecutter.enable_docker %}

# === Local dev: build → up → migrate ===
# Idempotent — re-run anytime. Migrations are no-ops when already at head;
# admin seeding is a separate target (`make seed`) so re-running `make dev`
# doesn't keep retrying user creation.
dev:
	@echo "▶ Building backend image…"
	docker compose -f docker-compose.dev.yml build app
	@echo "▶ Starting services…"
	@if ! docker compose -f docker-compose.dev.yml $(COMPOSE_DEV_PROFILES) up -d; then \
		echo ""; \
		echo "⚠ First start failed. Tearing down stale containers and retrying once…"; \
		echo "  (volumes preserved — DB data is safe; use 'make clean' for a full wipe)"; \
		docker compose -f docker-compose.dev.yml down --remove-orphans; \
		docker compose -f docker-compose.dev.yml $(COMPOSE_DEV_PROFILES) up -d; \
	fi
	$(call _wait_for_db,docker-compose.dev.yml)
	@echo "▶ Applying migrations…"
	docker compose -f docker-compose.dev.yml exec -T app {{ cookiecutter.project_slug }} db upgrade
	@echo ""
	@echo "🚀 Dev stack ready:"
	@echo "   API:      http://localhost:{{ cookiecutter.backend_port }}"
	@echo "   Docs:     http://localhost:{{ cookiecutter.backend_port }}/docs"
{%- if cookiecutter.use_jwt %}
	@echo "   Admin:    http://localhost:{{ cookiecutter.backend_port }}/admin"
{%- endif %}
{%- if cookiecutter.use_frontend %}
	@echo "   Frontend: http://localhost:{{ cookiecutter.frontend_port }}  (run 'make dev-frontend' or 'cd frontend && bun dev')"
{%- endif %}
{%- if cookiecutter.use_jwt %}
	@echo ""
	@echo "First time? Run 'make seed' to create the default admin user."
{%- endif %}

{%- if cookiecutter.use_jwt %}

# === First-time setup: seed default admin user (one-shot) ===
# Skipped when admin@example.com already exists. Safe to run again — exits
# clean either way. Replace email/password before deploying anywhere real.
seed:
	@echo "▶ Seeding admin user (admin@example.com / admin123)…"
	@if docker compose -f docker-compose.dev.yml exec -T app \
		{{ cookiecutter.project_slug }} user list 2>/dev/null \
		| grep -q "admin@example.com"; then \
		echo "  (admin@example.com already exists — nothing to do)"; \
	else \
		docker compose -f docker-compose.dev.yml exec -T app \
			{{ cookiecutter.project_slug }} user create \
				--email admin@example.com --password admin123 --superuser \
		&& echo "  ✅ Admin created. Login at http://localhost:{{ cookiecutter.backend_port }}/admin"; \
	fi

# Convenience: bootstrap a fresh checkout end-to-end.
bootstrap: dev seed
{%- else %}

bootstrap: dev
{%- endif %}

dev-down:
	docker compose -f docker-compose.dev.yml $(COMPOSE_DEV_PROFILES) down

# Full wipe — containers, networks, AND volumes. Use after a corrupted state
# (e.g. detached networks, port conflicts that left orphans). DESTROYS DB data.
docker-clean:
	@echo "▶ Removing containers, networks, AND volumes for the dev stack…"
	@echo "  ⚠️  This deletes all local DB data and uploaded files."
	docker compose -f docker-compose.dev.yml $(COMPOSE_DEV_PROFILES) down -v --remove-orphans
	@echo "✅ Cleaned. Run 'make dev' to start fresh."

dev-logs:
	docker compose -f docker-compose.dev.yml $(COMPOSE_DEV_PROFILES) logs -f

dev-rebuild:
	docker compose -f docker-compose.dev.yml build --no-cache app
	docker compose -f docker-compose.dev.yml up -d --force-recreate app

{%- if cookiecutter.use_frontend %}
dev-frontend:
	docker compose -f docker-compose.frontend.yml up -d
	@echo ""
	@echo "✅ Frontend at http://localhost:{{ cookiecutter.frontend_port }}  (backend must be up — 'make dev')"
{%- endif %}

# === Staging: built images, no bind mounts (production-like, local DB) ===
stage:
	docker compose -f docker-compose.yml up -d --build
	$(call _wait_for_db,docker-compose.yml)
	docker compose -f docker-compose.yml exec -T app {{ cookiecutter.project_slug }} db upgrade
	@echo "✅ Staging stack at http://localhost:{{ cookiecutter.backend_port }}"

stage-down:
	docker compose -f docker-compose.yml down

# === Production: external Nginx, real secrets in backend/.env ===
prod:
	@test -f backend/.env || (echo "❌ backend/.env missing — run 'cp backend/.env.example backend/.env' and fill in real secrets" && exit 1)
	docker compose --env-file backend/.env -f docker-compose.prod.yml up -d --build
	@echo "▶ Waiting for DB then running migrations…"
	@sleep 5
	docker compose --env-file backend/.env -f docker-compose.prod.yml exec -T app {{ cookiecutter.project_slug }} db upgrade
	@echo "✅ Production stack up. Configure your nginx host with nginx/nginx.conf"

prod-down:
	docker compose --env-file backend/.env -f docker-compose.prod.yml down

prod-logs:
	docker compose --env-file backend/.env -f docker-compose.prod.yml logs -f

# Legacy alias
quickstart: dev
{%- endif %}

# === Setup ===
install:
	uv sync --directory backend --dev
{%- if cookiecutter.enable_precommit %}
	@if git rev-parse --git-dir > /dev/null 2>&1; then \
		uv run --directory backend pre-commit install; \
	else \
		echo "⚠️  Not a git repository - skipping pre-commit install"; \
		echo "   Run 'git init && make install' to set up pre-commit hooks"; \
	fi
{%- endif %}
	@echo ""
	@echo "✅ Installation complete!"
	@echo ""
	@echo "Next steps:"
{%- if not cookiecutter.generate_env %}
	@echo "  • cd backend && cp .env.example .env"
	@echo "  • Edit backend/.env with your settings"
{%- endif %}
	@echo "  • make docker-db        # Start PostgreSQL"
	@echo "  • make db-upgrade       # Apply migrations"
	@echo "  • make run              # Start development server"
{%- if cookiecutter.generate_env %}
	@echo ""
	@echo "Note: backend/.env is pre-configured for development"
{%- endif %}

# === Code Quality ===
format:
	uv run --directory backend ruff format app tests cli
	uv run --directory backend ruff check app tests cli --fix

lint:
	uv run --directory backend ruff check app tests cli
	uv run --directory backend ruff format app tests cli --check
	uv run --directory backend ty check

# === Testing ===
test:
	uv run --directory backend pytest tests/ -v

test-cov:
	uv run --directory backend pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing


# === Database ===
{%- if cookiecutter.enable_docker %}
db-init: docker-db
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 8
	cd backend && uv run {{ cookiecutter.project_slug }} db migrate -m "initial" || true
	cd backend && uv run {{ cookiecutter.project_slug }} db upgrade
	@echo ""
	@echo "✅ Database initialized!"
{%- else %}
db-init:
	cd backend && uv run {{ cookiecutter.project_slug }} db migrate -m "initial" || true
	cd backend && uv run {{ cookiecutter.project_slug }} db upgrade
	@echo ""
	@echo "✅ Database initialized!"
{%- endif %}

db-migrate:
	@read -p "Migration message: " msg; \
	uv run --directory backend {{ cookiecutter.project_slug }} db migrate -m "$$msg"

db-upgrade:
	uv run --directory backend {{ cookiecutter.project_slug }} db upgrade

db-downgrade:
	uv run --directory backend {{ cookiecutter.project_slug }} db downgrade

db-current:
	uv run --directory backend {{ cookiecutter.project_slug }} db current

db-history:
	uv run --directory backend {{ cookiecutter.project_slug }} db history

# === Server ===
run:
	uv run --directory backend {{ cookiecutter.project_slug }} server run --reload

run-prod:
	uv run --directory backend {{ cookiecutter.project_slug }} server run --host 0.0.0.0 --port 8000

routes:
	uv run --directory backend {{ cookiecutter.project_slug }} server routes

{%- if cookiecutter.use_jwt %}

# === Users ===
create-admin:
	@echo "Creating admin user..."
	uv run --directory backend {{ cookiecutter.project_slug }} user create-admin

user-create:
	uv run --directory backend {{ cookiecutter.project_slug }} user create

user-list:
	uv run --directory backend {{ cookiecutter.project_slug }} user list
{%- endif %}

{%- if cookiecutter.use_celery %}

# === Celery ===
celery-worker:
	uv run --directory backend {{ cookiecutter.project_slug }} celery worker

celery-beat:
	uv run --directory backend {{ cookiecutter.project_slug }} celery beat

celery-flower:
	uv run --directory backend {{ cookiecutter.project_slug }} celery flower
	@echo ""
	@echo "✅ Flower started at http://localhost:5555"
{%- endif %}

{%- if cookiecutter.use_taskiq %}

# === Taskiq ===
taskiq-worker:
	uv run --directory backend {{ cookiecutter.project_slug }} taskiq worker

taskiq-scheduler:
	uv run --directory backend {{ cookiecutter.project_slug }} taskiq scheduler
{%- endif %}

{%- if cookiecutter.enable_docker %}

# === Docker: Backend (Development) ===
docker-up:
	docker compose build app
	docker compose up -d
	@echo ""
	@echo "✅ Backend services started!"
	@echo "   API: http://localhost:{{ cookiecutter.backend_port }}"
	@echo "   Docs: http://localhost:{{ cookiecutter.backend_port }}/docs"
{%- if cookiecutter.use_celery %}
	@echo "   Flower: http://localhost:5555"
{%- endif %}
	@echo "   PostgreSQL: localhost:5432"
{%- if cookiecutter.enable_redis %}
	@echo "   Redis: localhost:6379"
{%- endif %}

docker-down:
	docker compose down
{%- if cookiecutter.use_frontend %}
	docker compose -f docker-compose.frontend.yml down 2>/dev/null || true
{%- endif %}

docker-logs:
	docker compose logs -f

docker-build:
	docker compose build

docker-shell:
	docker compose exec app /bin/bash

{%- if cookiecutter.use_frontend %}

# === Docker: Frontend (Development) ===
docker-frontend:
	docker compose -f docker-compose.frontend.yml up -d
	@echo ""
	@echo "✅ Frontend started!"
	@echo "   URL: http://localhost:{{ cookiecutter.frontend_port }}"
	@echo ""
	@echo "Note: Backend must be running (make docker-up)"

docker-frontend-down:
	docker compose -f docker-compose.frontend.yml down

docker-frontend-logs:
	docker compose -f docker-compose.frontend.yml logs -f

docker-frontend-build:
	docker compose -f docker-compose.frontend.yml build
{%- endif %}

# === Docker: Production (with Traefik) ===
docker-prod:
	docker compose -f docker-compose.prod.yml up -d
	@echo ""
	@echo "✅ Production services started with Traefik!"
	@echo ""
	@echo "Endpoints (replace DOMAIN with your domain):"
{%- if cookiecutter.use_frontend %}
	@echo "   Frontend: https://$$DOMAIN"
{%- endif %}
	@echo "   API: https://api.$$DOMAIN"
{%- if cookiecutter.use_celery %}
	@echo "   Flower: https://flower.$$DOMAIN"
{%- endif %}
	@echo "   Traefik: https://traefik.$$DOMAIN"

docker-prod-down:
	docker compose -f docker-compose.prod.yml down

docker-prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

docker-prod-build:
	docker compose -f docker-compose.prod.yml build


# === Docker: Individual Services ===
docker-db:
	docker compose up -d db
	@echo ""
	@echo "✅ PostgreSQL started on port 5432"
	@echo "   Connection: postgresql://postgres:postgres@localhost:5432/{{ cookiecutter.project_slug }}"

docker-db-stop:
	docker compose stop db

{%- if cookiecutter.enable_redis %}

docker-redis:
	docker compose up -d redis
	@echo ""
	@echo "✅ Redis started on port 6379"

docker-redis-stop:
	docker compose stop redis
{%- endif %}

{%- if cookiecutter.use_frontend %}

# === Vercel (Frontend Deployment) ===
vercel-deploy:
	cd frontend && npx vercel --prod
	@echo ""
	@echo "✅ Frontend deployed to Vercel!"
	@echo "   Set environment variables in Vercel dashboard:"
	@echo "   BACKEND_URL=https://api.your-domain.com"
	@echo "   BACKEND_WS_URL=wss://api.your-domain.com"
{%- if cookiecutter.use_jwt %}
	@echo "   NEXT_PUBLIC_AUTH_ENABLED=true"
{%- endif %}
{%- if cookiecutter.enable_rag %}
	@echo "   NEXT_PUBLIC_RAG_ENABLED=true"
{%- endif %}
{%- endif %}
{%- endif %}

# === Cleanup ===
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ty_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml

# === Help ===
help:
	@echo ""
	@echo "{{ cookiecutter.project_name }} - Available Commands"
	@echo "======================================"
	@echo ""
{%- if cookiecutter.enable_docker %}
	@echo "🚀 Bootstrap (first-time setup):"
	@echo "  make bootstrap      'make dev' + 'make seed' — full setup from a fresh clone"
	@echo ""
	@echo "Day-to-day dev:"
	@echo "  make dev            Build + start dev stack + apply migrations (idempotent)"
{%- if cookiecutter.use_jwt %}
	@echo "  make seed           One-shot admin seed (admin@example.com / admin123)"
{%- endif %}
	@echo "  make dev-down       Stop dev stack"
	@echo "  make dev-logs       Tail dev container logs"
	@echo "  make dev-rebuild    Force-rebuild backend image"
	@echo "  make docker-clean   Wipe containers + networks + volumes (DESTROYS data)"
{%- if cookiecutter.use_frontend %}
	@echo "  make dev-frontend   Start frontend container (after 'make dev')"
{%- endif %}
	@echo ""
	@echo "📦 Other environments:"
	@echo "  make stage          Production-like stack on localhost (no bind mounts)"
	@echo "  make prod           Production stack (requires backend/.env + nginx)"
	@echo ""
{%- endif %}
	@echo "Setup (without Docker):"
	@echo "  make install       Install Python deps + pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  make run           Start dev server (with hot reload)"
	@echo "  make test          Run tests"
	@echo "  make lint          Check code quality"
	@echo "  make format        Auto-format code"
	@echo ""
	@echo "Database:"
	@echo "  make db-init       Initialize database (start + migrate)"
	@echo "  make db-migrate    Create new migration"
	@echo "  make db-upgrade    Apply migrations"
	@echo "  make db-downgrade  Rollback last migration"
	@echo "  make db-current    Show current migration"
	@echo ""
{%- if cookiecutter.use_jwt %}
	@echo "Users:"
	@echo "  make create-admin  Create admin user (for SQLAdmin access)"
	@echo "  make user-create   Create new user (interactive)"
	@echo "  make user-list     List all users"
	@echo ""
{%- endif %}
{%- if cookiecutter.enable_rag %}
	@echo "RAG:"
	@echo "  uv run {{ cookiecutter.project_slug }} rag-ingest <path> -c <collection>  Ingest files"
	@echo "  uv run {{ cookiecutter.project_slug }} rag-search <query> -c <collection>  Search"
	@echo "  uv run {{ cookiecutter.project_slug }} rag-collections                     List collections"
	@echo "  uv run {{ cookiecutter.project_slug }} rag-sources                         List sync sources"
	@echo "  uv run {{ cookiecutter.project_slug }} rag-source-add                      Add sync source"
	@echo "  uv run {{ cookiecutter.project_slug }} rag-source-sync <id>                Trigger sync"
	@echo ""
{%- endif %}
{%- if cookiecutter.use_celery %}
	@echo "Celery:"
	@echo "  make celery-worker  Start Celery worker"
	@echo "  make celery-beat    Start Celery beat scheduler"
	@echo "  make celery-flower  Start Flower monitoring UI"
	@echo ""
{%- endif %}
{%- if cookiecutter.use_taskiq %}
	@echo "Taskiq:"
	@echo "  make taskiq-worker     Start Taskiq worker"
	@echo "  make taskiq-scheduler  Start Taskiq scheduler"
	@echo ""
{%- endif %}
{%- if cookiecutter.enable_docker %}
	@echo "Docker (Development):"
	@echo "  make docker-up            Start backend services"
	@echo "  make docker-down          Stop all services"
	@echo "  make docker-logs          View backend logs"
	@echo "  make docker-build         Build backend images"
{%- if cookiecutter.use_frontend %}
	@echo "  make docker-frontend      Start frontend (separate)"
	@echo "  make docker-frontend-down Stop frontend"
{%- endif %}
	@echo "  make docker-db            Start only PostgreSQL"
{%- if cookiecutter.enable_redis %}
	@echo "  make docker-redis         Start only Redis"
{%- endif %}
	@echo ""
	@echo "Docker (Production with Traefik):"
	@echo "  make docker-prod          Start production stack"
	@echo "  make docker-prod-down     Stop production stack"
	@echo "  make docker-prod-logs     View production logs"
	@echo ""
{%- endif %}
	@echo "Other:"
	@echo "  make routes        Show all API routes"
	@echo "  make clean         Clean cache files"
	@echo ""
