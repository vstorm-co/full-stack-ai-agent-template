"""Tests for the upgrade manifest (fastapi_gen.upgrade.manifest)."""

import json
from pathlib import Path

import pytest

from fastapi_gen.config import ProjectConfig, get_generator_version
from fastapi_gen.upgrade import (
    MANIFEST_FILENAME,
    build_manifest,
    compute_context_hash,
    read_manifest,
    redact_secrets,
    write_manifest,
)


class TestRedactSecrets:
    """Secret redaction preserves flags, redacts real secret strings."""

    def test_redacts_secret_string_values(self) -> None:
        ctx = {
            "stripe_secret_key": "sk_live_abcdef",
            "auth_password": "hunter2",
            "some_api_key": "xyz",
            "access_token": "tok_123",
        }
        cleaned = redact_secrets(ctx)
        assert all(v == "<redacted>" for v in cleaned.values())

    def test_preserves_secret_shaped_boolean_flags(self) -> None:
        ctx = {
            "use_api_key": True,
            "use_shared_secret_jwt": False,
            "websocket_auth_api_key": False,
        }
        assert redact_secrets(ctx) == ctx

    def test_preserves_non_secret_strings_and_empty_values(self) -> None:
        ctx = {
            "project_name": "acme",
            "timezone": "Europe/Warsaw",
            "empty_token": "",
        }
        assert redact_secrets(ctx) == ctx

    def test_does_not_mutate_input(self) -> None:
        ctx = {"stripe_secret_key": "sk_live_x"}
        redact_secrets(ctx)
        assert ctx["stripe_secret_key"] == "sk_live_x"


class TestComputeContextHash:
    """context_hash is a stable fingerprint that ignores volatile fields."""

    def test_prefixed_and_deterministic(self) -> None:
        ctx = {"a": 1, "b": "x"}
        h1 = compute_context_hash(ctx)
        h2 = compute_context_hash({"b": "x", "a": 1})
        assert h1.startswith("sha256:")
        assert h1 == h2

    def test_ignores_volatile_generated_at(self) -> None:
        base = {"a": 1, "generated_at": "2026-01-01T00:00:00Z"}
        other = {"a": 1, "generated_at": "2026-07-02T12:00:00Z"}
        assert compute_context_hash(base) == compute_context_hash(other)

    def test_changes_when_real_input_changes(self) -> None:
        assert compute_context_hash({"a": 1}) != compute_context_hash({"a": 2})


class TestBuildManifest:
    """Manifest structure and defaults."""

    def test_has_all_expected_fields(self) -> None:
        ctx = {"generator_version": "1.2.3", "generated_at": "2026-01-01T00:00:00Z"}
        m = build_manifest(ctx, package_version="1.2.3")
        for field in (
            "template",
            "template_ref",
            "package_version",
            "generator_name",
            "generator_version",
            "generated_at",
            "commit",
            "context_hash",
            "context",
        ):
            assert field in m

    def test_template_ref_defaults_to_the_release_tag(self) -> None:
        m = build_manifest({}, package_version="0.2.14")
        assert m["template_ref"] == "0.2.14"
        assert m["package_version"] == "0.2.14"

    def test_explicit_ref_and_commit_are_kept(self) -> None:
        m = build_manifest({}, package_version="1.0.0", template_ref="abc123", commit="deadbeef")
        assert m["template_ref"] == "abc123"
        assert m["commit"] == "deadbeef"

    def test_package_version_defaults_to_installed(self) -> None:
        m = build_manifest({})
        assert m["package_version"] == get_generator_version()

    def test_context_is_redacted(self) -> None:
        m = build_manifest({"stripe_secret_key": "sk_live_x", "project_name": "acme"})
        assert m["context"]["stripe_secret_key"] == "<redacted>"
        assert m["context"]["project_name"] == "acme"


class TestWriteReadManifest:
    """Round-trip through disk."""

    def test_write_then_read(self, tmp_path: Path) -> None:
        ctx = {"generator_version": "1.0.0", "project_name": "acme"}
        path = write_manifest(tmp_path, ctx, package_version="1.0.0")
        assert path == tmp_path / MANIFEST_FILENAME
        assert path.exists()

        loaded = read_manifest(tmp_path)
        assert loaded["package_version"] == "1.0.0"
        assert loaded["context"]["project_name"] == "acme"

    def test_written_file_is_valid_json_with_trailing_newline(self, tmp_path: Path) -> None:
        write_manifest(tmp_path, {"a": 1})
        text = (tmp_path / MANIFEST_FILENAME).read_text(encoding="utf-8")
        assert text.endswith("\n")
        json.loads(text)

    def test_read_accepts_manifest_path_directly(self, tmp_path: Path) -> None:
        write_manifest(tmp_path, {"a": 1})
        loaded = read_manifest(tmp_path / MANIFEST_FILENAME)
        assert "context" in loaded

    def test_read_missing_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="predates upgrade manifests"):
            read_manifest(tmp_path)


class TestManifestFromRealContext:
    """Manifest built from a real ProjectConfig context is safe and stable."""

    def test_no_secret_string_leaks(self, minimal_config: ProjectConfig) -> None:
        ctx = minimal_config.to_cookiecutter_context()
        manifest = build_manifest(ctx)
        for key, value in manifest["context"].items():
            if isinstance(value, str):
                assert not value.startswith(("sk_", "sk-", "tok_"))
                _ = key

    def test_hash_stable_across_renders_despite_timestamp(
        self, minimal_config: ProjectConfig
    ) -> None:
        ctx1 = minimal_config.to_cookiecutter_context()
        ctx2 = minimal_config.to_cookiecutter_context()
        assert ctx1["generated_at"] != ctx2["generated_at"] or ctx1 == ctx2
        assert compute_context_hash(ctx1) == compute_context_hash(ctx2)


class TestRedactNested:
    def test_redacts_secret_in_nested_dict_and_list(self) -> None:
        ctx = {
            "enable_x": True,
            "creds": {"api_key": "sk_live_123", "name": "keep"},
            "tokens": [{"token": "tok_abc"}],
        }
        cleaned = redact_secrets(ctx)
        assert cleaned["enable_x"] is True
        assert cleaned["creds"]["api_key"] == "<redacted>"
        assert cleaned["creds"]["name"] == "keep"
        assert cleaned["tokens"][0]["token"] == "<redacted>"


class TestReadManifestErrors:
    def test_corrupt_json_raises_value_error(self, tmp_path: Path) -> None:
        (tmp_path / MANIFEST_FILENAME).write_text("{not json", encoding="utf-8")
        with pytest.raises(ValueError, match="Corrupt manifest"):
            read_manifest(tmp_path)

    def test_missing_keys_raises_value_error(self, tmp_path: Path) -> None:
        (tmp_path / MANIFEST_FILENAME).write_text(
            json.dumps({"package_version": "1.0.0"}), encoding="utf-8"
        )
        with pytest.raises(ValueError, match="missing required keys"):
            read_manifest(tmp_path)

    def test_non_object_context_raises_value_error(self, tmp_path: Path) -> None:
        """Present-but-wrong-shape gets past the presence check, and every consumer
        indexes into `context` — reconcile does dict(context), the renderer does .get."""
        (tmp_path / MANIFEST_FILENAME).write_text(
            json.dumps(
                {
                    "package_version": "1.0.0",
                    "template_ref": "1.0.0",
                    "context_hash": "sha256:x",
                    "context": ["enable_rag"],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="non-object 'context'"):
            read_manifest(tmp_path)
