"""Upgrade manifest — ``.fastapi-fullstack.json``.

The manifest is written into every generated project so it self-describes: which
generator version built it and the full derived cookiecutter context it was built
from. That context is what lets the upgrade tool re-render BASE (template @ old
version) and THEIRS (template @ new version) with the *same* answers, which is the
precondition for a sound 3-way merge (see docs/guides/version-upgrade.md).

The manifest is committed to the client's repo, so it must be safe to commit: no
secrets or environment values. Today the derived context contains no secret
*values* (only feature flags), but :func:`redact_secrets` guards the future.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from ..config import GENERATOR_NAME, get_generator_version

MANIFEST_FILENAME = ".fastapi-fullstack.json"

TEMPLATE_URL = "https://github.com/vstorm-co/full-stack-ai-agent-template"

VOLATILE_KEYS: frozenset[str] = frozenset({"generated_at"})

_REDACTED = "<redacted>"

_SECRET_KEY_RE = re.compile(
    r"(secret|password|passwd|token|api[_-]?key|apikey|credential|private[_-]?key)",
    re.IGNORECASE,
)


def redact_secrets(context: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``context`` with secret-looking string values redacted.

    A value is redacted only when it is a non-empty ``str`` *and* its key matches
    :data:`_SECRET_KEY_RE`. Non-string values (the feature flags) are always kept,
    so the manifest stays fully re-renderable. Recurses into nested dicts/lists so a
    future non-flat context shape can't leak a live key into the committed manifest.
    """

    def _clean(obj: Any, key: str | None = None, *, parent_secret: bool = False) -> Any:
        secret = parent_secret or (key is not None and bool(_SECRET_KEY_RE.search(key)))
        if isinstance(obj, dict):
            return {k: _clean(v, k, parent_secret=secret) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean(x, key, parent_secret=secret) for x in obj]
        if isinstance(obj, str) and obj and secret:
            return _REDACTED
        return obj

    return {k: _clean(v, k) for k, v in context.items()}


def _canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, compact separators, unicode preserved."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_context_hash(context: dict[str, Any]) -> str:
    """Stable ``sha256:`` fingerprint of the context, excluding volatile keys.

    Lets the upgrade tool assert that a reconstructed BASE was rendered from the
    exact inputs the client generated from, and detect manifest tampering/drift.
    """
    stable = {k: v for k, v in context.items() if k not in VOLATILE_KEYS}
    digest = hashlib.sha256(_canonical_json(stable).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def build_manifest(
    context: dict[str, Any],
    *,
    package_version: str | None = None,
    template_ref: str | None = None,
    commit: str | None = None,
) -> dict[str, Any]:
    """Build the manifest dict from a cookiecutter context.

    Args:
        context: The full derived context passed to cookiecutter at generation time
            (from :meth:`ProjectConfig.to_cookiecutter_context`).
        package_version: The ``fastapi-fullstack`` version that generated the
            project. Defaults to the currently-installed version. This is what the
            upgrade tool fetches from PyPI to render BASE.
        template_ref: The git tag/sha the template was rendered from. Defaults to
            ``package_version`` — release tags are the bare version (``0.2.16``),
            so a ``v``-prefixed ref would point at a tag that does not exist.
        commit: The template git commit sha, if known (unknown from an installed
            package — left ``None``).
    """
    pkg_version = package_version or get_generator_version()
    ref = template_ref or pkg_version
    safe_context = redact_secrets(context)

    return {
        "template": TEMPLATE_URL,
        "template_ref": ref,
        "package_version": pkg_version,
        "generator_name": context.get("generator_name", GENERATOR_NAME),
        "generator_version": context.get("generator_version", pkg_version),
        "generated_at": context.get("generated_at"),
        "commit": commit,
        "context_hash": compute_context_hash(safe_context),
        "context": safe_context,
    }


def atomic_write_text(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically (tmp file + ``os.replace``).

    A crash mid-write must never leave a torn ``.fastapi-fullstack.json`` — a truncated
    manifest sends the next ``upgrade`` into recovery. Shared by every manifest writer
    (write, pending, finalize, recovery candidate) so they all get the same guarantee.
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)


def write_manifest(
    project_path: Path,
    context: dict[str, Any],
    *,
    package_version: str | None = None,
    template_ref: str | None = None,
    commit: str | None = None,
) -> Path:
    """Write ``.fastapi-fullstack.json`` into ``project_path`` and return its path."""
    manifest = build_manifest(
        context,
        package_version=package_version,
        template_ref=template_ref,
        commit=commit,
    )
    manifest_path = project_path / MANIFEST_FILENAME
    atomic_write_text(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest_path


def read_manifest(project_path: Path) -> dict[str, Any]:
    """Read and parse the manifest from ``project_path``.

    Args:
        project_path: The project directory (or the manifest file itself).

    Raises:
        FileNotFoundError: If no manifest exists (the caller should fall back to
            best-effort recovery).
        ValueError: If the manifest is corrupt JSON or missing required keys.
    """
    manifest_path = (
        project_path if project_path.name == MANIFEST_FILENAME else project_path / MANIFEST_FILENAME
    )
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"No {MANIFEST_FILENAME} found in {project_path}. "
            "This project predates upgrade manifests; run recovery first."
        )
    try:
        data: Any = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Corrupt manifest {manifest_path}: {exc}. Run recovery to rebuild it."
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(
            f"Manifest {manifest_path} must be a JSON object, got {type(data).__name__}. "
            "Run recovery to rebuild it."
        )
    missing = {"package_version", "template_ref", "context", "context_hash"} - data.keys()
    if missing:
        raise ValueError(
            f"Manifest {manifest_path} is missing required keys: {sorted(missing)}. "
            "Run recovery to rebuild it."
        )
    # `context` earns its own check: it is the one key every consumer indexes into
    # (reconcile does dict(context), the renderer does context.get), so a hand-edit that
    # turns it into a list or a string gets past the presence check above and surfaces as
    # a bare TypeError several modules downstream.
    if not isinstance(data["context"], dict):
        raise ValueError(
            f"Manifest {manifest_path} has a non-object 'context' "
            f"({type(data['context']).__name__}). Run recovery to rebuild it."
        )
    return data
