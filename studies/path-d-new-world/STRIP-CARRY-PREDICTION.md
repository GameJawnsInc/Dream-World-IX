# STRIP-CARRY — prediction registration (BEFORE building)

2026-07-30, following the profile-carry rung's scored FAIL-on-form (PROFILE-CARRY-
PREDICTION.md), whose pre-declared FAIL branch names this lane. The owner chose it:
whole-mesh strip carry. Written before the first line of the builder; the donor inventory
(`probe_strip_donors.py` → `out/strip_donors.json`) is read-only analysis.

## The claim under test

**Rung F at full depth**: the look survives when the carried unit is the WHOLE MESH —
verts + uvs + tangents, geometry and texture inseparable — and the mint is only the
recomposition. Profile-carry established the finer carrier directly: fringe tiles correlate
with local ledge geometry that any resampling flattens. So nothing is resampled:

- **CARRIED**: three contiguous column-window strips of real wall mesh (topo-49 triangles,
  every vertex/uv/tangent verbatim), from three stock components — blk [22,14] +146.3° over
  47.2u, blk [17,12] +113.2° over 45.7u, blk [14,16] +93.9° over 48.6u (the probe's top
  composition: Σbend 353.4°, closing at R≈22.5u with **+2.2° kink per seam**, vs stock's own
  per-column |turn| median of 24.2°). Each strip: ONE rigid pose (translation + yaw about Y),
  **k = 1.0, no scaling, no per-vertex deformation** — except the declared seam taper below.
- **MINTED**: the recomposition only — three seam welds, the plateau-interior L3 top at the
  carried crest (T1's proven round-3/4 top machinery), and a HOLE cut in the flat bench
  grass under the wall+plateau footprint. The wall meets the ground by BURIAL PIERCE (the
  round-4 mechanism that earned "shape and coherence is better"): the flat 3.2u grass runs
  under the visible face and the carried mesh crosses it; the hole rim hides inside the
  wall body. **There is no apron** — the round-4 "warped/stretched grass" mechanism is
  deleted, not repaired.

Seat: the burial amendment unchanged — all strips crest-anchored at one TOP_Y in the stock
shelf band; drop = min(min column H − 0.3, 15.1); every column H ≥ 12.8u (probe-verified
for all three windows).

Seams: cut points may shift ≤2 columns from the registered windows BEFORE building, solely
so each juxtaposed atlas-column pair has support in the anatomy artifact's h_pairs table
(the decoded tile language serving as a seam-legality ORACLE, not a generator). Seam weld =
snap the incoming strip's boundary loop onto the outgoing loop, displacement ≤1.5u, tapered
to zero across one column. Closure solve distributes the +6.6° residual as ≤25°/seam kinks
(expected ~2°).

Bench: the ring's reach (crest R + measured foot flare + margin) exceeds the radius-40
island, so the bench island is re-minted at radius = ceil(max measured reach + 8), bounded
≤48 — the SAME six blocks, so `backups/terrace-t1-prewall.20260730-203328` remains the
revert point. Declared here, before building.

Why each scored round-4 finding cannot recur by construction: flipped/misplaced fringe
tiles (findings 2+3) — orientation and placement are carried UVs on carried ledge geometry;
stretched base grass (finding 4) — no apron exists; hard tiling (finding 5) — within-strip
adjacency is verbatim stock.

## REGISTERED PREDICTION

**PASS** — the owner reads it as FF9 interior rock wall (no "mess"/"tiling"/"flipped
tiles"/"stretched" class verdicts) within this single round. Basis: every carrier the four
failed rounds localized is now verbatim; the only minted surfaces (seams, top join, pierce
line) are each individually precedented (stock column adjacency gated by h_pairs; the T1
top; the round-4 foot read).

## Falsification semantics — declared in advance

- **FAIL on form** → recomposition itself is the killer: even whole-mesh strips fail when
  RE-COMPOSED, and the wall lane closes to WHOLE-FEATURE CARRY ONLY (carry an entire stock
  terrace verbatim, no compositional freedom) or rests. If the owner's complaint localizes
  to the three SEAMS specifically, record that as partial: strip carry works, seam grammar
  is the missing decode.
- **Plumbing failure** (gates red offline, holes, missing faces) → fix or stop; no verdict.
- **PASS** → the wall rung closes SOLVED at strip granularity: minted-plan walls are
  buildable from carried mesh strips; productization (`world-terrace`) becomes eligible.

One round. Scored on the owner's verdict, whichever way it lands.
