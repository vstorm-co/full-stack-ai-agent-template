"""Tests for fastapi_gen.upgrade.render."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from fastapi_gen.config import (
    BackgroundTaskType,
    CIType,
    DatabaseType,
    ProjectConfig,
)
from fastapi_gen.generator import _find_template_dir
from fastapi_gen.upgrade import _render_worker
from fastapi_gen.upgrade import render as render_mod
from fastapi_gen.upgrade.render import RenderError, filter_context, render_template


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

    def test_renders_under_a_non_utf8_locale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The post-gen hook scans every rendered doc and frontend module for an empty
        body. Those files carry non-ASCII (emoji in the docs, Polish prose in the
        per-locale .tsx), so reading them with the platform default encoding kills both
        generation and this render on Windows or a C-locale container."""
        for var, value in (
            ("PYTHONUTF8", "0"),
            ("PYTHONCOERCECLOCALE", "0"),
            ("LC_ALL", "C"),
            ("LANG", "C"),
        ):
            monkeypatch.setenv(var, value)

        cfg = ProjectConfig(
            project_name="locale_probe",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.NONE,
            enable_docker=False,
            enable_logfire=False,
            ci_type=CIType.NONE,
        )
        out = render_template(_find_template_dir(), cfg.to_cookiecutter_context(), tmp_path)

        assert (out / "backend" / "app" / "main.py").exists()


class TestShimDir:
    def test_shim_dir_is_registered_for_cleanup(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The shim dir is rebuilt every run, so it must not accumulate in /tmp."""
        registered: list[tuple[object, ...]] = []
        monkeypatch.setattr(render_mod, "_shim_dir_cache", None)
        monkeypatch.setattr(render_mod.atexit, "register", lambda *a: registered.append(a))

        shim_dir = render_mod._ensure_shim_dir()

        assert (Path(shim_dir) / "bun").exists()
        assert registered == [(render_mod.shutil.rmtree, shim_dir, True)]
        render_mod.shutil.rmtree(shim_dir, ignore_errors=True)


class TestRenderErrors:
    def test_error_on_nonzero_exit(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            render_mod.subprocess,
            "run",
            lambda *_a, **_k: SimpleNamespace(returncode=1, stdout="", stderr="boom"),
        )
        with pytest.raises(RenderError, match="failed"):
            render_template(tmp_path / "tpl", {}, tmp_path / "out", filter_to_template=False)

    def test_error_when_no_output_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            render_mod.subprocess,
            "run",
            lambda *_a, **_k: SimpleNamespace(returncode=0, stdout="noise\n", stderr=""),
        )
        with pytest.raises(RenderError, match="did not report"):
            render_template(tmp_path / "tpl", {}, tmp_path / "out", filter_to_template=False)


class TestRenderWorker:
    def test_wrong_argc(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert _render_worker.main(["prog"]) == 2
        assert "usage" in capsys.readouterr().err

    def test_happy_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ctx = tmp_path / "ctx.json"
        ctx.write_text('{"project_name": "x"}', encoding="utf-8")
        monkeypatch.setattr(
            _render_worker, "cookiecutter", lambda *_a, **_k: str(tmp_path / "proj")
        )
        rc = _render_worker.main(["prog", str(tmp_path / "tpl"), str(ctx), str(tmp_path / "out")])
        assert rc == 0
        assert "RENDERED::" in capsys.readouterr().out
