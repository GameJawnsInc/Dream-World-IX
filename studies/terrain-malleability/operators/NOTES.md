# Operator inventory -- lane "operators" (terrain-malleability study)

Question: inventory every terrain-editing operator the kit ships (`ff9mapkit/ff9mapkit/world/*.py` + the `world-*` CLI
verbs), what each changes, what it preserves / gates, how proven it is, its limits; an operator x axis matrix; and the
study-only operators that carry a proven law but were never productized.

Everything below is READ-ONLY work: AST/static censuses, the kit's own readers over the install (container index + mesh
decode), and dry-run / stub probes. No `world-*` verb was run, nothing was deployed, no mod folder was read or written.
Bulky outputs are in `out/` (derived counts and coordinates only; no mesh bytes, atlases or asset dumps).

All commands run from the repo root `C:\gd\Dream-World-IX` (`py studies/terrain-malleability/operators/<script>.py`).

## 0. Scripts (rerun order) and the numbers they own

| script | what it does | key numbers (this run) |
|---|---|---|
| `inventory_ast.py` | AST census of `world/*.py` + the CLI verb table (handler, flags, world imports) -> `out/inventory_ast.json` | 33 modules / 30,250 lines; **37 `world-*` verbs** |
| `study_operator_census.py` | which `studies/` scripts WRITE terrain, and which are named by kit/tests/tools -> `out/study_operator_census.json` | 458 study scripts; 66 write-capable; 16 named by the kit; **50 write-capable with no kit reference** |
| `writer_gate_census.py` | which writers carry which safety nets (gate, mirror, ledger, sidecar, wrap, stock-vs-stacked read); 12 calibration controls incl. a break-it | see sec 4 / F-series |
| `operator_matrix.py` | the hand-curated operator x axis matrix + 4 mechanical cross-checks (coverage of all 37 verbs; Disc-4 mirror and read-source vs the census; break-it) -> `out/operator_matrix.{md,json}` | X1-X4 PASS |
| `disc_tree_inventory.py` / `disc_tree_channels.py` / `disc_mirror_eligible.py` | Disc1 vs Disc4 asset trees; what differs; which real blocks the auto-mirror gate can carry | 179/260 terrain blocks differ; 175 differ in GEOMETRY; **71/260 land blocks mirror-eligible** |
| `quick_counts.py` | map-scale denominators + the mesh-contract ceiling | 63 Object blocks; 44 beach donors; stock terrain <=736 tris/block vs ceiling 21,845 |
| `donor_part_exposure.py` | per Donor.txt lane: which donor-prefab parts the lane neither overrides nor blanks | 6 part kinds no kit writer can touch |
| `probe_reshape_read_source.py` | does `world-terrain` read pristine stock or the deployed override? (stub probe, 2 controls) | PRISTINE STOCK |
| `probe_island_ground_refusal.py` | which `--ground` families does `world-island` mint? (positive control: grass) | mints grass/desert/snow only |
| `probe_inplace_excise.py` | can the only land-removal tweak act in place on a real cell? (control: scanner-certified cliff bump) | 0/260 real 1x1 cells give a non-empty excise plan (exit 3 by design: calibration (b) unmet) |
| `defs_digest.py` | dumps public defs + docstring heads of chosen world modules -> `out/defs_digest_*.txt` | (reading aid) |

## 1. Engine anchors (every engine claim here cites one of these; paths under `C:\gd\FFIX\Memoria\Assembly-CSharp`)

STOCK = present in Memoria without our patches; s34 / s74 / s60 = added by `memoria-patches/` (grep-verified:
`WorldMeshOverride.cs` is a NEW file in s34, the WMWorld.cs hunks are s34, the `overrideDiscTag` namespace is s74).

