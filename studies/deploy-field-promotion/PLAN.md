# PLAN — Promote single-field deploy into the package (`deploy_field` gap)

> **Status: Phases 0 + 1 ★ DONE. Phase 2 deferred (and still the right call).** Self-contained brief for a
> fresh session; file:line refs are so you *verify*, not trust.
>
> *Was `HANDOFF_DEPLOY_FIELD_PROMOTION.md` at the repo root; moved here 2026-07-26 in the root-clutter
> cleanup. Its file:line links are now `../../`-relative — verify them against current code before trusting.*
>
> ⚠ **Every file:line below is STALE** — the doc was written against a much older `build.py`. As of the
> Phase-0 pass: `build_mod` is at **:8579** (not 6766) and `_verbatim_donor_id` at **:4926** (not 3965).
> Grep for the symbol, don't jump to the line.
>
> ⚠ **Two claims in this doc were FALSIFIED while implementing Phase 0 — see the Phase-0 section for both.**
> Short version: there is a **fourth** ad-hoc emitter the doc never listed (`coop.py`), and **suggested
> commit step 2 — "delete `build_campaign`'s emit" — is WRONG and must not be done.**

---

## TL;DR

`tools/deploy_field.py` (the edit→deploy→debug-menu dev loop) is a **repo-only script** whose deploy logic never
got promoted into the `ff9mapkit` package. Consequences on a **fresh exe install** (no repo):

1. **Convenience gap:** there is no `ff9mapkit deploy` verb. Only `deploy-campaign` / `deploy-journey`
   ship. A user who authors one `field.toml` can install it *standalone* via `build --out <game>/Folder`
   (documented at [cli.py:426](../../ff9mapkit/ff9mapkit/cli.py:426)) but gets no reversible/iterative loop.
2. **Correctness bug (the important one):** `build_mod` emits a **complete** standalone mod folder —
   DictionaryPatch/BattlePatch/TextPatch/ModDescription + all assets — **EXCEPT `ForkDonorPatch.txt`**.
   That file is written only at deploy time. So `build --out` on a **forked real field** silently drops
   the s24–s33 fork-donor behaviors (overlay occlusion, off-mesh exemptions, scroll binds). It builds,
   boots, and looks subtly wrong with no error. **Novel fields are unaffected.**

The fix is **not** "move 541 lines into the package." `build_mod` already does almost all of it. The plan
is three separable pieces, smallest-first:

- **Phase 0 (correctness, ~10 lines):** make `build_mod` emit `ForkDonorPatch.txt`. Fixes the fork bug for
  `build --out` and every future consumer. **Do this regardless of the rest.**
- **Phase 1 (the `deploy` verb):** a thin `ff9mapkit.deploy.deploy_field()` targeting a *dedicated* folder
  + snapshot revert. Mostly wiring existing functions; mirror `deploy_campaign`.
- **Phase 2 (deferred, optional):** port the *shared-folder surgical merge* (the bulk of deploy_field.py).
  Only needed if installed users must iterate many fields into ONE shared folder like the repo loop does.

---

## Why this was invisible

The toolkit has two homes with different assumptions:
- **Package (the product)** — install-clean, per-user dirs, no repo. Ships via PyPI/`uv`/the exe.
- **Repo checkout (the workshop)** — repo-flavored paths (`backups/`, `tools/scroll_out/`, `.ff9deploy.toml`).

