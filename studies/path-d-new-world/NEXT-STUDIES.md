# NEXT STUDIES — after the V-shore corner closed (2026-08-02)

The V-shore corner is owner-accepted on both axes (playtest 9 flow, 11 cliff,
12 look). This plans what follows. Written at the close of the arc so the
next session starts from the ledger, not from the transcript.

## Where the six registered study angles landed

| # | Angle | Status |
|---|---|---|
| 1 | THE RENDER GATE | ★ DONE — built, calibrated, then grown four times (close-range owner cameras, texture-flow, peer, blank-paint, T-junction) |
| 2 | VERBATIM COAST-SEGMENT TRANSPLANT | ★ DONE — census → seat → weld → gate pipeline works; it is how the corner's shape was chosen |
| 3 | THE MESHEDIT SUBSTRATE | **OPEN — now P1** |
| 4 | THE ATLAS MAP | ★ DONE — `ATLAS-MAP.md`, and it paid off inside the build (poison/tone validation) |
| 5 | THE FAN-AWARE BOUNDARY LINTER | **PARTIAL — the flow constraint is census-enforced in the study script, not productized. P2** |
| 6 | CURTAIN GRAMMAR II (offset-loop) | ★ DONE — superseded in a better form by THE TUCK REBUILD: measure the island's OWN wall and sweep it, rather than offsetting a loop |

Four closed, two open — and both open ones are **productization**, which is
exactly the right shape of remaining work after a proof.

---

## P0 — THE FOLD-BACK DEBT ★ CLOSED (2026-08-02)

**Measured, not assumed:**
- all **19** `terrace-strip-prewall.*` snapshots are **byte-identical** — the
  root anchor is stable and redundantly stored;
- `full_skirt.py --bench-src <prewall>` reproduces the corner's baseline
  Terrain for (5,7) and (5,8) **byte-identically**;
- the full chain rebuilt **all six bench blocks byte-identical to the live,
  owner-accepted bench** — `bench_pipeline.py check` → FULL REPRODUCTION.

**What changed:**
1. **THE SOURCE SEAM** (`terrace_wall_strip.load_bench(bench_src=)` /
   `BENCH_SRC`). Every bench generator read the live install directly, so the
   only way to exercise one was to mutate the owner's game — the reason the
   whole chain ended up anchored to untracked timestamped backups. The
   generator now runs fully offline against a snapshot. Same law as the
   deploy-target seam in the brief: *pin the path through a seam, never read
   the real file.*
2. **THE BASELINE SEAM** (`$FF9_BENCH_BASELINE`) — the corner builds off the
   REGENERATED bench instead of `...025232` backups that nothing tracks.
3. **`bench_pipeline.py`** — `verify | regen | corner | check | all`: checks
   the anchors, regenerates offline, re-applies the corner, and diffs the
   result against the accepted bench. `bench_manifest.json` records the
   accepted hashes, so any future rebuild that diverges is caught by name.
4. **THE CORNER GUARD** (`terrace_wall_strip.corner_guard`) — wired into
   **all six** bench generators and verified to fire in each. They emit a
   corner-less bench; deploying one silently reverted the corner *and left
   every gate green*. The guard fires immediately after argument parsing,
   before any work, and names the driver to use instead.

**Two findings worth carrying:** the chain also depended on a gitignored
intermediate (`out/rock_tiles.json`) that no manifest listed — regenerable via
`rock_wall_language.py`, and now declared as a prerequisite in the driver. And
my first placement of the guard was **unreachable** (the generators abort at a
pristine assert long before their deploy site) — it tested as "guarded" only
because the script failed for an unrelated reason. *A guard that has not been
observed to fire is not a guard.* → [[feedback-a-check-that-cannot-fail]]

---

<details>
<summary>the original P0 registration (kept for the record)</summary>

**The risk, stated plainly:** every result above lives in study scripts that
edit two live blocks in place. `full_skirt` (the generator that built the
island) still emits the OLD corner. Anyone who regenerates the bench —
including a future session that has read only `CLAUDE.md` — silently reverts
twelve playtests of work, with every gate still green, because the gates run
on whatever is in the blocks.

**The work:**
1. Make the corner spec an INPUT to the generator, not a post-edit: the crest
   polyline (donor window + seat), the tuck-wall sweep, the ear cover, the sea
   cut. `full_skirt` should emit the accepted corner directly.
