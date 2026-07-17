# HANDOFF — Promote single-field deploy into the package (`deploy_field` gap)

> **Status:** planned, not started. Self-contained brief for a fresh session. Everything below was
> established by reading the code; file:line refs are so you *verify*, not trust. No code has been written yet.

---

## TL;DR

`tools/deploy_field.py` (the edit→deploy→F6 dev loop) is a **repo-only script** whose deploy logic never
got promoted into the `ff9mapkit` package. Consequences on a **fresh exe install** (no repo):

1. **Convenience gap:** there is no `ff9mapkit deploy` verb. Only `deploy-campaign` / `deploy-journey`
   ship. A user who authors one `field.toml` can install it *standalone* via `build --out <game>/Folder`
   (documented at [cli.py:426](ff9mapkit/ff9mapkit/cli.py:426)) but gets no reversible/iterative loop.
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
is a *true* shim ([tools/deploy_campaign.py:3](tools/deploy_campaign.py:3) — "Thin repo shim over
`ff9mapkit.deploy.deploy_campaign`"). `deploy_field.py` is **not** — its whole deploy algorithm lives in the
script, so there's nothing for a subcommand to call. Because development always ran from the repo, the
fresh-install path was never exercised.

---

## The core finding (verify these first)

`build_mod` writes a complete mod folder into `--out`:
- `def build_mod` — [build.py:6766](ff9mapkit/ff9mapkit/build.py:6766)
- DictionaryPatch.txt — [build.py:6814](ff9mapkit/ff9mapkit/build.py:6814)
- BattlePatch.txt — [build.py:6843](ff9mapkit/ff9mapkit/build.py:6843)
- TextPatch.txt — [build.py:6849](ff9mapkit/ff9mapkit/build.py:6849)
- ModDescription.xml — [build.py:6865](ff9mapkit/ff9mapkit/build.py:6865)
- **ForkDonorPatch.txt — NOT emitted here.** Only `_verbatim_donor_id` helper exists: [build.py:3965](ff9mapkit/ff9mapkit/build.py:3965)

Three ad-hoc emitters exist *around* `build_mod` (all should eventually collapse to the Phase-0 emit):
- `build_campaign` — post-build write from `plan.members`: [campaign.py:624](ff9mapkit/ff9mapkit/campaign.py:624)
- `deploy_field.py` — inline write from `_verbatim_donor_id`: [deploy_field.py:237](tools/deploy_field.py:237)
- `merge_dists` (single-folder journey) — concatenates every `*Patch.txt`, incl. ForkDonorPatch:
  [journey.py:1917](ff9mapkit/ff9mapkit/journey.py:1917). Its comment names the past bug: *"the bug
  ForkDonorPatch first exposed"* — the same silent-drop, one layer up.

---

## Phase 0 — `build_mod` emits `ForkDonorPatch.txt` (DO FIRST)

**Change:** after the other patch-file writes in `build_mod` (~[build.py:6849](ff9mapkit/ff9mapkit/build.py:6849)),
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
like campaign does at [campaign.py:631](ff9mapkit/ff9mapkit/campaign.py:631).)

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
2. **Leave `build_campaign`'s emit in place** ([campaign.py:624–633](ff9mapkit/ff9mapkit/campaign.py:624)) —
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

---

## Phase 1 — the `ff9mapkit deploy` verb (dedicated folder, reversible)

**Goal:** installed users get a one-command, reversible single-field install. Target a **dedicated** mod
folder (default = the field's own name) so no surgical merge/guards are needed — a fresh folder has nothing
to preserve, so build_mod's complete output IS the correct install (now incl. ForkDonorPatch from Phase 0).

**Add** `deploy_field()` to `ff9mapkit/deploy.py`, mirroring `deploy_campaign`
([deploy.py:153](ff9mapkit/ff9mapkit/deploy.py:153)):

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
- `_render_folder_revert` (snapshot-restore revert) — [deploy.py:434](ff9mapkit/ff9mapkit/deploy.py:434)
- `DeployError` / `_emit` / the `backups_dir`+`reverts_dir` injection pattern from `deploy_campaign`
- ModDescription auto-detect means a fresh folder self-registers into `Memoria.ini` on next launch
  (first deploy of a NEW folder needs one relaunch — note this in output).

**Wire it:**
- CLI subcommand `deploy` (or `deploy-field`) → calls `deploy.deploy_field(..., backups_dir=provision.deploy_backups_dir(), reverts_dir=provision.deploy_reverts_dir())`.
  Register near the other deploy parsers ([cli.py:6318](ff9mapkit/ff9mapkit/cli.py:6318)); per-user dirs at
  [provision.py:103](ff9mapkit/ff9mapkit/provision.py:103) / [:110](ff9mapkit/ff9mapkit/provision.py:110).
- **Shrink `tools/deploy_field.py`** to a thin shim calling the same function with `REPO/"backups"` +
  `tools/scroll_out/` — mirror `tools/deploy_campaign.py` exactly. **But keep the repo-only dev features
  the shim needs** (see Out-of-scope): the sandbox id-forcing, `.ff9deploy.toml` resolution, prior-id
  auto-revert, and F6 messaging stay in the shim layer, NOT the package function.

**Decision to make (ask the user):** verb name `deploy` vs `deploy-field`; and whether Phase 1 should default
to a dedicated folder (recommended) or offer `--mod-folder FF9CustomMap` (which pulls in Phase 2's merge).

---

## Phase 2 — shared-folder surgical merge parity (DEFERRED)

Only if installed users must iterate multiple fields into ONE shared folder like the repo loop. This is the
bulk of `tools/deploy_field.py`. Side-effect inventory (what deploy_field adds on top of `build_mod`):

| Side effect | Source | Deploy-only work | Needed for |
|---|---|---|---|
| scene/`.eb`/`.mes`, Models/Animations/Sounds/CSVs/Abilities/Scripts-DLL/face-atlas | `build_mod` | copy | ✅ already in `build --out` |
| **ForkDonorPatch.txt** | script only | emit | **Phase 0** |
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
Sandbox id/name forcing, `.ff9deploy.toml` worktree defaults, prior-id auto-revert, F6-reload messaging.
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
1. `feat(build): emit ForkDonorPatch.txt from build_mod (fixes standalone fork installs)` + new test. Run suite.
2. `refactor(campaign): drop redundant post-build ForkDonorPatch emit (now in build_mod)` — only after (1) green.
3. `feat(deploy): ff9mapkit deploy — reversible single-field install into a dedicated folder`.
4. `refactor(tools): deploy_field.py → thin shim over ff9mapkit.deploy.deploy_field`.
5. (later / optional) Phase 2, restore-engine, deploy-battle.

## Definition of done (Phases 0–1)
- `ff9mapkit build <fork> --out <dir>` produces a correct ForkDonorPatch.txt; novel field produces none.
- `ff9mapkit deploy <field.toml>` installs reversibly on a machine with **no repo**; revert restores cleanly.
- `tools/deploy_field.py` is a thin shim; the repo dev loop (F6/sandbox/worktree) still works unchanged.
- Full suite green: `py -m pytest -n 6`.
