# THE BENCH WALK SIMULATOR — study B registration (BEFORE building)

2026-08-01. Study A (`WALK-QUERY-DECODE.md`) banked the engine's walk query end to end
— double-verified, all three playtest regimes produced by one code path. This study
implements that algorithm offline over the DEPLOYED bench bytes and is gated by THE
CALIBRATION LAW: **the simulator may not gate any fix until it reproduces the
playtest's defect classes at their loci.** Prior art: `scratch/synth-island/sim_place.py`
(the placement sim, validated in-game 2026-07-07) donates the proven core — winding
convention, barycentric, first-in-order scan; this build corrects its dead-parameter
2.8u drop cap (refuted by the decode) and adds what it lacked: the ring cache, the
deflection fan, the two-probe commit, the mask.

## The claim under test

The decoded algorithm over the live shingle-build bytes shows: (1) stacked-WALKABLE
sheets confined to strips at the carried footprint's boundary (the partial-tri shingle
gap — the model's leading candidate); (2) at least one defect-armed strip (walkable
sheet under a walkable surface with gap > 2.34375, or a scan-order inversion) within
~8u of the owner's pin (434,−542); (3) simulated walkers crossing those strips commit
y BELOW the top walk surface (the sunken/phase class) or fail to climb where the hill
is unreachable (the missed-hill class); (4) the PRISTINE control (backup Terrain
`terrace-strip-prewall.20260731-220001`, same Object/Beach/Sea) shows ZERO
stacked-walkable land points and zero sunken events on the same trajectories.

## Instrument — `walk_sim.py`, engine-exact by construction

- Mesh model: per bench block, the SHIPPED parts in framework registration order
  (Object, Terrain, Beach1, Sea1-5 — BL-6), triangles in stored buffer order
  (`blockmesh_from_ff9mesh` regroups the index buffer verbatim). Stated assumption:
  the runtime-minted WorldDisc registers exactly the shipped components in framework
  order; if calibration fails inexplicably, re-read the s23-s33/s74 loader before
  blaming the data.
- Query: unbounded down-ray from `y + 2.34375`; mapid skip {4078, 4088, 2040};
  geometric winding `ny > 0.1`; 0x31EE veto abandons the whole mesh; first hit in
  mesh-then-triangle order; block ownership by `int(x/64), int(|z|/64)`, no neighbors.
- Ring: 10 slots per walker, probe `(Number+i)%10` (newest, then oldest→), write-back
  only on full-scan hit at `(Number+1)%10`; cached retest FILTER-FREE (no mapid/normal
  test, above-origin still rejects, 0x31EE still vetoes); no invalidation. Walkers
  start with a cold ring and warm it on the approach (the realistic history).
- Movement: candidate at new (x,z) sampled from OLD y; miss → reject; on-foot mask
  {0-7,10-13,16-23,27,28,30,31,32-38,41,42,45,46,52}; deflection fan ±78.75° in 11.25°
  steps (+ before −); two-probe slope-corrected commit (speed 0.4375,
  `num9 = speed²/step3D`); fully failed fan = stall.
- Measurements: (A) a 0.5u two-sheet census over the bench land (x 320-512, z −576..
  −448): every up-facing filter-passing intersection per plan point, stacked-walkable
  points, gap classes, scan-order inversions (first-in-order ≠ topmost); (B) trajectory
  sims through every stacked cluster and through the pin from 12 headings, logging
  SUNKEN (committed y < top walk surface − 0.3), STALL, and pop-up events; (C) the
  pristine control for both; plus a TransportControls.csv presence check (the mask
  override gap).

## Falsification semantics — declared in advance

- **No stacked-walkable points and no order inversions near the pin** → the partial-tri
  shingle-gap candidate is WRONG for the observed spot; re-diagnose from bytes
  (cross-block overhang, ring danging across the deploy, sea-class involvement) before
  any fix design.
- **The pristine control shows defects** → the instrument is broken or the "pristine =
  single-sheet" assumption is false; fix the instrument first — an uncalibrated probe
  falsifies nothing.
- **Census clean but trajectories sink anyway** (or vice versa) → the static picture
  and the dynamic picture disagree; the ring is the suspect — measure before designing.
