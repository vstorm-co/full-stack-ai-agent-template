"""Subprocess entry point that renders a cookiecutter template.

Run as ``python -m fastapi_gen.upgrade._render_worker <template_dir>
<context_json> <output_dir>``. It exists as a separate process so the caller
(:mod:`fastapi_gen.upgrade.render`) can hand it a controlled environment — a
``PATH`` containing only no-op shims — which the post-gen hook (a grandchild
process) inherits, neutralizing ``uv lock`` / ``bun install`` / ``ruff`` etc.
without modifying any released template.

Prints ``RENDERED::<path>`` on success so the parent can capture the output path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from cookiecutter.main import cookiecutter

_RESULT_PREFIX = "RENDERED::"


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: _render_worker <template_dir> <context_json> <output_dir>", file=sys.stderr)
        return 2
    template_dir, context_file, output_dir = argv[1], argv[2], argv[3]
    context = json.loads(Path(context_file).read_text(encoding="utf-8"))

    path = cookiecutter(
        template_dir,
        no_input=True,
        extra_context=context,
        output_dir=output_dir,
        overwrite_if_exists=True,
    )
    print(f"{_RESULT_PREFIX}{path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