A **dev-loop shim** is a thin wrapper that injects the repo flavor around package logic. `deploy_campaign.py`
is a *true* shim ([tools/deploy_campaign.py:3](../../tools/deploy_campaign.py:3) — "Thin repo shim over
`ff9mapkit.deploy.deploy_campaign`"). `deploy_field.py` is **not** — its whole deploy algorithm lives in the
script, so there's nothing for a subcommand to call. Because development always ran from the repo, the
fresh-install path was never exercised.

---

## The core finding (verify these first)

`build_mod` writes a complete mod folder into `--out`:
- `def build_mod` — [build.py:6766](../../ff9mapkit/ff9mapkit/build.py:6766)
- DictionaryPatch.txt — [build.py:6814](../../ff9mapkit/ff9mapkit/build.py:6814)
- BattlePatch.txt — [build.py:6843](../../ff9mapkit/ff9mapkit/build.py:6843)
- TextPatch.txt — [build.py:6849](../../ff9mapkit/ff9mapkit/build.py:6849)
- ModDescription.xml — [build.py:6865](../../ff9mapkit/ff9mapkit/build.py:6865)
- **ForkDonorPatch.txt — NOT emitted here.** Only `_verbatim_donor_id` helper exists: [build.py:3965](../../ff9mapkit/ff9mapkit/build.py:3965)

~~Three~~ **FOUR** ad-hoc emitters exist *around* `build_mod` (the doc missed one; and they do **not** all
collapse to the Phase-0 emit — see Phase 0 below):
- `build_campaign` — post-build write from `plan.members`: [campaign.py:638](../../ff9mapkit/ff9mapkit/campaign.py:638).
  **KEEP THIS ONE — it is not redundant.** Reason in Phase 0.
- `deploy_field.py` — inline write from `_verbatim_donor_id`: [deploy_field.py:240](../../tools/deploy_field.py:240)
- `merge_dists` (single-folder journey) — concatenates every `*Patch.txt`, incl. ForkDonorPatch:
  [journey.py:1954](../../ff9mapkit/ff9mapkit/journey.py:1954). Its comment names the past bug: *"the bug
  ForkDonorPatch first exposed"* — the same silent-drop, one layer up.
- **`setup_coop_room`** — hardcoded `<field_id> <COOP_DONOR>` write right after its own `build_mod` call,
  under the comment *"build_mod doesn't emit ForkDonorPatch"*: [coop.py:476](../../ff9mapkit/ff9mapkit/coop.py:476).
  That comment is now false — its project is a `write_native_project` fork, so build_mod emits the same
  mapping and coop's write is a redundant (harmless, identical-content) overwrite. Safe to drop; left in
  place in the Phase-0 commit as out-of-scope.

---

## Phase 0 — `build_mod` emits `ForkDonorPatch.txt` ★ DONE (`c942899e`)

**Shipped as planned, plus two things this doc got wrong.** What actually landed:
- `ModLayout.fork_donor_patch` added ([config.py](../../ff9mapkit/ff9mapkit/config.py)) — it did *not*
  already exist.
- The guarded emit in `build_mod`, right after the TextPatch write. Lines are emitted in **project order**
  (matching every other emit in the function), not sorted — `build_mod` already rejects duplicate ids
  upstream, so the doc's `sorted(set(...))` dedupe was unnecessary.
- **NEW, not in this doc: `preserve_existing` needs a foreign-line merge** (`_foreign_donor_lines`, the twin
  of `_merge_foreign_registrations`). `build --out <live folder> --preserve-existing` — the GUI's "Install to
  game" — rewrites the file wholesale, so without it, installing one fork into a folder holding another
  **drops the other's mapping and switches its fork gates off**: the exact bug this phase fixes, one folder
  over. Foreign rows can only reach that write under `preserve_existing`; otherwise the DictionaryPatch
  foreign-registration refusal fires first.
- 4 tests in `test_build.py`: fork emits · novel doesn't · self-mapping (`donor == id`) skipped ·
  `preserve_existing` keeps a foreign row and is idempotent.

### ⚠ FALSIFIED: do NOT delete `build_campaign`'s emit (this doc's commit step 2)
The doc calls it "redundant" and schedules its deletion. **It is not redundant — deleting it regresses
editable campaigns.** `build_mod` derives the donor from each member TOML via `_verbatim_donor_id`, but an
**EDITABLE** member is emitted by `_emit_logic_only_member` ([campaign.py:139](../../ff9mapkit/ff9mapkit/campaign.py:139))
as an art-less stub whose TOML records **no donor key at all** — no `source_field`, no `[verbatim_eb] donor`.
Only `plan.members`' `real_id` knows it. So campaign's set is a strict **superset** of what `build_mod` can
see, and both writes must stay (campaign's runs second and overwrites — harmless). Encoded as a comment at
both call sites.

*Corollary — a real remaining bug, same class, not yet fixed:* an editable campaign member built standalone
via `build --out` still gets no donor line. The clean fix is to have `_emit_logic_only_member` record
`source_field = real_id` (it already sets the donor's `text_block`, and `source_field` is exactly the key
`donor_block_for` / `lint_text_block` expect alongside it). That would also make the two sets equal and
*then* make campaign's emit genuinely redundant.

### ⚠ FALSIFIED: `test_campaign.py`'s fork-donor assert is not an equivalence check
The doc claims it "now exercises both paths = a live equivalence check." It does not: campaign's write
overwrites build_mod's, so the assert only ever sees campaign's output. It is also
`skipif(not _game_ready())` — it needs the install + UnityPy + extracted templates, so in a worktree it
**skips**. Equivalence has to be asserted directly, or not claimed.

<details><summary>Original Phase-0 sketch (superseded by the above)</summary>

**Change:** after the other patch-file writes in `build_mod`,
compute donor lines per project and write the file **guarded on non-empty**:

```python
donor_lines = []
for p in projects:
    fid = p.field.get("id")
    donor = _verbatim_donor_id(p)
    if donor and fid is not None and donor != fid:
        donor_lines.append(f"{fid} {donor}")
donor_lines = sorted(set(donor_lines))          # dedupe across a multi-project build
if donor_lines:                                  # NOVEL fields -> no file (matches campaign's guard)
    layout.fork_donor_patch.write_text(          # or Path(out_root)/"ForkDonorPatch.txt"
        "# ff9mapkit fork-fidelity: <forkId> <donorRealId>\n" + "\n".join(donor_lines) + "\n",
        encoding="utf-8", newline="\n")
```
(Check whether `ModLayout` already has a `fork_donor_patch` property; if not, write to `out_root` directly
like campaign does at [campaign.py:631](../../ff9mapkit/ff9mapkit/campaign.py:631).)

### Safety (analysis done — HIGH confidence as an additive change)
- **No test asserts build_mod's file set or ForkDonorPatch absence.** Searched `test_build*.py`/
  `test_campaign.py` for `iterdir`/`rglob`/`listdir`/set-equality — none.
- Tests touching ForkDonorPatch assert **presence** or hand-write inputs, so none break; they become free
  guardrails: `test_campaign.py:842` (`["30100 300","30101 301"]`), `test_journey_merge.py:83`,
  `test_verbatim.py:95`/`:156`.
- **`deploy_field.py` does NOT glob root `*Patch.txt`** — it computes its own ForkDonorPatch and handles each
  patch file explicitly. The new file lands in the throwaway build temp dir (`rmtree`'d). No interaction.
- **Guard `if donor_lines:`** keeps novel builds byte-identical (protects any `.eb` golden test).
- Stock engine ignores ForkDonorPatch; patched engine is additive → no runtime regression.

### The one residual unknown + how it's neutralized
Not proven by inspection: that `build_mod`'s per-project lines are byte-identical to `build_campaign`'s
`plan.members` lines. **Neutralize by sequencing:**
1. Add the guarded emit to `build_mod`.
2. **Leave `build_campaign`'s emit in place** ([campaign.py:624–633](../../ff9mapkit/ff9mapkit/campaign.py:624)) —
   it runs *after* build_mod and overwrites, so campaign/journey output stays byte-identical regardless.
3. Run the suite. `test_campaign.py:842` now exercises both paths = a live equivalence check.
4. **Only if green**, delete campaign's redundant emit as a *separate* commit.

### Verify Phase 0
```
py -m pytest -n 6 tests/test_campaign.py tests/test_journey_merge.py tests/test_verbatim.py tests/test_build.py
```
Then a manual check: `ff9mapkit build <a verbatim fork>.field.toml --out /tmp/x` → assert
`/tmp/x/ForkDonorPatch.txt` exists with the right `<forkId> <donorId>`; build a **novel** field → assert
**no** ForkDonorPatch.txt.

### New test to add
`build_mod` on a verbatim/native fork emits ForkDonorPatch with the expected line; on a novel field emits
none. (Mirror `test_campaign.py:842`.)

</details>

### How Phase 0 was actually verified (and the worktree trap it walked into)
A **fresh worktree has no `data/` templates**, so the first run of the new tests reported `6 skipped` —
including the two pre-existing `preserve_existing` tests. Green there means nothing (CLAUDE.md §5). The
templates are gitignored and in-tree, so point at the main repo's copy rather than re-extracting:

```bash
FF9MAPKIT_DATA="C:/gd/Dream-World-IX/ff9mapkit/ff9mapkit/data" py -m pytest -n 6 -q
```

With that set the new tests actually execute. The full suite in this worktree still reports **67 failed /
35 skipped / 30 errors** — a pre-existing environment gap (no local `.ff9mapkit-cache/` extract cache),
**not** regressions: the identical counts appear with the change stashed. The meaningful signal is the
delta — `5235 → 5239` passed, exactly the 4 new tests. A true green still has to come from the main repo.

---

## Phase 1 — the `ff9mapkit deploy` verb ★ DONE

**Shipped:** `deploy.deploy_field()` + `default_field_folder()` + `_render_field_revert()`, CLI verb
**`deploy`** with alias **`deploy-field`** (both registered, so the naming question the doc left open is
moot), 9 tests in `tests/test_deploy_field.py` running against a fake game dir under `tmp_path`.

Decisions taken (the doc left these to ask):
- **Verb name:** `deploy`, with `deploy-field` as an argparse alias. No reason to choose.
- **Dedicated folder by default:** yes — `FF9CustomMap-<name>`, keeping the `FF9CustomMap*` family the
  install already stacks. Sanitized, so a field name can't escape the path.
- **`--mod-folder` is allowed but GATED.** Pointed at a folder holding other fields, the wholesale install
  would unregister them, so it ABORTS (`--allow-drop` overrides) — reusing `_regs_wiped` +
  `_wiped_regs_warning`. That is the same rule `build_mod` enforces for `--out`, and it is what keeps
  Phase 2 genuinely deferred rather than half-done.

Two things the sketch got wrong:
- **`_render_folder_revert` could NOT be reused.** It only restores a snapshot; when the deploy CREATES
  the folder there is no snapshot, and it would leave the install in place while reporting success. Hence
  `_render_field_revert`, which removes the folder in that case. Both branches are tested by actually
  running the emitted script.
- **`tools/deploy_field.py` was NOT shrunk to a shim** — deliberately, see below.

Also carried over from `deploy_campaign`: the offline lint gate (`lint_all`, aborts on errors), and the
name / GLOBAL-EventDB-id / text-block-shadow guards run against the BUILT dist.

### Why `tools/deploy_field.py` is still 590 lines (the doc's step 4, NOT done)
The doc assumed the repo script could become a thin shim once the package had `deploy_field()`. It cannot,
yet: the two do genuinely different installs. The package function OWNS a dedicated folder and replaces it
wholesale; the repo script does a **surgical per-id merge into a SHARED folder** (splices BattlePatch /
TextPatch under `//field-<id>` markers, merges DictionaryPatch and MusicMetaData non-destructively, handles
the live Scripts-DLL recompile). That merge is exactly Phase 2. Until Phase 2 lands there is nothing for
the shim to delegate to, so the script stays as-is and the dev loop is untouched.

<details><summary>Original Phase-1 sketch (superseded)</summary>

**Goal:** installed users get a one-command, reversible single-field install. Target a **dedicated** mod
folder (default = the field's own name) so no surgical merge/guards are needed — a fresh folder has nothing
to preserve, so build_mod's complete output IS the correct install (now incl. ForkDonorPatch from Phase 0).

**Add** `deploy_field()` to `ff9mapkit/deploy.py`, mirroring `deploy_campaign`
([deploy.py:153](../../ff9mapkit/ff9mapkit/deploy.py:153)):

```python
def deploy_field(target, *, game=None, mod_folder=None, apply=False,
                 backups_dir, reverts_dir, verbose=True) -> dict:
    # 1. FieldProject.load(target); default mod_folder = the field's name
    # 2. build_mod([proj], <staging>) then install into <game>/<mod_folder> (fresh dedicated folder)
    #    OR build_mod straight into <game>/<mod_folder>
    # 3. snapshot prior folder state -> backups_dir; write revert -> reverts_dir
    # 4. dry-run by default (print plan); --apply to touch the game
```
Reuse existing pieces:
- `_render_folder_revert` (snapshot-restore revert) — [deploy.py:434](../../ff9mapkit/ff9mapkit/deploy.py:434)
- `DeployError` / `_emit` / the `backups_dir`+`reverts_dir` injection pattern from `deploy_campaign`
- ModDescription auto-detect means a fresh folder self-registers into `Memoria.ini` on next launch
  (first deploy of a NEW folder needs one relaunch — note this in output).

**Wire it:**
- CLI subcommand `deploy` (or `deploy-field`) → calls `deploy.deploy_field(..., backups_dir=provision.deploy_backups_dir(), reverts_dir=provision.deploy_reverts_dir())`.
  Register near the other deploy parsers ([cli.py:6318](../../ff9mapkit/ff9mapkit/cli.py:6318)); per-user dirs at
  [provision.py:103](../../ff9mapkit/ff9mapkit/provision.py:103) / [:110](../../ff9mapkit/ff9mapkit/provision.py:110).
- **Shrink `tools/deploy_field.py`** to a thin shim calling the same function with `REPO/"backups"` +
  `tools/scroll_out/` — mirror `tools/deploy_campaign.py` exactly. **But keep the repo-only dev features
  the shim needs** (see Out-of-scope): the sandbox id-forcing, `.ff9deploy.toml` resolution, prior-id
  auto-revert, and menu-reload messaging stay in the shim layer, NOT the package function.

**Decision to make (ask the user):** verb name `deploy` vs `deploy-field`; and whether Phase 1 should default
to a dedicated folder (recommended) or offer `--mod-folder FF9CustomMap` (which pulls in Phase 2's merge).

</details>

---

## Phase 2 — shared-folder surgical merge parity (DEFERRED)

Only if installed users must iterate multiple fields into ONE shared folder like the repo loop. This is the
bulk of `tools/deploy_field.py`. Side-effect inventory (what deploy_field adds on top of `build_mod`):

| Side effect | Source | Deploy-only work | Needed for |
|---|---|---|---|
| scene/`.eb`/`.mes`, Models/Animations/Sounds/CSVs/Abilities/Scripts-DLL/face-atlas | `build_mod` | copy | ✅ already in `build --out` |
| **ForkDonorPatch.txt** | ~~script only~~ `build_mod` | merge into shared file | **Phase 0 ★ DONE** · shared = P2 |
| DictionaryPatch.txt | `build_mod` (complete) | non-destructive merge into shared file | dedicated ✅ · shared = P2 |
| BattlePatch / TextPatch | `build_mod` (complete) | splice under `//field-<id>` markers | dedicated ✅ · shared = P2 |
| MusicMetaData.txt | `build_mod` | merge custom-band entries | dedicated ✅ · shared = P2 |
| backup + revert script | — | snapshot + codegen | Phase 1 |
| Scripts-DLL live-Overload sticky recompile, drift warn, running-game lock handling | — | recompile/guard | P2 nicety |
| guards: text-shadow, id-collision, CSV-shadow (`ff9mapkit.deploystack`) | pkg | run + warn | P2 (only when stacking) |
| sandbox id/name forcing, prior-id auto-revert, `.ff9deploy.toml` | — | in-memory override | **repo-only — never promote** |

The merge primitives already live in the package (`dictpatch`, `deploystack`, `battle.battlepatch.merge_battle_patch`,
`content.itemtext.merge_text_patch`, `sound`, `battle.overload`, `battle.scriptcompile`) — Phase 2 is
orchestration, not re-implementation.

---

## Out of scope (stays repo-only, correctly)
Sandbox id/name forcing, `.ff9deploy.toml` worktree defaults, prior-id auto-revert, menu-reload messaging.
These are dev-loop concerns with no meaning on a single-game install; they live in the `tools/` shim layer.

---

## Adjacent findings (context, not this task)
- **`restore_memoria_dll.py`** has the same gap: install is productized (`setup --install-engine`) but there's
  no `setup --restore-engine`; users are told to hand-copy DLLs. Worth a parallel fix later.
- **`deploy_battle.py`** is the battle twin of this exact gap (`battle-build` exists, no `battle-deploy`).
- Fuller `tools/` reachability audit exists in the conversation that produced this doc — most scripts are
  correctly dev-only (test/calibration/research/regen); the only genuine user-facing gaps are deploy_field,
  deploy_battle, and restore-engine.

---

## Suggested commit sequence
1. ★ **DONE** (`c942899e`) `feat(build): emit ForkDonorPatch.txt from build_mod` + 4 tests.
2. ~~`refactor(campaign): drop redundant post-build ForkDonorPatch emit`~~ — **CANCELLED, it is not
   redundant and dropping it regresses editable campaigns.** See the falsified note in Phase 0. The
   prerequisite, if anyone wants this collapse: first make `_emit_logic_only_member` record
   `source_field = real_id` (which is worth doing on its own — it closes the same standalone-install hole
   for editable members).
3. ★ **DONE** `feat(deploy): ff9mapkit deploy — reversible single-field install into a dedicated folder`.
4. ~~`refactor(tools): deploy_field.py → thin shim`~~ — **BLOCKED ON PHASE 2, not skipped.** The repo script
   does a surgical per-id merge into a SHARED folder; the package function owns a dedicated one. Different
   installs, nothing to delegate to yet. See the Phase-1 note.
5. (later / optional) Phase 2, restore-engine, deploy-battle, and dropping `coop.py`'s now-redundant write.

## Definition of done (Phases 0–1)
- ★ `ff9mapkit build <fork> --out <dir>` produces a correct ForkDonorPatch.txt; novel field produces none.
- ★ `ff9mapkit deploy <field.toml>` installs reversibly with **no repo**; revert restores (or removes) cleanly.
- ⚠ `tools/deploy_field.py` is NOT a shim — correctly, it is blocked on Phase 2. The repo dev loop is
  untouched (the script was not modified at all).
- ⚠ Full suite: **not verifiable in a worktree.** Delta vs the same tree without these changes is clean
  (`5235 → 5250` passed = the 15 new tests; identical 67 failed / 35 skipped / 30 errors, all pre-existing
  environment gaps). **A true green still has to come from the main repo.**
- ⚠ **No in-game playtest yet.** Nothing here changes the repo dev loop, and the fork-gate payoff is only
  observable on a standalone install — worth one confirmation that a `ff9mapkit deploy`'d fork boots with
  its occlusion intact.
