"""Fetch a given generator version's bundled cookiecutter template.

Every ``fastapi-fullstack`` release bundles its template under
``fastapi_gen/template`` (see ``[tool.hatch.build.targets.wheel.force-include]``
in pyproject.toml). So to render BASE (template @ old version X) we just download
that version's wheel from PyPI and extract the template — no template-repo access
needed, works even if the repo is private.

Primary path: download the wheel straight from PyPI's JSON API with stdlib only
(no dependency on ``uv``/``pip`` being present in the runtime). Fallback: shallow
git clone of the template repo at tag ``vX``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from ..config import GENERATOR_NAME
from .manifest import TEMPLATE_URL

_PYPI_JSON = "https://pypi.org/pypi/{name}/{version}/json"
_PYPI_LATEST_JSON = "https://pypi.org/pypi/{name}/json"

_BUNDLED_TEMPLATE_SUBPATH = Path("fastapi_gen") / "template"

_CACHE_ROOT = Path(tempfile.gettempdir()) / "fastapi-fullstack-upgrade" / "templates"


class TemplateFetchError(RuntimeError):
    """Raised when a version's template cannot be obtained by any method."""


def _cache_dir(version: str) -> Path:
    return _CACHE_ROOT / version


def _validate_template_dir(path: Path) -> Path:
    if not (path / "cookiecutter.json").exists():
        raise TemplateFetchError(
            f"Extracted template at {path} has no cookiecutter.json — "
            "the wheel layout may have changed."
        )
    return path


def latest_pypi_version(*, timeout: float = 30.0) -> str:
    """Return the latest published version of the generator on PyPI.

    Used as the rename-guard baseline: the working tree may already carry a bumped
    (unreleased) version, so comparing against it would be a no-op — the last
    *published* release is the correct baseline.
    """
    url = _PYPI_LATEST_JSON.format(name=GENERATOR_NAME)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 (trusted host)
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise TemplateFetchError(
            f"Could not query PyPI for the latest {GENERATOR_NAME} version: {exc}"
        ) from exc
    version = data.get("info", {}).get("version")
    if not version:
        raise TemplateFetchError(f"PyPI returned no latest version for {GENERATOR_NAME}.")
    return str(version)


def _pypi_wheel_url(version: str, *, timeout: float = 30.0) -> str:
    """Return the download URL of the wheel for ``version`` from PyPI."""
    url = _PYPI_JSON.format(name=GENERATOR_NAME, version=version)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 (trusted host)
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise TemplateFetchError(
            f"Could not query PyPI for {GENERATOR_NAME}=={version}: {exc}"
        ) from exc

    for entry in data.get("urls", []):
        if entry.get("packagetype") == "bdist_wheel" and entry.get("url"):
            return str(entry["url"])
    raise TemplateFetchError(f"No wheel found on PyPI for {GENERATOR_NAME}=={version}.")


def _fetch_from_pypi(version: str, dest: Path, *, timeout: float = 30.0) -> Path:
    """Download the wheel for ``version`` and extract its bundled template into ``dest``."""
    wheel_url = _pypi_wheel_url(version, timeout=timeout)
    dest.mkdir(parents=True, exist_ok=True)
    wheel_path = dest / "package.whl"
    try:
        with urllib.request.urlopen(wheel_url, timeout=timeout) as resp:  # noqa: S310
            wheel_path.write_bytes(resp.read())
    except Exception as exc:
        raise TemplateFetchError(f"Failed to download wheel for {version}: {exc}") from exc

    extract_dir = dest / "extracted"
    with zipfile.ZipFile(wheel_path) as zf:
        zf.extractall(extract_dir)

    template_dir = extract_dir / _BUNDLED_TEMPLATE_SUBPATH
    if not template_dir.exists():
        raise TemplateFetchError(
            f"Wheel for {version} does not bundle a template at {_BUNDLED_TEMPLATE_SUBPATH}."
        )
    return _validate_template_dir(template_dir)


def _fetch_from_git(version: str, dest: Path) -> Path:
    """Fallback: shallow-clone the template repo at tag ``vX``."""
    git = shutil.which("git")
    if not git:
        raise TemplateFetchError("git not available for template-repo fallback.")
    dest.mkdir(parents=True, exist_ok=True)
    clone_dir = dest / "repo"
    result = subprocess.run(
        [git, "clone", "--depth", "1", "--branch", f"v{version}", TEMPLATE_URL, str(clone_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise TemplateFetchError(
            f"git clone of {TEMPLATE_URL}@v{version} failed: {result.stderr.strip()}"
        )
    return _validate_template_dir(clone_dir / "template")


def fetch_template(
    version: str,
    *,
    local_template: Path | None = None,
    running_version: str | None = None,
    use_cache: bool = True,
) -> Path:
    """Return a path to the cookiecutter template dir for ``version``.

    Args:
        version: The generator version to obtain (e.g. ``"0.2.10"``).
        local_template: If given and ``version == running_version``, this local
            template dir is used directly (THEIRS when upgrading to the running
            ``@latest`` — no download needed).
        running_version: The version of the currently-running generator.
        use_cache: Reuse a previously-extracted template for the same version.

    Raises:
        TemplateFetchError: If the template cannot be obtained by PyPI or git.
    """
    if local_template is not None and running_version is not None and version == running_version:
        return _validate_template_dir(local_template)

    cache = _cache_dir(version)
    cached_template = cache / "extracted" / _BUNDLED_TEMPLATE_SUBPATH
    if use_cache and cached_template.exists():
        return _validate_template_dir(cached_template)
    cached_git_template = cache / "repo" / "template"
    if use_cache and cached_git_template.exists():
        return _validate_template_dir(cached_git_template)

    if use_cache and cache.exists():
        shutil.rmtree(cache)

    try:
        return _fetch_from_pypi(version, cache)
    except TemplateFetchError:
        return _fetch_from_git(version, cache)