| claim | citation | origin |
|---|---|---|
| loose `.ff9mesh` override, keyed `WorldMap/Disc{d}/0_1/r{y}/Block[x][y] <transform.name>`, highest-priority mod folder wins | `Memoria/World/WorldMeshOverride.cs:31-57`; applied per registered part at `Global/WM/WMWorld/WMWorld.cs:823-831` | **s34** (+ s74 `overrideDiscTag`) |
| override loader rejects vcount > 65535 / icount > 3*vcount | `WorldMeshOverride.cs:186-188` | s34 |
| a SEA cell with a loose Terrain file is diverted onto a land donor prefab (both sites must agree) | `WMWorld.cs:521-536` (LoadBlock) and `:1285-1296` (streaming reload) | s34 |
| `Donor.txt` ("dx,dy") picks the real prefab whose transforms the cell exposes; no sidecar -> `LandDonorPrefab` = Block[12][10] | `WorldMeshOverride.cs:89-135`; `WMWorld.cs:549-569`, `:1210-1211` | s34 / s74 |
| render-only Object override on a BARE block (no `AddWalkMeshForm1`); on a block with a stock ObjectForm1 the override IS fed to the walkmesh | `WMWorld.cs:595-596`, `:868-884`; `:588-589` | s34 |
| parts the engine registers per block (override surface): ObjectForm1/2, TerrainForm1/2, Volcano{Crater,Lava}{1,2}, Beach1/2, Stream, River, RiverJoint, Falls, Sea1-6 (+ block-219 Sea{3,4,5}[_2] early return) | `WMWorld.cs:588-637`, `:638-657`, `:748-807` | STOCK |
| the walk-mesh build is UNINDEXED (`vertices.Length/3` over `triangles[i*3]`) | `Global/WM/WMBlock/WMBlock.cs:55-73` | STOCK |
| per-triangle id = `tangents[triangles[t*3]].x`; id 0x31EE is a veto except controller type 1 | `WMBlock.cs:210-211`, `:231-232` | STOCK |
| ray scan = linear over all tris, first up-facing hit in buffer order, skips ids 4078/4088/2040 | `Global/WM/WMPhysics.cs:6-45`; 10-slot hit cache first: `WMBlock.cs:145-162` | STOCK |
| IDALL layout: event `(id&0xC000)>>14`, area `(id&0x3F00)>>8`, topograph `(id&0xFC)>>2` | `Global/ff9/ff9.cs:2335-2348` | STOCK |
| movement gate: topograph bit-tested against the controller mask | `ff9.cs:5924-5937` | STOCK |
| tile AREA -> encounter ZONE -> (topograph, fog) record; area also names the location text and (area 12) forces a camera flag | `ff9.cs:9229-9262` (fallthrough hole = no encounter is **s60**); `ff9.cs:3752-3759`; `ff9.cs:2771-2772` | STOCK (+s60) |
| the world is an x/z torus (`Wrap` shifts all blocks in 64u steps) | `WMWorld.cs:1114-1146` | STOCK |

## 2. The inventory: 37 verbs = 20 terrain/table editors + 5 derived-state editors + 12 readers

(`out/inventory_ast.json`; X1 in `operator_matrix.py` proves every verb is classified exactly once.)

* **Editors (20 verbs, 21 matrix rows -- `world-transplant --in-place` is its own row):** world-deploy, -terrain,
  -retarget, -reclaim, -coast, -transplant, -fuse, -rim-retile, -island, -hill, -forest, -mountain, -water, -coastnav,
  -entrance, -mesh-build, -mirror, -atlas-reskin, -atlas-add-tile, -encounters.
* **Derived-state editors (5):** -encounter-frequency, -encounter-rate, -environment, -rename-markers, -minimap.
* **Readers / instruments (12):** -extract, -locate, -mesh-export, -mesh-trim, -texture-palette, -atlas-extract,
  -atlas-catalog, -morphs (the window scanner: *the builders are the oracle*), -donors, -render, -readback, -ledger.
* Library-only (no verb): `meshedit.py` (sweep_wall, cover_gap, earclip, flat/lattice patch, retag_flat, T-junction
  repair, vertex_components, boundary_cycles -- the Path D primitives); `water.deploy_island_sea` (no caller);
  `transplant.deepen_shallow_plan` (dead end, internal); `islandbeach.py` (FALSIFIED ladder mint, kept for its mechanics).

## 3. Operator x axis matrix

