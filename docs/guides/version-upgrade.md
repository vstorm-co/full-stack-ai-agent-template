# Upgrading a generated project

Once you generate a project it's *yours* — you edit routes, add business logic, tweak
config. Meanwhile the template keeps improving. The `upgrade` command pulls those
improvements into your existing project **without losing your customizations**, by doing
a real 3-way merge and leaving conflicts for you to resolve in your normal git tooling.

- **You run it from inside your project** (`make upgrade`).
- **Nothing is overwritten silently.** Files only you changed are kept; files only the
  template changed are updated; files both changed are either auto-merged or flagged as a
  conflict for you to resolve.
- **It's always reversible.** The upgrade lands on a dedicated git branch; your history is
  untouched and one command undoes everything.

---

## How it works (in one picture)

An upgrade compares three versions of every file:

| Role   | What it is                                                        |
| ------ | ----------------------------------------------------------------- |
| BASE   | the template at the version you generated from, rendered with your answers |
| OURS   | your current project (your live, customized code)                 |
| THEIRS | the template at the target version, rendered with your answers    |

Rendering both template versions with **your original answers** is what makes the merge
accurate: any BASE↔OURS difference is genuinely *your* edit, and any BASE↔THEIRS difference
is genuinely a *template* change. The tool gets your answers from a small manifest file,
`.fastapi-fullstack.json`, that the generator writes into every new project.

The result is applied to a new branch, `template-upgrade/v<version>`, which you review and
merge like any other change.

---

## Prerequisites

- A **clean git working tree** (commit or stash your work first). The upgrade refuses to run
  otherwise, so it's always reversible.
- Network access to **PyPI** (the tool fetches the template versions from published releases).
- Your project's **Makefile** exposes `make upgrade-dry-run` / `make upgrade` /
  `make upgrade-new-features` / `make upgrade-finalize` (all projects generated with a recent
  template version have these).
