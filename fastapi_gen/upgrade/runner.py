"""Orchestrator for the ``upgrade`` and ``upgrade finalize`` commands."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from packaging.version import InvalidVersion, Version

from ..config import get_generator_version
from ..generator import _find_template_dir
from .classify import Classification, classify_trees
from .fetch import fetch_template
from .manifest import MANIFEST_FILENAME, build_manifest, read_manifest
from .merge import (
    MergeResult,
    apply_renames,
    assert_clean_worktree,
    cleanup_store,
    current_branch,
    has_uncommitted_changes,
    materialize,
    merge_trees,
    undo_command,
)
from .metadata import UpgradeMetadata, _parse_version, load_metadata
from .normalize import normalize_tree
from .reconcile import ConfirmFn, ReconcileReport, reconcile_context
from .report import console, print_report

_PENDING_SUFFIX = ".pending"
_UPGRADE_BRANCH_KEY = "_upgrade_branch"


class UpgradeError(RuntimeError):
    """Raised for user-facing upgrade failures."""


@dataclass
class UpgradeOutcome:
    from_version: str
    to_version: str
    classification: Classification
    reconcile: ReconcileReport
    merge: MergeResult | None
    applied: bool
    branch: str | None = None
    orig_branch: str | None = None


def _find_upgrades_file() -> Path | None:
    """Locate UPGRADES.yaml — dev repo root, or bundled inside the package."""
    dev = Path(__file__).resolve().parents[2] / "UPGRADES.yaml"
    if dev.exists():
        return dev
    bundled = Path(__file__).resolve().parents[1] / "UPGRADES.yaml"  # pragma: no cover
    return bundled if bundled.exists() else None  # pragma: no cover


def _extract_head(client_repo: Path, dest: Path) -> None:
    """Materialize the client's committed HEAD into ``dest`` (tracked files only).

    Uses ``read-tree`` + ``checkout-index`` through a throwaway index rather than
    ``git archive``: ``archive`` applies the client's ``.gitattributes``
    ``export-ignore`` / ``export-subst`` rules, which would silently drop tracked
    files from OURS (the merge then reads them as client deletions) or rewrite
    ``$Format:…$`` content into phantom edits. ``checkout-index`` honors neither.
    """
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fastapi-fullstack-idx-") as idx_dir:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(idx_dir) / "index")}
        subprocess.run(
            ["git", "-C", str(client_repo), "read-tree", "HEAD"],
            env=env,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(client_repo), "checkout-index", "-a", f"--prefix={dest}/"],
            env=env,
            capture_output=True,
            check=True,
        )


def _rename_pairs(metadata: UpgradeMetadata) -> list[tuple[str, str]]:
    return [(r.from_path, r.to_path) for r in metadata.renames]


def _normalize_target(to_version: str) -> str:
    """Validate ``--to`` and return it in the canonical release form.

    ``_parse_version`` deliberately degrades an unparseable string to ``0`` so a
    malformed UPGRADES.yaml entry can't crash a run — but applied to user input that
    turns ``--to nope`` into "Target vnope is older than v0.2.16. Downgrades are not
    supported." Canonicalizing also drops a typed ``v`` prefix, which would otherwise
    survive into the PyPI URL and the clone tag and 404 there.
    """
    try:
        return str(Version(to_version))
    except InvalidVersion as exc:
        raise UpgradeError(
            f"Invalid target version {to_version!r}: {exc}. Expected a release like 0.2.16."
        ) from exc


def run_upgrade(
    client_repo: Path,
    *,
    to_version: str | None = None,
    dry_run: bool = False,
    with_new_features: bool = False,
    force: bool = False,
    confirm: ConfirmFn | None = None,
) -> UpgradeOutcome:
    """Run the full upgrade workflow. Returns the outcome for the caller."""
    manifest = read_manifest(client_repo)
    from_version = manifest["package_version"]
    context = manifest["context"]

    recorded_hash = manifest.get("context_hash")
    if recorded_hash:
        from .manifest import compute_context_hash

        if compute_context_hash(context) != recorded_hash:
            console.print(
                "[yellow]⚠ Manifest context_hash does not match its context[/] — the manifest "
                "may have been hand-edited; BASE will be rendered from the stored context as-is."
            )

    running = get_generator_version()
    target = _normalize_target(to_version) if to_version else running

    if from_version == target:
        console.print(f"[green]Already at v{target} — nothing to upgrade.[/]")
        return UpgradeOutcome(
            from_version, target, Classification(), ReconcileReport(), None, applied=False
        )

    if _parse_version(target) < _parse_version(from_version):
        raise UpgradeError(
            f"Target v{target} is older than the project's v{from_version}. "
            "Downgrades are not supported."
        )

    if _parse_version(target) > _parse_version(running):
        raise UpgradeError(
            f"Target v{target} is newer than this generator (v{running}). "
            "The bundled UPGRADES.yaml is this (older) version's, so renames recorded "
            "for the newer range are missing — moved files would degrade to delete+add "
            "and lose your edits. Run the newer generator instead:\n"
            "  uvx fastapi-fullstack@latest upgrade"
        )

    if not dry_run:
        assert_clean_worktree(client_repo)
        if current_branch(client_repo) == "HEAD":
            raise UpgradeError(
                "Refusing to upgrade from a detached HEAD — check out a branch first "
                "(the upgrade needs a branch to return to)."
            )
    elif has_uncommitted_changes(client_repo):
        # OURS is always the committed HEAD, so a dry run silently ignores whatever is
        # still in the worktree. Without this the preview can promise zero conflicts and
        # the real run — which demands a clean tree, so those edits get committed first —
        # produces them.
        console.print(
            "[yellow]⚠ Uncommitted changes are not part of this preview[/] — OURS is your "
            "committed HEAD. Commit them and re-run the dry run for an accurate report."
        )

    local_template = _find_template_dir()
    upgrades_file = _find_upgrades_file()
    metadata = (
        load_metadata(upgrades_file, from_version, target) if upgrades_file else UpgradeMetadata()
    )

    base_template = fetch_template(
        from_version, local_template=local_template, running_version=running
    )
    theirs_template = fetch_template(target, local_template=local_template, running_version=running)

    theirs_context, reconcile_report = reconcile_context(
        context,
        base_template,
        theirs_template,
        metadata,
        with_new_features=with_new_features,
        confirm=(lambda *_: False) if dry_run else confirm,
    )

    work = Path(tempfile.mkdtemp(prefix="fastapi-fullstack-upgrade-"))
    from .render import render_template

    result: MergeResult | None = None
    try:
        base_dir = render_template(base_template, context, work / "base_parent")
        theirs_dir = render_template(theirs_template, theirs_context, work / "theirs_parent")
        ours_dir = work / "ours"
        _extract_head(client_repo, ours_dir)

        renames = _rename_pairs(metadata)
        apply_renames(base_dir, renames)
        apply_renames(ours_dir, renames)

        generated_at = context.get("generated_at")
        client_node_modules = client_repo / "frontend" / "node_modules"
        if context.get("use_frontend") and not client_node_modules.exists():  # pragma: no cover
            console.print(
                "[yellow]Frontend deps not installed[/] — run [bold]bun install[/] in "
                "frontend/ for cleaner frontend merges (skipping Prettier normalization)."
            )
        # One shared ruff config for all three trees (the client's, so the delivered
        # result keeps their formatting) — otherwise each tree formats to its own
        # pyproject.toml and the diff fills with false conflicts.
        client_ruff_config = client_repo / "backend" / "pyproject.toml"
        ruff_config = client_ruff_config if client_ruff_config.exists() else None
        ruff_bin = next(
            (
                cand
                for cand in (
                    client_repo / "backend" / ".venv" / "bin" / "ruff",
                    client_repo / ".venv" / "bin" / "ruff",
                )
                if cand.exists()
            ),
            None,
        )
        # Same reasoning on the frontend side: one Prettier config (and one ignore file)
        # for all three trees, so a client-tweaked .prettierrc can't make every .ts/.tsx
        # file look edited in OURS and turn each template change into a conflict.
        prettier_config = next(
            (
                cand
                for cand in (
                    client_repo / "frontend" / ".prettierrc",
                    client_repo / "frontend" / ".prettierrc.json",
                    client_repo / "frontend" / "prettier.config.js",
                    client_repo / "frontend" / "prettier.config.mjs",
                )
                if cand.exists()
            ),
            None,
        )
        prettier_ignore = client_repo / "frontend" / ".prettierignore"
        for tree, rendered in ((base_dir, True), (theirs_dir, True), (ours_dir, False)):
            normalize_tree(
                tree,
                generated_at=generated_at,
                format_code=True,
                frontend_node_modules=client_node_modules,
                ruff_config=ruff_config,
                ruff_bin=ruff_bin,
                prettier_config=prettier_config,
                prettier_ignore=prettier_ignore,
                rendered=rendered,
            )

        result = merge_trees(base_dir, ours_dir, theirs_dir)
        classification = classify_trees(
            base_dir, ours_dir, theirs_dir, set(result.conflicted_paths)
        )

        print_report(
            classification,
            reconcile_report,
            metadata,
            from_version=from_version,
            to_version=target,
            dry_run=dry_run,
        )

        if dry_run:
            return UpgradeOutcome(
                from_version, target, classification, reconcile_report, result, applied=False
            )

        branch = f"template-upgrade/v{target}"
        orig_branch = materialize(
            result, client_repo, branch=branch, force=force, generated_at=generated_at
        )

        # Past this point the branch exists with staged changes; if the bookkeeping
        # below fails, the user still needs the undo command, so always surface it.
        pending_file = MANIFEST_FILENAME + _PENDING_SUFFIX
        try:
            pending = build_manifest(theirs_context, package_version=target)
            pending[_UPGRADE_BRANCH_KEY] = branch
            _write_pending(client_repo, pending)
        except Exception:
            console.print(
                f"[red]Applied on branch[/] [bold]{branch}[/] but writing the pending "
                "manifest failed."
            )
            console.print(
                f"[dim]Undo:[/] {undo_command(branch, orig_branch)} && rm -f {pending_file}"
            )
            raise

        console.print(f"[green]Applied on branch[/] [bold]{branch}[/] (was {orig_branch}).")
        if classification.conflicts:  # pragma: no cover
            console.print(
                f"[yellow]{len(classification.conflicts)} conflict(s)[/] — resolve them in your "
                "IDE's 3-way merge editor, then run [bold]make upgrade-finalize[/]."
            )
        else:
            console.print(
                "No conflicts. Review the branch, then run [bold]make upgrade-finalize[/]."
            )
        console.print(f"[dim]Undo:[/] {undo_command(branch, orig_branch)} && rm -f {pending_file}")

        return UpgradeOutcome(
            from_version,
            target,
            classification,
            reconcile_report,
            result,
            applied=True,
            branch=branch,
            orig_branch=orig_branch,
        )
    finally:
        if result is not None:
            cleanup_store(result.merged_tree)
        shutil.rmtree(work, ignore_errors=True)


def _write_pending(client_repo: Path, manifest: dict) -> None:
    import json

    from .manifest import atomic_write_text

    atomic_write_text(
        client_repo / (MANIFEST_FILENAME + _PENDING_SUFFIX),
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
    )


def run_recover(client_repo: Path) -> Path:
    """Recover a candidate manifest for a manifest-less legacy project.

    Dry-run only: writes ``.fastapi-fullstack.json.candidate`` and prints warnings.
    The developer reviews it, renames it to the real manifest, then upgrades normally.
    """
    from .recovery import recover_context, write_candidate_manifest

    result = recover_context(client_repo)
    candidate = write_candidate_manifest(client_repo, result)

    console.print(f"[cyan]Recovered a candidate manifest → {candidate.name}[/]")
    detected = sorted(k for k, v in result.context.items() if v is True)
    if detected:
        console.print(f"[dim]Detected features:[/] {', '.join(detected)}")
    console.print(f"[dim]Detected version:[/] {result.version or 'unknown'}")
    for warning in result.warnings:
        console.print(f"[yellow]⚠[/] {warning}")
    console.print(
        f"\nReview it, then `mv {candidate.name} {MANIFEST_FILENAME}` and commit it "
        "before running `upgrade`."
    )
    return candidate


def run_finalize(client_repo: Path) -> str:
    """Promote the pending manifest after a clean, conflict-free resolution."""
    import json

    pending_path = client_repo / (MANIFEST_FILENAME + _PENDING_SUFFIX)
    if not pending_path.exists():
        raise UpgradeError("No pending upgrade found. Run `upgrade` first (nothing to finalize).")

    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    expected_branch = pending.get(_UPGRADE_BRANCH_KEY)
    on_branch = current_branch(client_repo)
    if expected_branch and on_branch != expected_branch:
        raise UpgradeError(
            f"finalize must run on the upgrade branch '{expected_branch}', not '{on_branch}'. "
            f"Check out '{expected_branch}' first, or delete {pending_path.name} to abandon it."
        )

    status = subprocess.run(
        ["git", "-C", str(client_repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    unmerged = [
        ln for ln in status.splitlines() if ln[:2] in ("UU", "AA", "DD", "AU", "UA", "DU", "UD")
    ]
    if unmerged:
        raise UpgradeError(
            "Unresolved merge conflicts remain — resolve them before finalizing:\n"
            + "\n".join(unmerged)
        )

    pending.pop(_UPGRADE_BRANCH_KEY, None)
    from .manifest import atomic_write_text

    manifest_path = client_repo / MANIFEST_FILENAME
    atomic_write_text(manifest_path, json.dumps(pending, indent=2, ensure_ascii=False) + "\n")
    pending_path.unlink()

    to_version = pending["package_version"]
    console.print(f"[green]Finalized — manifest now at v{to_version}.[/]")
    console.print("[dim]Commit the changes and merge the upgrade branch into your main branch.[/]")
    return to_version
