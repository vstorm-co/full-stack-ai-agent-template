{%- if cookiecutter.use_taskiq %}
"""Regression tests for the Taskiq worker/scheduler configuration (issue #92)."""

import sys

import pytest
from taskiq.schedule_sources import LabelScheduleSource

from app.worker.taskiq_app import broker, scheduler


class TestTaskiqScheduler:
    """The scheduler must receive ScheduleSource instances, not module paths."""

    def test_sources_are_schedule_source_instances(self):
        """A bare string source crashes startup: 'str' has no attribute 'startup'."""
        assert scheduler.sources
        for source in scheduler.sources:
            assert not isinstance(source, str)
            assert hasattr(source, "startup")

    def test_uses_label_schedule_source(self):
        """Schedules are declared via @broker.task(schedule=...) labels."""
        assert any(isinstance(s, LabelScheduleSource) for s in scheduler.sources)

    @pytest.mark.anyio
    async def test_scheduler_sources_start_and_list_schedules(self):
        """Each source starts cleanly and exposes its schedules without error."""
        for source in scheduler.sources:
            await source.startup()
            schedules = await source.get_schedules()
            assert isinstance(schedules, list)


class TestTaskRegistration:
    """Importing the broker module must register tasks for the worker process."""

    def test_importing_taskiq_app_imports_task_modules(self):
        """Without this side-effect import the worker discovers zero tasks."""
        assert "app.worker.tasks.schedules" in sys.modules
{%- endif %}