2. Regenerate the bench from scratch and diff against the live blocks — the
   render gate's six cameras plus the peer/blank-paint/T-junction gates must
   all match. **That diff is the acceptance test for the fold-back.**
3. Only then delete the "do not regenerate the bench" hazard.

**Prediction to register before building:** a from-generator bench reproduces
the accepted corner within the render gate's determinism threshold (0 px at
identical cameras). If it does not, the difference names an operator the study
scripts apply that the generator does not — which is precisely the debt.

</details>

---

## P1 — STUDY ANGLE 3: THE MESHEDIT SUBSTRATE ★ LANDED (2026-08-02)

**Shipped:** `ff9mapkit/ff9mapkit/world/meshedit.py` + `tests/test_world_meshedit.py`
(26 tests, hermetic — synthetic geometry only, no install and no extracted
templates, so they actually RUN in a fresh worktree instead of skipping).

**Every law is provably enforced, not merely documented.** A mutation pass
removed each law from the module in turn and confirmed its test catches it:

| law removed | caught by |
|---|---|
| THE FLOW CONSTRAINT (135 → the falsified 125) | `test_flow_constraint_accepts_the_lawful_window…` |
| THE OVERHANG-CONTEXT LAW (drop the walk-visible check) | `test_sweep_wall_rejects_an_overhang_profile` |
| DENSIFY FIRST (build on the raw chain) | `test_sweep_wall_publishes_rungs_that_cover_the_whole_run` |
| THE BAND WRAP SPLIT | `test_sweep_wall_is_walk_visible_with_the_foot_seaward` |
| A REPAIR THAT IS NOT EXACT IS A HOLE | `test_repair_refuses_a_loose_tolerance…` |
| SCORE AGAINST THE NEIGHBOUR | `test_cover_gap_scores_tone_against_the_neighbourhood…` |

6/6 caught. That table is the point of the exercise — the recurring defect
class here is a check that cannot fail.

**Design:** the atlas/tone-dependent operators take INJECTED validators
(`uv_at`, `is_clean`, `tone`, `ref_tone`, `on_ring`), so the geometry is
testable with no game install — the same seam law that closed P0.

**EQUIVALENCE PROVEN, not asserted:** `vcorner_transplant.py` now consumes
`ME.earclip` and `ME.repair_tjunctions`, and `bench_pipeline check` still
reports **FULL REPRODUCTION** — all six blocks byte-identical to the
owner-accepted bench. Also 578 world tests pass, no regressions.

**Remaining (next session):** `sweep_wall`, `cover_gap` and the seat/census
predicates are landed and tested but the study script still runs its own
copies; wire each through and re-run `bench_pipeline check` for the same
byte-identity proof. `cut_sea_under` is deliberately still out of the module
(it is entangled with per-part world mesh semantics, not pure geometry).

<details>
<summary>the original P1 registration</summary>

Promote the proven operators out of `vcorner_transplant.py` into a tested kit
module (`world/meshedit.py`). They have earned it — each one is now
playtest-validated, and several encode a law that was expensive to learn:

- `segment_census` / `seat_segment` — donor windows by tangent + kink + family
  + flow, and the rigid chord seat. Carries THE JOINT-KINK LAW and THE FLOW
  CONSTRAINT (135°, re-affirmed after a falsified relaxation).
- `sweep_wall(crest, profile)` — the tuck sweep: densify first, mitered foot
  offset, arc-parameterised u with band wrapping, v from height. Carries THE
  OVERHANG-CONTEXT LAW (the profile must come from the neighbours, not stock)
  and THE TEXEL-DENSITY GATE.
- `cover_gap(ring, donors)` — the ear cover: ear-clip, adaptive refinement
  until the atlas footprint is clean, neighbourhood tone matching, dilated
  footprint validation.
- `repair_tjunctions(tris, ext_verts)` — with the hard-won rule that **a
  repair that is not exact is a hole**.
- `cut_sea_under(cover)` — walkable-only cover, pristine-rebuild semantics.

**Unit tests on synthetic meshes** (worktree-safe — no extracted templates, so
they actually run in a fresh worktree; cf. the worktree skip trap). Each law
gets a test that FAILS when the law is removed — otherwise it is a docstring
wish, not a law.