Axes: **V** vertical reshape | **H** horizontal reshape (outline/positions) | **T** retexture/retile (UV) | **P**
re-topograph (IDALL: walkability / encounter zone / event) | **A** add land | **R** remove land (land->sea conversion, excise/drop, and the sea CUT under land) | **C** carry/transplant
(verbatim donor bytes) | **W** water parts (Sea*/Beach*) | **O** objects | **S** multi-block seams | **D** disc-4 mirroring.
Codes: `●` primary, `○` secondary / constrained / incidental, `✗` refused or structurally absent, blank = not this axis.
D-axis convention: `●` when the operator's usual targets are OCEAN cells / kit islands (the mirror gate passes: destination real
cell absent); `○` when it edits REAL land or can (the gate blocks 189/260 real land blocks, F6); `✗` when it has no mirror.
`reads`: where the operator takes the geometry it edits from -- **stock** (pristine p0data; re-runs REPLACE, never stack),
**deployed** (the mod folder's own override; stacks), **stacked** (deployed if present else stock), n/a (synthesizes/carries).

| operator | V | H | T | P | A | R | C | W | O | S | D | reads | proof |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `world-deploy` (legacy) | ● |   |   |   |   |   | ○ |   |   | ● | ○ | stock | in-game |
| `world-terrain` | ● |   |   |   |   |   |   |   |   | ● | ○ | stock* | in-game |
| `world-retarget` |   |   |   | ● |   |   |   |   |   |   | ○ | stock | in-game |
| `world-reclaim` | ○ | ○ | ○ | ○ | ● |   |   | ✗ |   | ○ | ● | n/a | flat in-game; island/cliff superseded |
| `world-coast` |   |   |   |   | ● |   | ● | ○ | ○ |   | ● | n/a | in-game |
| `world-transplant` | ○ | ○ | ○ | ○ | ● | ○ | ● | ● | ○ | ● | ● | stock | in-game (per flag, sec 4) |
| `world-transplant --in-place` | ○ | ● | ○ |   |   |   |   | ● |   |   | ○ | stock | in-game |
| `world-fuse` |   | ○ |   |   | ● |   | ● | ● |   | ● | ● | stock | in-game |
| `world-rim-retile` |   |   | ● |   |   |   | ○ | ● |   | ○ | ✗ | deployed | in-game |
| `world-island` | ○ | ● | ● | ○ | ● | ○ |   | ○ | ○ | ● | ● | n/a | in-game |
| `world-hill` | ● |   |   |   |   |   |   |   |   | ○ | ● | deployed | in-game |
| `world-forest` | ○ | ○ | ○ | ○ |   |   | ● |   |   | ○ | ● | deployed | in-game |
| `world-mountain` | ● | ○ | ○ | ○ |   |   | ● |   | ○ | ○ | ● | deployed | in-game (R5c look pending) |
| `world-water` |   |   | ● | ○ | ○ |   |   | ● |   | ● | ● | n/a | in-game |
| `world-coastnav` |   |   |   | ● |   |   |   | ● |   | ○ | ○ | deployed | in-game |
| `world-entrance` | ○ |   | ○ | ● |   |   |   |   | ● |   | ○ | stacked | in-game |
| `world-mesh-build` |   |   | ○ | ○ |   |   |   |   | ● |   | ○ | stacked | in-game (terrain lane CLOSED) |
| `world-mirror` |   |   |   |   |   |   | ○ |   |   |   | ● | stock | in-game |
| `world-atlas-reskin` |   |   | ● |   |   |   |   |   |   |   |   | n/a | offline (art task) |
| `world-atlas-add-tile` |   |   | ● |   |   |   |   |   |   |   |   | n/a | offline (magenta test) |
| `world-encounters` |   |   |   | ● |   |   |   |   |   |   |   | n/a | in-game |
| `world-encounter-frequency` |   |   |   | ○ |   |   |   |   |   |   |   | n/a | in-game (CLAUDE.md s8) |

\* `world-terrain` reads pristine stock when `target_disc == disc` (probe), and the deployed override only for a synthetic
`--target-disc` (terrain.py:132-138).

Column totals over the 21 editor rows (`operator_matrix.py`): primary(●) V4 H2 T5 P4 A5 R**0** C5 W6 O2 S6 D10; refused(✗) W1 D1.
**Axis R (remove land) has no primary operator**; H and O have only two each.

## 4. Operator cards

Format: *changes* (XZ / Y / UV / IDALL / topology / parts / sidecars) | *reads* | *gates & preserved invariants* | *proof* | *limits*.

**world-deploy** (`cli.py:4090`; library `mesh.deform_radial/flatten_region/lift_block/raise_vertex_near_center`)
changes Y only on the Terrain part (hill/crater/flatten/lift/spike; `recompute_normals`, which is render-inert on
WorldMap/Terrain -- `mesh.py:1310-1313`); a no-flag run is a faithful copy. Reads **stock**. Gates: entrance-block REFUSAL
(`--allow-entrances`, cli.py:4154), grid bounds, ledger ownership refusal. In-game (lift/hill 2026-07-02). Limits: Terrain
only; no one-way-wall gate.

**world-terrain** (`terrain.reshape`, terrain.py:88-172) changes Y only, radial / ridge / flatten, one shape per call,
across every touched block with identical world-space weights (shared edge verts move identically). Reads **pristine stock**
(terrain.py:139-143). Gates: ONE-WAY-WALL refusal (rise/run > tan 79.43 deg = `WALK_RAY_START 2.34375 / WALK_SPEED 0.4375`,
`--allow-steep`), flank WARN > 28.6 deg, off-grid SEAM NOTE, grid bounds. Preserves UV/IDALL/index/topology. In-game 2026-07-02.
Limits: see F2-F5.

**world-retarget** (cli.py:4265; `mesh.retarget_tiles`) rewrites tangent.x (event/area/topograph) per triangle in a circle (library also takes
box/polygon); geometry byte-untouched. Reads **stock** (cli.py:4275). In-game for topograph (walkability); `--event/--area`
alone do not make an entrance (the destination is the world `.eb` object-0 cell tag). Limits: F5 (area is not cosmetic).

**world-reclaim** (`terrain.reclaim`, terrain.py:317-424) synthesizes a fresh Terrain mesh per OCEAN cell (profiles flat /
island / cliff; unindexed, up-wound, palette-stamped UVs). No Donor.txt -> the cell loads `LandDonorPrefab` (12,10), whose own
water free-rides (F7). Gates: MOD-OVERWRITE, grid bounds. Flat slab in-game 2026-07-02; island/cliff = superseded placeholders
(`mesh.blob_cliff_block_mesh` is UNWIRED, terrain.py:401-404). Whole 64u cells only.

**world-coast** (`terrain.coast`, terrain.py:178-225) copies a donor block's Terrain to the target cell and writes `Donor.txt`;
beach/sea/foam/Object render from the donor prefab UNROTATED. Gates: MOD-OVERWRITE only (no placement census, no
prefab-parts gate). In-game 2026-07-02 (18,15). The ungated predecessor of world-transplant.

**world-transplant** (`transplant.transplant` / `transplant_region`; tweaks in `coastmorph.py`)
changes: XZ rigid (rot 0/90/180/270, shift 0 mod 4, RowInsert/RowInsertZ growth columns, cliff/beach shape tweaks); Y verbatim
(+VertexDisplace/bank_lower); UV verbatim (+TileRetexture, GroundRetile, rim); IDALL verbatim (+ground-retile relabels);
topology: Sutherland-Hodgman clip at the cell frame (adds tris), DropTris/EmitTris; parts `PARTS = terrain, beach1, sea1-5`
(transplant.py:46) + blanks; sidecar `Donor.txt` per cell. Reads **stock**. Gates (all must pass or the deploy is refused,
transplant.py:2898-2915): OPEN-OCEAN target, MOD-OVERWRITE, frame bounds, land-fit margin, tweak scope counts, weld audit (0
near-miss pairs), T-JUNCTION differential, engine-placement census MISS==0, effective-prefab arm, object anchor; WARN-default
and report-only: wang-carry, orphan-decal, texture+sea (`--enforce-*` hard-fails, `--allow-*` waives).
Per-flag proof: rot/shift/size, `--grow-cut(-z)`, `--cliff-bump/-headland/-bay/-lobes`, `--beach-rebuild/-reshape/-slide`
(seaward AND landward), `--beach-mint` r1/r2a, `--band-convert`, `--virgin-mint` + `--bank-lower` (island B), `--ground` retile
(round 1) and `--redress-orphans` (3 rounds / 15 cells) are all owner-played; `--excise` is partial (3/8 masses admit deep
morphs); `--strips/--sand/--cap-rebuild` are identity proofs (caps/sand byte-equal, strips fresh-pick).
Limits: Object is NOT carried (renders from the prefab; lawful only unrotated+unshifted+untouched -- OBJECT POSE LAW); beach2
/ sea6 / stream / volcano free-ride (F7); beach verbs refuse `--size`; `--ground` refuses `--in-place` (cli.py:4790-4792, "unstudied");
wall-context law refuses retiling coastal walls into canyon/scrub/brush/dunes (transplant.py:717-734); x-seam unaware (F8).

**world-transplant --in-place** (`morph_in_place`, transplant.py:3286-3378): applies tweaks to a REAL cell's own parts (reads
**stock**, deploys only touched parts, no Donor.txt, no census). Gates: IN-PLACE-FRAME (block-frame vert set byte-unchanged) +
BOUNDS. Cannot emit into a part the cell lacks (the (6,17)/(18,3) lesson). In-game (cliff morphs on the live continent).