- **Frontend projects:** run `bun install` in `frontend/` first. The upgrade normalizes
  formatting with your installed Prettier so template changes to `.ts/.tsx` files merge
  cleanly; without it, frontend files fall back to whitespace-only normalization and may
  show spurious diffs. (You'll get a warning if deps are missing — the upgrade still runs.)

---

## Scenario 1 — a project that has a manifest (the normal case)

Every project generated with a recent template version contains `.fastapi-fullstack.json`.
Check with `ls .fastapi-fullstack.json`. If it's there, follow these steps.

### 1. Start clean

```bash
cd my-project
git status            # make sure the working tree is clean
git checkout -b before-upgrade   # optional: a safety branch
```

### 2. Preview the upgrade (optional but recommended)

```bash
make upgrade-dry-run             # or: fastapi-fullstack upgrade --dry-run
```

This prints a grouped report and changes nothing:

```
Upgrade plan: v0.2.10 → v0.2.14

New files (3)                         ← new features/files the template added
New migrations (auto-added) (1)       ← new Alembic migrations
Auto-updates (template changed, you didn't) (12)
Auto-merged (both changed, merged cleanly) (2)
Kept your changes (template unchanged) (5)
Conflicts (need manual resolution) (1)
Your files (left untouched) (8)       ← files only you created

Manual steps after merge
  • Run `alembic upgrade head` (new migrations were added).
  • Re-run `uv lock` / `bun install` if dependencies changed.
```

### 3. Apply

```bash
make upgrade                     # or: fastapi-fullstack upgrade
```

The tool creates the branch `template-upgrade/v<version>`, applies every safe change, adds
new files and migrations, and leaves any genuine conflicts as standard git conflict markers.
It prints the exact undo command at the end.

To also adopt **new optional features** introduced since your version (off by default — an
upgrade shouldn't silently turn on features you never chose):

```bash
make upgrade-new-features    # prompts Yes/No for each new feature
```

### 4. Resolve conflicts (if any)

Open the conflicted files in your IDE's 3-way merge editor (PyCharm, VS Code, or
`git mergetool`). The markers show your version vs the template's:

```python
<<<<<<< ours          # your version
API_TIMEOUT = 30
=======
API_TIMEOUT = 60      # the template's version
>>>>>>> theirs
```

Resolve, then stage the files:

```bash
git add <resolved-files>
```

### 5. Finalize

```bash
make upgrade-finalize            # or: fastapi-fullstack upgrade finalize
```

This checks the tree is conflict-free and **bumps the manifest** to the new version. (It
refuses to run while conflicts remain — that's the safety net that stops the manifest from
lying about your version.)

### 6. Run the post-steps and merge

```bash
uv lock            # if backend deps changed
bun install        # if frontend deps changed  (run in frontend/)
make db-upgrade    # if new migrations were added
make test          # verify nothing broke
```

Then merge `template-upgrade/v<version>` into your main branch like any PR.

### Undo at any point

```bash
git checkout <your-branch> && git branch -D template-upgrade/v<version>
```

---

## Scenario 2 — a legacy project without a manifest

Projects generated before manifests existed have no `.fastapi-fullstack.json`
(`ls .fastapi-fullstack.json` → not found). The tool can't know the answers they were
generated from, so you first create a manifest, review it, then upgrade as in Scenario 1.

### 1. Reconstruct a candidate manifest

```bash
cd my-legacy-project
fastapi-fullstack upgrade recover
```

This inspects your project's file layout to infer which features are on, reads the version
from the README footer, and writes a **candidate** file, `.fastapi-fullstack.json.candidate`.
It never touches your code and never writes the real manifest — recovery is best-effort:

- It reliably detects **boolean feature flags** (RAG on/off, frontend present, which task
  queue, which AI framework, …).
- It **cannot** recover *value* settings that leave no structural trace — `db_pool_size`,
  `timezone`, `author_name`, `project_description`, ports, the LLM/vector-store choice, etc.
  Those are listed in a warning and left for you to fill in.

### 2. Review and promote the manifest

Open `.fastapi-fullstack.json.candidate`, correct the `package_version` if the detected one
is wrong, and fill in any values the warning flagged (inside the `context` object). The more
accurate the context, the less noise in the upgrade (an inaccurate context makes files look
"changed" when they aren't — safe, but noisy).

When it looks right, promote it and commit:

```bash
mv .fastapi-fullstack.json.candidate .fastapi-fullstack.json
git add .fastapi-fullstack.json && git commit -m "chore: add upgrade manifest"
```

### 3. Upgrade as in Scenario 1

From here your project self-describes — follow **Scenario 1** (`make upgrade` → resolve →
`make upgrade-finalize`). Every future upgrade is a clean, manifest-based run.

> **Tip:** even with a hand-written manifest, expect some files in "Kept your changes" that
> you didn't actually change — that's the residual of an imperfect reconstructed context.
> It's safe (your files are never overwritten); it just means fewer template updates apply
> automatically to those files.

---

## Understanding the report

| Section | Meaning | Action taken |
|---|---|---|
| **New files** | The template added a file you don't have. | Added. |
| **New migrations** | New Alembic migrations. | Added (append-only, safe). Run `make db-upgrade`. |
| **Auto-updates** | The template changed a file you didn't. | Updated to the template's version. |
| **Auto-merged** | Both changed the file, in non-overlapping ways. | Merged cleanly by git. |
| **Kept your changes** | You changed a file the template didn't. | Left as yours. |
| **Already converged** | You and the template made the same change. | Nothing to do. |
| **Conflicts** | Both changed the same lines / added the same file differently. | Left with conflict markers for you. |
| **Your files** | Files only you created. | Never touched. |
| **Removed by template** | The template deleted a file you hadn't changed. | Proposed for deletion. |

---

## What is never touched

The merge always skips these — they're never read, written, or merged:

- **Secrets**: `.env`, `.env.*`
- **Lockfiles**: `uv.lock`, `package-lock.json`, `bun.lock`, `bun.lockb` (re-generate them
  after the upgrade if dependencies changed)
- `.git/`, `node_modules/`, `.venv/`, build artifacts, `__pycache__/`, caches
- `.gitattributes` and git submodules
- The manifest itself (`.fastapi-fullstack.json`) — it's bumped only by `upgrade finalize`

Alembic migrations are special-cased: **new** migrations are added automatically, **modified**
existing migrations are only flagged for review, and your own migrations are never touched.

---

## The manifest — `.fastapi-fullstack.json`

Written into every generated project. It records the generator version and the full set of
answers the project was built from, so upgrades are reproducible. It contains **no secrets**
(secret-shaped values are stripped before writing), so it's safe to commit — and you should
commit it.

```json
{
  "template": "https://github.com/vstorm-co/full-stack-ai-agent-template",
  "template_ref": "0.2.14",
  "package_version": "0.2.14",
  "generated_at": "2026-07-01T10:00:00Z",
  "context_hash": "sha256:…",
  "context": { "project_name": "…", "enable_rag": false, "...": "…" }
}
```

`upgrade finalize` is the **only** thing that bumps `package_version` — and only after a
clean, conflict-free resolution — so the manifest never claims a version you haven't fully
merged.

---

## Command reference

```bash
# from inside the project (Makefile shims)
make upgrade-dry-run               # preview the report, change nothing
make upgrade                       # run the upgrade
make upgrade-new-features          # upgrade + opt into newly added features
make upgrade-finalize              # bump the manifest after resolving

# extra/one-off flags go through ARGS on the plain `upgrade` target:
make upgrade ARGS=--to=0.3.0

# the underlying CLI (run from anywhere with --path, or from the project dir)
fastapi-fullstack upgrade [--path DIR] [--to VERSION] [--dry-run] [--with-new-features] [--force]
fastapi-fullstack upgrade finalize [--path DIR]
fastapi-fullstack upgrade recover  [--path DIR]
```

| Flag | Effect |
|---|---|
| `--dry-run` | Print the report and change nothing. |
| `--to VERSION` | Upgrade to a specific version instead of the latest. |
| `--with-new-features` | Prompt to adopt optional features added since your version (off by default). |
| `--force` | Recreate the `template-upgrade/v…` branch if it already exists. |
| `--path DIR` | Target project directory (defaults to the current directory). |

---

## For template maintainers — `UPGRADES.yaml`

Content diffing can't tell that a file was **renamed/moved** or a cookiecutter **variable
renamed** between versions — it reads those as an unrelated delete + add, which would lose
the client's edits. Record those structural facts in `UPGRADES.yaml` (repo root), one block
per release:

```yaml
- version: "0.2.15"
  renames:                       # file/dir moves — trailing "/" means a whole directory
    - from: "backend/app/core/config.py"
      to:   "backend/app/core/settings.py"
    - from: "backend/app/rag/"
      to:   "backend/app/knowledge/"
  variable_renames:              # cookiecutter context keys renamed between versions
    - from: "use_pgvector"
      to:   "vector_store"
      value_map: { "true": "pgvector" }
  removed:                       # files intentionally dropped by the template
    - "backend/app/legacy_auth.py"
  breaking:                      # surfaced in the upgrade report
    - "JWT secret env var renamed SECRET_KEY → AUTH_SECRET_KEY."
  manual_steps:                  # things the tool can't do for the client
    - "Run `alembic upgrade head` (new billing tables)."
```

- **renames** align the moved file across BASE/OURS before the merge, so a client's edits
  follow the file to its new path instead of being lost.
- **variable_renames** map old answers to new keys during context reconciliation.
- **removed** documents files intentionally dropped, shown in the report so the user knows
  the disappearance was deliberate.
- **breaking** + **manual_steps** are aggregated across every version in the upgrade range
  and shown in the report.

### Recording renames automatically

You don't have to hand-write the `renames` blocks. At release time, run:

```bash
uv run python scripts/record_renames.py            # detect moves and write them
uv run python scripts/record_renames.py --dry-run  # just print the proposed block
```

It fetches the last published template, pairs deletions with additions by content
similarity, and writes the new moves into `UPGRADES.yaml` under the current version. **Review
the diff** — similarity matching can occasionally mis-pair moves, and a wrong rename would
lose client edits. Then add any `breaking` / `manual_steps` / `variable_renames` by hand —
those describe intent a diff can't infer.

A CI guard (`scripts/check_rename_coverage.py`, run by `.github/workflows/rename-guard.yml`)
diffs consecutive releases and **fails the build** if a likely file move has no matching
`renames` entry (or an explicit waiver) — so a forgotten rename can't silently ship. On
failure it prints a ready-to-paste block.

---

## Troubleshooting

**"No `.fastapi-fullstack.json` found … run recovery first."**
Your project predates manifests — follow **Scenario 2**.

**"Working tree has uncommitted changes."**
Commit or stash first. The upgrade requires a clean tree so it stays reversible.

**"Unresolved merge conflicts remain" when finalizing.**
Resolve the remaining conflicts and `git add` them, then run `upgrade finalize` again.

**Lots of files in "Kept your changes" that I didn't change.**
Your manifest context doesn't perfectly match how the project was generated (common after a
Scenario-2 recovery). It's safe — nothing is overwritten — but fewer template updates apply
automatically. Improving the manifest's `context` reduces this.

**The README version footer still shows the old version after upgrading.**
Expected. The render deliberately reuses the original stamp so it doesn't conflict during the
merge; only the manifest is bumped at `finalize`. Update the footer by hand if you rely on it.

**I want to throw the whole thing away.**
`git checkout <your-branch> && git branch -D template-upgrade/v<version>`.
