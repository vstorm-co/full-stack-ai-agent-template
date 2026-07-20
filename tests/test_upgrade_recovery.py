"""Tests for fastapi_gen.upgrade.recovery."""

import json
from pathlib import Path

from fastapi_gen.generator import _find_template_dir
from fastapi_gen.upgrade.manifest import MANIFEST_FILENAME
from fastapi_gen.upgrade.recovery import (
    _PRESENCE_DETECTORS,
    detect_version,
    recover_context,
    write_candidate_manifest,
)


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


def test_every_detector_path_exists_in_template() -> None:
    """Every recovery sentinel must map to a path the template actually ships.

    A sentinel that never exists in the template always infers its feature as
    absent — e.g. the earlier ``agents/pydantic_ai_agent.py`` typo silently disabled
    the client's AI framework on recovery. This guards against that regression.
    """
    slug_dir = _find_template_dir() / "{{cookiecutter.project_slug}}"
    missing = [rel for _, rel in _PRESENCE_DETECTORS if not (slug_dir / rel).exists()]
    assert not missing, f"recovery detector paths absent from the template: {missing}"