**world-fuse** (`fuse.fuse_layout` / `compose_layout`): validated multi-placement layout + compose tiers (island, mountain,
forest, hill, coastnav, rim_retile in fixed order); gates rect-overlap, fuse border certification, existing-overrides,
manifest-drift. THE FUSE LAW (in-game 2026-07-09): land never knits, water knits.

**world-rim-retile** (`rimretile.rim_retile`): repartitions a deployed island's cropped shallow ring using tiles HARVESTED
byte-exact from the donor's own sea5 terminators; geometry untouched (`repartition_ok`). Reads **deployed**. **Writes in place
with no Disc-4 mirror** (rimretile.py has no mirror call; F6). Refuses seam-spanning input.

**world-island** (`island.build_landmass` + `verify_landmass` + `landmass`): synthetic outline (blob / multi-lobe), faithful ~73
deg rock wall, real grass tile language, optional `--relief`; per block: Terrain + cut Sea4 + blanked Object/Sea1/2/3/5/Beach1 +
Donor.txt; coastnav stamp then ONE mirror pass. x-seam aware (wraps at the deploy stage, island.py:1080-1087). Gates:
cracks, closed-surface once-edges, winding, grain <= 8u, holes, UV bounds, placement census MISS 0, texgates (WARN-default),
OPEN-OCEAN, MOD-OVERWRITE, WALL-CONTEXT. In-game. Limits: F9 (`--ground`), `--beach` FALSIFIED, ~5% seed yield at r>=120.

