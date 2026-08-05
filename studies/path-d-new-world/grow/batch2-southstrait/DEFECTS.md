# Batch-2 playtest defects — forensics + fixes (2026-08-05)

> **★ Both fixes owner-verified in-game same day: "looks good."** c4 approved as the next
> round ("c4 next") — in progress below.

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

- **c4 — the green twin wedge** in `Block[6][10]` (18 tris, cut at x 386.9–397.6, z=−640,
  ~78u² hole). Same cut class, but its hole is flanked by sea4 west / sea3-sea5 east — no
  single band is lawful; needs a 3-band mini-ladder. Reads as part of the horseshoe from
  a distance (green), which is why it wasn't reported.
- **The north frame is structurally off-language**: `Block[6][10]` runs 7 `N|N` tips in a
  row (stock: 0) — a straight crop line cannot be tiled in a language whose transition band
  never runs straight more than one cell. A rim-retile redesign class, not a per-tile fix.
- The north-frame `E`-fold at (7,10)(1,0) sits inside live shore scope (coastnav 53) —
  separate change per the module's own `_near_shore` rule.
- **~115 donor-inherited stale coastnav classes** on (7,10)'s open water (pre-existing
  across the whole carry); `fix_fragment.py --nav-reset full` clears them if wanted.
- c5: a ~1u² floating 2-tri wall sliver on the terrace border — cosmetically invisible.
