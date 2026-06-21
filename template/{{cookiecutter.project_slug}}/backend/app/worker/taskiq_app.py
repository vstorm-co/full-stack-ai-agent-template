{%- if cookiecutter.use_taskiq %}
"""Taskiq application configuration."""

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.core.config import settings

broker = ListQueueBroker(
    url=settings.TASKIQ_BROKER_URL,
).with_result_backend(
    RedisAsyncResultBackend(
        redis_url=settings.TASKIQ_RESULT_BACKEND,
    )
)

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)


@broker.on_event("startup")
async def startup() -> None:
    pass


@broker.on_event("shutdown")
async def shutdown() -> None:
    pass


import app.worker.tasks.schedules  # noqa: F401
{%- else %}
# Taskiq not enabled for this project
{%- endif %}
