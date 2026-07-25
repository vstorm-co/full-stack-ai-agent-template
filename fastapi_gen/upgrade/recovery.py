"""Best-effort recovery for projects generated before manifests existed.

A manifest-less project cannot be upgraded directly — we don't know the answers it
was generated from. Recovery infers *boolean feature flags* from the project's file
layout and parses the version from the README footer, producing a **candidate**
manifest for the developer to review and commit. It is deliberately dry-run only: it
cannot recover *value* variables (``db_pool_size``, ``timezone``, …) that leave no
structural trace, so a human must confirm before any upgrade runs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .manifest import MANIFEST_FILENAME, atomic_write_text, build_manifest

_PRESENCE_DETECTORS: tuple[tuple[str, str], ...] = (
    ("enable_rag", "backend/app/services/rag"),
    ("use_frontend", "frontend"),
    ("enable_docker", "docker-compose.yml"),
    ("enable_teams", "backend/app/db/models/organization.py"),
    ("enable_billing", "backend/app/services/billing"),
    ("enable_email", "backend/app/services/email"),
    ("enable_admin_panel", "backend/app/admin.py"),
    ("use_celery", "backend/app/worker/celery_app.py"),
    ("use_pydantic_ai", "backend/app/agents/assistant.py"),
    ("use_langchain", "backend/app/agents/langchain_assistant.py"),
    ("use_langgraph", "backend/app/agents/langgraph_assistant.py"),
    ("use_deepagents", "backend/app/agents/deepagents_assistant.py"),
    ("use_pydantic_deep", "backend/app/agents/pydantic_deep_assistant.py"),
)

_UNRECOVERABLE = (
    "db_pool_size",
    "db_max_overflow",
    "db_pool_timeout",
    "timezone",
    "author_name",
    "author_email",
    "project_description",
    "backend_port",
    "frontend_port",
    "vector_store",
    "llm_provider",
    "embedding_provider",
)

_VERSION_RE = re.compile(r"v(\d+\.\d+\.\d+)")

_GENERATED_AT_RE = re.compile(r'^generated_at\s*=\s*"([^"]*)"', re.MULTILINE)


@dataclass
class RecoveryResult:
    context: dict[str, object]
    version: str | None
    warnings: list[str] = field(default_factory=list)


def detect_version(project_path: Path) -> str | None:
    """Parse the generator version from the README footer (``…) v0.2.x.``).

    Takes the *last* ``vX.Y.Z`` in the file: the generator stamps its version in the
    footer, so an earlier match (a Python/FastAPI/dependency version) must not win.
    """
    readme = project_path / "README.md"
    if not readme.exists():
        return None
    matches = _VERSION_RE.findall(readme.read_text(encoding="utf-8", errors="ignore"))
    return matches[-1] if matches else None


def detect_generated_at(project_path: Path) -> str | None:
    """Read the generation timestamp back out of ``backend/pyproject.toml``.

    Alone among the value variables this one leaves a trace: generation stamps it into
    ``[tool.<generator>] generated_at`` and into every alembic ``Create Date:`` header.
    Recovering it is not cosmetic — ``normalize`` blanks the stamp in all three trees so
    it cancels, but only when it knows the value. Without it BASE and THEIRS render the
    stamp empty while the client's files carry the real one, so every stamped file reads
    as an edit they never made. ``backend/pyproject.toml`` moves on nearly every release,
    which turns the first upgrade of a recovered project into a conflict on a file
    nobody touched.

    Returns ``None`` when the stamp cannot be found, and ``""`` when the project
    genuinely recorded an empty one — the caller must not warn about the latter, since
    an empty stamp is already what the template renders by default.
    """
    pyproject = project_path / "backend" / "pyproject.toml"
    if not pyproject.exists():
        return None
    match = _GENERATED_AT_RE.search(pyproject.read_text(encoding="utf-8", errors="ignore"))
    return match.group(1) if match else None


def recover_context(project_path: Path) -> RecoveryResult:
    """Infer a best-effort context + version from a project's file layout."""
    context: dict[str, object] = {"project_name": project_path.resolve().name}
    for key, rel in _PRESENCE_DETECTORS:
        context[key] = (project_path / rel).exists()

    generated_at = detect_generated_at(project_path)
    if generated_at:
        context["generated_at"] = generated_at

    version = detect_version(project_path)
    warnings = [
        "Recovery is best-effort. Review this candidate manifest carefully before upgrading.",
        "Value variables cannot be recovered from files and were NOT set: "
        + ", ".join(_UNRECOVERABLE),
    ]
    if version is None:
        warnings.append("Could not detect the generator version — set `package_version` by hand.")
    if generated_at is None:
        warnings.append(
            "Could not detect `generated_at` — set it by hand, or every file carrying the "
            "generation timestamp (backend/pyproject.toml, every alembic Create Date: header) "
            "will read as an edit you made and conflict on the first release that touches it."
        )
    return RecoveryResult(context=context, version=version, warnings=warnings)


def write_candidate_manifest(project_path: Path, result: RecoveryResult) -> Path:
    """Write ``.fastapi-fullstack.json.candidate`` for human review (never the real file)."""
    manifest = build_manifest(result.context, package_version=result.version or "UNKNOWN")
    candidate = project_path / (MANIFEST_FILENAME + ".candidate")
    atomic_write_text(candidate, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return candidate