**world-hill / -forest / -mountain** (`interior.py`): operate on a DEPLOYED kit island (`read_deployed_blocks`). hill = pure-Y
raised cosine; forest = verbatim topo-37 canopy blob + grass annulus; mountain = verbatim rock massif (rigid, grass apron
conforms) + optional ensemble parts (Object/Falls/River/RiverJoint + Donor.txt re-point). All in-game; zero-byte-diff identity vs
the studies is the acceptance test. hill and forest are **grass-ground only** (interior.py:922 requires topo-0 mains; desert
ground is topo 17, `grassland.GROUNDS`); mountain takes `--ground`. Qualified massif donors: Uaho (0,0), crag (10,5-6),
horseshoe (5-6,15-16), comp20 (12,16-17) (`data/donors.toml`).

**world-water** (`water.py`): Wang/marching-band open ocean from a depth field: per cell flat Terrain stub (Y -0.1, topo 57) +
Sea3/4/5 + blanked Sea1/2 + Donor.txt (15,4). In-game (17/17 shape match). Gate: MOD-OVERWRITE over the whole cell list. No
`--target-disc` (water.py:296-305) -> cannot write the Path D namespace.

**world-coastnav** (`coastnav.stamp`): rewrites ONLY the topograph bits of every water tri in deployed Sea1-5 overrides
(KEEL 56 / BELT 55 / CLIFF 54 / BEACH 53 / open 57); geometry, UV, event, area byte-preserved. Mirror to Disc4 only with
`--mirror-disc`.

**world-entrance** (`entrance.author_entrance`): event tiles (IDALL), topo-59 footprint hull (exact polygon split), optional
flatten pad (Y), building Object part, per-language world `.eb` trigger + nameplate band. Reads **stacked** (`--fresh` = stock).

**world-mesh-build / -mesh-export / -mesh-trim** (`blendio`): OBJ round trip for the Object part only; the Terrain rebuild lane
is CLOSED (an OBJ cannot carry per-triangle IDALL).

**world-mirror / auto_mirror** (`discmirror`): see F6/F10.

**world-atlas-reskin / -add-tile**: replace pixels in / add a tile to the ONE shared terrain or object atlas -> global, every
block. Offline pipeline only (repaint is an art task). The active atlas is Moguri's HD atlas, not stock (memory
`project-ff9-overworld-terrain-authoring`).

**world-encounters** (`worldpack.py`, `discmr.img` sub-table 3, 355 records): re-meanings, not geometry.

## 5. Findings that change the picture (all rerunnable; engine facts per sec 1)

**F1 [law] Every geometry operator rides the s34 loose-override engine patch.** The override is per PART, keyed by
`transform.name` of a transform the EFFECTIVE prefab exposes (WMWorld.cs:823-831). The malleability envelope is therefore (a)
the 20 engine-registered transform kinds (+3 water-shrine variants on block 219; sec 1), (b) the mesh contract (flat; vcount <= 65535 => <= 21,845 tris per
part-block => finest uniform lattice 0.612u vs the 4u stock lattice), and (c) what the kit's languages can dress. Stock terrain
uses <= 736 tris/block (median 314), so the engine is not the resolution limit (29.7x headroom; the linear ray scan,
WMPhysics.cs:6-45, is softened by the 10-slot hit cache, WMBlock.cs:145-162). [measurement: `quick_counts.py`]

**F2 [law, probe] `world-terrain` (same-disc), `world-deploy`, `world-retarget` and every `--in-place` morph read PRISTINE stock,
so edits to one real block do NOT compose: the last writer wins.** `probe_reshape_read_source.py`: calibrated (C1: a `--target-disc`
run uses the stacked reader; C2: swapped stubs swap the counters) -> same-disc `reshape` calls `extract.read_block` only.
`world-retarget` (cli.py:4275), `world-deploy` (cli.py:4149) and `morph_in_place` (transplant.py:3304-3306, `world_tris`) are the same.
Only `world-entrance` (stacked) and the interior verbs (deployed) stack. Consequence: a hill, then a retarget, then a cliff bump
on the same real block cannot coexist; the ledger refusal (`mesh.py:491`) only blocks FOREIGN bytes, and the previous bytes are
parked as `.bak-<ts>`.

**F3 [law, source-read] `world-terrain` moves Y on the Terrain part only.** Coincident Beach1 / Sea / Object verts are not
moved (terrain.py:159 deploys `part="Terrain"` only); transplant's `VertexDisplace` is the only weld-preserving multi-part mover
and it exists only for tweaks. On the 63 Object blocks / 44 beach blocks a reshape can leave the water or structure at the old
height. [measurement: 63/44 from `quick_counts.py`; the weld-gap size itself is OPEN]

**F4 [law, source-read] The entrance-block refusal lives only in the legacy `world-deploy`** (cli.py:4154, `--allow-entrances`);
`terrain.reshape` has no entrance guard (`writer_gate_census.py`: control "terrain: NO entrance guard identifier").

