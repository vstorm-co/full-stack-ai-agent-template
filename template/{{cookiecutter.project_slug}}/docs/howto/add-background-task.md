# How to: Add a Background Task

## Overview

Background tasks run asynchronously outside the request-response cycle. Your project uses **{{ cookiecutter.background_tasks }}** as the task queue.

## Step-by-Step

### 1. Create the task

{%- if cookiecutter.use_celery %}
```python
# app/worker/tasks/notifications.py
from app.worker.celery_app import celery_app


@celery_app.task(name="send_notification")
def send_notification(user_id: str, message: str) -> dict:
    """Send a notification to a user."""
    # Your logic here — email, push notification, etc.
    print(f"Sending to {user_id}: {message}")
    return {"status": "sent", "user_id": user_id}
```
{%- elif cookiecutter.use_taskiq %}
```python
# app/worker/tasks/notifications.py
from app.worker.taskiq_app import broker


@broker.task
async def send_notification(user_id: str, message: str) -> dict:
    """Send a notification to a user."""
    # Your async logic here
    print(f"Sending to {user_id}: {message}")
    return {"status": "sent", "user_id": user_id}
```
{%- elif cookiecutter.use_arq %}
```python
# In app/worker/arq_app.py, add to the functions list:
async def send_notification(ctx, user_id: str, message: str) -> dict:
    """Send a notification to a user."""
    print(f"Sending to {user_id}: {message}")
    return {"status": "sent", "user_id": user_id}
```
{%- elif cookiecutter.use_prefect %}
```python
# app/worker/tasks/notifications.py
from prefect import flow


@flow(name="send-notification", log_prints=True)
async def send_notification_flow(user_id: str, message: str) -> dict:
    """Send a notification to a user."""
    # Your async logic here
    print(f"Sending to {user_id}: {message}")
    return {"status": "sent", "user_id": user_id}
```
{%- endif %}

### 2. Call it from your API

```python
# In any route or service:
{%- if cookiecutter.use_celery %}
from app.worker.tasks.notifications import send_notification

# Fire and forget
send_notification.delay("user_123", "Your order is ready!")

# Or with options
send_notification.apply_async(
    args=["user_123", "Your order is ready!"],
    countdown=60,  # Delay 60 seconds
)
{%- elif cookiecutter.use_taskiq %}
from app.worker.tasks.notifications import send_notification

# Fire and forget
await send_notification.kiq("user_123", "Your order is ready!")
{%- elif cookiecutter.use_arq %}
# Use the ARQ pool from lifespan state
await request.state.arq_pool.enqueue_job(
    "send_notification", "user_123", "Your order is ready!"
)
{%- elif cookiecutter.use_prefect %}
import asyncio

from app.worker.tasks.notifications import send_notification_flow

# Fire and forget — runs the flow in the background (tracked in the Prefect UI)
asyncio.create_task(send_notification_flow("user_123", "Your order is ready!"))
{%- endif %}
```

### 3. Add scheduling (optional)

{%- if cookiecutter.use_celery %}
In `celery_app.py`, add to `beat_schedule`:
```python
celery_app.conf.beat_schedule["daily-digest"] = {
    "task": "send_notification",
    "schedule": crontab(hour=9, minute=0),  # Daily at 9 AM
    "args": ["broadcast", "Daily digest"],
}
```
{%- elif cookiecutter.use_taskiq %}
In `tasks/schedules.py`, add to `SCHEDULES`:
```python
SCHEDULES.append({
    "task": "app.worker.tasks.notifications:send_notification",
    "cron": "0 9 * * *",  # Daily at 9 AM
    "args": ["broadcast", "Daily digest"],
})
```
{%- elif cookiecutter.use_arq %}
In `arq_app.py`, add to `WorkerSettings.cron_jobs`:
```python
cron_jobs = [
    cron(send_notification, hour=9, minute=0),
]
```
{%- elif cookiecutter.use_prefect %}
In `app/worker/prefect_app.py`, register a scheduled deployment in `main()`:
```python
from prefect.client.schemas.schedules import CronSchedule

from app.worker.tasks.notifications import send_notification_flow

deployments.append(await send_notification_flow.ato_deployment(
    name="daily-digest",
    parameters={"user_id": "broadcast", "message": "Daily digest"},
    schedules=[CronSchedule(cron="0 9 * * *")],  # Daily at 9 AM
))
```
{%- endif %}

### 4. Run the worker

```bash
{%- if cookiecutter.use_celery %}
make celery-worker    # Start worker
make celery-beat      # Start scheduler (for cron jobs)
make celery-flower    # Start monitoring UI (optional)
{%- elif cookiecutter.use_taskiq %}
make taskiq-worker    # Start worker
make taskiq-scheduler # Start scheduler (for cron jobs)
{%- elif cookiecutter.use_arq %}
# ARQ worker is started via Docker or manually:
uv run arq app.worker.arq_app.WorkerSettings
{%- elif cookiecutter.use_prefect %}
# The prefect-server + prefect-runner containers start with `make dev`.
# To run the runner directly (registers deployments + polls for work):
uv run --directory backend python -m app.worker.prefect_app
# Prefect UI: http://localhost:4200
{%- endif %}
```
