"""Tests for fastapi_gen.upgrade.fetch."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fastapi_gen.upgrade import fetch as fetch_mod
from fastapi_gen.upgrade.fetch import (
    TemplateFetchError,
    _pypi_wheel_url,
    fetch_template,
    latest_pypi_version,
)


def _make_template(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "cookiecutter.json").write_text("{}", encoding="utf-8")
    return path


class TestPypiWheelUrl:
    def test_returns_first_wheel_url(self) -> None:
        payload = {
            "urls": [
                {"packagetype": "sdist", "url": "https://x/pkg.tar.gz"},
                {"packagetype": "bdist_wheel", "url": "https://x/pkg.whl"},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode()
        mock_resp.__enter__.return_value = mock_resp
        with patch.object(fetch_mod.urllib.request, "urlopen", return_value=mock_resp):
            assert _pypi_wheel_url("1.0.0") == "https://x/pkg.whl"

    def test_raises_when_no_wheel(self) -> None:
        payload = {"urls": [{"packagetype": "sdist", "url": "https://x/pkg.tar.gz"}]}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode()
        mock_resp.__enter__.return_value = mock_resp
        with (
            patch.object(fetch_mod.urllib.request, "urlopen", return_value=mock_resp),
            pytest.raises(TemplateFetchError, match="No wheel found"),
        ):
            _pypi_wheel_url("1.0.0")

    def test_raises_on_network_error(self) -> None:
        with (
            patch.object(fetch_mod.urllib.request, "urlopen", side_effect=OSError("boom")),
            pytest.raises(TemplateFetchError, match="Could not query PyPI"),
        ):
            _pypi_wheel_url("1.0.0")


class TestLatestPypiVersion:
    def test_returns_info_version(self) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"info": {"version": "3.1.4"}}).encode()
        mock_resp.__enter__.return_value = mock_resp
        with patch.object(fetch_mod.urllib.request, "urlopen", return_value=mock_resp):
            assert latest_pypi_version() == "3.1.4"

    def test_raises_when_no_version(self) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"info": {}}).encode()
        mock_resp.__enter__.return_value = mock_resp
        with (
            patch.object(fetch_mod.urllib.request, "urlopen", return_value=mock_resp),
            pytest.raises(TemplateFetchError, match="no latest version"),
        ):
            latest_pypi_version()

    def test_raises_on_network_error(self) -> None:
        with (
            patch.object(fetch_mod.urllib.request, "urlopen", side_effect=OSError("boom")),
            pytest.raises(TemplateFetchError, match="Could not query PyPI"),
        ):
            latest_pypi_version()


class TestFetchTemplate:
    def test_uses_local_when_version_is_running_version(self, tmp_path: Path) -> None:
        local = _make_template(tmp_path / "local_template")
        result = fetch_template("9.9.9", local_template=local, running_version="9.9.9")
        assert result == local

    def test_local_ignored_for_different_version(self, tmp_path: Path) -> None:
        local = _make_template(tmp_path / "local_template")
        with (
            patch.object(fetch_mod, "_fetch_from_pypi", side_effect=TemplateFetchError("x")),
            patch.object(fetch_mod, "_fetch_from_git", side_effect=TemplateFetchError("y")),
            pytest.raises(TemplateFetchError),
        ):
            fetch_template("1.0.0", local_template=local, running_version="9.9.9")

    def test_returns_cached_extracted_template(self, tmp_path: Path) -> None:
        version = "1.2.3"
        cached = _make_template(tmp_path / version / "extracted" / "fastapi_gen" / "template")
        with patch.object(fetch_mod, "_cache_dir", return_value=tmp_path / version):
            result = fetch_template(version)
        assert result == cached

    def test_falls_back_to_git_when_pypi_fails(self, tmp_path: Path) -> None:
        with (
            patch.object(fetch_mod, "_cache_dir", return_value=tmp_path / "v"),
            patch.object(fetch_mod, "_fetch_from_pypi", side_effect=TemplateFetchError("no pypi")),
            patch.object(fetch_mod, "_fetch_from_git", return_value=tmp_path / "git-template"),
        ):
            _make_template(tmp_path / "git-template")
            result = fetch_template("1.0.0")
        assert result == tmp_path / "git-template"


@pytest.mark.slow
class TestFetchTemplateLive:
    """Real PyPI fetch — skipped automatically if offline."""

    def test_fetches_published_version(self) -> None:
        try:
            template = fetch_template("0.2.13")
        except TemplateFetchError as exc:
            pytest.skip(f"PyPI unreachable: {exc}")
        assert (template / "cookiecutter.json").exists()
