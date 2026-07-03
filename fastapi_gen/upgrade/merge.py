"""The 3-way merge engine.

Runs git's real merge machinery over three fully-rendered trees (BASE, OURS,
THEIRS) using ``git merge-tree --write-tree --merge-base=<tree>`` inside a
throwaway bare repository — no checkout, no fabricated ancestry, full rename /
binary / mode handling. The merged tree (with conflict markers embedded
for conflicted paths) is then materialized onto a fresh branch in the client's
real repo, leaving their history untouched.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

_EXCLUDED_NAMES = frozenset(
    {
        ".env",
        "uv.lock",
        "package-lock.json",
        "bun.lockb",
        "bun.lock",
        ".fastapi-fullstack.json",
        ".gitattributes",
    }
)

_EXCLUDED_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".next",
        ".turbo",
        "dist",
        "build",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
)


def is_excluded(rel_path: str) -> bool:
    """True if a repo-relative path must never enter the merge."""
    parts = Path(rel_path).parts
    if any(p in _EXCLUDED_DIRS for p in parts):
        return True
    name = parts[-1] if parts else rel_path
    if name in _EXCLUDED_NAMES:
        return True
    return name.startswith(".env.")


_CONFLICT_RECORD = re.compile(rb"^([0-7]{6}) ([0-9a-f]{40}) ([1-3])\t(.*)$", re.DOTALL)

_MERGE_CONFIG = (
    "-c",
    "merge.renames=true",
    "-c",
    "merge.renameLimit=20000",
    "-c",
    "diff.renameLimit=20000",
    "-c",
    "core.attributesFile=/dev/null",
)


@dataclass
class MergeResult:
    """Outcome of a 3-way merge."""

    merged_tree: str
    conflicts: dict[str, dict[int, tuple[str, str]]] = field(default_factory=dict)
    clean: bool = True

    @property
    def conflicted_paths(self) -> list[str]:
        return sorted(self.conflicts)


def _git(
    git_dir: Path, *args: str, index_file: Path | None = None, work_tree: Path | None = None
) -> str:
    env_prefix: list[str] = ["git", f"--git-dir={git_dir}"]
    if work_tree is not None:
        env_prefix.append(f"--work-tree={work_tree}")
    env = None
    if index_file is not None:
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = str(index_file)
    result = subprocess.run(
        [*env_prefix, *args], capture_output=True, text=True, check=True, env=env
    )
    return result.stdout


def _copy_filtered(src: Path, dst: Path) -> None:
    """Copy ``src`` into ``dst`` dropping excluded paths."""
    for path in src.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(src).as_posix()
        if is_excluded(rel):
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _stage_tree(git_dir: Path, work_dir: Path, tmp: Path, label: str) -> str:
    """Stage a filtered copy of ``work_dir`` into an isolated index; return tree oid."""
    staged = tmp / f"staged-{label}"
    staged.mkdir(parents=True, exist_ok=True)
    _copy_filtered(work_dir, staged)
    index_file = tmp / f"index-{label}"
    _git(git_dir, "add", "-A", "--force", index_file=index_file, work_tree=staged)
    return _git(git_dir, "write-tree", index_file=index_file).strip()


def _parse_merge_output(raw: bytes, returncode: int) -> MergeResult:
    fields = raw.split(b"\x00")
    merged_tree = fields[0].decode().strip()
    conflicts: dict[str, dict[int, tuple[str, str]]] = {}
    for chunk in fields[1:]:
        m = _CONFLICT_RECORD.match(chunk)
        if m:
            mode, oid, stage, path = m.groups()
            conflicts.setdefault(path.decode("utf-8", "surrogateescape"), {})[int(stage)] = (
                mode.decode(),
                oid.decode(),
            )
    return MergeResult(
        merged_tree=merged_tree,
        conflicts=conflicts,
        clean=(returncode == 0 and not conflicts),
    )


def apply_renames(tree_dir: Path, renames: list[tuple[str, str]]) -> None:
    """Pre-move paths in a rendered tree so client edits follow moved files.

    Applied to BASE and OURS (never THEIRS) *before* merging, in version order, so
    all three trees agree on the new path and the merge becomes an ordinary content
    3-way instead of a delete+add that silently drops the client's edits.

    Args:
        renames: (from_path, to_path) pairs; a trailing ``/`` on ``from_path`` moves
            a whole directory subtree.
    """
    for from_path, to_path in renames:
        if from_path.endswith("/"):
            src = tree_dir / from_path.rstrip("/")
            dst = tree_dir / to_path.rstrip("/")
            if src.is_dir():
                dst.parent.mkdir(parents=True, exist_ok=True)
                for item in src.rglob("*"):
                    if item.is_file():
                        rel = item.relative_to(src)
                        target = dst / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(item), str(target))
                shutil.rmtree(src, ignore_errors=True)
        else:
            src = tree_dir / from_path
            if src.is_file():
                dst = tree_dir / to_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))


def merge_trees(base_dir: Path, ours_dir: Path, theirs_dir: Path) -> MergeResult:
    """3-way merge three concrete trees; return the merged tree + conflicts."""
    tmp = Path(tempfile.mkdtemp(prefix="fastapi-fullstack-merge-"))
    git_dir = tmp / "store.git"
    subprocess.run(["git", "init", "--bare", "-q", str(git_dir)], check=True)

    base = _stage_tree(git_dir, base_dir, tmp, "base")
    ours = _stage_tree(git_dir, ours_dir, tmp, "ours")
    theirs = _stage_tree(git_dir, theirs_dir, tmp, "theirs")

    proc = subprocess.run(
        [
            "git",
            f"--git-dir={git_dir}",
            *_MERGE_CONFIG,
            "merge-tree",
            "--write-tree",
            "-z",
            f"--merge-base={base}",
            ours,
            theirs,
        ],
        capture_output=True,
        check=False,
    )
    if proc.returncode not in (0, 1):  # pragma: no cover
        raise RuntimeError(f"git merge-tree failed:\n{proc.stderr.decode(errors='replace')}")

    result = _parse_merge_output(proc.stdout, proc.returncode)
    _MERGE_STORES[result.merged_tree] = git_dir
    return result


_MERGE_STORES: dict[str, Path] = {}


def _client_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=check
    )


def assert_clean_worktree(repo: Path) -> None:
    """Refuse to proceed unless the client's tracked tree is clean."""
    status = _client_git(repo, "status", "--porcelain", "--untracked-files=no").stdout
    if status.strip():
        raise RuntimeError(
            "Working tree has uncommitted changes. Commit or stash them first "
            "(the upgrade must be reversible via plain git)."
        )