**F5 [law; CONTRADICTS a recorded claim] Tile AREA is not cosmetic.** `world-retarget --area` help (cli.py:9025) calls it "a
COSMETIC regional tag"; memory `project-ff9-world-locate-cell-tag-join` says "Tile `--area` stamps are pure bookkeeping".
True for entrance DISPATCH; false for the engine: area -> zone -> encounter record (`ff9.cs:9229-9262`), area -> location text
(`ff9.cs:3752-3759`), area 12 -> camera flag (`ff9.cs:2771-2772`). `world-entrance` stamps the tile area by default
(`--no-tile-area` to skip), so an entrance edit also re-zones those tiles' encounters.

**F6 [measurement, law] The Disc-4 axis is the weakest.** `discmirror.mirror` copies a cell to Disc4 only if the destination's REAL
cell is absent or part-set-equal AND byte-identical in every part (discmirror.py:275-289). Calling that gate's own helpers over
all real blocks (`disc_mirror_eligible.py`; calibrated: an open-ocean cell passes, distinct blocks differ): of 260 land blocks
**71 are eligible, 189 blocked** (184 differ in some part, 5 differ in part set); 13 of 15 sea-only blocks eligible.
Terrain alone: 81 identical / 179 differ, and 175 of the 179 differ in GEOMETRY (115 by vertex count = re-tessellated; 60 by
vertices) (`disc_tree_channels.py`; the 4 geometry-identical ones differ in UV (3) or normals (1) only). So a `world-terrain` /
`--in-place` / `world-retarget` edit on 73% of real land exists on discs 1-3 only, and needs a separate `--disc 4` run
(auto_mirror skips `src == dst`). Separately **`world-rim-retile` never mirrors** and **`world-coastnav` mirrors only with
`--mirror-disc`** (`writer_gate_census.py`, `operator_matrix.py` X2), so after transplant -> rim-retile -> coastnav the Disc4
tree keeps the un-retiled, un-stamped sea until a manual `world-mirror`.

**F7 [measurement] Free-ride exposure.** A Donor.txt cell renders every prefab transform it does not override or blank
(WMWorld.cs:588-807 + :823). `donor_part_exposure.py`: island / water / transplant lanes have ZERO free-riders for their standard
donors ((0,0), (7,17), (20,5), (15,4), horseshoe ensemble) -- the calibration controls. `world-reclaim` (no sidecar) free-rides
Block (12,10)'s full 373-tri Sea4 plane + Sea1/3/5 patches (4/88/36 tris, x 28-64, z -64..-28) -- contradicting the engine
comment "no beach/sea" (WMWorld.cs:1207, s34) -- and `world-coast` free-rides ALL donor water. **No kit writer can override or
blank beach2 (4 blocks), sea6 (4), stream (7), volcanocrater (2), volcanolava (1), sea4f (1)**; the TerrainForm2/ObjectForm2
variants are not addressed by any operator (the kit reads lod 0_1, the Form-1 walkmesh, extract.py:11; whether Form2 meshes are separate assets sharing `transform.name` is OPEN). [Beach2/Sea6 blind spot was already recorded; stream/volcano extend it.]

**F8 [law] Multi-block seams are operator-specific.** Only `world-island` is x-seam aware (island.py:1080-1087; engine Wrap is
stock, WMWorld.cs:1114-1146); `terrain.reshape` warns it does NOT wrap (terrain.py:162-168); `rimretile`/interior refuse
seam-spanning input; `mesh.require_block_in_grid` refuses Block[24]/[-1]; `transplant`/`fuse`/`reclaim`/`coast` address cells 0..23
only (census: `wrap_aware` is set for island + coastnav + navimap only). z-wrap is kit-policy refused.

**F9 [law; CONTRADICTS the CLI help] `world-island --ground`** help (cli.py:9608-9612) says canyon is "island-complete" and
scrub/brush/dunes "mintable". Calibrated probe (`probe_island_ground_refusal.py`, positive control grass builds): ONLY
grass/desert/snow mint; canyon/scrub/brush/dunes are refused by THE WALL-CONTEXT LAW (island.py:254-273; fail-closed since
2026-07-19; CLAUDE.md s8 agrees with the code, not the help).

**F10 [law] Disc-4 auto-mirror evidence contract:** `auto_mirror` mirrors only cells named by this call's own written paths,
skips non-real discs (Path D) and `src == dst`; `--skip-mirror` and `DEFERRED` are the only opt-outs (discmirror.py:119-239).
Path D (disc 9) support is verb-by-verb: only 11 verbs expose `--target-disc` (coast, forest, fuse, hill, island, minimap,
mountain, reclaim, rim-retile, terrain, transplant); water, entrance, mesh-build, retarget and deploy do not (coastnav has its
own `--disc` namespace flag).

**F11 [law] Axis R is empty.** No operator removes REAL land in place: `--excise` is carry-only; `excise_plan` yields a non-empty
plan on **0 of 260** real 1x1 cells (`probe_inplace_excise.py`; control: a scanner-certified cliff bump passes the same in-place
dry-run, so the harness works) and `morph_in_place` is single-cell. The nearest things are all secondary and bounded: `cliff-bay` converts a depth-limited wedge of coastal
grass to sea (pure-sea4 shores only; refused if it reaches a land component), `bank_lower` sinks a bank (Y only), and
`world-terrain --lower` is Y-only and adds no water over a lowered interior.

