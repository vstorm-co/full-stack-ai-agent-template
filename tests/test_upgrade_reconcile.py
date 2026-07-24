"""Tests for fastapi_gen.upgrade.reconcile."""

import json
from pathlib import Path

from fastapi_gen.upgrade.metadata import UpgradeMetadata, VariableRename
from fastapi_gen.upgrade.reconcile import (
    apply_variable_renames,
    default_confirm,
    reconcile_context,
)


def _template(tmp_path: Path, defaults: dict, name: str = "template") -> Path:
    t = tmp_path / name
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
        source = _template(tmp_path, {"project_name": "x"}, name="source")
        target = _template(tmp_path, {"project_name": "x", "enable_charts": True})
        ctx = {"project_name": "acme"}
        result_ctx, report = reconcile_context(ctx, source, target, UpgradeMetadata())
        assert result_ctx["enable_charts"] is False
        assert report.new_features_available == ["enable_charts"]
        assert report.new_features_accepted == []

    def test_prompts_and_accepts_with_flag(self, tmp_path: Path) -> None:
        source = _template(tmp_path, {}, name="source")
        target = _template(tmp_path, {"enable_charts": True, "enable_deep_research": False})

        def confirm(_message: str, _default: bool) -> bool:
            return "charts" in _message

        result_ctx, report = reconcile_context(
            {}, source, target, UpgradeMetadata(), with_new_features=True, confirm=confirm
        )
        assert result_ctx["enable_charts"] is True
        assert result_ctx["enable_deep_research"] is False
        assert report.new_features_accepted == ["enable_charts"]

    def test_existing_feature_not_treated_as_new(self, tmp_path: Path) -> None:
        source = _template(tmp_path, {"enable_charts": True}, name="source")
        target = _template(tmp_path, {"enable_charts": True})
        ctx = {"enable_charts": True}
        _result_ctx, report = reconcile_context(ctx, source, target, UpgradeMetadata())
        assert report.new_features_available == []


class TestReconcileIncompleteContext:
    """A recovered manifest carries only the keys recovery could infer from the
    file layout. Everything else must fall back to the source version's default —
    treating it as a brand-new feature and forcing it off would render THEIRS
    without the client's auth/database/i18n, and the merge would delete all of it."""

    def test_unanswered_key_falls_back_to_the_source_default(self, tmp_path: Path) -> None:
        source = _template(
            tmp_path,
            {"use_database": True, "use_auth": True, "enable_i18n": True},
            name="source",
        )
        target = _template(
            tmp_path,
            {"use_database": True, "use_auth": True, "enable_i18n": True, "enable_charts": True},
        )
        # Only what recovery detected — the rest is unknown, not "new".
        ctx = {"use_database": True}

        result_ctx, report = reconcile_context(ctx, source, target, UpgradeMetadata())

        assert result_ctx["use_auth"] is True
        assert result_ctx["enable_i18n"] is True
        assert report.new_features_available == ["enable_charts"]
        assert result_ctx["enable_charts"] is False

    def test_recorded_answer_wins_over_the_default(self, tmp_path: Path) -> None:
        source = _template(tmp_path, {"enable_i18n": True}, name="source")
        target = _template(tmp_path, {"enable_i18n": True})
        result_ctx, _report = reconcile_context(
            {"enable_i18n": False}, source, target, UpgradeMetadata()
        )
        assert result_ctx["enable_i18n"] is False


def test_default_confirm_delegates_to_wizard_helper(monkeypatch) -> None:
    monkeypatch.setattr("fastapi_gen.prompts._confirm_with_back", lambda *_a, **_k: True)
    assert default_confirm("adopt X?", default=False) is True
