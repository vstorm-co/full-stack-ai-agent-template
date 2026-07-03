"""Reconcile the recorded context with the target template version.

Handles context drift: map renamed variables, and decide what happens to
brand-new feature questions the target version introduced. By default an upgrade
keeps the client's *existing* feature set — new optional features are only reported,
never enabled — so an upgrade never silently becomes a product migration.
Passing ``with_new_features`` prompts Yes/No for each, reusing the main wizard's UX.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .metadata import UpgradeMetadata, VariableRename

_FEATURE_PREFIX = "enable_"

ConfirmFn = Callable[[str, bool], bool]


@dataclass
class ReconcileReport:
    """What reconciliation changed / surfaced, for the upgrade report."""

    variable_renames_applied: list[str] = field(default_factory=list)
    new_features_available: list[str] = field(default_factory=list)
    new_features_accepted: list[str] = field(default_factory=list)


def _template_defaults(template_dir: Path) -> dict[str, Any]:
    data = json.loads((template_dir / "cookiecutter.json").read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def apply_variable_renames(
    context: dict[str, Any], variable_renames: list[VariableRename]
) -> list[str]:
    """Rename context keys (and map values) in place; return applied ``from→to`` labels."""
    applied: list[str] = []
    for vr in variable_renames:
        if vr.from_key in context:
            value = context.pop(vr.from_key)
            if isinstance(value, str) and value in vr.value_map:
                value = vr.value_map[value]
            context[vr.to_key] = value
            applied.append(f"{vr.from_key}→{vr.to_key}")
    return applied


def default_confirm(message: str, default: bool) -> bool:
    """Yes/No prompt reusing the main wizard's helper."""
    from ..prompts import _confirm_with_back

    return bool(_confirm_with_back(message, default=default, allow_back=False))


def reconcile_context(
    context: dict[str, Any],
    target_template: Path,
    metadata: UpgradeMetadata,
    *,
    with_new_features: bool = False,
    confirm: ConfirmFn | None = None,
) -> tuple[dict[str, Any], ReconcileReport]:
    """Return an augmented context ready to render THEIRS, plus a report.

    Args:
        context: The client's recorded context (from the manifest).
        target_template: The target version's template dir (source of new keys/defaults).
        metadata: Composed UPGRADES.yaml metadata for the version range.
        with_new_features: If False (default), new feature toggles are forced OFF and
            merely reported; if True, the client is prompted per new feature.
        confirm: Yes/No callback (defaults to the interactive wizard prompt).
    """
    confirm = confirm or default_confirm
    ctx = dict(context)
    report = ReconcileReport()

    report.variable_renames_applied = apply_variable_renames(ctx, metadata.variable_renames)

    defaults = _template_defaults(target_template)
    new_feature_keys = sorted(k for k in defaults if k.startswith(_FEATURE_PREFIX) and k not in ctx)
    report.new_features_available = new_feature_keys

    for key in new_feature_keys:
        if not with_new_features:
            ctx[key] = False
            continue
        default_on = bool(defaults.get(key, False))
        label = key[len(_FEATURE_PREFIX) :].replace("_", " ")
        if confirm(f"Enable new feature '{label}' ({key})?", default_on):
            ctx[key] = True
            report.new_features_accepted.append(key)
        else:
            ctx[key] = False

    return ctx, report
