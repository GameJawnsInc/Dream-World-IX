# Synthesizing landmasses: what the laws actually forbid (deep dive, 2026-11-08)

The owner asked for a deeper dive into synthesis: the limits and laws, contradictions, over-restrictive constraints,
and new approaches. Method: five readers mapped the law record (182 laws, each tagged engine fact / stock census /
playtest verdict / kit policy / heuristic, with the scope it was MEASURED on vs the scope it is APPLIED to; 75
falsified attempts with what was and was NOT tested). Three analysts then looked for contradictions (23),
over-restrictions (19) and new approaches (17). An adversarial verifier per analyst opened the sources and tried to
refute each finding. Verdicts: 20 supported, 35 partly, 1 refuted, 3 already on record. I re-measured four
load-bearing claims myself (below). Evidence: `evidence/synth-deep-dive/law-maps.json` (the law-scope register) and
`findings-verified.json` (every finding with its verdict, citations and corrected claim).

## The bottom line

**The ban on synthesis is much narrower than the one-line rules say.** The record splits cleanly, as
[`SYNTHESIS-RECONSIDERED.md`](../path-d-new-world/SYNTHESIS-RECONSIDERED.md) already argued:

- **Works, in game:** anything on a LATTICE language or a DECLARED GLOBAL MAP. That covers the coastline outline,
  the cliff profile, grass mains, verbatim meadow stamps, relief, hills, the whole `world-island` verb,
  rotation/spread/rock-height of carries, the de-tilt, quarter-turned carries, ground retiles, and world-river's join
  columns.
- **Fails, every time:** inventing CONTINUOUS-FLOW TEXTURE ORGANIZATION (massif flanks, gore panels, canopy dressing,
  ecotone arrangement), or deforming real bytes PER VERTEX (the bend-carry ribbon, local conforms), or keeping only
  LABELS (the dunes label-stamp).

The defects land on authored JUNCTIONS: feet, seams, aprons. Almost every falsification killed the attempt there,
and several "falsified" verdicts were measured once, on one bench, before the decoded foot laws or the
render/peer gates existed. So the space of lawful new landmasses is bigger than the kit lets you use: the kit's
limits are mostly the largest values anyone tried, not measured failures.

## What I re-measured myself

