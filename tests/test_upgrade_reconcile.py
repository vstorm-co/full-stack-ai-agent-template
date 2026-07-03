"""Tests for fastapi_gen.upgrade.reconcile."""

import json
from pathlib import Path

from fastapi_gen.upgrade.metadata import UpgradeMetadata, VariableRename
from fastapi_gen.upgrade.reconcile import apply_variable_renames, reconcile_context


def _template(tmp_path: Path, defaults: dict) -> Path:
    t = tmp_path / "template"
    t.mkdir()
    (t / "cookiecutter.json").write_text(json.dumps(defaults), encoding="utf-8")
    return t


class TestApplyVariableRenames:
    def test_renames_key_and_maps_value(self) -> None:
        ctx = {"use_pgvector": "yes"}
        applied = apply_variable_renames(
            ctx,
            [VariableRename("use_pgvector", "vector_store", "0.2.0", {"yes": "pgvector"})],
        )
        assert ctx == {"vector_store": "pgvector"}
        assert applied == ["use_pgvector→vector_store"]

    def test_noop_when_key_absent(self) -> None:
        ctx = {"other": 1}
        assert apply_variable_renames(ctx, [VariableRename("x", "y", "0.1.0")]) == []
        assert ctx == {"other": 1}


class TestReconcileNewFeatures:
    def test_new_feature_off_by_default(self, tmp_path: Path) -> None:
        template = _template(tmp_path, {"project_name": "x", "enable_charts": True})
        ctx = {"project_name": "acme"}
        result_ctx, report = reconcile_context(ctx, template, UpgradeMetadata())
        assert result_ctx["enable_charts"] is False
        assert report.new_features_available == ["enable_charts"]
        assert report.new_features_accepted == []

    def test_prompts_and_accepts_with_flag(self, tmp_path: Path) -> None:
        template = _template(tmp_path, {"enable_charts": True, "enable_deep_research": False})
        answers = {"enable_charts": True, "enable_deep_research": False}

        def confirm(_message: str, _default: bool, *, _a=answers) -> bool:
            return "charts" in _message

        result_ctx, report = reconcile_context(
            {}, template, UpgradeMetadata(), with_new_features=True, confirm=confirm
        )
        assert result_ctx["enable_charts"] is True
        assert result_ctx["enable_deep_research"] is False
        assert report.new_features_accepted == ["enable_charts"]

    def test_existing_feature_not_treated_as_new(self, tmp_path: Path) -> None:
        template = _template(tmp_path, {"enable_charts": True})
        ctx = {"enable_charts": True}
        _result_ctx, report = reconcile_context(ctx, template, UpgradeMetadata())
        assert report.new_features_available == []
