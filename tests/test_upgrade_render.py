"""Tests for fastapi_gen.upgrade.render."""

import json
from pathlib import Path

import pytest

from fastapi_gen.config import (
    BackgroundTaskType,
    CIType,
    DatabaseType,
    ProjectConfig,
)
from fastapi_gen.generator import _find_template_dir
from fastapi_gen.upgrade.render import filter_context, render_template


class TestFilterContext:
    def test_keeps_declared_drops_unknown_and_private(self, tmp_path: Path) -> None:
        template = tmp_path / "template"
        template.mkdir()
        (template / "cookiecutter.json").write_text(
            json.dumps({"project_name": "x", "use_celery": False, "_private": "y"}),
            encoding="utf-8",
        )
        ctx = {
            "project_name": "acme",
            "use_celery": True,
            "_private": "z",
            "removed_in_new_version": 1,
        }
        result = filter_context(ctx, template)
        assert result == {"project_name": "acme", "use_celery": True}


@pytest.mark.slow
class TestRenderTemplate:
    """Rendering neutralizes env-ops (no uv.lock / no network)."""

    def test_renders_and_skips_env_ops(self, tmp_path: Path) -> None:
        cfg = ProjectConfig(
            project_name="render_probe",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.NONE,
            enable_docker=False,
            enable_logfire=False,
            ci_type=CIType.NONE,
        )
        out = render_template(_find_template_dir(), cfg.to_cookiecutter_context(), tmp_path)

        assert out.exists()
        assert (out / "backend" / "app" / "main.py").exists()
        assert not (out / "backend" / "uv.lock").exists()
