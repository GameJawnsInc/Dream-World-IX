# Rung 8 — THE BENCH (the assembly lane)

> Where the four build lanes meet. Contract = [`../STORYBOARD.md`](../STORYBOARD.md) §6.2/§6.3/§6.4;
> deploy = [`../RUNBOOK.md`](../RUNBOOK.md).
>
> **Status: ASSEMBLED + STAGED + 49/49 CHECKS GREEN. Nothing deployed, nothing committed, the live
> install untouched** (`FF9CustomMap/…/SpecialEffects/` still holds only `ef084`, the Thomas/M1b bench).

---

## 1. What is here

| File | What it is |
|---|---|
| **`rung8.field.toml`** | THE BENCH. A strict superset of `rung3-fresh-id/rung3.field.toml`: the same two `[[playable]]` characters and room, plus the `"Nimbra"` ability (§6.2) and the `[[summon]]` block with the whole `[summon.staging]` curve composition (§6.4). Field id 4814 / `MISTBENCH`, deployed to slot **30301**. |
| **`build_rung8_bench.py`** | The rehearsal. Drives the REAL `build_mod` → `emit_overlay` → `mint_song` chain into `../stage/final/`, then re-reads every emitted byte and runs 49 checks. `--clean --check`. |
| **`deploy_rung8_audio.py`** | The one deploy step with no CLI verb (§3). Idempotent; `--dry-run` / `--out` for staging. |
| `art/` | the room's two layer PNGs + Iviv's portrait, copied from rung 3 (see §4). |

```
py studies/custom-summons/rung8-epic/bench/build_rung8_bench.py --clean --check
cd ff9mapkit && py -m ff9mapkit lint ../studies/custom-summons/rung8-epic/bench/rung8.field.toml
```

---

## 2. THE TWO SEAMS THIS ROUND FOUND — both real, both shipped fixed

Neither was visible inside any single lane. Both are the same shape: **a green lane and a green lane can
still meet badly.**

### 2.1 `normalize_spec` was not idempotent for a curve table — *and it broke the real deploy command*

`deploy.deploy()` normalizes the block and hands the **spec** to `emit_overlay`, which normalizes again;
both docstrings promise idempotency. K4 quietly broke it: pass 1 splits `staging = <table>` into
`staging = "curves"` **+** a separate `staging_curves` key, so pass 2 saw a bare `"curves"` string with no
table and raised THE MOVEMENT TRAP refusal.

