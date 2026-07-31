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

## AMENDMENT (pre-deploy, 2026-07-30): the composition re-derived on a CALIBRATED instrument

Building against the registered composition exposed an instrument fault, not a claim fault:
the probe's nearest-neighbour chains STITCH WALL RUNS FROM DIFFERENT TIERS — blk [22,14]'s
n=14 chain has a 15.8u crest-height spread (the strip builder's mesh dump shows one "cut
loop" spanning y 3.4→37.6), so its +146.3° "bend" was partly tier-noise, not wall-line
curvature; the closure solve on real mesh left a 28.8u gap. Stock's own law (the round-4
amendment: crests are LEVEL per run) is the calibration gate: chains are split at crest
jumps >2.5u and windows searched only on level sub-chains (plan-zigzag sub-chains dropped).

The calibrated pool composes at S=4 (the level pool carries less bend per strip):
**blk [17,12] chain-17 cols [5..14] (+96.5°) + blk [22,14] chain-10 cols [0..7] (+85.5°) +
blk [13,16] chain-19 cols [0..8] (+67.1°) + blk [18,9] chain-12 cols [2..9] (+53.8°)** —
R≈25.3u, mean kink **+14.3°/seam** (still under stock's per-column |turn| median, 24.2°).
Four seams instead of three; the bench island re-mint bound rises to ≤48 (same six blocks).
Everything else — the claim, k=1.0 rigid poses, the seam mechanics, h_pairs gating, the
burial pierce, no apron, the PASS prediction, and the scoring semantics — is unchanged.

## AMENDMENT 2 (pre-deploy, 2026-07-30): MORTAR COLUMNS replace the snap-weld; the seat details

Building exposed that the registered seam model (snap ≤1.5u + taper) assumed cross-sections
are near-coincident y-graphs. Both assumptions are false for real walls: a ledge in a cut
column breaks y-monotonicity, and a battered face leans ~10-12u inward, so a kinked seam
separates matched-y verts by the CORNER WARP (measured 6-16u), not 1.5u. Stock's own answer
is the corner column — one column of quads absorbing the turn. The build mints it
explicitly: **a one-column MORTAR BRIDGE per seam** (the SPUR zip over both strips' REAL
boundary paths, so every cut edge pairs exactly), texture = the outgoing column's tile
continued and LAW-2-mirrored back into its own atlas window, width gated by the mechanistic
warp bound (2·12·sin(kmax/2) + base gap + shape spread). Carried geometry moves ZERO —
strictly less deformation than the registered snap.

Supporting facts fixed under the same pre-deploy line, all instrument/plumbing:
- Cut windows landed at [17,12] 5-14 · [22,14] 1-7 · [13,16] 0-8 · [18,9] 2-9 (within the
  ±2 freedom): [22,14]'s col 0 is a tapered natural end below the burial bar, and its col 8
  swings −55°; the ring order (17,12)→(13,16)→(22,14)→(18,9) and kinks (24.6, 25, 25, 11.8)
  come from the closure solve (gap 1.8u, absorbed by the final mortar's width).
- The strip carries EMBEDDED POCKETS (non-49 tris ≥2-edge-enclosed below the crest) — the
  donor's ledge vegetation is part of the face sheet, and topo-only carry left real holes.
- The bench island re-minted at radius 47 (same six blocks, declared bound ≤48).
- Residual exact-partition slivers (crest tangencies, class-boundary chains) are capped by
  a bounded component capper (≤16 edges, ≤9u, fan-fill); the watertight gate then demands
  ZERO undeclared once-edges, and gets it.
- Root-caused in passing, fixed here and inherited by nothing else yet: the L3 ground
  mapper's cell key must be floor(z/4) (negative), NOT int(−z//4) — the negated key clamps
  fz and collapses u, which is ROUND 3's "banded grass on top" defect. With the fix the
  top L3 seeds from 167 decoded bench cells (previously 0).

The claim, k=1.0 rigid poses, h_pairs gating (all four seams lawful, zero shifts needed
for tiles), the burial pierce, no apron, the PASS prediction, and the scoring semantics
are unchanged.

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