- Declared freedoms: grid pitch, y-dedup epsilon (0.02), the sunken threshold (0.3),
  the pin radius (~8u). Resolved by measurement, reported with results.
- NOT a fix round. No deploy, no bench mutation; the live bench is READ. The fix gets
  its own registration after this calibrates.

## PREDICTION (registered)

The census finds stacked-walkable strips hugging the carried footprint boundary,
including at the pin; the deepest class sits where the carried surface climbs fastest
off the lawn (gap > 2.34375 within a strip ≈ the sunken spots); trajectories through
the pin sink and through steep-strip zones fail hills; pristine is clean. If the SCAN
ORDER puts kept lawn before carried skirt in the merged Terrain buffer, order
inversions make lawn win even where both sheets are reachable — a static (not just
history-dependent) defect the fix must kill by DELETION, not ordering.

---

## FINDINGS (2026-08-01) — CALIBRATED: the pin reproduced at 0.00u, pristine clean

**Gates: 4/4 PASS.** g1: 4,688 stacked-walkable points. g2: the nearest stacked point
to the pin is AT the pin (0.00u; the registered centroid metric was wrong for a
ring-shaped cluster — declared-freedom resolution: min point distance). g3: 239 SUNKEN
events, median depth 0.89u, max 1.34u — walkers crossing (434,−542) ground at y=3.2
(the lawn) under the carried surface at 4.26, mid-body burial, exactly the playtest.
g4: the pristine control shows ZERO stacked points and ZERO sunken events on the same
trajectories — the instrument's false-positive rate is clean. TransportControls.csv
exists in the mod folder (the sim's hardcoded mask matched behavior; note for reruns).

**The measured defect map** (`out/walk_sim/class_map.png`, probe_walk_map.py):
- **LAWN-UNDER 3,187 pts (~800u²)** — kept lawn below carried skirt. The lawn is
  buffer-EARLIER everywhere it survives (pin: lawn tri#124 vs carried tri#395), so
  **even a cold full scan grounds under the hill: the defect is STATIC, not
  history-dependent.** 382 pts armed (gap > 2.34375, the NE red arc): hills
  unreachable = "some spots miss hills"; the rest (gap 0.3-1.7): grounded inside the
  hill = "you phase into the ground".
- **DEAD-UNDER 1,501 pts** — carried apron dipping BELOW the lawn (rim relaxation).
  Benign by scan order (the lawn wins and is the top), ring-armed only second-order.
- Blocked-under-walkable (rule-f fodder): 1,916 live ≈ 1,919 pristine — the stock
  full-cell-sea idiom, unchanged, not ours to fix.

**The registered prediction scored:** right in KIND (strips at the kept boundary, the
armed class where the skirt climbs fastest, pristine clean, the static order defect),
WRONG in EXTENT — the cut missed roughly HALF the covered lawn (2,558 cut-missed vs
2,872 cut-fired points, probe_shingle_extent.py). Both post-hoc mechanism candidates
REFUTED by measurement: no single radial cutoff separates fired from missed (per-angle
bins overlap: dropped_max 6.3-39.0 vs lawn_under_min 21.4-37.4), and the pin's kept
tri is a plain 4u lattice tile, not a boundary-crosser. **The measured mechanism
class: the east extension's high-ground-only flood (EXT_Y 3.7) makes the carried
boundary a SIEVE — holes and wiggles at triangle scale — and the whole-tri drop rule
(all 3 verts covered + all 3 verts ≥1.2u from EVERY boundary segment) keeps nearly
every lawn tri that touches it.** A patchwork miss in every direction is exactly the
owner's "couldn't track the pattern".

**The fix implication (recorded, NOT designed here):** the invariant is *no walkable
sheet under a walkable sheet* — whole-triangle granularity cannot satisfy it against a
sieve boundary. The fix class is per-triangle CLIPPING of the lawn against the carried
coverage (split at the coverage boundary, delete the covered-below portions; the cut
edge hides under the carried sheet exactly as the shingle class intended), with the
DEAD-UNDER direction (clip the hidden carried under-lawn portions, never the visible
surface) an open design choice. The fix round registers separately and is gated by
THIS simulator: 0 LAWN-UNDER, 0 SUNKEN on trajectories, pristine-class sightlines
preserved.
