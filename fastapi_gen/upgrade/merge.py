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

from .normalize import _GENERATED_AT_PLACEHOLDER, restore_generated_at

_EXCLUDED_NAMES = frozenset(
    {
        ".env",
        "uv.lock",
        "package-lock.json",
        "bun.lockb",
        "bun.lock",
        ".fastapi-fullstack.json",
        ".gitattributes",
        # OS junk. A maintainer who builds the wheel locally ships whatever sits in
        # template/ (hatch force-includes the directory), and the upgrade would then
        # add it to every client repo — where their .gitignore covers it.
        ".DS_Store",
        "Thumbs.db",
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

# Suffixes that mark a `.env.*` file as a committed *sample* rather than a live env file.
_ENV_TEMPLATE_SUFFIXES = (".example", ".sample", ".template")


def is_excluded(rel_path: str) -> bool:
    """True if a repo-relative path must never enter the merge."""
    parts = Path(rel_path).parts
    if any(p in _EXCLUDED_DIRS for p in parts):
        return True
    name = parts[-1] if parts else rel_path
    if name in _EXCLUDED_NAMES:
        return True
    if not name.startswith(".env."):
        return False
    # `.env.example` is the opposite of a secret: it is committed, it is rendered from
    # the same context in all three trees, and it is where a release announces every new
    # setting. Excluding it means new env vars never reach the client — silently, since
    # classify_trees filters on this same predicate, so no report line mentions it.
    return not name.endswith(_ENV_TEMPLATE_SUFFIXES)


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


_SAFE_CONFIG = ("-c", "core.autocrlf=false", "-c", "core.attributesFile=/dev/null")


def _git(
    git_dir: Path, *args: str, index_file: Path | None = None, work_tree: Path | None = None
) -> str:
    env_prefix: list[str] = ["git", f"--git-dir={git_dir}", *_SAFE_CONFIG]
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


def _commit_tree(git_dir: Path, tree: str, parent: str | None = None) -> str:
    """Wrap a bare tree oid in a throwaway commit and return the commit oid.

    ``merge-tree --write-tree`` accepts bare *tree* oids only since Git 2.45, and its
    ``--merge-base`` flag needs 2.40 — Debian 12 ships 2.39 and Ubuntu 24.04 ships
    2.43, so both would fail. Feeding real commits instead (OURS/THEIRS as children of
    a common BASE commit) lets ``merge-tree`` discover the merge base from ancestry,
    which works down to Git 2.38 without ``--merge-base`` at all.
    """
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "upgrade",
        "GIT_AUTHOR_EMAIL": "upgrade@local",
        "GIT_COMMITTER_NAME": "upgrade",
        "GIT_COMMITTER_EMAIL": "upgrade@local",
        "GIT_AUTHOR_DATE": "@0 +0000",
        "GIT_COMMITTER_DATE": "@0 +0000",
    }
    args = ["git", f"--git-dir={git_dir}", "commit-tree", tree]
    if parent is not None:
        args += ["-p", parent]
    args += ["-m", "upgrade"]
    return subprocess.run(args, capture_output=True, text=True, check=True, env=env).stdout.strip()


def merge_trees(base_dir: Path, ours_dir: Path, theirs_dir: Path) -> MergeResult:
    """3-way merge three concrete trees; return the merged tree + conflicts."""
    tmp = Path(tempfile.mkdtemp(prefix="fastapi-fullstack-merge-"))
    git_dir = tmp / "store.git"
    subprocess.run(
        ["git", "init", "--bare", "-q", "--object-format=sha1", str(git_dir)], check=True
    )

    base = _stage_tree(git_dir, base_dir, tmp, "base")
    ours = _stage_tree(git_dir, ours_dir, tmp, "ours")
    theirs = _stage_tree(git_dir, theirs_dir, tmp, "theirs")

    base_commit = _commit_tree(git_dir, base)
    ours_commit = _commit_tree(git_dir, ours, parent=base_commit)
    theirs_commit = _commit_tree(git_dir, theirs, parent=base_commit)

    proc = subprocess.run(
        [
            "git",
            f"--git-dir={git_dir}",
            *_MERGE_CONFIG,
            "merge-tree",
            "--write-tree",
            "-z",
            ours_commit,
            theirs_commit,
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


def has_uncommitted_changes(repo: Path) -> bool:
    """True if the client has uncommitted changes to *tracked* files."""
    status = _client_git(repo, "status", "--porcelain", "--untracked-files=no").stdout
    return bool(status.strip())


def assert_clean_worktree(repo: Path) -> None:
    """Refuse to proceed unless the client's tracked tree is clean."""
    if has_uncommitted_changes(repo):
        raise RuntimeError(
            "Working tree has uncommitted changes. Commit or stash them first "
            "(the upgrade must be reversible via plain git)."
        )


def current_branch(repo: Path) -> str:
    return _client_git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def _ls_tree_entries(out: str) -> list[tuple[str, str]]:
    """Parse ``ls-tree -r -z`` output into (mode, path) pairs.

    ``-z`` is essential: without it ``ls-tree`` C-quotes any non-ASCII path when
    ``core.quotepath`` is at its default, so ``żółć.txt`` comes back as a mangled
    literal that then breaks every downstream pathspec.
    """
    entries: list[tuple[str, str]] = []
    for record in out.split("\0"):
        if not record:
            continue
        meta, _, path = record.partition("\t")
        mode = meta.split(" ", 1)[0]
        entries.append((mode, path))
    return entries


def _tracked_files(repo: Path, ref: str) -> set[str]:
    out = _client_git(repo, "ls-tree", "-r", "-z", ref).stdout
    return {path for mode, path in _ls_tree_entries(out) if mode != "160000"}


def _tracked_symlinks(repo: Path, ref: str) -> set[str]:
    out = _client_git(repo, "ls-tree", "-r", "-z", ref).stdout
    return {path for mode, path in _ls_tree_entries(out) if mode == "120000"}


def _untracked_files(repo: Path) -> set[str]:
    out = _client_git(repo, "ls-files", "--others", "--exclude-standard", "-z").stdout
    return {p for p in out.split("\0") if p}


def _tree_files(store: Path, tree: str) -> set[str]:
    out = subprocess.run(
        ["git", f"--git-dir={store}", "ls-tree", "-r", "--name-only", "-z", tree],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {p for p in out.split("\0") if p}


def materialize(
    result: MergeResult,
    client_repo: Path,
    *,
    branch: str,
    force: bool = False,
    generated_at: str | None = None,
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

    try:
        _materialize_onto_branch(
            result, client_repo, store, base_ref, force=force, generated_at=generated_at
        )
    except Exception:
        _client_git(client_repo, "checkout", "--force", orig_branch, check=False)
        _client_git(client_repo, "branch", "-D", branch, check=False)
        raise

    return orig_branch


def _materialize_onto_branch(
    result: MergeResult,
    client_repo: Path,
    store: Path,
    base_ref: str,
    *,
    force: bool = False,
    generated_at: str | None = None,
) -> None:
    merged_files = _tree_files(store, result.merged_tree)
    in_scope_tracked = {f for f in _tracked_files(client_repo, base_ref) if not is_excluded(f)}
    symlinks = _tracked_symlinks(client_repo, base_ref) | {
        p for p in _untracked_files(client_repo) if (client_repo / p).is_symlink()
    }

    collisions = sorted((_untracked_files(client_repo) & merged_files) - symlinks)
    if collisions and not force:
        raise RuntimeError(
            "These untracked files would be overwritten by the upgrade:\n"
            + "\n".join(f"  {c}" for c in collisions)
            + "\nCommit, stash, or remove them first (or re-run with --force)."
        )

    # Delete stale paths *before* extraction: doing it after would let a case-only
    # rename (Readme.md → README.md, same inode on case-insensitive filesystems)
    # unlink the freshly-written file, and a file→dir change raise IsADirectoryError.
    for rel in sorted(in_scope_tracked - merged_files - symlinks):
        target = client_repo / rel
        if target.is_symlink():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink()

    # _SAFE_CONFIG is not optional here: `git archive` honors the *global* attributes
    # file even for this throwaway store, so a stray `export-ignore` would silently
    # drop merged files (the template update then looks "already applied", and a
    # brand-new file makes the `add --pathspec-from-file` below fail), and
    # `export-subst` would rewrite `$Format:…$` content.
    archive = subprocess.run(
        [
            "git",
            f"--git-dir={store}",
            *_SAFE_CONFIG,
            "archive",
            "--format=tar",
            result.merged_tree,
        ],
        capture_output=True,
        check=True,
    ).stdout
    subprocess.run(["tar", "-x", "-C", str(client_repo)], input=archive, check=True)

    # Restore the real generated_at stamp on the worktree *before* staging, so the
    # index never carries the <normalized-generated-at> placeholder into a commit.
    if generated_at:
        restore_generated_at(client_repo, generated_at)

    # Stage only the merge-scoped paths (adds, edits, deletions) instead of a blanket
    # `add -A`, which would sweep unrelated untracked files onto the upgrade branch.
    #
    # `--force` for the same reason `_stage_tree` uses it: `git add` given an *explicit*
    # pathspec that a .gitignore covers fails the whole call with exit 1 ("The following
    # paths are ignored…"), which would abort the entire upgrade. That is reachable
    # whenever the client ignores a path the template ships — including in the very
    # upgrade that adds the ignore rule, since .gitignore is merged too. The pathspec
    # list is exact (the merged tree plus what was already tracked), so forcing can only
    # stage files the merge itself produced.
    to_stage = sorted((merged_files | in_scope_tracked) - symlinks)
    if to_stage:
        payload = ("\0".join(to_stage) + "\0").encode("utf-8", "surrogateescape")
        subprocess.run(
            [
                "git",
                "-C",
                str(client_repo),
                "--literal-pathspecs",
                "add",
                "-A",
                "--force",
                "--pathspec-from-file=-",
                "--pathspec-file-nul",
            ],
            input=payload,
            capture_output=True,
            check=True,
        )

    if result.conflicts:
        index_info: list[str] = []
        null_oid = "0" * 40
        placeholder_b = _GENERATED_AT_PLACEHOLDER.encode("utf-8")
        value_b = generated_at.encode("utf-8") if generated_at else None
        for path, stages in result.conflicts.items():
            index_info.append(f"0 {null_oid} 0\t{path}")
            for stage, (mode, oid) in sorted(stages.items()):
                blob = subprocess.run(
                    ["git", f"--git-dir={store}", "cat-file", "blob", oid],
                    capture_output=True,
                    check=True,
                ).stdout
                # Rewrite the placeholder in the conflict stage blobs too, so an
                # "accept ours/theirs" in the IDE can't reintroduce it.
                if value_b:
                    blob = blob.replace(placeholder_b, value_b)
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
        payload = b"".join((rec + "\0").encode("utf-8", "surrogateescape") for rec in index_info)
        subprocess.run(
            ["git", "-C", str(client_repo), "update-index", "-z", "--index-info"],
            input=payload,
            capture_output=True,
            check=True,
        )


def cleanup_store(merged_tree: str) -> None:
    """Remove the throwaway store for a completed merge."""
    store = _MERGE_STORES.pop(merged_tree, None)
    if store and store.parent.exists():
        shutil.rmtree(store.parent, ignore_errors=True)


def undo_command(branch: str, orig_branch: str) -> str:
    """The exact plain-git command that reverts an applied upgrade.

    ``-f`` is required: with a conflicted index a plain ``git checkout`` refuses,
    and with a clean index it would otherwise carry the staged upgrade onto the
    original branch instead of discarding it.
    """
    return f"git checkout -f {orig_branch} && git branch -D {branch}"