**F12 [law] Retexture on REAL land has no operator.** `GroundRetile` rides carries only (`--ground` refuses `--in-place`,
cli.py:4790-4792); the atlas verbs are global; `world-rim-retile` retiles water only. The same gap holds for IDALL at polygon
granularity (library `retarget_tiles`/`split_retarget_by_polygon` support it; the CLI exposes a circle only).

**F13 [measurement] `world-hill` and `world-forest` cannot run on non-grass islands** (interior.py:922; ground family is topo
17 for desert). Source-read; not executed against a desert island (see experiment E4).

**F14 [law] Gates are mostly PER-OPERATOR, not per-writer** (`writer_gate_census.py`): MOD-OVERWRITE is called by island,
transplant, water and terrain.reclaim/coast (NOT by reshape/retarget/deploy/morph_in_place, correct only if they read the
deployed bytes -- F2 shows they do not); `weld_audit`, the T-junction differential, the placement census and the
wang/orphan/texture gates are called only by transplant / island / interior; `world-coast` has none of them.

## 6. Study-only operators that carry a proven law (never a verb)

(`study_operator_census.py`: 66 write-capable study scripts, 16 absorbed, 50 unreferenced by kit/tests/tools; the table is the
curated subset with a proven law. "Absorbed" = a kit module/test names the script.)

| study operator | law it carries | evidence of proof | what the kit absorbed | gap |
|---|---|---|---|---|
| **V-shore corner stack** (`path-d-new-world/vcorner_transplant.py`, `vcorner_crest.py`, `vcorner_sea_cut.py`, `vcorner_repack.py`, `full_skirt.py`, `terrace_wall_strip.py`, `bench_pipeline.py`, `coast_lint.py`) | OVERHANG-CONTEXT, FLOW CONSTRAINT >=135 deg, JOINT-KINK <=12 deg, TEXEL-DENSITY, PEER GATE, A REPAIR THAT IS NOT EXACT IS A HOLE | owner-accepted on flow AND look after 12 playtests (`SEGMENT-TRANSPLANT-PREDICTION.md:491-497`) | `meshedit.py` primitives (no verb), `render.py` gate; unreferenced: vcorner_* (sea_cut is named by meshedit) | seat-a-verbatim-coast-segment-into-a-cut-sea orchestration has NO verb; `meshedit.py:55-58` itself lists `cut_sea_under` as "deliberately NOT here yet" |
| **Rung F two-ground composer** (`overworld-topography/junction_compose.py` + `rung_f_layout/stitch/holefill/build.py`, `uvf_fix3..8.py`) | L1-L8: ONE WINDOW PER TRI, family field, diversity policy, spike/sliver shave, orphan redress; THE ONE-SITE WORLD LAW | accepted in-game after eight rounds (`GROUND-FAMILY-DECODE-2026-07-19.md:2406`); carried into 9013 (36 gates, 180 files) | texgates.py + orphangate.py (the gates) | the GENERATOR is a study script; only one site exists |
| **Dunes whole-component stamp** (`dunes_true_carry.py`, `dunes_field_mint.py`, `dunes_fringe_fix.py`) | DUNES SIZE-CLASS (>= ~130 cells), bijective rigid dihedral stamp, carried ecotone | playtest "The ecotone is nice now" (`GROUND-FAMILY-DECODE:1237`) | orphangate rule set | no verb; small-patch dunes mint FALSIFIED |
| **Mixed-biome mint** (`mixed_biome_mint.py`, `gd_seam_dress.py`) | desert\|grass combining language (Round 10-11) | first deploy "a big weird mess ... solid green floors" (`GROUND-FAMILY-DECODE:2301`) | -- | FALSIFIED as built (flat-sheet stain), superseded by Rung F; kept as record |
| **Biome-patch window carry** (`dunes_patch_carry.py`, `dunes_patch_mint.py`) | THE ENSEMBLE LAW, size-class | scrub rung closed by removal; patch mint closed by law | -- | not a lane |
| **Sea repair family** (`beach_island_sea_patch.py`, `sea_patch_reset.py`, `waterfix_1119*.py`, `sea1_ladder_corner.py`) | SEA-LAYER (all stock sea layers at Y=0, disjoint plan coverage), FLAT-MESH, EFFECTIVE-PREFAB ARM | (8,17) hole fix confirmed in-game 2026-07-20 | `effective_prefab_arm`, write-seam asserts | one-shot repair scripts |
| **Mesa / terrace / two-level / bend / strip / rim-aware syntheses** (`mesa_carry.py` x2, `terrace_build.py`, `two_level_f.py`, `two_level_v3.py`, `terrace_wall_t1.py`, `apron_carry.py`, `band_seat.py`) | THE FORM LESSON: correct tiles on INVENTED MASSING fail; carry-with-minted-context | refuted over registered rounds (CLAUDE.md s8) | -- | records, not lanes |
| **Scene ladder** (`scene-ladder/rung0..3c`) | world-scripted-object lane | rungs 0-3c owner-confirmed | -- | `.eb` lane, not terrain |
| **Path D arm tiles** (`rung6/worldside/arm_tiles.py`) | entrance tile arming on 9013 | round trip owner-confirmed 2026-08-05 | -- | no verb |