</details>

---

## P2 — STUDY ANGLE 5: ONE GATE COMMAND ★ LANDED (2026-08-02)

**`py terrain_gate.py [staged|live]` — 10 gates, ~30s, one verdict + a JSON
report.** weld · cover · sea · walk (hug both directions / statics / ring-0) ·
latent · flow-uv · blank · **holes** · tjunc · peer.

**Proven end-to-end, not merely assembled.** A real geometric defect was
injected into the staged mesh — one lawn vertex pulled 0.085u, the classic
crack — and the suite went from ALL GREEN to **RED on `holes`**, then restored
(`bench_pipeline check` still FULL REPRODUCTION). That is the first time in
this arc a gate has been *shown* to catch a defect rather than assumed to.

**Two gates had to be CALIBRATED before they could judge — both initially
scored the owner-accepted island as defective:**
- `holes` (new, and it closes a real blind spot: a crack shows SKY, so the
  blank-paint test cannot see it). First version counted any background with
  land above and below — that also describes the sky between two distant
  silhouettes. Now it requires a THIN run (<= 3 px) and is **differential**
  against a recorded baseline (`hole_baseline.json`, 65 px of the bench's own
  silhouette gaps, measured identical on staged and baseline).
- `tjunc` carries `tjunction_allowlist.json`: the two sub-0.0014u residuals
  present when the corner was accepted, each with its reason. Not a blanket
  tolerance — any T-junction not on that list still fails, so a regression
  cannot hide behind it, and a permanently-red gate does not train us to
  ignore it.

**An honest gap this exercise exposed: there is no TONE gate.** The
neighbourhood tone check is a build-time assert, so a patch that is tonally
wrong but otherwise clean would ship. The meadow-patch mutation was caught
only incidentally (by `blank`). → tracked as a task.

Also worth recording: two of my three policy mutations were invalid, not
missed — one targeted a function that the P1 promotion had already replaced
(a no-op), and one no longer reproduces a defect because the other fixes
prevent it. **Check what the mutation actually changed before believing the
result** — the same trap as the unreachable guard in P0.

---

<details>
<summary>the original P2 registration</summary>

Today the gate suite is eight scripts run by hand in an order held in my head.
It should be one command over any terrain change:

    ff9mapkit world verify <blocks> --against baseline

running: walk_sim hug/latent/statics · render at committed cameras + diff ·
texel density · peer comparison vs approved neighbours · blank paint ·
T-junctions vs baseline · texture flow. Fail loud, name the face, save the PNG.

Value is measurable, not speculative: of the last four playtest failures,
three had their root cause visible in a gate that either did not exist yet or
was not wired into the path it was written for.

</details>

---

## P3 — PATH D RUNG 5, THE REST OF THE COAST  ← **next**

The corner is ONE span of ONE island. The pipeline that closed it is now
general (census → seat → tuck sweep → ears → sea cut → gates). Apply it to
the remaining coast, in owner-reviewable batches rather than one big deploy —
the arc's own evidence is that batch size drives defect count.

Open question worth a probe before starting: does the peer gate stay
meaningful once most of the coast is ours? Its power comes from comparing
against approved shore; as the approved fraction shrinks, the reference must
shift to the stock islands rather than this bench.

## P4 — PATH D RUNG 6, ENTRANCE / EXIT

Connect Path D to the rest of the game (`PLAN.md` §3 Rung 6). Untouched by
this arc; unblocked once the coast is stable.

---

## Carry-forward laws (the ones that cost the most to learn)

1. **THE OVERHANG-CONTEXT LAW** — a verbatim stock element can be wrong for
   the context it was torn from. Verbatim is not automatically safe.
2. **THE DEFECT FOLLOWS THE AUTHORSHIP** — held for a third arc. The cheapest
   fix in this whole arc deleted 332 authored triangles.
3. **SCORE AGAINST THE NEIGHBOUR, NOT THE MARGINAL** — the peer gate, the
   neighbourhood tone reference, the baseline T-junction diff. Every gate that
   scored an element in isolation passed a defect the owner then found.
4. **A REPAIR THAT IS NOT EXACT IS A HOLE.**
5. **A FIX IN A FUNCTION THE HOT PATH DOES NOT CALL IS NOT A FIX** — measure
   the output, not the intention.
