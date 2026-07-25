"""Tests for fastapi_gen.upgrade.recovery."""

import json
from pathlib import Path

from fastapi_gen.generator import _find_template_dir
from fastapi_gen.upgrade.manifest import MANIFEST_FILENAME
from fastapi_gen.upgrade.recovery import (
    _PRESENCE_DETECTORS,
    detect_generated_at,
    detect_version,
    recover_context,
    write_candidate_manifest,
)


def _write_pyproject(project: Path, body: str) -> None:
    backend = project / "backend"
    backend.mkdir(parents=True, exist_ok=True)
    (backend / "pyproject.toml").write_text(body, encoding="utf-8")


def test_detect_version_from_readme(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "# Project\n\n*Generated with [Template](https://x) v0.2.9.*\n", encoding="utf-8"
    )
    assert detect_version(tmp_path) == "0.2.9"


def test_detect_version_missing_readme(tmp_path: Path) -> None:
    assert detect_version(tmp_path) is None


def test_recover_detects_features_from_layout(tmp_path: Path) -> None:
    (tmp_path / "frontend").mkdir()
    (tmp_path / "backend" / "app" / "services" / "rag").mkdir(parents=True)
    (tmp_path / "README.md").write_text("v0.2.10", encoding="utf-8")

    result = recover_context(tmp_path)
    assert result.context["use_frontend"] is True
    assert result.context["enable_rag"] is True
    assert result.context["enable_billing"] is False
    assert result.version == "0.2.10"
    assert any("best-effort" in w.lower() for w in result.warnings)
    assert any("value variables" in w.lower() for w in result.warnings)


def test_write_candidate_manifest_is_separate_file(tmp_path: Path) -> None:
    result = recover_context(tmp_path)
    candidate = write_candidate_manifest(tmp_path, result)
    assert candidate.name == MANIFEST_FILENAME + ".candidate"
    assert not (tmp_path / MANIFEST_FILENAME).exists()
    data = json.loads(candidate.read_text())
    assert "context" in data


def test_detect_version_readme_without_version(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Project\nno version here\n", encoding="utf-8")
    assert detect_version(tmp_path) is None


def test_detect_generated_at_reads_the_stamp_back(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        '[tool.fastapi-fullstack]\ngenerator_version = "0.2.16"\n'
        'generated_at = "2025-03-14 10:22:01"\n',
    )
    assert detect_generated_at(tmp_path) == "2025-03-14 10:22:01"


def test_detect_generated_at_without_pyproject(tmp_path: Path) -> None:
    assert detect_generated_at(tmp_path) is None


def test_detect_generated_at_without_the_stamp(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, '[project]\nname = "x"\n')
    assert detect_generated_at(tmp_path) is None


def test_recovered_context_carries_generated_at(tmp_path: Path) -> None:
    """Without it, every stamped file reads as an edit the client never made.

    `generated_at` is rendered into backend/pyproject.toml and every alembic
    `Create Date:` header. If recovery drops it, run_upgrade passes None to
    strip_generated_at, BASE/THEIRS render the stamp empty while OURS carries the real
    one, and the first release touching backend/pyproject.toml conflicts on a file
    nobody edited.
    """
    _write_pyproject(tmp_path, '[tool.x]\ngenerated_at = "2025-03-14 10:22:01"\n')

    result = recover_context(tmp_path)

    assert result.context["generated_at"] == "2025-03-14 10:22:01"
    assert not any("generated_at" in w for w in result.warnings)


def test_unrecoverable_generated_at_is_warned_about(tmp_path: Path) -> None:
    result = recover_context(tmp_path)

    assert "generated_at" not in result.context
    assert any("generated_at" in w for w in result.warnings)


def test_an_empty_stamp_is_recovered_without_a_warning(tmp_path: Path) -> None:
    """An empty stamp is what the template renders by default, so it needs no warning
    and nothing to set — the three trees already agree on it."""
    _write_pyproject(tmp_path, '[tool.x]\ngenerated_at = ""\n')

    result = recover_context(tmp_path)

    assert detect_generated_at(tmp_path) == ""
    assert "generated_at" not in result.context
    assert not any("generated_at" in w for w in result.warnings)


def test_every_detector_path_exists_in_template() -> None:
    """Every recovery sentinel must map to a path the template actually ships.

    A sentinel that never exists in the template always infers its feature as
    absent — e.g. the earlier ``agents/pydantic_ai_agent.py`` typo silently disabled
    the client's AI framework on recovery. This guards against that regression.
    """
    slug_dir = _find_template_dir() / "{{cookiecutter.project_slug}}"
    missing = [rel for _, rel in _PRESENCE_DETECTORS if not (slug_dir / rel).exists()]
    assert not missing, f"recovery detector paths absent from the template: {missing}"