def current_branch(repo: Path) -> str:
    return _client_git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def _tracked_files(repo: Path, ref: str) -> set[str]:
    out = _client_git(repo, "ls-tree", "-r", "--name-only", ref).stdout
    return {line for line in out.splitlines() if line}


def _tree_files(store: Path, tree: str) -> set[str]:
    out = subprocess.run(
        ["git", f"--git-dir={store}", "ls-tree", "-r", "--name-only", tree],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {line for line in out.splitlines() if line}


def materialize(
    result: MergeResult,
    client_repo: Path,
    *,
    branch: str,
    force: bool = False,
) -> str:
    """Write the merged result onto a fresh branch in the client's repo.

    Creates ``branch`` at the current HEAD, writes the merged tree into the
    worktree (conflict markers included for conflicted paths), deletes files the
    template dropped, and reproduces a genuine conflicted index so an IDE 3-way
    editor lights up. Returns the original branch name so the caller can print
    the exact undo command.
    """
    store = _MERGE_STORES.get(result.merged_tree)
    if store is None:
        raise RuntimeError("Merge store not found; call merge_trees() in the same process.")

    assert_clean_worktree(client_repo)
    orig_branch = current_branch(client_repo)
    base_ref = _client_git(client_repo, "rev-parse", "HEAD").stdout.strip()

    existing = _client_git(client_repo, "branch", "--list", branch, check=False).stdout.strip()
    if existing:
        if not force:
            raise RuntimeError(
                f"Branch {branch} already exists. Delete it or re-run with force=True."
            )
        _client_git(client_repo, "branch", "-D", branch)

    _client_git(client_repo, "checkout", "-b", branch, base_ref)

    merged_files = _tree_files(store, result.merged_tree)
    in_scope_tracked = {f for f in _tracked_files(client_repo, base_ref) if not is_excluded(f)}

    archive = subprocess.run(
        ["git", f"--git-dir={store}", "archive", "--format=tar", result.merged_tree],
        capture_output=True,
        check=True,
    ).stdout
    subprocess.run(["tar", "-x", "-C", str(client_repo)], input=archive, check=True)

    for rel in sorted(in_scope_tracked - merged_files):
        target = client_repo / rel
        if target.exists():
            target.unlink()

    _client_git(client_repo, "add", "-A")

    if result.conflicts:
        index_info: list[str] = []
        null_oid = "0" * 40
        for path, stages in result.conflicts.items():
            index_info.append(f"0 {null_oid} 0\t{path}")
            for stage, (mode, oid) in sorted(stages.items()):
                blob = subprocess.run(
                    ["git", f"--git-dir={store}", "cat-file", "blob", oid],
                    capture_output=True,
                    check=True,
                ).stdout
                new_oid = (
                    subprocess.run(
                        ["git", "-C", str(client_repo), "hash-object", "-w", "--stdin"],
                        input=blob,
                        capture_output=True,
                        check=True,
                    )
                    .stdout.decode()
                    .strip()
                )
                index_info.append(f"{mode} {new_oid} {stage}\t{path}")
        subprocess.run(
            ["git", "-C", str(client_repo), "update-index", "--index-info"],
            input="\n".join(index_info) + "\n",
            text=True,
            capture_output=True,
            check=True,
        )

    return orig_branch


def cleanup_store(merged_tree: str) -> None:
    """Remove the throwaway store for a completed merge."""
    store = _MERGE_STORES.pop(merged_tree, None)
    if store and store.parent.exists():
        shutil.rmtree(store.parent, ignore_errors=True)


def undo_command(branch: str, orig_branch: str) -> str:
    """The exact plain-git command that reverts an applied upgrade."""
    return f"git checkout {orig_branch} && git branch -D {branch}"
