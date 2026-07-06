"""Orchestrator for the ``upgrade`` and ``upgrade finalize`` commands."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

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
    """Materialize the client's committed HEAD into ``dest`` (tracked files only)."""
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "-C", str(client_repo), "archive", "--format=tar", "HEAD"],
        capture_output=True,
        check=True,
    ).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)


def _rename_pairs(metadata: UpgradeMetadata) -> list[tuple[str, str]]:
    return [(r.from_path, r.to_path) for r in metadata.renames]


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

    running = get_generator_version()
    target = to_version or running

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

    if not dry_run:
        assert_clean_worktree(client_repo)

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
        theirs_template,
        metadata,
        with_new_features=with_new_features,
        confirm=(lambda *_: False) if dry_run else confirm,
    )

    work = Path(tempfile.mkdtemp(prefix="fastapi-fullstack-upgrade-"))
    from .render import render_template

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
        for tree in (base_dir, theirs_dir, ours_dir):
            normalize_tree(
                tree,
                generated_at=generated_at,
                format_code=True,
                frontend_node_modules=client_node_modules,
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
            cleanup_store(result.merged_tree)
            return UpgradeOutcome(
                from_version, target, classification, reconcile_report, result, applied=False
            )

        branch = f"template-upgrade/v{target}"
        orig_branch = materialize(result, client_repo, branch=branch, force=force)

        from .normalize import restore_generated_at

        restore_generated_at(client_repo, generated_at)

        pending = build_manifest(theirs_context, package_version=target)
        pending[_UPGRADE_BRANCH_KEY] = branch
        _write_pending(client_repo, pending)

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
        pending_file = MANIFEST_FILENAME + _PENDING_SUFFIX
        console.print(f"[dim]Undo:[/] {undo_command(branch, orig_branch)} && rm -f {pending_file}")

        cleanup_store(result.merged_tree)
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
        shutil.rmtree(work, ignore_errors=True)


def _write_pending(client_repo: Path, manifest: dict) -> None:
    import json

    (client_repo / (MANIFEST_FILENAME + _PENDING_SUFFIX)).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
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
    manifest_path = client_repo / MANIFEST_FILENAME
    manifest_path.write_text(
        json.dumps(pending, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    pending_path.unlink()

    to_version = pending["package_version"]
    console.print(f"[green]Finalized — manifest now at v{to_version}.[/]")
    console.print("[dim]Commit the changes and merge the upgrade branch into your main branch.[/]")
    return to_version