| Claim | Result |
|---|---|
| Open-ocean room with the x seam counted (the kit already wraps columns) | 3x3: 30 without wrap, **56** with; 4x4: 4 / **19**; 5x5: 0 / **2** |
| Single-lobe islands fail the shape gate at large radius (the outline's turning falls as 1/R) | r60 4/6 clean; **r80 0/6, r100 0/6** (median turn 7.2 and 5.5 deg vs the 8 deg floor; stock is ~22 at every size) |
| A sub-block shift is "different land" (PREFABS.md P0) | **Wrong for the surface.** A framed meadow island shifted 4u or 32u gives identical height and UV at 382 sample points (max diff 4e-16); only the triangle split at block borders moves. A 2u shift (off the lattice) differs (UV 0.46). |
| SYNTHESIS-RECONSIDERED already flags the section 8 "synthetic frame" line | Yes (lines 60-82): "the section 8 line as written forbids the one hybrid that works." Never propagated to CLAUDE.md. |

## Contradictions and stale laws (verified)

Each is "supported" or "partly" after the adversarial pass; the corrected claim is the one stated here.

1. **CLAUDE.md section 8, "real content through a synthetic frame is still synthesis"**, forbids the architecture
   every prefab, Rung F, world-mountain and world-forest use. The two failures it cites WARPED or RELABELLED real
   bytes; a rigid or declared global map is a carry. Suggested wording is in the findings (C1).
2. **THE FORM LESSON is scoped wider than its evidence.** massif_synth ran 8 rounds on ONE r26 grass islet; the
   owner approved the face windows mid-arc, and the arc died at the FOOT, before the band-continuation, lawn-line
   and profile laws existed. The same foot class then beat a CARRIED massif 0 for 12 (R4) until those laws were
   decoded. The texture-organization verdict still stands (the last rounds named stretching and patchwork); the ban
   should read "invented massing with an invented foot", and a face-only round is a fair, risky test, not a closed
   lane (C2, R13).
3. **The terrace-wall refutation is confounded.** Its "banded top" was a cell-key bug (`int(-cz//4)`) later fixed in
   game, and its reference wall's "tile language" was a grouping artifact (uvclass R3). Lesson 2 ("a flat shelf
   bands even under lawful mains") is misattributed; flat elevated shelves are untested (C3, R12).
4. **Normals are engine-inert** (WorldMap Terrain binds no normal), yet `grassland.smooth_normals` and interior.py's
   header still describe them as part of the look (C4). `grassland.py`'s module docstring still says relief was
   retired, while the same file ships the resurrected relief (C5).
5. **Relief is "mutually exclusive" with the relief verbs only in a docstring.** The one enforcement is the hill's
   raw 2.4u y-span guard, which refuses 26% of grass and 92% of desert footprints on a relief island for ambient
   noise, and forest/mountain carves on relief are neither refused nor measured (C6, R1).
6. **S5 convicts lift-with-falloff aprons (0 of 176 stock components)**, yet world-mountain ships exactly that apron on
   every qualified donor and it passes (desert-peak-isle was walked today). S5 was measured as a census but convicted
   on one large-wall bench; restate its scope after a class-labelled foot census of shipped benches (C7).
7. **THE ONE-SITE WORLD LAW** is a dated stock-clearance scan that excluded seam-crossing footprints (columns now
   wrap). The reset re-frees its one site but adds none; a re-run with wrap allowed could find a second (C8, R5, A12).
8. **The open-ocean law probes the STOCK bundle**, so a sink never makes room (PREFABS.md said it would), and room
   comes only from removing kit override files. Its engine half (a dead Terrain override) holds only on ~15
   water-only own-prefab blocks per disc; the rest is kit policy (C9, R6).
9. **WALL-CONTEXT's reason text is wrong for scrub/brush/dunes:** they wear desert's coastal-lawful wall band byte
   for byte; what stock lacks is those GROUNDS reaching a sea crest. The refusal stands on that census, but the
   message and the island.py comment are stale (C10, R11).
10. **The prefab identity covers disc 1 only**; placement also writes disc 4, unfingerprinted, and the qualifying walk
    was on disc 1 (C14). A code gap in P1.
11. **The deformation ceilings are the largest values tried, on Uaho** (x2.0 height, x1.5 spread, from blind stills at
    the default camera), applied unchanged to M.flow donors no one has panel-tested; shrink below 1.0 refuses as
    "untested" (C15, R2, R3).
12. **The dunes size class's "closure proof" used the label-stamp mechanism** later convicted of castellating; a small
    MESH carry is untested, not falsified (C16, R14).
13. **"0 of 13 gates" is cited without its sequel:** once gates rendered pixels and compared against owner-accepted
    peers, 4 of 6 defects were caught offline and the next 3 verdicts passed (C18, R18).
14. **The canopy carry law's stated reason was retracted** (the 28-35 non-affine patches were a vertex-union
    artifact; canopy is tile-scale charts of shared art). Chart-level stamping, the mechanism that rescued meadows, was
    never tried (C21, R15).
15. Smaller: NO-FREE-MESA vs ENDPOINT-GRAMMAR's three closed mesa rings ("free-standing" must mean sea-ringed; C17);
    two grain ceilings (6.6u 3D vs 8.0u plan) with no named population (C23); the "30 windows" figure (C20, R8).
    Refuted: the sea2|sea3 table "disagreement" (coastmorph never tests sea2; R19).

## Over-restrictive constraints, with the cheapest safe test

| Constraint | Why it is over-broad | Cheapest test |
|---|---|---|
| Prefabs snap to whole 64u blocks (mine, P0) | The surface is identical at any 4u shift (measured above); the triangle fingerprint and the block-anchored relief/mountain frames are what force 64u | Anchor the frame at a 4u point, fingerprint the SURFACE (sampled height+uv) plus the placement census; offline |
| Rows don't wrap (edged z) | Kit write policy; the engine wraps z; the incident behind it was dead off-grid labels, which label wrapping also prevents | One r24 mint on the row 19/0 seam, offline gates, then one walk/sail/fly across |
| Room = 30 windows | x-wrap gives 56 (19 4x4, 2 5x5) | A prefab staged across x = 0, fingerprints compared; offline, minutes |
| Shrink < 1.0 refused | "lower is untested"; both registered restrictive predictions (X1, X3) were refuted permissively | uvc_deform at x0.8/0.9 uniform, then one blind still panel |
| Hill guard: raw y-span 2.4u | Guards hill-on-hill with a proxy that cannot tell relief from a hill | Detrended residual over the frame's own relief field; offline positive control on island E |
| Large single-lobe islands refused | The generator's ripple is angular (1/R), not the coast law | Arc-length-scaled ripple (opt-in, new mint version); sweep r60-140 offline |
| Transplant units not in prefabs | Missing measurement, not a hazard (block-local verts; seam relabel byte-identical 6/6) | Stage each unit at two anchors, compare fingerprints |
| Scrub/brush interior refused on islands | Real law is "never at a sea crest"; inside a lawful rim it is unmeasured | Read-only census of distance from those grounds to a coastal crest |

