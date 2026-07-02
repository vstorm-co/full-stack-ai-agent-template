# Version Upgrade Tooling — Design Plan

> Status: **PLAN** — no implementation in this PR. This document nails down
> the diff/merge strategy before any code is written.

## 1. Problem

A client generates a project from `fastapi-fullstack` at version **X**, then customizes
it (edits routes, adds business logic, tweaks config). Months later the template is at
version **Y** with new features and fixes. The client wants to pull the new "goodies"
into their live project **without losing their own changes**.

The hard part is classification. Given any file, we must know which of these it is:

1. **Identical** — client's file matches the template → nothing to do.
2. **Client-modified** — client changed it, template didn't → keep the client's version.
3. **Template-modified** — template changed it, client didn't → safe to update.
4. **Both-modified** — both changed it → **conflict**, needs a human.

Plus the structural cases: files **added** by the newer template (new features), files
**removed** by the newer template, and files the client **added** themselves.

## 2. Why a plain 2-way diff is not enough

Diffing "client project" against "latest template output" cannot distinguish case **2**
from case **3**. A line that differs might be a client customization we must preserve, or
a template improvement we want to apply — a 2-way diff looks identical in both. To tell
them apart we need the **common ancestor**: the project as it was *originally generated*.

This is exactly the classic **3-way merge**. The three inputs (the "3 versions" from the
issue discussion):

| Role   | What it is                                                        |
| ------ | ----------------------------------------------------------------- |
| BASE   | template **@ old version X**, rendered with the client's original answers |
| OURS   | the client's current project (their live, customized code)        |
| THEIRS | template **@ new version Y**, rendered with the client's answers   |

`git merge-file BASE OURS THEIRS` (or a patch of BASE→THEIRS applied onto OURS) then gives
correct, automatic behavior for cases 1–3 and clean conflict markers for case 4.

### 2.1 Render-then-diff: how the comparison actually works

We **never** diff the client's project against the raw Jinja template. The template contains
markers like `{% if cookiecutter.use_celery %}` and `{{ cookiecutter.project_name }}`; a
concrete client file contains `Acme CRM` and resolved code. A line-by-line diff between
those two is meaningless — every line "differs" even when it is logically the same file.

Instead we **render first, then diff**. Using the client's saved answers (from the manifest,
§3a, or recovered, §3b) we render the template **twice** — once at the old version, once at
the new — with the **same** answers:

```
client answers  +  template @ vX  (Jinja)  --render-->  BASE    (concrete code)
client answers  +  template @ vY  (Jinja)  --render-->  THEIRS  (concrete code)
client project  (already concrete, on disk)  --------->  OURS
```

After rendering, **none of the three trees contains any Jinja** — all three are plain code,
so a 3-way diff is well-defined. Example:

```python
# template/.../backend/app/main.py  (raw Jinja — never diffed directly)
{% if cookiecutter.use_celery %}
from app.worker import celery_app
{% endif %}
app = FastAPI(title="{{ cookiecutter.project_name }}")
```

With `use_celery = true`, `project_name = "Acme CRM"`, this renders (in both BASE and THEIRS)
to concrete code that lines up with the client's OURS file, so the diff reflects only real
changes.

**Why render with the client's answers, not defaults:** because we reuse the same answers,
every Jinja conditional resolves the same way it did on generation day. BASE therefore has
the **same file set and the same values** as the client's project at birth. That is what
makes the classification sound: any remaining BASE↔OURS difference is *genuinely* the
client's edit, and any BASE↔THEIRS difference is *genuinely* a template change. Rendering
with defaults instead would flip conditionals (wrong feature set) and substitute wrong names,
flooding the diff with false differences.

Consequences handled elsewhere: features the client turned **off** simply don't exist in BASE
or THEIRS, so they're never compared (enabling a new feature is the separate "new subtree"
case in §6.3); and template-side reformatting or variable churn between vX and vY is absorbed
by normalization (§6.1) and context-drift handling (§7).

