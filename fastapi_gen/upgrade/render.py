"""Render a template version into a concrete tree with env-ops neutralized.

To build BASE / THEIRS we render a historical (or current) template with the
client's recorded answers. The post-gen hook of any released version shells out
to ``uv lock`` / ``bun install`` / ``ruff`` / ``npx prettier`` — slow, network-
bound, and irrelevant to a content diff. We cannot patch a released hook, and
cookiecutter runs it as a *grandchild* process, so monkeypatching ``subprocess``
in-process would not reach it.

Instead we render in a subprocess whose ``PATH`` contains only **no-op shims** for
those tools. The hook's ``shutil.which(...)`` finds the shims (so even the
``python -m ruff`` fallback branch is never taken) and every external call becomes
an instant success that does nothing. The hook's *structural* cleanup (removing
files for disabled features) still runs normally — that shapes the tree correctly.
We also set ``FASTAPI_FULLSTACK_RENDER_ONLY=1`` so future template versions can
skip the env-ops block outright.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

_SHIMMED_TOOLS = (
    "uv",
    "uvx",
    "ruff",
    "bun",
    "npx",
    "npm",
    "pnpm",
    "yarn",
    "node",
    "prettier",
)

_RESULT_PREFIX = "RENDERED::"

_shim_dir_cache: str | None = None


class RenderError(RuntimeError):
    """Raised when rendering a template version fails."""


def _ensure_shim_dir() -> str:
    """Create (once per process) a dir of no-op executables and return its path."""
    global _shim_dir_cache
    if _shim_dir_cache and Path(_shim_dir_cache).exists():
        return _shim_dir_cache
    shim_dir = tempfile.mkdtemp(prefix="fastapi-fullstack-shims-")
    for tool in _SHIMMED_TOOLS:
        shim = Path(shim_dir) / tool
        shim.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        shim.chmod(0o755)
    _shim_dir_cache = shim_dir
    return shim_dir


def _template_keys(template_dir: Path) -> set[str]:
    """Keys declared in the template's cookiecutter.json (private keys excluded)."""
    data = json.loads((template_dir / "cookiecutter.json").read_text(encoding="utf-8"))
    return {k for k in data if not k.startswith("_")}


def filter_context(context: dict[str, Any], template_dir: Path) -> dict[str, Any]:
    """Keep only context keys the template declares.

    Implements the render-layer half of context-drift handling: unknown
    keys are dropped (the template fills them from its own defaults), which also
    avoids feeding a stale value into a variable that no longer exists.
    """
    allowed = _template_keys(template_dir)
    return {k: v for k, v in context.items() if k in allowed}


def render_template(
    template_dir: Path,
    context: dict[str, Any],
    dest_parent: Path,
    *,
    filter_to_template: bool = True,
) -> Path:
    """Render ``template_dir`` with ``context`` into ``dest_parent``; return the tree.

    Args:
        template_dir: A cookiecutter template dir (has ``cookiecutter.json``).
        context: The derived context (e.g. from the manifest).
        dest_parent: Directory the rendered project is created *inside*.
        filter_to_template: Drop context keys the template doesn't declare.

    Raises:
        RenderError: If the render subprocess fails.
    """
    render_context = filter_context(context, template_dir) if filter_to_template else context

    dest_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    ) as ctx_file:
        json.dump(render_context, ctx_file)
        ctx_path = ctx_file.name

    env = os.environ.copy()
    env["PATH"] = _ensure_shim_dir() + os.pathsep + env.get("PATH", "")
    env["FASTAPI_FULLSTACK_RENDER_ONLY"] = "1"

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "fastapi_gen.upgrade._render_worker",
                str(template_dir),
                ctx_path,
                str(dest_parent),
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        Path(ctx_path).unlink(missing_ok=True)

    if result.returncode != 0:
        raise RenderError(
            f"Rendering template at {template_dir} failed "
            f"(exit {result.returncode}):\n{result.stderr.strip()}"
        )

    for line in reversed(result.stdout.splitlines()):
        if line.startswith(_RESULT_PREFIX):
            return Path(line[len(_RESULT_PREFIX) :])
    raise RenderError(
        f"Render worker did not report an output path.\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
