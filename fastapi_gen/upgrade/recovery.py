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

from .manifest import MANIFEST_FILENAME, build_manifest

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


def recover_context(project_path: Path) -> RecoveryResult:
    """Infer a best-effort context + version from a project's file layout."""
    context: dict[str, object] = {"project_name": project_path.resolve().name}
    for key, rel in _PRESENCE_DETECTORS:
        context[key] = (project_path / rel).exists()

    version = detect_version(project_path)
    warnings = [
        "Recovery is best-effort. Review this candidate manifest carefully before upgrading.",
        "Value variables cannot be recovered from files and were NOT set: "
        + ", ".join(_UNRECOVERABLE),
    ]
    if version is None:
        warnings.append("Could not detect the generator version — set `package_version` by hand.")
    return RecoveryResult(context=context, version=version, warnings=warnings)


def write_candidate_manifest(project_path: Path, result: RecoveryResult) -> Path:
    """Write ``.fastapi-fullstack.json.candidate`` for human review (never the real file)."""
    manifest = build_manifest(result.context, package_version=result.version or "UNKNOWN")
    candidate = project_path / (MANIFEST_FILENAME + ".candidate")
    candidate.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return candidate
