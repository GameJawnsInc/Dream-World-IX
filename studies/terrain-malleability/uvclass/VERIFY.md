# uvclass: adversarial verification

This is a read-only check of the uvclass lane, covering findings UV-01 to UV-16. I re-opened every cited engine and
kit line, and I reran every lane script against a FRESH mesh cache (`$FF9_UVCLASS_CACHE` pointed at a scratch
folder). I also wrote targeted counterexample scripts, all prefixed `verify_` in this folder; their outputs are in
`out/verify_*.json`.

## Reproduction

- The fresh cache came out byte-identical in size (83,939 tris, 260 blocks; 3,693 object tris, 63 blocks).
- All nine lane JSON outputs re-ran byte-identical to the lane's own copies (`calibration`, `census_object`,
  `census_terrain`, `deform_envelopes`, `probe_*`, `reconcile`).
- `read_block` reads the stock p0data bundles only. Deployed overrides (for example, the live Uaho re-carve) are
  never mixed in.
- Disc 1 has no Terrain2/Object2 containers at LOD 0_1, so read_block's `target in c` substring match cannot
  return the wrong part.
- The atlas the engine renders here is MoguriMain's loose `res(1_24)_terrain.png` (`atlas.resolve_atlas_source`).
  That is the atlas the light probe reads.

## Verdicts

| id | verdict | why |
|---|---|---|
| UV-01 | **confirmed** | All cited lines are correct. `WMBlock.cs` and `WMPhysics.cs` are unmodified in the clone and no patch edits them. No UV read exists in Global/WM, Global/World, Memoria/World or ff9.cs; the only `mesh.uv` hits are the override loader's write and the dev debug menu's dump. |
| UV-02 | **corrected** | The numbers reproduce exactly. Two problems: "L is TAU-independent" holds by construction (`classify` decides L before any TAU test), and the M class is not "free charts". Map-wide, 39.7% of M-class area is exact 128 px tile-window rect-halves, which is 16% of all terrain area. |
| UV-03 | **corrected** | The ground-L / wall-not-L split reproduces. Rock49 is 5.4% L, not "2-4%". The W.keyed-vs-M.flow split inside the wall families does not separate keyed from unkeyed charts (see UV-07). |
| UV-04 | **corrected** | The counts, offsets and worked example reproduce. Only 1.8% of the off-lattice cells are pure translations, so the distortion is real. But the envelope is mostly a seam phenomenon: 77% of pinned cells touch another class and 59% touch a non-ground topo. The 1,207 interior-only cells have p90 1.12u, not 1.5u. The stretch 0.81-1.41 pools all L; L.rule alone is 0.82-1.38, interior 0.83-1.28. X2's "jitter every interior vertex ±1.5u" exceeds what stock shows. |
| UV-05 | **confirmed** | The density, survival and slope-envelope numbers reproduce. Height scaling on flat ground is trivially density-neutral, which the lane handles through the slope envelope. |
| UV-06 | **corrected** | The column-keyed lip, the (7,8) example (patch 4717, κ 0.9995) and the kit-docstring contradiction all hold. The u-rate spread is exactly 0.0625/width. But keying is UNDER-counted: lip58 M.flow area is 26% exact-128 windows (2.9% at 120 px, 0 at 136). In the same block, patch 4762 pins v at 3572/3696 over faces 4.8-6.1u and is still filed M.flow. The ×0.58-1.61 / ×0.72-1.39 ratios are the population p5 and p95 over the median, so they apply only to a median course. |
| UV-07 | **corrected** | The envelope and survival numbers reproduce. "Is not keyed" is false: 28.9% of M.flow area has a uv extent of exactly 128 px (±2/±4) against 0.5% at 120 px, while its geometric widths spread 3.9-6.2u (p10-p90). Membership in the population envelope is an uncalibrated proxy for the look. The memory records that the v1/v2 blend-conform with verbatim uvs SMEARED rock in-game, which is why ROCK-RIGID exists. X1 is mandatory before any relaxation. |
| UV-08 | **confirmed** | Sector means are flat (102-105) and the injected control is recovered. Caveat: the probe tests facet-level window choice. It does not test the painted light direction INSIDE a plan-mapped ground tile, which a free-angle rotation of ground would turn. |
| UV-09 | **corrected** | The vertex-union artifact is real: `forest_uv_components.py` unions on ONE shared vertex, and the 35/28 counts reproduce. The edge patches are tile-scale (≤252 px, ≤9u), but they are NOT "near-affine" at the lane's own TAU: in (15,15), 6 of the 7 patches with ≥6 tris have 10-27 px residual. The L class has no affinity test at all. |
| UV-10 | **corrected** | The negative-control failure holds and is stronger than claimed. `_cell_rect` flags 1.8% (grass) and 0.4% (topo17) of lattice-aligned flat tris, but 56-89% of off-lattice-flat and 99% of steep tris. It measures plan-affine extrapolation geometry, not art. Rock art is shared (reproduced). But the replacement reason, "non-affine, unkeyed flow charts", is wrong: much of the rock is keyed 128 px tiles. |
| UV-11 | **refuted** | R3's tile counts use a phase-0 128 px grid. The rock lattice phase is u 8 / v 64 px: 54% and 63% of vertices land on it, against 9% and 0.5% at phase 0 and 11% by chance. At the true phase, the share of continuous edges that cross a tile boundary is 53.8%, not 67.4%. On the wall, 92% of tris pair into quads; the quads' median uv extent is exactly 128×128, 73.5% of quads are exactly one tile, and 63.9% of tris are axis-aligned rect-halves of a tile. So the recorded "ONE 128 px tile per wall QUAD" stands. The continuity is the recorded WINDOWED CONTINUATION / LAW 3. The offered mechanism contradicts TERRACE-WALL-PREDICTION.md round 2: a faithful tile-language build failed on FORM/massing, not on cuts. |
| UV-12 | **refuted** | The list rests on the misfiling W/M split. **50** of the 144 highland blocks have ≥50% of their rock area as exact tile rect-halves, not 10. **44** of the "mural" (M ≥ 80%) blocks have ≥30%. Examples: (21,11) is 64% exact-tile but filed 90% M; (14,13) is 70% exact-tile but filed 65% M. |
| UV-13 | **corrected** | The numbers reproduce. "CARRY-DOMINANT" inherits the M misfile (about 40% of M area is exact tiles), so carry-only content is overstated. |
| UV-14 | **confirmed** | Uaho's 9 patches are identical at 0.25/0.5/1.0/1.536/3/6 quanta (verified; C0 itself ran only 1.536). Global drift is 1.9%. Three caveats: the "0.00 px floor" is p50 only (p90 17.6 px); 3 of the 8 synthetic controls (S6-S8) inject `reuse_far`/`decoded`, so they cannot fail on the instrument; and no control has keyed tiles with partial-tile fringes, which is the case that breaks κ. |
| UV-15 | **refuted** | The s34 clone at `WMWorld.cs:835-846` is overwritten. `LoadBlock` calls `block.SetupPreloadedMaterials()` afterwards (`WMWorld.cs:808`, stock), and that call re-assigns `renderer.material` by GameObject name (`WMBlock.cs:106-111`). "Terrain" is in `MaterialDatabase` whenever the loose atlas exists (`WMBlock.cs:273-306`), and on this install Moguri supplies it. A `Block[x][y] Terrain.png` is therefore dead here: X4's tinted PNG would show no tint. This agrees with the capacity lane's X5. Sea parts are not in the table, which is why the ocean works. |
| UV-16 | **corrected** | The audit facts hold: `reshape` and `flatten_region` are pure-Y and class-blind, and every operator cite is correct. "More conservative than stock requires" leans on UV-04, whose envelope is mostly seam-conforming, and on X3/X5, which have not been run. |

