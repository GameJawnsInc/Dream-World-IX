# Batch-2 playtest defects — forensics + fixes (2026-08-05)

> **★ Both fixes owner-verified in-game same day: "looks good."** c4 approved as the next
> round ("c4 next") — in progress below.

> ⚠ **OPEN — the c4 water fill is visibly stretched (owner in-game, 2026-08-05):** "seems
> weirdly stretched or something" at world ~(390-398, -644..-649), Block[6][10] Sea4.
> Byte-confirmed: the c4 fix's CONTINUE-AFFINE cells (local (4,-7.2)..(8,-9.2) etc., tris
> t236/t237/t230/t231) inherited their UV map from a parent Sea4 tile that is itself a
> donor coast-cut remnant with a skewed affine — the weld made the seam invisible but
> propagated the parent's distortion (measured uv span up to 0.694 over a 4u tri vs the
> lawful ~0.504, u escaping negative to -0.2954). **THE WATER DENSITY GATE** (the permanent
> coast-morph rule that every emitted water tri's density must sit inside the real donor
> envelope) was not in the c4 gate suite, and the rim retile can't repair Sea4 (it plans
> sea3/sea5 only). A fix workflow was launched (re-emit the violating cells through a
> harvested mains map, census the c2 fill + east-wangs conversions for siblings) and
> **STOPPED MID-RUN by the owner before any write** — diagnosis/design only, nothing
> applied, install unchanged. Resume: re-run the density census + fix over Block[6][10]
> Sea4 (and audit Block[7][10]'s c2 fill + the east-wangs Sea4/Sea5 conversions for the
> same class) before the next 9013 session.

## 1. The clipped desert wedge at (473,−643) — FIXED

**Diagnosis (bytes):** the donor's own content — a toe of stock (7,14)'s landmass poking
south across the block border into (7,15), severed flat by the carry rect's north frame.
27 tris (desert-plateau top + wall), and the "pale face" was literally NOTHING: an
11.4u × 3.2u open cut with zero triangles — backface culling shows sea/sky through the
hull in the cut's silhouette. Not a tongue/strip artifact; `--strips auto` behaved.

**Fix (`fix_fragment.py`, applied):** drop the 27 tris; close the water with a two-band
lattice fill split on the z=−644 lattice line (sea5 frame row / sea3 below — the bands both
flanks already carry; sea3 never touches sea4, and no sea3 lands on the frame against the
prefab deep ring). Every uv/normal/tangent byte-harvested from the block's own sheets;
T-vertex neighbour splits; orphaned BELT/KEEL coastnav ring (an invisible boat wall) reset
to open-sea then re-stamped `land-anywhere`. 22 gates green; armed tiles untouched;
`Block[7][10]` Terrain 41→14 tris, Sea3/Sea5 refilled; ledger-recorded.

## 2. The east crop-line missed Wangs at (513,−689)/(513,−760) — FIXED

**Diagnosis (bytes + a 60,689-edge stock oracle):** the east crop severed the donor's
shallow field lengthwise, leaving 1-wide shallow slivers enclosed by deep — a shape stock
NEVER ships (0 deep-enclosed shallow components map-wide; every EW/NS pinch is length 1).
The OPPOSITE-PINCH fold resolved them **unilaterally**; stock's own 5 pinches resolve
MUTUALLY (the neighbour over-paints too), and mid-sliver even the mutual has no tile.
The owner's sentence mapped 1:1 onto the two zero-support bigrams shipped (`ENW|ESW`,
`ESW|ESW`). The seam report was green throughout because it scores tiles against their OWN
geometry, never the neighbour's paint — a gate blind spot, now closed.

**Fix (`fix_eastwangs.py`, applied):** the deep closes over the sliver — 6 cells Sea5→Sea4
(no uv authored; corner-maps harvested from the block's own Sea4 mains by the anti-tiling
rule; positions/normals/tangents carried, so topo + coastnav classes intact). The pure-uv
"mutual over" alternative was measured and rejected (it just mints a different zero-support
pair). East column: contradictions → 0, zero-support verticals 7 → 3 (all benign-agreeing).

**Kit amendment (committed `a62b5e1d`):** `rimretile.edge_disagreements()` +
`unpaintable_slivers()` — the neighbour-facing census the seam report lacked; the CLI now
prints both with world coordinates (on this deploy it names exactly the owner's first
coordinate). 5 hermetic tests; domain suites green (rimretile 20 / transplant 127 / 132+54).

**Composition note:** the fragment fill introduced 1 under-seam the wangs gate caught
(its 22-gate suite lacked the wang census) — resolved by re-running `run_rim_fix.py`
between the two (1→0), then the wangs fix went green. Order for any replay:
fragment → rim → wangs.

## Flagged, NOT fixed (owner's call, each its own round)

- **c4 — FIXED (2026-08-05, `fix_c4.py`):** the twin toe dropped (18 tris) + a 3-band
  lattice ladder (sea4 | sea5 separator at x=392 | sea3 at x=396; the forced cell (2,1)
  was the whole reason one band could not work; the free cell (1,0) decided by the stock
  bigram oracle, min support 24). Three c2-machinery corrections shipped inside it:
  the coastnav orphan proxy replaced by the classifier itself (13 stale classes the
  radius test exonerated), zero repaints of spanning tiles, and THE UV WELD at lattice
  crossings. All gates green incl. the wang census + bigram oracle (nothing introduced);
  Block[6][10] only; armed file untouched.
- **The north frame is structurally off-language**: `Block[6][10]` runs 7 `N|N` tips in a
  row (stock: 0) — a straight crop line cannot be tiled in a language whose transition band
  never runs straight more than one cell. A rim-retile redesign class, not a per-tile fix.
- The north-frame `E`-fold at (7,10)(1,0) sits inside live shore scope (coastnav 53) —
  separate change per the module's own `_near_shore` rule.
- **~115 donor-inherited stale coastnav classes** on (7,10)'s open water (pre-existing
  across the whole carry); `fix_fragment.py --nav-reset full` clears them if wanted.
- c5: a ~1u² floating 2-tri wall sliver on the terrace border — cosmetically invisible.
