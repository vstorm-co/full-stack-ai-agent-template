"""In-process background tasks (FastAPI BackgroundTasks fallback).

These run inside the API worker process. When no distributed queue is
configured (Celery/Taskiq/ARQ), services dispatch work here via
``fire_and_forget()`` so request handlers return immediately — matching the
non-blocking semantics of a real queue.

Caveats vs. a distributed queue:
- The task lives in the API process; if the process restarts mid-flight,
  the task is lost. There is no retry, persistence, or fan-out.
- Long-running CPU-bound work will starve the event loop.
Pick a real queue (Celery/Taskiq/ARQ) for production workloads.
"""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)


def fire_and_forget(coro: Coroutine[Any, Any, Any], *, label: str) -> None:
    """Run ``coro`` as a non-awaited asyncio task with structured error logging.

    Use this from request handlers when there is no distributed queue: the
    request returns as soon as the task is scheduled, and exceptions are
    logged instead of crashing the server.
    """
    task = asyncio.create_task(coro, name=label)

    def _on_done(t: asyncio.Task[Any]) -> None:
        if t.cancelled():
            logger.warning("background_task_cancelled", extra={"task": label})
            return
        exc = t.exception()
        if exc is not None:
            logger.exception("background_task_failed", extra={"task": label}, exc_info=exc)

    task.add_done_callback(_on_done)
