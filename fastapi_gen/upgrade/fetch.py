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

import hashlib
import json
import os
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


def _cache_root() -> Path:
    """Per-user cache root. A shared, guessable path lets another local user
    pre-seed a poisoned template whose post-gen hook runs as us during render."""
    uid = getattr(os, "getuid", lambda: "shared")()
    return Path(tempfile.gettempdir()) / f"fastapi-fullstack-upgrade-{uid}" / "templates"


_CACHE_ROOT = _cache_root()


class TemplateFetchError(RuntimeError):
    """Raised when a version's template cannot be obtained by any method."""


def _cache_dir(version: str) -> Path:
    return _CACHE_ROOT / version


def _secure_mkdir(path: Path) -> None:
    """Create ``path`` (and its parent) private to the current user, refusing a
    pre-existing dir owned by someone else."""
    getuid = getattr(os, "getuid", None)
    for target in (path.parent, path):
        if target.exists():
            if getuid is not None and target.stat().st_uid != getuid():
                raise TemplateFetchError(
                    f"Refusing to use cache dir {target} owned by another user — "
                    "it could contain a poisoned template."
                )
        else:
            target.mkdir(mode=0o700, parents=True, exist_ok=True)


def _assert_cache_owned(template_path: Path, cache: Path) -> None:
    """Refuse a cached template if any component up to the cache root is a symlink
    or owned by another user.

    The write path is ownership-checked by :func:`_secure_mkdir`, but a *cache hit*
    reads the tree straight from the guessable ``/tmp`` location — so without this a
    pre-seeded, poisoned template would render (running its post-gen hook as us)
    with no check at all.
    """
    getuid = getattr(os, "getuid", None)
    if getuid is None:
        return
    uid = getuid()
    stop = cache.parent
    current = template_path
    while True:
        if current.is_symlink():
            raise TemplateFetchError(
                f"Refusing cached template — {current} is a symlink (possible cache poisoning)."
            )
        try:
            not_ours = current.exists() and current.stat().st_uid != uid
        except OSError:
            break
        if not_ours:
            raise TemplateFetchError(
                f"Refusing cached template — {current} is owned by another user "
                "(possible cache poisoning)."
            )
        if current == stop or current.parent == current:
            break
        current = current.parent


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


def _pypi_metadata(version: str, *, timeout: float = 30.0) -> dict:
    """Fetch and parse PyPI's release JSON for ``version``."""
    url = _PYPI_JSON.format(name=GENERATOR_NAME, version=version)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 (trusted host)
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise TemplateFetchError(
            f"Could not query PyPI for {GENERATOR_NAME}=={version}: {exc}"
        ) from exc


def _pypi_wheel_url(version: str, *, timeout: float = 30.0) -> str:
    """Return the download URL of the wheel for ``version`` from PyPI."""
    data = _pypi_metadata(version, timeout=timeout)
    for entry in data.get("urls", []):
        if entry.get("packagetype") == "bdist_wheel" and entry.get("url"):
            return str(entry["url"])
    raise TemplateFetchError(f"No wheel found on PyPI for {GENERATOR_NAME}=={version}.")


def _wheel_sha256(version: str, wheel_url: str, *, timeout: float = 30.0) -> str | None:
    """Best-effort: the expected sha256 for ``wheel_url`` from PyPI (``None`` if unknown)."""
    try:
        data = _pypi_metadata(version, timeout=timeout)
    except TemplateFetchError:
        return None
    for entry in data.get("urls", []):
        if entry.get("url") == wheel_url:
            return entry.get("digests", {}).get("sha256")
    return None


def _fetch_from_pypi(version: str, dest: Path, *, timeout: float = 30.0) -> Path:
    """Download the wheel for ``version`` and extract its bundled template into ``dest``."""
    wheel_url = _pypi_wheel_url(version, timeout=timeout)
    _secure_mkdir(dest)
    wheel_path = dest / "package.whl"
    try:
        with urllib.request.urlopen(wheel_url, timeout=timeout) as resp:  # noqa: S310
            wheel_bytes = resp.read()
    except Exception as exc:
        raise TemplateFetchError(f"Failed to download wheel for {version}: {exc}") from exc

    expected = _wheel_sha256(version, wheel_url, timeout=timeout)
    if expected and hashlib.sha256(wheel_bytes).hexdigest() != expected:
        raise TemplateFetchError(
            f"Wheel for {version} failed sha256 verification against PyPI's digest."
        )
    wheel_path.write_bytes(wheel_bytes)

    # Extract into a staging dir and only rename into place on success. A corrupt or
    # truncated wheel raises BadZipFile/OSError (now wrapped so the git fallback still
    # fires) instead of leaving a half-populated tree that a later run would cache-hit
    # (_validate_template_dir passes on cookiecutter.json alone).
    extract_dir = dest / "extracted"
    staging = dest / "extracted.partial"
    shutil.rmtree(staging, ignore_errors=True)
    try:
        with zipfile.ZipFile(wheel_path) as zf:
            zf.extractall(staging)
    except (zipfile.BadZipFile, OSError) as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise TemplateFetchError(
            f"Wheel for {version} could not be extracted (corrupt download?): {exc}"
        ) from exc

    template_dir = staging / _BUNDLED_TEMPLATE_SUBPATH
    if not template_dir.exists():
        shutil.rmtree(staging, ignore_errors=True)
        raise TemplateFetchError(
            f"Wheel for {version} does not bundle a template at {_BUNDLED_TEMPLATE_SUBPATH}."
        )
    _validate_template_dir(template_dir)
    shutil.rmtree(extract_dir, ignore_errors=True)
    os.replace(staging, extract_dir)
    return _validate_template_dir(extract_dir / _BUNDLED_TEMPLATE_SUBPATH)


def _fetch_from_git(version: str, dest: Path) -> Path:
    """Fallback: shallow-clone the template repo at tag ``vX``."""
    git = shutil.which("git")
    if not git:
        raise TemplateFetchError("git not available for template-repo fallback.")
    _secure_mkdir(dest)
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
        _assert_cache_owned(cached_template, cache)
        return _validate_template_dir(cached_template)
    cached_git_template = cache / "repo" / "template"
    if use_cache and cached_git_template.exists():
        _assert_cache_owned(cached_git_template, cache)
        return _validate_template_dir(cached_git_template)

    if use_cache and cache.exists():
        shutil.rmtree(cache)

    try:
        return _fetch_from_pypi(version, cache)
    except TemplateFetchError:
        shutil.rmtree(cache, ignore_errors=True)  # clean slate for the fallback
    try:
        return _fetch_from_git(version, cache)
    except TemplateFetchError:
        shutil.rmtree(cache, ignore_errors=True)
        raise