### 6b. Falsified / closed operator lanes (so nobody re-opens them; sources: CLAUDE.md s8, memory coast-mosaic LAW INDEX, CLI help)

* `world-island --beach` (THE LADDER MINT, 4 playtests) -> superseded by `world-transplant --ground` ((7,17) retile carry); `islandbeach.py` kept for mechanics. CLI help carries the banner.
* `world-coast-custom` ribbon-warp (`bay_warp`) -> failed in-game 2026-07-06; the "one global winding flip" law is historical.
* From-scratch massif synthesis (8 rounds) -> carry (`world-mountain`). Terrace-wall synthesis from the decoded tile language, bend-carry, strip-carry, profile-carry, rim-aware -> refuted/plumbing-stopped; carry-with-minted-context (Rung F) is the road.
* Small-scale dunes mint (size-class law); scrub PATCH rung (closed by removal); mixed-biome thin ribbon (RIBBON FALLACY); canyon ISLAND (wall-context law, now a code gate -- F9).
* `world-mesh-build` TERRAIN lane (OBJ cannot carry per-triangle IDALL); `mesh.blob_cliff_block_mesh` (unwired); `deepen_shallow_plan` (re-shading a ring as deep: rejected in play).
* `world-reclaim --profile island|cliff` are stylized placeholders superseded by donor carries; the ladder `--beach-mint` is a DIFFERENT live lane despite the name.
* The TOPOGRAPH 36-38 encounter law (`world-encounter-rate` is the Ragtime Mouse; the real lever is `world-encounter-frequency`).

## 7. Gap-map seeds from the matrix (operator-level, with the finding that names each)

1. Remove land / flood land in place: no operator (F11).  2. Retexture a region of REAL land: no operator (F12).
3. Edit one real block more than once: last-writer-wins (F2).  4. Move water/Object with a Y edit: no operator (F3).
5. Disc-4 parity for edits on 189/260 real land blocks: manual `--disc 4` runs; rim-retile/coastnav not auto-mirrored (F6).
6. Parts no writer can touch: beach2, sea6, stream, volcano*, sea4f, Form2 variants (F7).  7. Seam-spanning transplant/fuse (F8).
8. Polygon-granularity IDALL from the CLI (F12).  9. Non-grass interior relief (F13).  10. Path D (disc 9) for water/entrance/mesh-build/retarget/deploy (F10).

## 8. Proposed experiments (designed, NOT run; cheapest first)

* **E1 non-composition (offline, scratch mod folder):** two overlapping `world-terrain` hills -> `world-mesh-export --mod-folder`;
  predict only the second hill survives (F2). Same for hill + `world-retarget` on one block.
* **E2 Disc-4 parity (in-game, 1 deploy):** `world-terrain --raise` at a mirror-BLOCKED block (e.g. (6,8)); read the SKIP line;
  switch to disc 4 in the debug menu (~ -> World); predict the hill is absent there; then repeat with `--disc 4`.
* **E3 reclaim free-ride (in-game):** `world-reclaim --cells X,Y --height 6` on open ocean; predict shallow-water patches in the
  cell's SE quadrant (donor (12,10): Sea3 x 36-64 z -64..-32).
* **E4 hill on desert (offline, no write):** `world-hill --near ... --dry-run` against a deployed desert island; predict
  "not lawful (pure mains)" (F13).
* **E5 rim-retile Disc4 (offline):** byte-compare Disc1 vs Disc4 Sea3/Sea5 of a retiled island (`world-ledger --drift`); predict they differ.
* **E6 density (in-game):** `world-reclaim --profile flat --seg 104` (2*104^2 = 21,632 tris, under the 21,845 ceiling); walk it; predict no
  frame-rate change thanks to the 10-slot hit cache (WMBlock.cs:145-162).

## 9. Open questions

* Does a Y edit on a coastal / Object block visibly tear (F3)? Needs the weld census over the 44 beach + 63 Object blocks.
* TerrainForm2 / ObjectForm2 / Volcano*2: what do the world-state forms look like and do they share `transform.name` with Form1?
* Are the 4 Disc1/Disc4 geometry-identical-but-different blocks (UV/normal/IDALL only) worth a partial-mirror mode?
* How many of the 66 write-capable study scripts carry a law not listed in sec 6 (the 50-script list is mechanical, the curation is mine)?
