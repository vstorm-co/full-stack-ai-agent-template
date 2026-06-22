---
name: background-task
description: Add or modify work that runs outside the request/response cycle — emails, document ingestion, webhooks, cleanups, scheduled jobs. Use when something is slow or fire-and-forget, or when adding a periodic/cron task. This project's queue is {{ cookiecutter.background_tasks }}.
---

# Background Tasks ({{ cookiecutter.background_tasks }})

Tasks live in `backend/app/worker/tasks/` (e.g. `email_tasks.py`, `rag_tasks.py`, `cleanup_tasks.py`). The app uses **{{ cookiecutter.background_tasks }}**. An in-process fallback (`worker/background/`) exists for trivial cases.

## When to use a task vs. inline

- **Task:** anything slow, retryable, or fire-and-forget — sending email, ingesting/embedding documents, calling slow external APIs, periodic cleanups, materialized-view refreshes.
- **Inline:** fast, transactional work that the response depends on.

## Add a task

1. **Define it** in `backend/app/worker/tasks/<area>.py`:
{%- if cookiecutter.use_celery %}
   ```python
   from app.worker.celery_app import celery_app

   @celery_app.task(name="send_welcome_email")
   def send_welcome_email(user_id: str) -> dict: ...
   ```
   Enqueue: `send_welcome_email.delay(user_id)` (or `.apply_async(args=[...], countdown=60)`).
{%- elif cookiecutter.use_taskiq %}
   ```python
   from app.worker.taskiq_app import broker

   @broker.task
   async def send_welcome_email(user_id: str) -> dict: ...
   ```
   Enqueue: `await send_welcome_email.kiq(user_id)`.
{%- elif cookiecutter.use_arq %}
   ```python
   # add the coroutine, then list it in arq_app.WorkerSettings.functions
   async def send_welcome_email(ctx, user_id: str) -> dict: ...
   ```
   Enqueue: `await request.state.arq_pool.enqueue_job("send_welcome_email", user_id)`.
{%- elif cookiecutter.use_prefect %}
   ```python
   from prefect import flow

   @flow(name="send-welcome-email", log_prints=True)
   async def send_welcome_email_flow(user_id: str) -> dict: ...
   ```
   Fire-and-forget from a service: `asyncio.create_task(send_welcome_email_flow(user_id))`.
{%- endif %}

2. **Call it from a service** (not from the route directly) — keep business logic in `services/`, enqueue at the end of the unit of work.

3. **Schedule it (optional):**
{%- if cookiecutter.use_celery %}
   add to `beat_schedule` in `celery_app.py` (run `make celery-beat`).
{%- elif cookiecutter.use_taskiq %}
   append to `SCHEDULES` in `tasks/schedules.py` (run `make taskiq-scheduler`).
{%- elif cookiecutter.use_arq %}
   add a `cron(...)` entry to `WorkerSettings.cron_jobs` in `arq_app.py`.
{%- elif cookiecutter.use_prefect %}
   register a deployment with a `CronSchedule`/`IntervalSchedule` in `app/worker/prefect_app.py`.
{%- endif %}

4. **Run / verify:**
{%- if cookiecutter.use_celery %}
   `make celery-worker` (+ `make celery-beat` for schedules, `make celery-flower` to monitor).
{%- elif cookiecutter.use_taskiq %}
   `make taskiq-worker` (+ `make taskiq-scheduler` for schedules).
{%- elif cookiecutter.use_arq %}
   the worker runs in the dev stack (`make dev`), or `uv run --directory backend arq app.worker.arq_app.WorkerSettings`.
{%- elif cookiecutter.use_prefect %}
   the `prefect-server` + `prefect-runner` start with `make dev`; watch runs at <http://localhost:4200>.
{%- endif %}

## Rules

- Tasks take **serializable args** (ids, primitives) — not ORM objects or sessions. Re-fetch inside the task with a fresh session.
- Make tasks **idempotent** where possible (safe to retry).
- Keep heavy imports inside the task function to keep the API import-light.
- See `docs/howto/add-background-task.md` for the full walkthrough.