## 3. The linchpin: reconstructing BASE

To render BASE we need two things about the client's original generation:

1. **The version X** — already recoverable today: the generator stamps
   `generator_version` into the cookiecutter context and the generated `README.md`
   footer contains `v{{ generator_version }}`. Git tags cover every release (0.1.7 → 0.2.14).
2. **The client's cookiecutter answers** (~120-variable derived context) — **NOT persisted
   anywhere in the generated project today.** This is the gap that must be closed.

Solution has a forward half and a backward half.

### 3a. Forward fix — emit an upgrade manifest (make future upgrades trivial)

Add a machine-readable manifest to every generated project, e.g. `.fastapi-fullstack.json`
(mirrors how [`cruft`](https://cruft.github.io/cruft/) uses `.cruft.json`):

```json
{
  "template": "https://github.com/vstorm-co/full-stack-ai-agent-template",
  "generator_version": "0.2.14",
  "generated_at": "2026-07-01T10:00:00Z",
  "commit": "<template git sha or tag>",
  "context": { "...": "the full cookiecutter context used at generation time" }
}
```

- Written by the generator / `post_gen_project.py` hook.
- Records the **full derived context** (not just the raw prompt answers), so BASE and
  THEIRS regenerate deterministically without re-running `ProjectConfig` derivation logic
  that may itself have changed between versions.
- From this point on, every project self-describes and `upgrade` is a clean 3-way merge.

### 3b. Backward fix — recovery for projects generated before the manifest existed

Existing client projects have no manifest. Recovery path:

1. **Version**: parse the `README.md` footer (`v0.2.x`); fall back to asking the user.
2. **Answers**: reconstruct the context via a wizard that is **pre-filled by
   feature-detection** — scan the project for tell-tale evidence and infer flags:
   - `backend/app/worker/` + celery config → `use_celery`
   - `backend/app/rag/` → `enable_rag`, inspect for vector-store backend
   - `frontend/` present → `use_frontend`
   - `backend/app/agents/<framework>.py` → which AI framework
   - …one detector per feature flag.
   The user confirms/corrects the inferred answers, and we write a manifest — after which
   the project is upgraded exactly like a 3a project.

**Recovery is best-effort — a known limitation.** Feature detection reliably recovers
*boolean toggles* (celery on/off) from file presence, but it **cannot** recover *value*
variables that have no structural footprint — `db_pool_size`, `rate_limit_requests`,
`timezone`, `author_name`, `project_description`, pool timeouts, etc. If these are wrong,
BASE mis-renders and **every file containing that value shows a spurious conflict**. Handling:
default such values, **warn the user explicitly** which variables are guessed, and let them
correct the manifest by hand. (A later enhancement could reverse-extract some values by
parsing the client's files, but that is fragile and out of scope for v1.)

## 4. Build vs adopt: `cruft` as the engine

`cruft` already implements 3-way template diffing and updating for cookiecutter templates
(`cruft diff`, `cruft update`, stores `.cruft.json`, applies BASE→THEIRS as a patch onto
OURS with git-style conflict handling). We should **not** reinvent this.

**Division of labour (the agreed model).** We do **not** hand the whole job to cruft as a
black box. Instead:

1. **We own the rendering.** The `fastapi-fullstack upgrade` wrapper renders **two** trees
   from the client's recorded answers — BASE (template @ old version X) and THEIRS
   (template @ new version Y) — exactly as in §2.1.
2. **cruft/git owns the 3-way apply.** We take the client's project (OURS) plus BASE and
   THEIRS and let the merge engine apply the BASE→THEIRS change onto OURS.

The wrapper is therefore responsible for: reading/writing our manifest, resolving
`version → git ref`, feeding the **final derived context** in non-interactively (no
re-prompting), and orchestrating the two renders. The merge engine is responsible only for
the 3-way apply.

**Honest caveat about cruft's role in this model.** Because we render the two versions
ourselves, cruft's headline feature (managing `.cruft.json` + re-rendering) is largely
bypassed — what we actually need from it collapses to "apply a BASE→THEIRS diff onto OURS
with 3-way conflict handling," which plain `git apply --3way` / `git merge-file` already
does. So the **first implementation task is a spike** (Phase 2) that decides whether cruft
earns its place here or whether cookiecutter (render) + git (3-way merge) is simpler. Open
questions the spike must answer:
- Does cruft support our template living in the `template/` **subdirectory** (cookiecutter
  `--directory` style)?
- Can we drive it fully **non-interactively** with the recorded derived context?
- Existing client projects have **no `.cruft.json`** (they were made via `fastapi-fullstack
  create`, not cruft) — can we synthesize/bootstrap one, or is plain git cleaner?

## 5. The `upgrade` command — workflow

```bash
fastapi-fullstack upgrade [PROJECT_DIR] [--to VERSION] [--dry-run]
```

1. **Locate manifest** in `PROJECT_DIR` (or run §3b recovery).
2. **Resolve refs**: old version X (from manifest) and target Y (`--to`, default = latest tag).
3. **Reconcile context & new features** (§7, §7.1): fill drifted/derived variables, prompt
   the client about any new opt-in feature questions, augment the context.
4. **Render BASE**: check out template @ X into a temp worktree, run cookiecutter with the
   recorded context → BASE tree.
5. **Render THEIRS**: same with template @ Y and the augmented context → THEIRS tree.
6. **Apply structural map** (§8): use the maintainer-curated `UPGRADES.yaml` to align renamed
   /moved files between BASE and OURS *before* diffing, so the client's edits follow the file
   to its new path instead of being lost.
7. **Classify** every path via the §6 matrix (BASE vs OURS vs THEIRS).
8. **Report**: grouped summary (auto-updatable / conflicts / new files / removed / new
   migrations / client-only) **plus the breaking-changes & manual-steps digest** accumulated
   between X and Y (§8). `--dry-run` stops here.
9. **Apply**: auto-apply the safe hunks (template-only changes); land the template update on
   a dedicated git branch and let the client resolve conflicts with their normal git tooling
   (§5.1); never touch the excluded set (§6).
10. **Bump manifest** to Y (authored directly, not merged — see §6.2).

### 5.1 Conflict resolution — git branch + merge (start here)

Rather than build custom conflict UX up front, we lean on git — the client's project is
already a git repo and the client already knows their merge tools.

- `upgrade` requires a clean working tree and does its work on a dedicated branch, e.g.
  `template-upgrade/vY`.
- Safe hunks (template changed, client didn't — `A/A/B`) apply cleanly.
- Genuine conflicts (`A/B/C`) are produced via `git apply --3way`, so git computes them from
  BASE/OURS/THEIRS the same way as any merge.
- The client then resolves them with what they already use — the **3-way merge editor** in
  PyCharm / VS Code (`git mergetool`), reviews the whole thing as an ordinary diff/PR, and
  merges into their main branch. Aborting is just `git checkout` away.

This is deliberately the **simplest thing that could work**: cruft already emits `git apply
--3way`-style output, so we write very little. We ship this first and see how it feels in
practice.

**Fallback if this proves inconvenient:** if resolving template conflicts through the IDE
turns out to be awkward (e.g. too many scattered hunks, or clients not comfortable with
merge tooling), we implement our own **interactive hunk-by-hunk wizard** — `git add -p`-style,
prompting only on genuine conflicts, with per-hunk *keep-yours / take-template / edit / skip*
and an "apply to all remaining" escape hatch. That is a larger custom build on top of cruft
(cruft's own apply step stops at `git apply --3way`), so we defer it until the git-native flow
shows it's actually needed.

## 6. File classification matrix (the diff/merge design)

Let `=` mean byte-identical after normalization (§6.1).

| BASE | OURS | THEIRS | Situation                         | Action                          |
| ---- | ---- | ------ | --------------------------------- | ------------------------------- |
| A    | A    | A      | untouched everywhere              | none                            |
| A    | A    | B      | template updated, client didn't   | **apply update** (fast-forward) |
| A    | B    | A      | client customized, template stable| keep client                     |
| A    | B    | B      | both made the *same* change       | keep (already converged)        |
| A    | B    | C      | both changed differently          | **conflict** → markers/report   |
| —    | —    | new    | new file in Y (new feature)       | **add** (if feature applies)    |
| old  | old  | —      | template removed the file         | propose delete                  |
| old  | mod  | —      | template removed, client edited   | **conflict** → ask              |
| —    | new  | —      | client-authored file              | keep, never touch               |

### 6.1 Normalization (reduce false conflicts)

- **Volatile stamped fields** — `generator_version` and `generated_at` are injected into
  `README.md`, `backend/pyproject.toml` **and every `alembic/versions/*.py` file**. Rendered
  as vX in BASE and vY in THEIRS, they would make those files (all 22+ migrations!) diff on
  the stamp alone. Strip/blank these fields in all three trees before comparing.
- Run a formatter on BASE/OURS/THEIRS before comparing, since `post_gen_project.py` formats
  output — otherwise formatting noise masquerades as conflicts. **Use a single pinned
  formatter version for all three trees** (formatting BASE/THEIRS with a newer `ruff`/Prettier
  than the client used would reintroduce formatting-only diffs).
- Normalize line endings and trailing whitespace.

### 6.2 Never-auto-merge / excluded set

- `.env`, `.env.*`, any secrets → **never** read or write.
- Lockfiles (`uv.lock`, `package-lock.json`, `bun.lockb`) → flag only; after the upgrade the
  client must re-run `uv lock` / `bun install` (surfaced as an explicit post-step, since new
  features pull new deps into `pyproject.toml` / `package.json`, which **do** merge normally).
- `.fastapi-fullstack.json` / `.cruft.json` (the manifest) → **excluded from the merge**; the
  tool authors it directly in step 10. Otherwise it always "conflicts" (vX vs vY) every run.
- `.git/`, `node_modules/`, `.venv/`, build artifacts → ignored.
- Binary files → compared by hash only; report, never merge.

### 6.2.1 Alembic migrations (special-cased, not blanket-excluded)

Migrations are append-only history, so a blanket "flag only" is unsafe: the client would
silently miss schema for new features (the template ships 22+ migrations and new versions add
more, e.g. `0021_create_items`, `0022_sync_source_org_scope`).

- **New** migration files in THEIRS (`—/—/new`) → **added automatically** (append-only, safe).
- **Modified** existing migrations → **flag only** for manual review (never auto-merge).
- Client-authored migrations → **never touched**.
- **Warn** when the client has their own migrations whose revision numbers / `down_revision`
  chain could collide with the incoming template migrations — merging can fork the revision
  graph, which the tool cannot safely resolve. The `UPGRADES.yaml` digest (§8) should note
  when a version introduced migrations so the client knows to run `alembic upgrade head`.

### 6.3 Feature-flag-conditional files

420 of 851 template files are Jinja-conditional. A file absent in BASE because a feature was
**off** but present in THEIRS means either (a) the template started emitting it for the
client's existing flags, or (b) the client wants to **enable a new feature** (a whole new
subtree). The command should detect and clearly separate "updates to features you already
have" from "optional new features you could turn on."

## 7. Version-aware rendering & context drift

- Render old versions by checking out the git **tag** into a temp worktree and running
  cookiecutter against that historical template dir.
- **Context drift**: variables get added/renamed/removed between X and Y. When rendering, the
  recorded context may be missing keys the old/new `cookiecutter.json` expects, or contain
  stale keys. Strategy: drop unknown keys, **log the variable-set diff**, and for missing keys
  distinguish two cases (see §7.1): *internal / derived* variables are filled silently from
  that version's `cookiecutter.json` defaults, while *new user-facing feature questions* are
  surfaced to the client instead of being defaulted silently.

### 7.1 New features / new questions introduced between versions

The interesting drift case: vY adds a **brand-new cookiecutter question** that did not exist
in vX — e.g. `enable_deep_research`, `enable_charts`. The client's saved context has no answer
for it, and we genuinely **don't know whether they want the feature**. Silently taking the
default is wrong in both directions: default-off hides a "goody" the client came here for, default-on forces an opt-in feature (new deps, new env vars) on a
client who never asked for it.

**Mechanism:**

1. **Detect new questions.** Diff the *variable set* of vY's `cookiecutter.json` against the
   keys in the client's manifest context. Split the newcomers into:
   - *User-facing feature toggles* — keys that gate an optional feature (the `enable_*` /
     `use_*` family, framework/provider choices). These need a human answer.
   - *Internal / derived / cosmetic* — everything else (derived booleans, defaults that don't
     branch a feature). Filled silently from vY defaults; only logged.
   The split is driven by a small curated allowlist of "these are real user choices" rather
   than guessing — the template already knows which variables are prompts vs derived (see
   `prompts.py` / `cookiecutter.json`).
2. **Ask the client, once, per new feature — using the same Yes/No UX as the main wizard.**
   Reuse the template's existing `questionary`-based helper `_confirm_with_back()`
   (`fastapi_gen/prompts.py`) — a `Yes` / `No` select with `default = Yes if <feature default>
   else No` — rather than a bespoke `[y/N]` prompt, so the upgrade flow feels identical to
   project creation:
   ```
   vY adds a new optional feature since your version (v0.2.5):

   ? Deep Research agent — multi-step web research tool. (enable_deep_research)
   ❯ Yes
     No

   ? Charts / visualization — render charts in chat. (enable_charts)
     Yes
   ❯ No
   ```
   Each question's wording and default come from the same source the main wizard uses, so a
   feature is presented consistently whether at creation or at upgrade time.
   `--accept-new-defaults` / `--reject-new-features` flags skip the prompts for scripted runs.
3. **Record the answer** into the updated manifest, so the decision is remembered and the next
   upgrade never re-asks.
4. **Render THEIRS with the augmented context.** If the client said **yes**, the feature's
   whole subtree now appears in THEIRS and flows through the normal classification (§6) as
   *added* files (`—/—/new`); if **no**, those files simply don't exist in THEIRS and nothing
   is added. Either way it's handled by machinery we already have — the only new part is
   *asking*.

This is what makes "pull the latest goodies" real: new optional features are offered
explicitly, not smuggled in or silently dropped.

## 8. Structural upgrade metadata — `UPGRADES.yaml`

Content diffing alone can't see that a file was **renamed/moved** or a **variable renamed**
between versions — it reads those as unrelated delete+add, which silently loses the client's
edits (a real hole; see §9). So the template repo carries a maintainer-curated, per-version
metadata file, `UPGRADES.yaml`, that records the *structural* facts a diff can't infer.

```yaml
# UPGRADES.yaml — maintained by template authors, one block per release
- version: "0.2.10"
  renames:                       # file/dir moves — used to align BASE↔OURS before diff (§5 step 6)
    - from: "backend/app/core/config.py"
      to:   "backend/app/core/settings.py"
    - from: "backend/app/rag/"           # trailing slash = whole directory
      to:   "backend/app/knowledge/"
  variable_renames:              # cookiecutter context keys renamed between versions
    - from: "use_pgvector"
      to:   "vector_store"       # (with optional value mapping)
  removed:                       # files intentionally dropped by the template
    - "backend/app/legacy_auth.py"
  breaking:                      # surfaced in the upgrade report (§5 step 8)
    - "JWT secret env var renamed SECRET_KEY → AUTH_SECRET_KEY."
  manual_steps:                  # things the tool cannot do for the client
    - "Run `alembic upgrade head` (new billing tables in 0012–0015)."
```

How the tool consumes it:

- **renames** → applied in §5 step 6: before classification, the corresponding files in BASE
  (and OURS) are aligned to the new path, so a template change to `settings.py` merges onto the
  client's edited (formerly) `config.py` instead of appearing as *delete config + add settings*.
- **variable_renames** → feed the §7 context reconciliation so old answers map to new keys.
- **removed** → distinguishes "template deleted this on purpose" (propose delete) from an
  accidental disappearance.
- **breaking** + **manual_steps** → aggregated across every version between X and Y into the
  report digest (§5 step 8), turning the file-merge into a real *upgrade*, not just a diff.

Maintenance cost is real but small and one-directional: authors add one block per release. It
is the single highest-leverage addition, because it converts the most dangerous silent-failure
modes (lost edits on rename, missed manual steps) into explicit, reviewed data. This subsumes
the plain "what's new since your version" idea — the CHANGELOG stays human-facing; `UPGRADES.yaml`
is the machine-actionable counterpart.

## 9. Risks & known limitations

Tracked so reviewers see what is *not* yet fully solved:

1. **Engine still to be validated (§4).** In the agreed "render two versions ourselves" model,
   cruft's role shrinks to a 3-way apply that plain git already does — the Phase 2 spike must
   confirm cruft earns its place (subdir support, non-interactive, no pre-existing `.cruft.json`)
   or we fall back to cookiecutter + git.
2. **Rendering historical versions runs that version's `post_gen_project.py`** — which shells out
   to `uv lock`, `bun install`, `ruff`, `npx prettier` ([post_gen_project.py:605–677](template/hooks/post_gen_project.py:605)).
   We need the hook's *file-removal* logic (to get the right tree for disabled features) but
   **not** its network installs / formatting. Requires a "render-only" hook mode or stubbing —
   non-trivial, and a hard dependency to design before Phase 2.
3. **Recovery can't recover value variables (§3b).** Best-effort + warnings only in v1.
4. **Rename detection depends on `UPGRADES.yaml` being maintained (§8).** If an author forgets a
   rename block, that file falls back to delete+add and the client's edits to it are at risk.
5. **Multi-version jumps** (e.g. 0.1.7 → 0.2.14, 30+ tags) collapse all intermediate changes into
   one diff; correctness relies on the accumulated `breaking`/`manual_steps` digest being complete.
6. **Toolchain requirements at upgrade time**: network access to **PyPI** (both BASE and THEIRS
   templates come from published generator packages — §10; git clone of the template repo is only
   a fallback for unpublished versions), plus a pinned formatter and, for frontend normalization,
   a node/prettier toolchain. **Assumes every release is published to PyPI.**
7. **Testing (Phase 2+).** Needs golden fixtures: (old version) × (synthetic client edits) ×
   (new version) → expected classification, with a case per matrix row (§6) and for volatile-field
   stripping, migration-add, and rename-map application.

## 10. How the command is invoked — `make upgrade` in the generated project

The developer should run the upgrade **from inside their project**, using the project's own
command surface (it already exposes a `Makefile` and a CLI in `backend/cli/commands.py`). But
the upgrade *logic* (clone template, render two versions, 3-way merge, cruft) must **not** be
baked into every generated project — that would bloat each project and freeze the upgrade
engine at generation time. So the project-side command is a **thin shim that delegates** to the
generator tool, fetched fresh:

```makefile
# added to the generated project's Makefile
upgrade:                       ## Pull the latest template improvements into this project
	uvx fastapi-fullstack@latest upgrade .
```

(`uvx`/`pipx` runs the latest published generator without a persistent install; a CLI
subcommand `<project> upgrade` can wrap the same call.)

**This answers "does the developer download the template?" — no, nothing manual.** They run
`make upgrade`; the fetching is automatic. And because **every published version of the
generator bundles its own template snapshot** (`pyproject.toml` force-includes `template` into
`fastapi_gen/template`), *both* versions we need come straight from **PyPI** — no template repo
access, no git, no tags on the developer's machine:

1. **THEIRS** (target version Y) = `uvx fastapi-fullstack@latest` (or `@Y`) → its bundled
   `fastapi_gen/template`.
2. **BASE** (old version X) = `uvx fastapi-fullstack==X` → *that* version's bundled template —
   exactly the one that generated the project.

This is strictly better than cloning the template repo at tag `vX`: it works even when the
template repo is **private** and the developer has no access to it, and it needs only network
access to PyPI. The only requirement is that each release is published to PyPI (a release-process
guarantee). **Git clone of the template repo remains a fallback** for versions not on PyPI.

So the generated project stays lean: it only knows *how to call* the generator; the generator
owns fetching, rendering, and merging. The manifest (`.fastapi-fullstack.json`, §3a) is the only
upgrade-specific artifact the project carries, and it is pure data.

## 11. End-to-end: what a correct upgrade looks like, step by step

**Prerequisite (maintainer side):** a new template version is tagged and released, and its
`UPGRADES.yaml` block (§8) records any renames / breaking changes / manual steps for that
release. Without that block the upgrade still runs, but rename-tracking and the manual-steps
digest degrade (§9.4).

**Developer side — upgrading an existing project:**

1. **Get to a clean git state.** Commit or stash local work; be on a clean working tree. The
   tool refuses to run otherwise (so the upgrade is always reversible via git).
2. **Run the command from the project root:** `make upgrade` (→ `uvx fastapi-fullstack@latest
   upgrade .`). Fetches the latest generator from PyPI (§10).
3. **Tool reads the manifest** `.fastapi-fullstack.json` → old version **X** + the recorded
   answers. (No manifest → best-effort recovery wizard, §3b.)
4. **Resolve target version Y** (latest by default, or `--to X.Y.Z`). THEIRS = the template
   bundled in the just-fetched `@latest`/`@Y` generator; BASE = the template bundled in
   `fastapi-fullstack==X` from PyPI (git-clone fallback only if X isn't published — §10).
5. **Reconcile context & new features** (§7, §7.1): drifted/derived variables are filled;
   for each *new opt-in feature* the tool asks Yes/No in the main-wizard style; answers are
   recorded back into the manifest.
6. **Render BASE and THEIRS** from the (augmented) answers; normalize (strip volatile stamps,
   pinned formatter — §6.1); apply the `UPGRADES.yaml` rename map so edits follow moved files (§8).
7. **Review the report** (`--dry-run` stops here): grouped as *auto-updates / conflicts / new
   files / new migrations / removed / client-only*, plus the **breaking-changes & manual-steps
   digest** accumulated from X→Y.
8. **Apply:** tool creates branch `template-upgrade/vY`, auto-applies safe hunks, **adds new
   migration files**, and leaves genuine conflicts as git 3-way markers (§5.1, §6.2.1).
9. **Resolve conflicts** in your IDE's 3-way merge editor (PyCharm / VS Code); review the whole
   change as an ordinary diff.
10. **Run the flagged post-steps:** `uv lock` / `bun install` (new deps), `alembic upgrade head`
    (new migrations), and any `manual_steps` from the digest (e.g. renamed env vars).
11. **Verify:** run the test suite and the app to confirm nothing broke.
12. **Merge** `template-upgrade/vY` into your main branch. The manifest is now bumped to **Y**,
    so the next upgrade starts cleanly from here.

At the end the project has the new template goodies, the developer's customizations are
preserved (or explicitly reconciled at conflicts), and the manifest records the new baseline
for the following upgrade.
