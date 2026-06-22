# Quick Start

Get your AI application running in minutes — three commands.

## 1. Generate the project

```bash
# Interactive wizard (recommended)
fastapi-fullstack

# Or skip the wizard with a preset
fastapi-fullstack create my_app --preset ai-agent
```

## 2. Bring everything up

```bash
cd my_app
make bootstrap
```

`make bootstrap` (= `make dev` + `make seed`) builds the backend image, starts PostgreSQL and the API in Docker, applies migrations, and seeds the default admin (`admin@example.com` / `admin123`). It's idempotent — re-run it anytime.

!!! note "Windows Users"
    The `make` command requires GNU Make. Install via [Chocolatey](https://chocolatey.org/) (`choco install make`), use WSL, or run commands manually from the Makefile.

## 3. Start the Frontend

Open a new terminal:

```bash
cd frontend
bun install
bun dev
```

## Access Your Application

| Service | URL |
|---------|-----|
| **API** | http://localhost:8000 |
| **API Docs** | http://localhost:8000/docs |
| **Admin Panel** | http://localhost:8000/admin |
| **Frontend** | http://localhost:3000 |

## Day-to-day

After the first bootstrap:

```bash
make dev        # rebuild + restart (idempotent, no admin re-seed)
make dev-down   # stop the stack
make dev-logs   # tail container logs
```

<details>
<summary><b>Run the backend on your host (for IDE breakpoints)</b></summary>

Keep the database in Docker but run the API process directly:

```bash
cd my_app
make install        # uv sync + pre-commit hooks
make docker-db      # start PostgreSQL only
make db-upgrade     # apply migrations
make create-admin   # interactive admin creation
make run            # uvicorn --reload
```

</details>

## Project CLI

Each generated project has a CLI:

```bash
cd backend

# Server commands
uv run my_app server run --reload

# Database commands
uv run my_app db migrate -m "Add users"
uv run my_app db upgrade

# User commands
uv run my_app user create-admin
```

## Next Steps

- [Configuration](configuration.md) - Customize your project
- [AI Agents](../ai-agent.md) - Set up AI frameworks
- [Deployment](../deployment.md) - Deploy to production
