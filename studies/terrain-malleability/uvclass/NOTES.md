# uvclass: the deformation-tolerance census (disc 1)

**Question.** Which overworld terrain can be moved or stretched without its texture breaking? This lane
classifies every disc-1 Terrain triangle (83,939 tris, 260 blocks) and Object triangle (3,693 tris, 63 blocks)
by how its UV is parameterized. It then measures, for each class, how far stock itself lets that texture stretch.
It also answers the interior knowledge base's open question #1: which highland blocks are murals and which are
tiles.

Everything here is read-only and offline. The raw mesh cache lives outside the repo at
`%TEMP%\ff9_uvclass_cache\`; the folder can be overridden with `$FF9_UVCLASS_CACHE`. Everything under `out/`
is derived statistics or renders.

## Rerun (in this order; about 4 minutes in total)

```
cd C:\gd\Dream-World-IX\studies\terrain-malleability\uvclass
py uvc_features.py terrain     # builds the cache if it is missing, then per-patch features   (~95 s)
py uvc_features.py object
py uvc_census.py terrain       # classes, map, per-family/topo/block tables                   (~3 s)
py uvc_census.py object
py uvc_calibrate.py            # C0-C4: decomposition reproduction, floor, known cases, 8 synthetic controls
py uvc_deform.py               # stock envelopes, carried-uv survival, corner-pin, course, lip u-rate
py uvc_reconcile.py            # R1-R3: the three disagreements with recorded laws, side by side
py uvc_probe_keying.py         # the keying exponent per family
py uvc_probe_flow.py           # flow-uniformity (G-variation) + tile-lattice pin per family
py uvc_probe_charts.py         # per-tri contour/uphill texel rates on the calibration cases
py uvc_probe_light.py          # is shading baked per facing? (reads the atlas read-only, cache=False)
```

The last full run's console output is in `out/full_rerun.log`. Units are Moguri atlas px, `(u*2048, v*4096)`,
the convention every prior UV study uses. In these units mains grass is isotropic at about 31 px/u, and one tile
is about 128 px. Stock UV is quantized to 1/1024, so one step is 2 px in u and 4 px in v.

## The classifier (`uvc_classify.py`)

1. **Patch** = the edge-continuous UV patch. Two triangles join when they share a geometric edge and carry equal
   UVs at both shared endpoints. Stock continuity is exact-or-nothing: the global decomposition gives 17,784 /
   17,643 / 17,447 patches at a UV-match tolerance of 0.5 / 1.5 / 3 quanta, and Uaho's patches are identical at
   every tolerance.
2. **Per-patch features**, fitted on distinct vertices. A fit only counts when it has at least 2 redundant
   points:
   - plan-affine `T=A(x,z)+c`;
   - 3D-affine `T=M(x,y,z)+c`, plus the elevation of its invariant direction;
   - straight wall projection `T=A(s,y)`, with the best horizontal invariant direction;
   - arc-unrolled `T=A(s_arc,y)`, with arclength measured along the patch's own quartic plan curve;
   - a full quadratic fit;
   - a per-4u-cell plan fit;
   - the contour-flow spread;
   - the **keying exponent** κ = −d log(density)/d log(tri size). κ≈1 means the UV window is fixed per vertex
     role whatever the geometry does; κ≈0 means it is projected;
   - **art reuse**: the atlas is gridded at 16 px, and for each cell we count the blocks at least 2 blocks away
     that sample the same texels.
3. **Classes.** TAU = 8 px.
   - **L** (tile-scale chart of reused art: UV extent ≤ 264 px and plan extent ≤ 9u) has three sub-classes:
     **L.rule** when the art lies in a decoded kit vocabulary (grassland GROUNDS mains / desert2 / meadow D /
     B strip / STRIPS), **L.free** when it does not, and **L.keyed**, a larger flat chart with κ ≥ 0.6.
   - **P**: a plan-affine chart larger than one tile, or an oblique 3D-affine chart whose invariant direction is
     ≥ 45° above horizontal. **P.unique** is a tile-scale chart of unique art that is plan-affine.
   - **W**: **W.proj**, **W.arc** or **W.oblique** for a straight, arc-unrolled or low-elevation affine wall
     chart; **W.keyed** for a steep chart with κ ≥ 0.6, i.e. a course or column keyed to vertex roles.
   - **M**: no affine fit and not keyed. **M.smooth** when the quadratic fits, **M.flow** when the texture axis
     follows the contour (spread ≤ 15°), **M.free** otherwise; **M.unique** is tile-scale unique art that is not
     affine.

## Calibration (`uvc_calibrate.py`, `out/calibration.json`)

| check | result |
|---|---|
| C0: Uaho (0,0) decomposition (recorded 9 patches, 47/21/21/12/11/9/7/5/1) | **reproduced exactly**; panel 3D-affine residual p90 14.5-24.3 px, and the 12-tri panel u-p90 40.4 px (recorded "≤25 typical, patch 3 = 40px") |
| C0: forest canopies, edge-union | (19,13) 46 patches, (17,14) 42, (15,15) 32 (the recorded 28-35 used vertex-union: see R1) |
| C1: affine floor on mains grass (15,15) | plan residual p50 0.00 px (multi-cell patches are piecewise: see corner-pin) |
| C3: grass mains (15,15) topo 0 | 95.6% L.rule, 4.1% M.free ✓ |
| C3: (14,13) reference rock wall (476 topo-49 tris) | 64.3% M.flow, 29.6% W.keyed, 3.7% L.free (recorded "tile language": see R3) |
| C3: (15,15) canopy blob | 100% L.free (recorded "non-affine ⇒ M": see R1) |
| C3: Uaho mountain | 77.9% M.free, 12% M.flow, 8.2% L.keyed |
| C4: 8 synthetic controls (plan-projected dome; dome with a 20 px warp; zigzag wall projection; 140° arc unroll; keyed coastal course; reused-decoded, reused-undecoded and unique tile cells) | **8/8 recovered**. The warped dome must FAIL to P and does |
| art-reuse instrument | positive control: Object part (town art) 100% unique (far-reuse 0); negative control: topo-0 grass 1.2% unique (far-reuse p50 113 blocks) |
| facing-light instrument | an injected cosine b=12 @135° is recovered as b=11.94 @137° |

## Results

### Map-wide (Terrain, area-weighted, TAU 8)

- **L 47.9%**: L.rule 34.4, L.free 10.6, L.keyed 2.8.
- **P 1.3%.**
- **W 10.6%**: W.keyed 9.3, W.proj 0.9, W.oblique 0.4.
- **M 40.3%**: M.flow 34.7, M.free 3.5, M.smooth 1.5, M.unique 0.6.

TAU sensitivity (L / P / W / M):

| TAU | L | P | W | M |
|---|---|---|---|---|
| 4 px | 47.9 | 0.8 | 9.7 | 41.6 |
| 8 px | 47.9 | 1.3 | 10.6 | 40.3 |
| 16 px | 47.5 | 3.4 | 14.7 | 34.4 |
| 32 px (a quarter tile) | 45.9 | 8.7 | 24.5 | 20.9 |

L is TAU-independent. The M/W boundary is the soft one.

The Object part is 0 L, 23.7 P (P.unique 21.6), 7.4 W and 69.0 M (M.unique 33.2). Object art is 100% unique.

### The class is a property of the topo FAMILY, almost perfectly (`census_terrain.json` per_family / per_topo)

| family | tris | L | P | W | M | dominant |
|---|---|---|---|---|---|---|
| rock49 | 27,790 | 5.4 | 1.2 | 14.8 | 78.7 | M.flow 71.1, W.keyed 13.5 |
| desert 16-23 | 14,561 | 94.7 | 1.4 | 0.1 | 3.7 | L.rule 78.9 |
| grass 0-3,42 | 11,146 | 93.5 | 1.3 | 0.1 | 5.0 | L.rule 83.3 |
| lip58 | 7,808 | 2.2 | 0.1 | 48.9 | 48.8 | M.flow 48.2, W.keyed 41.5 |
| forest 36/37 | 3,435 | 92.5 | 0.2 | 0.2 | 7.1 | L.free 86.2 |
| canyon 45/46 | 3,333 | 94.7 | 1.8 | 0 | 3.5 | L.free 51.7, L.rule 41.2 |
| plateau 10-12 | 3,188 | 93.3 | 0.5 | 0 | 6.2 | L.rule 88.5 |
| brush38 | 3,119 | 88.7 | 2.5 | 0.2 | 8.6 | L.rule 61.0 |
| snow 27/28 | 2,354 | 90.0 | 2.9 | 0.3 | 6.8 | L.rule 77.9 |
| bldg59 | 2,341 | 37.8 | 5.7 | 14.0 | 42.5 | mixed |
| scrub 4-6 | 1,877 | 98.4 | 0.9 | 0 | 0.7 | L.rule 96.3 |
| dunes41 | 862 | 93.5 | 0.9 | 0 | 5.6 | L.rule 90.7 |
| sand 31-33 | 752 | 74.6 | 7.4 | 5.1 | 12.9 | L.free 72.3 |
| bank62 | 480 | 3.5 | 0 | 40.6 | 55.9 | M.flow 45.9, W.keyed 35.8 |
| shelf13 | 461 | 88.3 | 5.0 | 0 | 6.7 | L.rule 85.7 |
| flat7 | 430 | 98.5 | 0 | 1.1 | 0.4 | L.free 98.5 |

Every walkable ground family is 74.6-98.5% L. Every wall family (49/58/62) is 2-4% L.

### Blocks (`out/class_map_terrain.png` per-tri, `out/class_blocks_terrain.png` per-block stacked bars)

- Per-block M share is p10/p25/p50/p75/p90 = 9.6/17.4/29.0/50.4/69.2%.
- L+P ≥ 90%: 8 blocks: (20,6), (15,15), (18,5), (15,5), (19,4), (14,15), (16,15), (5,7).
- L+P ≥ 80%: 25 blocks. L+P ≥ 50%: 142 blocks.
- **Carry-dominant (M ≥ 50%): 67 blocks**, all listed in `census_terrain.json`. The largest-mass ones are
  (20,15) 89%, (13,4) 82%, (21,11) 81%, (21,13) 80%, (9,0) 80%, (16,13) 79%, (17,4) 78%, (22,14) 77% and
  (12,11) 75%.
- **Open question #1 (murals vs tiles per highland block).** There are 144 blocks with ≥ 20 topo-49 tris.
  Their rock's M share is p10/p50/p90 = 56/81/97%. 75 blocks are mural-rock (M ≥ 80%). Only **10 blocks wear
  ≥ 50% of their rock as keyed courses or tiles**: (18,11), (16,4), (16,1), (14,5), (19,3), (17,5), (16,3),
  (13,18), (6,15) and (15,1). The full list is under `highland_rock_by_block`.

### How far each class stretches (`uvc_deform.py`, `out/deform_envelopes.json`)

Stock envelope per class:

| class | density px/u (p5 / p50 / p95) | anisotropy (p50 / p95) | slope (p50 / p90 / p99) |
|---|---|---|---|
| L.rule | 28.1 / 31.4 / 36.9 | 1.12 / 1.60 | 7.2 / 18.9 / 34.9 |
| W.keyed | 23.1 / 31.0 / 43.1 | 1.43 / 2.17 | 65.2 / 79.3 / 84.7 |
| M.flow | 20.6 / 26.7 / 38.4 | 1.42 / 2.10 | 53.7 / 75.7 / 84.4 |

**Carried-UV survival** is the share of each class's tris whose density and anisotropy stay inside the class's
own stock p1-p99. The baseline is about 97%.

| case | L.rule | L.free | W.keyed | M.flow |
|---|---|---|---|---|
| uniform ×1.1 | 92.7 | 95.2 | 94.7 | 94.5 |
| uniform ×1.25 | **26.0** | 84.2 | 83.6 | 79.5 |
| plan ×1.25 | 26.8 | 78.9 | 89.5 | 87.5 |
| height ×1.5 | 96.8 | 95.8 | 89.8 | 89.9 |
| height ×2.0 | 95.3 | 94.1 | **67.5** | **63.5** |
| height ×0.5 | 97.4 | 75.8 | 81.4 | 84.6 |
| plan shear 0.25 | 96.3 | 95.6 | 96.6 | 96.5 |
| tilt 0.15 | 97.3 | 96.8 | 96.8 | 96.9 |

A rotation about Y cannot leave the envelope.

Other envelope measurements:

- **Plan-law slope envelope** (L.rule + P.chart): p50/p90/p99/p99.9 = 7.2/18.9/35.0/52.2°. Only 0.47% of stock
  plan-law tris are steeper than 40°.
- **THE CORNER-PIN ENVELOPE.** 9,598 L.rule cells carry a tile window's four corners. 4,316 of them sit exactly
  on the 4u lattice. **5,282 carry the full window on corners moved off-lattice**, by a max corner offset of
  p50 0.86 / p90 1.51 / p99 2.0u. That gives a plan texel stretch of p5-p95 0.81-1.41×. Separately, 58% of
  L.rule vertices sit exactly on the lattice.
- **THE COURSE ENVELOPE (W.keyed).** Column width is p5/p50/p95 3.15/4.35/6.07u; face Δy is
  2.08/3.60/5.81u. For lip58 alone: width 3.48/4.39/5.85u, Δy 2.08/2.98/4.69u.
- **Lip along-shore u-rate per tri** (atlas u per world u): p5/p50/p95 = 0.011/0.014/0.020. Only 17.9% fall
  inside 0.0115-0.013.
- **No facing-baked light** (`probe_light.json`). For steep rock-49 the luminance swing with facing azimuth is
  b = 0.85 (mean 103, within-sector std 29, R² 0.0005). For lip58, b = 0.13. For the canopy curtain, b = 0.13.

## LAWFUL DEFORMATIONS PER CLASS (interpretation; numbers above)

| class | pure-Y | XZ translate | rotate about Y | uniform / plan scale | shear / tilt | re-derive UV? |
|---|---|---|---|---|---|---|
| **L.rule** | ✓ to the plan-law slope envelope (p99 35°; the kit warns at 28.6°) | 0-mod-4 exact. Per-vertex jitter ≤ ~1.5u with carried corner UVs is stock-normal (corner-pin) | 90° steps exact. A free angle keeps every tile intact, but the lattice no longer aligns with the host (hypothesis) | **±10% only** (×1.25 → 26%). Beyond that, re-decode | ✓ (≥96%) | ✓ by rule, per centroid cell (ONE-WINDOW-PER-TRI) |
| **L.free** (canopy, canyon, sand, brush, flat7) | ✓ for tops; curtains ×0.5 → 76% | tile travels | ✓ | ×1.1 ✓, ×1.25 84% | ✓ | ✗ (no decoded window rule); charts are ≤ 2×2 cells, so smooth deformation is local-affine (hypothesis) |
| **P** (rare, 1.3%) | ✓ exactly (the carried UV IS the re-projection) | re-project | ✓ | re-project | ✓ | ✓ re-project |
| **W.keyed** (lip, rock courses, bank) | height ×[0.58, 1.61] keeps the course in the stock Δy envelope; ×2 → 67.5% | along-wall moves keeping column width within ×[0.72, 1.39] | ✓ (no baked facing light) | ×1.1 ✓, plan ×1.25 89.5% | ✓ | ✓ re-key per column/course (the kit's arc rule approximates it) |
| **W.proj / arc** | displacement along the wall's horizontal NORMAL is invariant | arc: bending along the contour is isometric | ✓ | ×1.1 ✓ | ✓ | ✓ re-project |
| **M.flow** (rock 71%, lip 48%) | height ×[0.75, 1.5] ≥ 89.9% inside; ×2 → 63.5% | rigid ✓ | ✓ (no baked facing light) | ±10% ✓ (94.5-96.5%), ×1.25 79.5% | ✓ | ✗ (8 falsified synth rounds). Carry with a strain budget |
| **M.free / unique** (Uaho, towns) | as M.flow | rigid | ✓ | ×1.1 ✓ | ✓ | ✗. Carry |

## Engine evidence (C:\gd\FFIX\Memoria\Assembly-CSharp)

- **UV is render-only.** This is stock code: WMBlock.cs, WMPhysics.cs and the WMBlock directory are unmodified
  in the clone, and no patch touches them.
  - `WMBlock.cs:54-84` `AddWalkMesh` stores vertices, triangles, normals and tangents, and recomputes the
    triangle normals from positions (`:64-72`).
  - `WMPhysics.cs:6-22` raycasts on positions plus those normals, skips idall 4078/4088/2040, and filters
    `dot(up,n) ≤ 0.1`.
  - `WMBlock.cs:210` reads the mapid from `tangents[...].x`.
  - No UV read exists anywhere in `Global/WM` or `ff9.cs` (grep).
  - `WMBlock.cs:310-314` binds the material and atlas by sub-mesh name (Terrain → `res(1_24)_terrain.png`).
  - **So a UV change never changes gameplay; every texture law is a look law.**
- **PATCH s34**:
  - `Memoria/World/WorldMeshOverride.cs:229` passes override UVs straight to `mesh.uv`.
  - `WMWorld.cs:831-847` plus `WorldMeshOverride.cs:141-170` (s34, namespace s74) provide a
    **per-cell+part loose PNG texture override**. It clones the material and sets wrap Repeat whenever a mesh
    override exists.
  - That is a lever to RE-BAKE a per-block texture for deformed M content. It is in-game proven for the custom
    ocean only, and **open** for Terrain.

## Kit operators vs the classes

| operator | what it does | verdict against the classes |
|---|---|---|
| `terrain.reshape` (`terrain.py:88`, via `mesh.deform_radial/ridge/flatten_region` `mesh.py:1258-1310`) | pure-Y field, carried UVs; `_walk_gate` (`terrain.py:34`) refuses one-way walls and warns at `MAX_FLANK` 28.6 | Lawful on L/P to about 35°. **Class-blind**: it also stretches any W.keyed or M.flow rock in its radius with no UV gate, and `flatten_region` collapses walls (height → 0). A class-aware warn could reuse this census |
| `interior.build_hill` (world-hill) | pure-Y raised cosine on mains | Lawful (L.rule plan law) |
| `interior.carve_mountain` (world-mountain) | ROCK-RIGID (de-tilt affine + ΔY), exact 90° rotations, UV verbatim, pure-Y apron, per-cell mains zip decode | Respects M and L. Its `MTN_ROCK_RIGID` = 0.035 edge drift is **more conservative** than the measured M.flow envelope (±10% stays ≥ 94.5% inside) |
| `interior.carve_forest` | rigid carry of the canopy | Respects L.free; conservative, since the charts are tile-scale |
| `transplant` (world-transplant), `GroundRetile` (`transplant.py:309`) | 0-mod-4 shifts, 90° rotations, per-class UV translation | Exact for L.rule. Its "free angles / arbitrary shifts strain the tile language" restriction is needed at the HOST SEAM only: inside the carried block, stock already ships off-lattice pinned corners (p99 2.0u) |
| `meshedit.seat_transform` (`meshedit.py:146`) | rotation + uniform plan scale, no shear | Fits W.keyed: plan ×1.1 95.3%, ×1.25 89.5% |
| `meshedit.sweep_wall` / `terrain._apply_cliff_rock_uvs` | constant-density arc dialect (URATE 0.012643 / 0.0125) | A third, lawful dialect (in-game accepted). Stock's keyed columns instead vary density as 1/width |

## Contradictions with recorded knowledge (located, not asserted: `uvc_reconcile.py`, `out/reconcile.json`)

- **R1. The CANOPY "non-affine" verdict** (interior KB forest chapter: "28-35 multi-tri continuity patches,
  non-affine, plan-affine max err ~0.15"; from `forest_uv_components.py`) is an artifact of VERTEX-union.
  - That script unions tris that share ONE vertex with equal UV.
  - Rebuilt on the same bytes: (19,13) gives 35 vertex comps vs 46 edge patches. Each big vertex comp contains
    2-7 edge patches and has a residual of about 155-234 px. The edge patches have plan residuals of 1.6-28 px,
    and some are exact.
  - The canopy is tile-scale charts (≤ 2×2 cells) of shared art (far-reuse 37 blocks), classified 100% L.free.
  - The CANOPY CARRY LAW (carry the layout) still stands. The non-affinity claim does not.
- **R2. BAKED-TERRAIN "hand-painted murals"** (coast memory LAW INDEX; `transplant.py:1941-1949`, "topo 49 97%
  UNIQUE per-cell UV").
  - The kit's own `_cell_rect` metric (`transplant.py:928`) reproduces 98.4% for topo 49.
  - But the same metric flags **43.1% of plain topo-0 grass and 62.1% of topo-17 desert mains** as baked-unique.
    It fails its negative control.
  - Measured as ART, rock is far-reused at p50 31 blocks, with only 3.6% unique art (Objects, the positive
    control, are 100% unique).
  - So the "murals" are hand-placed flow charts over a SHARED rock swatch, not one-off paintings. The refusal
    outcome stands, but for a different reason: non-affine, unkeyed flow.
- **R3. The (14,13) wall "TILE LANGUAGE, not a mural ... one 128px tile per wall quad"** (interior KB
  plateau-edge / rock-wall language).
  - 77.9% of the wall's 670 interior edges are UV-continuous.
  - 67.4% of those continuous edges join tris in DIFFERENT 128 px tiles.
  - 92% of its tris sit in continuous charts spanning ≥ 4 tiles.
  - `rock_wall_language.py`'s ≤ 1-rect grouping guard cut continuous charts at the tile lines by construction.
  - Agreement: 29.6% is genuinely keyed one-tile-per-quad course. The bulk is a Uaho-style band sweep. This is
    consistent with the in-game refutation of the terrace wall built from the decoded tile language
    (CLAUDE.md §8).
- **C4.** The `terrain.py:236-241` docstring says "UV density is tight ~0.0115-0.013 ... CONSTANT". Per tri it
  is p5/p50/p95 0.011/0.014/0.020, with 17.9% in the band.
  - 41.5% of lip58 area is COLUMN-KEYED. For example, the patch at block (7,8) steps u exactly 128 px per
    column over 4.0-6.2u widths, with v pinned to 3696/3572 at the base and top over 3.3-5.9u faces.
  - This agrees with the coast memory's (7,17) teardown ("rect-halves of one tile").

## Open items and the cheapest tests (described, not run)

- **X1. Rock stretch tolerance.** Use the existing world-mountain Uaho bench. Build three variants with the
  carried rock pure-Y scaled ×1.25 / ×1.5 / ×2.0 about its rim, UV carried. Prediction: ×1.25 is
  indistinguishable (95.4% inside the envelope), ×1.5 is borderline (89.9%), and ×2.0 reads stretched
  (63.5%). The harness world-teleports and faces the massif, `game_snap` takes stills, and the owner judges. If
  ×1.25 passes, `MTN_ROCK_RIGID` 0.035 can relax to about 0.10.
- **X2. Mains corner jitter.** Displace interior L.rule lattice verts ±1.5u in XZ with carried UV. Prediction:
  indistinguishable (stock p90 is 1.51u).
- **X3. Canopy bend.** Carry the (15,15) canopy with a plan stretch of ×1.1 and ×1.25. Prediction: ×1.1 is
  faithful (93.9% inside the envelope) and ×1.25 shows on some charts (78.9%).
- **X4. Per-block texture re-bake identity.** Deploy one bench block with a Terrain override plus
  `Block[x][y] Terrain.png` set to the stock atlas (from the install, never committed). Prediction: an
  identical render. Then a tinted copy to prove it is live. This unlocks re-baking deformed M content.
- **X5. Free-angle rotation.** Rotate an L.rule patch by 30°. Prediction: clean inside the patch; the lattice
  angle shows at the seams.

Remaining unknowns: κ is undetermined for 11-32% of M.flow patches (uniform tri sizes, so some may be keyed).
Disc 4 is not covered (the disc4 lane). Object classes are reported but not decomposed further.