## New approaches, ranked (verified; none falls into the known failure modes as scoped)

**Tier 1: more variety from what is already lawful (no new surface, cheap).**
- **Quarter-turn prefabs (A2).** A 90/180/270-degree turn about a block corner maps the block grid and the 4u lattice
  onto themselves, so no re-mint and no re-clip; mains keep one handedness. world-transplant already quarter-turns
  written stock triangles in game (the comma at 90). Each turn gets its own fingerprint; mirroring stays out.
- **Admit the walked carry units as prefabs (A5, C22):** the comma, reef, terminus pair, beach chain, plus their
  desert/snow ground retiles. Zero minted surface, real coasts and beaches.
- **Real coastline silhouettes (A3).** Feed rotated stock coast rings to `build_landmass(outline=...)`, which
  world-river already uses: bays, hooks and C-shapes that the star-convex blob cannot make, with the proven cliff and
  mains. Needs the frame measured under custom outlines.
- **Seam and 4u room (A9, R4, R8):** 56 windows instead of 30, and finer placement.

**Tier 2: new declared handles (one registered panel each).**
- **Declared shrink (A6)** and **anisotropic spread (A14):** smooth global maps the rock-rigid gate already handles.
  They would let Uaho sit on the r44/r60 grass islands that refused it, and turn 7 massifs into a continuous family.
- **Relief-hosted carries (A7):** a detrended hill guard, carries seated on framed relief; stock features sit on
  regional relief (a calm host is ~10% of stock).
- **A mid-water halo (A13):** a sea3/sea5 marching band (world-water's in-game-proven alphabet) around minted islands;
  only 5 of 23 small stock islands are mostly deep-fronted, which is the only context world-island ships today.
- **Multi-massif ranges (A8):** two rigid carries on one mint, with a guard against seating on the first's apron;
  plus the P4 arrangement search over all of the above.
- **Beaches by cove carry (A4):** generalize world-river's join columns to river-less coves; first census which of
  the 22 stock beach segments close without their whole bay.

**Tier 3: cheaper oracles (the owner walk is the bottleneck).**
- **Blind contact sheets with stock DECOYS (A10):** harness-shot stills of N candidates mixed with K verbatim stock
  islands; the decoys calibrate the owner's flag rate. Plus batched harness rim walks.
- **A calibrated look critic (A11)** on render_gate and the archived verdict corpus, used only to prune and order;
  dropped if held-out AUC < ~0.8 or pure stock scores as a fail.

**Tier 4: genuine falsification bets (register the prediction first; each is FORM-LESSON-exposed).**
- A synthesized FACE on a carried silhouette with a carried foot (R13): the face becomes the only authored variable.
- Canopy chart stamping on a real canopy's own shape (R15).
- A small MESH carry of a dunes lobe (R14).
- The terrace shelf rebuilt with the fixed cell key (R12).

**Rejected (with reasons in the findings):** morphing between two massifs (blends UV charts = synthesizing texture
organization); stock-as-texture reprojection (per-cell Terrain PNGs are clobbered while a loose atlas exists, and
~124 free atlas cells); mirroring carried rock (mains handedness; though stock walls do mirror).

## Recommended order

1. **Fix the record (docs only):** CLAUDE.md section 8's synthetic-frame line and the FORM LESSON scope; the 0-of-13
   sequel in section 7; ONE-SITE as a dated census; the stale docstrings (C4, C5, C10); PREFABS.md's sink and 30-window
   claims (done in this commit).
2. **Close P1's gap:** fingerprint and window-check disc 4 too (C14).
3. **Cheap generator wins, all offline-measurable:** seam room, transplant units as prefabs, quarter turns, 4u
   placement with a surface fingerprint.
4. **The P3 card**, now with turns and seam-aware placement in its handles.
5. **Tier 2 handles**, each behind one registered blind panel; then P4's search over the enlarged space, judged
   through decoy contact sheets.
6. **Tier 4 bets** only when the owner wants a research round.