The nasty part is *which* callers hit it. Every study build script (`build_rung8_stage.py`, and this
lane's first draft) calls `emit_overlay` **directly** and normalizes exactly once — all green. The only
caller that normalizes twice is `deploy()`, i.e. **`ff9mapkit summon-deploy`** — the actual command the
runbook tells the orchestrator to run. So the whole rung could have been "verified" end to end and still
died on the first live deploy, with an error message pointing at the TOML, which was fine.

Found by rehearsing the runbook's own command instead of only the build script's path.
Fixed in `summons/deploy.py:normalize_spec` (adopt an already-split `staging_curves`), regression-tested
in `tests/test_summon_curves.py::test_normalize_spec_is_idempotent_for_a_curve_table` — plus a companion
test that the genuine `staging = "curves"`-with-no-table refusal still fires.

### 2.2 `summon-deploy --from-toml` took relative paths verbatim

`lint` and `build` resolve a `[[summon]]` block's file paths against the TOML's own directory
(`content/summon.py:_path_problems`, `base_dir`). The standalone deploy verbs read the same block and
hand it to `normalize_spec`, which takes paths **as written** — so a block that linted green died at emit
(`model FBX not found`) the moment the caller's cwd was not the TOML's folder. The bench toml lives in
`bench/` and reaches into `../creature/`, so it hit this immediately.

Fixed in `cli._rebase_summon_paths` (relative → the TOML's dir; absolute untouched; the donor
index-selector form of `clips` never mangled), tested in
`test_from_toml_rebases_relative_paths_against_the_toml_dir` and end-to-end on this very toml in
`test_the_bench_toml_block_survives_the_real_from_toml_path`.

### 2.3 …and one shared-directory accident, fixed in place

`build_rung8_stage.py --clean` did `rmtree(stage/)`. But `stage/` is not that lane's private scratch —
the audio lane writes `stage/audio/`, the creature lane writes `stage/creature/`, and this lane writes
`stage/final/`. One `--clean` deleted all three (it did, once: the audio lane's masters, `.ogg`s and
validation report were gone by the time this lane went looking for them). `--clean` now removes only the
four subtrees that script owns, and the sibling lanes survive it — verified.

**Also corrected in passing:** `summon-deploy`'s receipt printed `donor 227` for an authored cast with no
donor at all (the schema default leaking into a human-readable line on a 100 %-original summon). It now
prints `authored cast (no donor)`.

---

## 3. The three lane handoffs, reconciled

| Seam | Contract | State |
|---|---|---|
| **creature → kit (clips)** | the creature lane ships **named** `emerge/drift/strike/driftlook.anim`; `deploy.clip_key_of` mints keys **60000..60003** and `clip_name_map` resolves `play.clip = "emerge"` onto them | ✔ verified on the emitted tree: keys `[60000, 60001, 60002, 60003]`, the manifest playlist reads `60000@1 / 60003@1 / 60002@1 / 60001@1` (RETIMED 2026-07-24 -- STORYBOARD 11.2, clips sized to their beats at Speed 1 per **11.9**), and each file loads under the kit's own `anim_frame_count` (15 / 75 / 30 / 25 frames) |
| **kit → engine (curves)** | `[summon.staging]` is the canonical TABLE form (the storyboard's `staging = "curves"` + table is not expressible in TOML — SEQUENCE-LANE §2.1) | ✔ all three curves span exactly the **110**-tick window; Movement anchors on `TargetAveragePosition*` (THE MULTI-TARGET NULL); playlist **145 ≥ 110** so it never freezes |
| **audio → `.seq` (ids)** | ids **100001/100002/100003** with pinned resource ids `Sounds02/SE00/nimbra_{drone,whispers,strike}` | ✔ the three `SOUND_ID` constants are **imported** from the audio lane's own modules by both bench scripts (never retyped), and the check asserts each id appears as `Sound=<id>` in the staged `.seq` |
| **two clocks** | `PlaySFX` at tick **25** + a **110**-tick manifest window = the instance drains at **135**, which is the tick `WaitSFXDone` was authored to resolve on (§11.2) | ✔ asserted arithmetically against the emitted manifest, not against the prose |
| **ability → effect** | `vfx1 = vfx2 = private_ef` | ✔ read back out of the **built** `Actions.csv`: `Nimbra;195;None(0);AllEnemy(8);0;0;0;0;91;91;85;34;128;0;22;0;24;0;159` (power **34** since the §11.4 re-tune) — and `Bahamut Cinema;194;` is still there, so the live M1b bench binding is untouched |

---

## 4. Deviations from the storyboard (both trivial, both flagged)

1. **`art/` is a copy, not a reference.** §6.3 says the bench is "a copy of `rung3.field.toml`"; the art
   lives in `rung3-fresh-id/art/`. A field toml **cannot** reach outside its own directory — `build.py`'s
   `FieldProject.path()` raises `PathTraversalError` on any `..` that climbs out (a deliberate guard
   against a shared toml reading arbitrary files off the builder's disk). So the three PNGs are copied
   into `bench/art/`. `[[summon]]` paths are **not** subject to that guard and do reach into the sibling
   lanes, which is why nothing else is duplicated.
2. **The bench toml lives in `bench/`, not at `rung8-epic/rung8.field.toml`** as §6.3 writes it — the
   assembly task pinned this folder. Same file, same id, same everything else.

---

## 5. What is NOT proven here

Everything in this folder is **offline**. The 49 checks prove the bytes are the right bytes in the right
places with the right numbers; they cannot prove a single thing about how the cast **looks or feels**.
Nothing in rung 8 is in-game proven yet, including:

- the yaw baseline (R4 — the one knob rung 7 spent two casts on);
- brightness (rung-7 residual b: no battle-actor lighting pass on this path);
- the ~90 concurrent billboards in the gather (R13, unmeasured on this install -- was ~180 before the §11.5 particle re-cut);
- the in-battle `ModelFactory.CreateModel` hitch at `PlaySFX` (R3, scheduled inside the blackout);
- `WaitSFXDone` sitting after the `EffectPoint` pair (R9 — suspect #1 if the cast hangs);
- ~~whether 32.3 s trips the netsync guest freeze cap~~ **retired**: the cast is 9.3 s (STORYBOARD §11.8).

The runbook's §5 phase table and §7 failure table are written to make the first playtest **decidable**
rather than impressionistic. Spend the first cast watching all five phases end to end -- and then **cast twice more**, because the complaint this round answers was a *repeat* complaint.

---

## 6. The suite, and one number that moved

`py -m pytest -n 6` → **4969 passed, 10 skipped** (≈2:20). `-k summon` → **240 passed**, of which **78**
are the rung-8 files (`test_summon_seqlint.py` 38 + `test_summon_curves.py` 40 — 36 from the kit lane,
**4 new** from this one). The audio lane's standalone suite is separate: `py -m pytest
studies/custom-summons/rung8-epic/audio/test_nimbra_audio.py` → **14 passed**.

> **`SEQUENCE-LANE.md` §5 reports `4233 passed, 262 skipped` — that number is stale, and the reason
> matters.** A **fresh worktree has no extracted template cache**, so ~450 byte-level tests silently
> SKIP and 14 files never even collect. That is the documented trap in the repo brief (*"which is how a
> black-screen reached a playtest"*), and it was live in this worktree the whole time the lanes were
> building. Seeded from the main repo's `ff9mapkit/ff9mapkit/data/{blank_field,region_template.bin}` +
> `tests/fixtures/` (all gitignored, install-derived, no re-extraction needed) — after which the field
> build worked at all and the suite runs whole. **Do this before trusting a suite count in a worktree.**