## The cross-cutting defect: the per-patch κ misses keying

In stock, keyed walls ship partial tiles at their fringes. Those partial tiles are smaller tris with
proportionally smaller windows, so they have the same texel density as the full tiles.

On (14,13), the M.flow tris split like this:

- 59% carry exactly half a tile, at size 3.53u and 25.4 px/u.
- The rest are size 2.66u with a uv area of about 4,960 px², at 25.2 px/u.

The size-density regression flattens as a result: pooled κ is 0.48 and per patch it is 0.1-0.4. The rect-halves
alone give κ 1.006.

The direct, non-circular test is the 128 px spike. Uv extents sit at exactly one tile far more often than at
neighbouring sizes (28.9% vs 0.5% for M.flow) while the geometry varies about ±25%. Run that test, or a role-pin
test, before trusting any W/M number.

## Scripts (read-only; rerun from this folder after the lane's own pipeline)

- `verify_rockwall.py`: phase-aware tile-crossing counts, phase-invariant tile spans, the quad = one tile test,
  and the κ of the wall's patches.
- `verify_rockwall_b.py`: per-tri half-tile uv area, rect-halves, κ split, and the map-wide rect-half share for
  topo 49 and 58.
- `verify_keyspike.py`: the exact-128 spike against the 112/120/136/144 controls, per class.
- `verify_mclass_tiles.py`: the map-wide rect-half and spike share for every sub-class.
- `verify_highland_tiles.py`: the per-block exact-tile share of rock against the classifier (UV-12).
- `verify_cornerpin.py` and `verify_cornerpin_stretch.py`: the translation-vs-distortion split, the
  boundary-vs-interior split, the window sizes, the worked example, and the L.rule-only stretch.
- `verify_baked_metric.py`: `_cell_rect` uniqueness by lattice alignment and slope.
- `verify_calib.py`: Uaho tolerance sweep and the mixed keyed synthetic controls.
