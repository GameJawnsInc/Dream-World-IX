# Lane `gap_disc4_edit_reach`: how far in-place edits of real land can lawfully reach disc 4

Read-only study. Nothing was deployed. The install, the live mod folders, the Memoria clone and the memory store
were not written. (The StreamingAssets bundle-hint file was already present for both discs; its mtime is unchanged.)
Every operator replay ran into **scratch mod folders** under the session scratchpad
(`...\scratchpad\gap_disc4\{p3_mod,k3,crack,pin_bug,pin_control}`), or with `dry_run=True`.

The decoded two-disc cache is `cache_v2.pkl` (vertex positions, so it is kept **outside the repo** for the
provenance gate). `out/` holds only derived counts, coordinates and verdicts.

**Rerun.** Run every script from `C:\gd\Dream-World-IX\ff9mapkit` as
`py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/<script>`. Run them in order: each one
reads the outputs of the earlier ones. All of them exit 0, and their calibrations are `assert`s.

| script | what it does | runtime |
|---|---|---|
| `s0_cache.py [--rebuild]` | Decodes both Form-1 trees with exact containers and matches triangles order-invariantly. Calibrations C1-C5 cover the matcher. | 10 s |
| `s1_gate.py` | Runs the gate three ways (shipped predicates, exact containers, order-invariant), then the P3 dry-run mirror on a scratch tree. | 10 s |
| `s2_footprint.py` | Builds the per-(cell, part) disc-diff footprint, the 5 hazard layers, and the F18 vs D4-01 reconciliation. | 15 s |
| `s3_tieground.py` | Strategy (i): the tie-ground difference on permuted cells. Lattice plus jitter, with a D4-18 reproduction and controls. | 20 s |
| `s4_calibrate.py` | K1-K5: replay and delta calibration, including an end-to-end run through `terrain.reshape` and `discmirror.mirror` into scratch. | 40 s |
| `s5_reach.py` | The reach census over the synthetic edit population (`out/reach.json`, `out/reach_summary.json`). Includes V1-V3. | 85 s |
| `s5b_crack_demo.py` | End-to-end proof of the partial-mirror crack, with 3 weld controls. | 5 s |
| `s5c_border_welds.py` | Border T-junction census on both discs, and a coincident-weld check after replay. | 5 s |
| `s5d_wallgate_preexisting.py` | Side observation: why the one-way-wall gate refuses so much. | 5 s |
| `s6_semantic.py` | Per-part refusals, overlay/new-position census, dispatcher coverage of closed entrances, area re-zoning, and the pin-path bug. | 5 s |
| `s7_morph_replay.py` | A byte-carried in-place verb: the documented (16,5) site, plus a certified cliff-bump on every refused coastal cell. | 10 min |
| `s9_morph_reach.py` | The SHIPPED replay (2026-10-09) over s7's 129 cells, through `world-transplant --in-place --dry-run`: 106 replayed, 10 copied, 13 refused on disc 4 (s7's 13). | 8 min |
| `s8_summarize.py` | Prints every headline number below from `out/*.json`. | 1 s |
| `o2_postfix.py [--n 400]` | O2 after the fix: the kit gate vs `s1`'s order-invariant column, the `s5b` edit, and random multi-cell reshapes mirrored the old way and the new way, cracks counted against stock disc 4. | 6 min |

`lib.py` holds the shared instruments: the exact container index (the disc4 lane's `MESH_RE`), `tri_keys` and
`delta_transfer`.

The **all-channel triangle key** is built from the 3 corners' raw vertex-record bytes. That covers pos, normal,
uv and tangent: the 4 channels a `.ff9mesh` carries (`mesh.ff9mesh_bytes`). No stock mesh has any other channel
(`s0`). The corners are rotated to a canonical start that preserves winding, and the key also includes the IDALL
the engine reads (`tangent.x` of buffer corner 0, `WMBlock.cs:210,231`, stock).

## Engine anchors used

Lines are cited at the pinned stock base `6b8bb2d5` (`git show`) and in the patched working tree.

| claim | where | origin |
|---|---|---|
| Ground = the first passing triangle in BUFFER order. IDALL 4078/4088/2040 are skipped, and `ny<=0.1` is skipped. | `Global/WM/WMPhysics.cs:6-47` | stock (no patch touches WMPhysics.cs) |
| A triangle's id is `tangents[triangles[t*3]].x` | `Global/WM/WMBlock/WMBlock.cs:210,231` | stock (same lines in the working tree) |
| The disc tree is `GetDisc() = SC>=11090 ? 4 : 1`, unless a `Disc4` WorldEnvironment condition overrides it | `Memoria/World/WorldConfiguration.cs:234-241`; parser `:358-372`; `_customDiscModifier` `:709` | stock |
| Per-disc prefab path `WorldMap/Prefabs/WorldDisc{disc}/r{y}/…` | `WMWorld.cs:502,755` (stock) / `:540,893` (working tree) | stock |
| The loose override is per PART: `WorldMap/Disc{tag}/0_1/r{y}/Block[x][y] {transform.name}` | `WMWorld.cs:823-825` (working tree) | s34 + s74 (`overrideDiscTag`) |
| Alternate (Form-2) place forms gate on `w_frameDisc == 1`, so on disc 4 the forms never switch | `WorldConfiguration.cs:174-188` | stock |
| Entrance dispatch keys on the walked CELL: `w_worldPos2Cell`, then `WorldEvent(x, z, id)` | `ff9.cs:9106` and `:5197` (stock) / `:9267` and `:5351` (working tree) | stock |
| The `~` debug disc switch reloads onto dispatcher 9009 | `Global/UI/UIKey/Ff9mkDebugMenu.cs:2006-2018` | **s22** (`s22-debug-menu-f6.patch:1648`) |
| Kit gate predicate: a cell is copied only if every real part is byte-identical | `ff9mapkit/world/discmirror.py:276-289`, `:83-87` | kit |
| Kit pin path, which uses substring `read_block` | `discmirror.py:323`; `extract.py:332-337` (`c.endswith(target) or (target in c)`) | kit |

## Calibrations (all asserted, all pass)

- **C1-C5, matcher (`s0`).** Self-compare matches. A whole-triangle shuffle is a permutation and not
  raw-identical. A corner rotation still matches when the 3 corners share `tangent.x`, and a winding reversal does
  not. A 1/256 Y nudge leaves exactly 1 triangle unmatched on each side. An IDALL change is unmatched on all
  channels but matched on geometry.
- **Gate reproduction (`s1`).** discmirror's own `_real_parts`/`_parts_identical` give **84 PASS / 191 SKIP
  (186 by content, 5 by part set)**, which is **189 of 260 land cells refused**. With exact containers the only
  disagreement is (12,0) (SKIP→PASS). That is the D4-17 sea4→sea4f false SKIP.
- **P3 (`s1`).** `discmirror.mirror(dry_run=True)` on a scratch tree logs `SKIP (16, 13): real cell differs …
  ['terrain']` and mirrors (14,1). The Disc4 tree is never created.
- **Tie ground (`s3`).** The disc4 lane's 0.5u lattice reproduces D4-18 exactly: (7,3) 24, (21,13) 16, (22,11) 8
  and (22,13) 8, all with dy 0 at its 1e-4 threshold. The controls (9,17) and (19,14) differ under jitter
  (185 and 237 samples), so the jitter test can fail.
- **K1/K2 (`s4`).** On all **71/71** eligible land cells, the byte mirror, replay and delta produce byte-identical
  `.ff9mesh` payloads, both for the identity edit and for a +2u r16 raise. The r16 raise moved vertices on 37 of
  them; the other 34 have no terrain within 16u of the centre.
- **K3 (`s4`).** End to end through the shipped code on 3 eligible cells:
  - `terrain.reshape(disc=1)`, then the real `discmirror.mirror` copy into scratch;
  - `terrain.reshape(disc=4)` into a second scratch tree;
  - a delta built from the deployed Disc1 file.

  All three are byte-equal, and so is `retarget_tiles` (r12, topo 59).
- **K4 (`s4`) and V3 (`s5`).** A raise on the Iifa re-cut (11,4) and on all 10 sampled D4-08 ridges is **refused by
  delta** (`R-unmatched`, 33-34 triangles). Replay still moves 71-89 disc-4 vertices there, and the ridges are
  flagged RIDGE.
- **K5 (`s4`).** On gate-refused cells, a ring-0 delta with the geometric support test is lawful for 287 of 456
  single-cell raises, and **287/287 are byte-equal to replay**.
- **V1 (`s5`).** The vectorized one-way-wall gate agrees with `terrain.reshape(dry_run=True)` on 80/80 (both discs).
- **V2 (`s5`).** The vectorized delta criterion agrees with the real `delta_transfer` + replay byte-equality on
  150/150.
- **`s5c`.** The border T-junction census reads 0 on a clean eligible pair ((2,11)|(3,11)) and 1 on the same pair
  with one border vertex nudged.
- **`s5b`.** Both weld controls read 0.0: the disc-1 deploy and the disc-4 replay. Stock disc 4 also reads 0.0.

## Findings

**G1 [measurement] The shipped gate refuses 189/260 real land cells. Order-invariance recovers 10 of them, and a
per-part gate recovers 24 for Terrain-only verbs.** (`s1`, `s6` A)
- **(i) Order-invariant gate.** All parts must be exact all-channel multiset permutations. It flips 11 cells
  SKIP→PASS: the 10 reorder-only land cells (3,8), (7,3), (7,7), (8,7), (8,8), (12,16), (18,8), (21,13), (22,11)
  and (22,13), plus (12,0), which is not land and is the prefix-bug false SKIP. Land refused drops 189 → **179**.
- **(i-b) Per-part gate.** Only the edited part has to match. For world-terrain, -retarget and -deploy that part is
  Terrain. Of the 189 refused cells, Terrain is **IDENT on 10 and PERM on 14** (ATTR 20, GEOM 145). Those 24 are
  refused only by sea1 (3), sea3 (1), sea4 (5), sea5 (4) or object (2).

The s34 override is per part (`WMWorld.cs:823-825`), so the other parts keep rendering their own disc-4 bytes.

**G2 [law + measurement] Strategy (i)'s tie-ground difference has measure zero.** (`s3`)
- On the 10 permuted land cells, the 0.5u lattice shows **56 differing samples out of 163,840**.
- Every one has a hit-triangle minimum barycentric weight of **0.0**, i.e. it lies exactly on a shared edge. There
  is a single sheet (`all_sheets` = 1) and dy 0.
- Under **16,384 jittered samples per cell, 0 of 163,840 differ**. The controls with real edits differ.
- This is the first-hit buffer-order rule (`WMPhysics.cs:6-47`, stock) resolving exact edge ties. A player can
  stand exactly on such a line only on a set of measure zero, so the difference is acceptable.

**G3 [law, demonstrated end-to-end] The current per-cell gate CRACKS disc 4 for any multi-cell edit that spans an
eligible and a refused cell.** (`s5b`, `s5`)

Demonstration (`s5b`): a world-terrain raise of +4, r16 at (256,-872).
- It spans the eligible cell (3,13) and the refused cell (4,13). (4,13) is refused only for `['sea1']`.
- `terrain.reshape` writes both Disc1 overrides. `mirror` copies (3,13) and SKIPs (4,13).
- On disc 4 the shared border then shows a **4.0u step** over 10 coincident border vertices.
- Controls: stock disc 4 reads 0.0, the disc-1 deploy 0.0, and the disc-4 replay 0.0.

Population (`s5`): **4,079 of 54,131 reshape edits (7.5%)** centred on refused cells crack under the shipped gate,
and 2,954 of them by ≥1u.

Relaxing the gate without making the mirror atomic **makes this worse**: the crack rate rises to **11.4%** under
the order-invariant gate and **12.5%** under the per-part gate. More eligible cells means more mixed write sets.

The skip is therefore not "harmless conservatism" whenever an edit spans cells. `auto_mirror` passes the written
cells to `mirror(cells=…)`, which gates each one independently (`discmirror.py:213-232`, `:273-289`).

**G4 [measurement] Strategy (ii), operation replay, reaches almost all refused land, but about a third of edits
land on a disc-4 hazard.** (`s5`, `s8`)

The edit population covers 185 of the 189 refused cells. The other 4, Shimmering (6,4), (6,5), (7,4) and (7,5),
have no walkable lattice point on disc 1 (topo 59 place footprint).

Replay:
- passes the verb's own gate on disc 4 for **99.8%** of edits (100% for retarget; the one-way wall refuses
  0.2-0.9% of reshapes);
- is lawful for 100% of edits on 174 cells and for ≥50% on all 185.

**Hazard-free ("clean") replay is 63.7%** overall. It falls with radius:

| radius | raise | lower | retarget |
|---|---|---|---|
| r8 | 81% | 81% | 82% |
| r16 | 58% | 58% | 62% |
| r24 | 38% | 38% | 44% |

RIDGE dominates the hazards: an edit's support touches a D4-08 ridge in 17%, 38% and 57% of raises at r8, r16 and
r24. Then come OBJECT (2-13%), ENTR_LOST (1-7%), ENTR_NEW (≤2%) and LAND2SEA (≤6% for retarget).

**G5 [law + measurement] Replay keeps disc-4 border welds.** (`s5c`, `s5b`)
- `deform_radial`, `flatten_region` and `deform_ridge` move a vertex by a function of its world XZ only
  (`mesh.py:1258-1306`). Coincident border vertices therefore get identical deltas: 220 sampled multi-block replays
  opened a maximum new coincident gap of **0.0**.
- The only weld a smooth reshape can open is a border T-junction, and that happens on either disc. Disc 4 has
  **10 such vertices against disc 1's 11** over 443 land|land pairs, and **no pair has more on disc 4**. A replay
  is never worse at a border than the same edit on disc 1.
- **Inside the blocks (ranked experiment O6, 2026-10-08, `o6_tjunctions.py`): 0 T-junctions on either disc.** Over
  260 land cells, Terrain plus its partner parts, three classes (a Terrain vertex on a Terrain edge, on a partner
  edge, a partner or welded vertex on a Terrain edge), 9,019 re-cut disc-4 Terrain triangles in 144 cells: none. The
  419 plan crossings are identical on both discs and all layered (vertical offset 0.797u or more). The registered
  prediction ("re-cut boundaries add interior T-junctions with small gaps") is refuted in the safe direction: the
  re-cut is conforming. Calibration: the grid finder equals `meshedit.find_tjunctions` on 6 real blocks, each with
  one injected mid-edge split; the 3-point gap model equals the real `deform_radial` (stitch pins, 4u taper) to
  1e-6. An injected junction opens 0.33-2.27u at +4 r16, so one would matter; stock has none.

**G6 [measurement] Strategy (iii), the region-disjoint delta, reaches 37.5% of edits. It never moves or retypes a
disc-4-changed Terrain triangle.** (`s5`, `s4`, `s7`)

The Terrain hazard layers (H1, H2, H4, H5) are made of unmatched Terrain triangles, so a lawful Terrain delta
never moves or retypes one. A lawful delta is the subset of replay that avoids disc-4-changed Terrain.

Changes in **other** parts are a different matter. 2-48 delta-lawful edits per class sit under a changed disc-4
**Object**: 32 of the r8 raises and 43-48 retargets (`reach_summary.json:delta_v_lawful_but_touching_hazard`).
The delta gate therefore also needs the all-parts footprint.

| delta variant | lawful edits | cells ≥50% | cells 100% |
|---|---|---|---|
| parametric-exact (`delta_v`) | **37.5%** (53% r8, 30% r16, 15% r24) | 67 | 10 |
| footprint gate at centre distance > r+m, m=0 | 34.1% | | |
| footprint gate, m=4 | 25.8% | | |
| footprint gate, m=8 | 19.3% | | |

`delta_v` has a lawful edit on 178 of 185 cells.

For the byte-carried verb (cliff-bump, certified on disc 1) on 129 refused coastal cells:
- replay passes its own gates on disc 4 for **116**. The 13 refusals: 7 fold a tile at the waterline at the same
  depth, 5 have no window ("not one connected cliff-base run"), and 1 hits the clearance gate.
- delta is lawful for **55**, and **delta == replay as a triangle multiset on 55/55**.
- Every delta refusal has XZ distance 0 to the footprint. Every lawful delta has a clearance of **≥2.08u**.
- The documented (16,5) minted-beach site is gate-ELIGIBLE. There, delta == replay on all 5 touched parts.

**G7 [law + measurement] A delta keyed on disc-1 vertex positions is blind to new disc-4 geometry, so the footprint
test must be geometric (XZ).** (`s4` K5, `s6` B)
- **8,616 of 13,746 (63%)** disc-4-only terrain triangles have a corner at a position no disc-1 vertex has.
- 4 floating components (41 triangles, mostly topo 59) share no corner at all with matched geometry.
- K5 caught the failure: at (19,11), a raise passed vertex-sharing closure but left disc-4-only tri #190 (topo 48)
  unmoved under a 2u lift. 1 of 288 transfers was wrong.
- Adding "no unmatched corner strictly inside the support" (parametric) or "R∪A XZ-disjoint from unmatched
  triangles" (byte-carried) fixes it. Margin needed:
  - parametric edits: **0** around the support (exact: V2 150/150, K5 287/287);
  - byte-carried edits: **strict separation**. 1-ring vertex closure and XZ disjointness agreed on 129/129 cliff
    bumps, and the observed minimum lawful clearance was 2.08u.

No extra border margin is needed when the edit is applied atomically to every block it touches. morph_in_place's
IN-PLACE-FRAME gate (`transplant.py:3343-3361`) keeps frame vertices byte-unchanged anyway.

**G8 [law, source + bytes] SEMANTIC TRAP: entrance re-stamps on disc-4 closed places.** (`s6` C)

Disc 4 removes event tiles from **24 disc-1 entrance cells**. The disc-4 free-roam dispatcher **9008
(EVT_WORLD_WORLD08) has an object-0 cell trigger for 0 of them**. The default dispatcher **9009 still has triggers
for 22**, with live arms. Examples:
- Esto Gaza (11,7) → case 48 → field 2300
- Desert Palace (37,8) → case 28 → field 2212
- Conde Petie (28,10/11) → case 33 → field 1500
- Ice Cavern (37,24) → case 4 → field 300
- South Gate (37,28) → case 8 → field 807
- Cleyra → case 93, which has no switch arm

All 13 free-roam switches carry cases 2-60, so 9008's switch still has these arms. Only the object-0 triggers are
gone. Consequences:
- **A tile-only re-stamp** (a replayed or delta'd `world-retarget --event`) is inert in 9008 but **fires in 9009**.
  9009 is the default arm and the `~` disc-switch reload target (`Ff9mkDebugMenu.cs:2006-2018`, s22).
- **A replayed `world-entrance`**, which authors a NEW trigger in every dispatcher whose switch carries the case,
  **re-opens the place in 9008 too**. It then routes to the 9008 arm at disc-4 story state (for example Esto Gaza
  2300).

Shimmering's disc-4 event-2 tiles are on its **Sea4** part, not on Terrain (0 terrain event cells on disc 4).

**G9 [measurement] SEMANTIC TRAP: disc 4 re-zones area on unchanged geometry.** (`s2`, `s6` D)
- **44 terrain blocks (1,191 triangles) change the area field with byte-identical positions.** The region is
  contiguous, x 12-22 by y 9-18 (the south-east continents).
- Main transitions: 0→7 (830 triangles), 7→0 (114), 0→22 (85), 0→14 (47), 6→7 (38).
- Area drives the encounter zone, location text and a camera flag (`ff9.cs:9229-9262` / `:3752-3759` /
  `:2771-2772`, stock; operators F5).
- A delta refuses these triangles, because all-channel matching treats them as unmatched.
- A replay of `world-retarget --topograph` keeps disc 4's area, because `retarget_tiles` keeps unset fields
  (`mesh.py:1363-1422`).
- But a replayed `world-entrance` stamps `area=case` by default, **overwriting disc 4's re-zone**.

**G10 [law, demonstrated] The pin path's `read_block` prefix bug pins the wrong mesh.** (`s6` E)
- Setup: a dry-run mirror of a scratch ocean cell whose `Donor.txt` is `19,11`.
- Result: **RiverJoint is pinned twice and River 0 times** (`Block[1][0] RiverJoint.ff9mesh` ×2).
- The reason: `discmirror.py:323` resolves `river` → RiverJoint through `extract.py:335`, and `bm.name` then names
  the RiverJoint file.
- On disc 4 such a cell would render the donor's **disc-4 River** as an unpinned free-rider.
- Control: donor (12,10) pins each of its 4 parts once.

**G11 [measurement] Every in-place verb already exposes a disc-4 replay entry point. What is missing is automation
and atomicity.**
- These verbs all read pristine stock on `--disc` and deploy to `Disc{disc}`:
  - `world-terrain --disc` (`terrain.py:88-172`; `cli.py:9140+`);
  - `world-deploy --disc` (`cli.py:4090`, flag at `:8973`);
  - `world-retarget --disc` (`cli.py:4265`, `:9022`);
  - `world-entrance --disc` (`cli.py:9877`);
  - `world-transplant --in-place --disc` (`cli.py:4802-4810` passes `args.disc` to every coastmorph builder and
    to `morph_in_place`).
- `auto_mirror` skips `src == dst` (`discmirror.py:178`), so a manual `--disc 4` run is today's replay.
- Nothing runs it automatically, and nothing ties the two runs into one edit.

**G12 [measurement, side observation for the operators lane] world-terrain's one-way-wall gate mostly refuses
slopes it did not create.** (`s5d`, `s5`)
- On disc 1 it refused 4,978 of 17,507 r8 raises and 11,701 of 17,507 r24 raises at walkable lattice points of
  refused cells. V1 confirms these numbers come from the real gate.
- **99.35% of 2,000 sampled refusals** come from an edge that was already above the 79.4° ceiling in stock.
- `_walk_gate` scans every edge of every triangle that has a moved vertex (`terrain.py:60-74`), including stock
  cliff and wall edges.
- Implication: the gate should compare the post-edit slope against the pre-edit slope, or only score edges that
  have a moved endpoint and whose slope increased.

## Reconciliation: operators F18 vs disc4 D4-01 (`s2`)

- **F18** (`operators/disc_tree_channels.py:30-52`) compares Terrain **index-aligned** on the 64 equal-vcount
  blocks. Reproduced from its own JSON: area 44, topograph 51, event 11 blocks. **11 / 14 / 0 of those blocks are
  pure permutations** (D4-18), where index misalignment reads as an IDALL change. Most of the rest mix misalignment
  with unrelated real edits.
- **D4-01** (`disc4/census.py`) classifies each (block, part) by its most severe change. Terrain "ATTR:id" (3) and
  "ATTR:id+uv" (3) are only the 6 blocks whose sole change is IDALL. IDALL edits on the kept triangles of RETOPO
  blocks are hidden behind the RETOPO label.
- **Order-invariant truth** (geometry-matched triangle pairs, all 260 terrain blocks):
  - **area changes in 44 blocks** (1,191 triangles). Only **17 of these are among F18's 44**; the equal count is a
    coincidence;
  - **topograph in 11 blocks** (36 triangles);
  - **event in 7 blocks** (32 triangles).
- Re-cut geometry also adds or drops field VALUES (a set compare): topograph in 82 blocks, area in 23, event in 21.
- Neither earlier count is "IDALL differs per disc". F18 over-counts through permutations and misses re-cut
  blocks. D4-01 under-counts by its severity rule.

## Hazard and trap list (what a correct geometric transfer can still get wrong)

| # | hazard / trap | size on disc 4 | replay | delta |
|---|---|---|---|---|
| H1 | RIDGE: topo-49 bark ridge laid over disc-1-walkable ground (D4-08) | 1,847 triangles / 109 cells | lands on it (17-57% of reshapes): raises or lowers the ridge with the ground | refuses |
| H2 | ENTR_LOST: event tiles removed (D4-14, Cleyra D4-12) | 111 triangles / 19 cells, 24 cells (32u) | geometric ops are safe. **Entrance/event re-stamps re-open the place (G8)** | refuses |
| H3 | OBJECT differs (D4-13 promotions at (20,10)/(14,17), Cleyra adds, (13,4)/(18,11) removals) | 2,397 triangles / 37 cells | Terrain moves under a different disc-4 object (F3: the object is never moved) | refuses only with the all-parts footprint. The Terrain-only footprint lets 32 r8 raises through (G6) |
| H4 | LAND2SEA (Shimmering sunk D4-11) | 522 triangles / 19 cells | a retarget turns disc-4 seabed tiles to land topographs | refuses |
| H5 | ENTR_NEW (Iifa grown; Treno grown) | 188 triangles / 6 cells | a stamp or raise lands on disc-4-only entrance tiles | refuses |
| T1 | area re-zone on unchanged geometry (G9) | 44 blocks | `world-entrance` replay overwrites disc-4 areas | refuses |
| T2 | Form 2 never selected on disc 4 (`WorldConfiguration.cs:174-188`, stock), and disc-4 Form-2 meshes are stale (forms F11) | 26 switchable cells | a Form-1 edit reaches the only form disc 4 uses | n/a |
| T3 | `~` disc switch loads 9009, not 9008 (G8) | n/a | the in-game view is not faithful for entrance semantics | n/a |

## Recommended discmirror design (function-level)

**Status 2026-10-08 (ranked experiment O2; `o2_postfix.py`):** 1 BUILT (`discmirror._tri_multiset`; the exact
container came with defect 1); 2 NOT BUILT, deliberately: since defect 5 a Terrain edit HOLDS the vertices welded to
its partner parts, so a copied Terrain edit fits only the partners it was built against, and on a cell whose other
parts differ across discs it can tear; replay covers those cells instead; 3 BUILT (`mirror(atomic=True)`, per
4-connected group of written cells, what `auto_mirror` passes); 4 BUILT for `world-terrain` and `world-deploy`
(`replay=`); the hazard check is a per-cell WARN naming how disc 4 differs, not the H1-H5 layers; retarget and entrance have no
replay yet (single-cell writers: they cannot crack, they stay un-mirrored); the in-place morph's replay is BUILT
2026-10-09 (`world-transplant --in-place` re-runs itself with `--disc 4`, every builder on disc 4's bytes; its dry run
previews it; in game: terrain study round 9); 5 NOT BUILT; 6 DONE with defect 1.

1. **`_parts_identical(blk, part, …)` becomes order-invariant and exact-container.**
   - Compare multisets of `lib.tri_keys` (canonical-rotation, all-channel, with the engine IDALL) through an
     exact-match reader. The disc4 lane's `d4lib.mesh_objects`/`MESH_RE` is enough.
   - This fixes (12,0) and recovers the 10 permuted land cells. The tie cost is measure zero (G2).
2. **Gate per edited part, not per cell.** `mirror(…, cells)` becomes `mirror(…, writes={cell: {parts}})`. Only the
   parts a writer actually overrode are compared (+24 cells for Terrain verbs, G1). Donor.txt cells keep the
   whole-cell rule; they are ocean, so they pass anyway.
3. **Make the mirror EDIT-ATOMIC (mandatory before 1 or 2).**
   - `auto_mirror` receives one writer call's write set. If any cell in it is not lawfully carried (copy, replay or
     delta), it carries **none** of the edit to Disc4 and prints one loud `NOT MIRRORED (would crack at …)` line.
   - The current per-cell SKIP produces 7.5-12.5% cracked edits (G3).
4. **Add a replay hook.** Each in-place writer passes `replay=lambda disc: <its own library call with the same
   world-space params, deploying to disc>` into `auto_mirror`. For a refused cell, `auto_mirror` calls
   `replay(4)`, which re-runs the verb's own gates on disc-4 stock (G4, G5). The library calls are:
   - `terrain.reshape(disc=4)`;
   - `retarget_tiles` on `read_block(disc=4)`;
   - the coastmorph builder with `disc=4` + `morph_in_place(disc=4)`;
   - `author_entrance(disc=4)`.

   Before deploying, replay runs a **hazard check**: the support against the disc-diff hazard layers (H1-H5). A
   geometric verb on H1/H3/H4/H5 is a WARN by default. An IDALL verb with `event`/`area` on H2 or T1 is REFUSED by
   default; overriding needs an explicit flag.
5. **Add a delta path, only for byte-carried writers that have no replay** (today only `world-mesh-build`'s
   Object). Use `lib.delta_transfer` semantics:
   - every removed triangle must have an exact disc-4 counterpart;
   - 1-ring vertex closure;
   - **plus an XZ footprint test**: R∪A strictly disjoint from the unmatched triangles of the edited part, of Object and of
     Terrain (G7).

   Keep it as a **cross-check oracle** for replay as well: whenever both are lawful they must agree (55/55, 287/287).
6. **Fix the pin path.** Replace `X.read_block(dx, dy, part=part)` at `discmirror.py:323` with an exact-container
   read (anchored `block[x][y] {part}(.asset)?$`), and take `part_name` from the container rather than from
   `bm.name` (G10). The same exact read should back `_parts_identical` and every `extract.read_block` caller
   (D4-17).

**Which strategy each in-place verb should use:**

| verb | strategy |
|---|---|
| `world-terrain` / `world-deploy` (reshape) | **REPLAY** (parametric, cheap, already `--disc`) with a hazard WARN. Delta is a strict subset and is not needed. |
| `world-retarget` | **REPLAY** for `--topograph`. For `--event`/`--area`, REFUSE on H2 (closed entrance) and T1 (re-zoned area) unless explicitly forced. |
| `world-entrance` | **REPLAY** of tiles + building only when the disc-4 cell is not ENTR_LOST. The `.eb` layer is already disc-agnostic (one shared dispatcher set), so re-authoring a trigger re-opens a closed place in 9008 (G8): refuse by default. |
| `world-transplant --in-place` (coastmorph tweaks) | **REPLAY** via the builders with `disc=4`, which pass their own gates 90% of the time (116/129). Where replay refuses (the window is absent or the depth folds on disc 4), delta does not rescue it (0/13). Report it as disc-4-unreachable. |
| `world-mesh-build` (Object, byte-carried OBJ) | **DELTA** with the XZ footprint gate over the Object and Terrain footprints. |

## Contradictions with recorded knowledge

1. **Operators F18** (`operators/out/disc_tree_channels.json`; `disc_tree_channels.py:30-52`) counts area, topograph
   and event differences index-aligned. 11/14/0 of its blocks are permutation artifacts. The order-invariant
   counts are area 44 (only 17 shared), topograph 11 and event 7 (`s2`).
2. **disc4 NOTES §4**, "order-sensitive … over-conservative, which is harmless" (D4-16), is right for a single-cell
   edit and wrong for the mirror as a whole. Per-cell skipping of a multi-cell write set cracks disc 4 (G3, 4.0u
   demonstrated), and relaxing the gate alone increases the cracks. The module docstring (`discmirror.py:12-16`)
   presents the skip as the safe behaviour.
3. **`studies/overworld-topography/README.md:764-766`** says "(16,5) real cell → disc 1 only (no mirror)". (16,5)
   is gate-ELIGIBLE (byte-identical across discs, `s1`/`s7`), so today's `auto_mirror` would mirror it. The README
   reflects the pre-`auto_mirror` state.
4. **Memory `project-ff9-overworld-worlds.md`** ("the ~ disc switch reloads onto 9009"; disc-4 free roam = 9008) is
   right. What it does not record: 9009 still carries the stock triggers for 22 of the 24 entrance cells disc 4
   closed, while 9008 carries none. A debug-switch view of disc 4 therefore re-arms closed entrances wherever event
   tiles exist (G8).

## One in-game probe (designed, NOT run)

The probe is a replayed raise on a refused cell, viewed after the debug-menu disc switch. It needs a bench mod
folder and 2 deploys.

1. `world-terrain --at 256 -872 --radius 16 --raise 4 --mod-folder <bench>` runs on disc 1, with auto-mirror. The
   log must show `SKIP (4, 13): … ['sea1']` and mirror (3,13).
2. In-game: `~` → World → disc 4. This reloads onto 9009, which is fine here because the probe is purely
   geometric. Teleport to (256,-872), then take a `tools/game_snap.ps1` frame and harness ground-Y readouts at
   (254,-872) and (258,-872).

   **Predicted:** a ~3.8u wall along x=256 between about z -856 and -888. The ground-Y difference across the
   border is about 3.8u.
3. `world-terrain … --disc 4` (the replay), then reload the overworld on disc 4. **Predicted:** a smooth +4u hill
   with no step. Readouts on both sides of the border agree to <1e-3, and the centre is stock disc-4 Y + 4.0.

One probe tests G3 (the crack) and G4/G5 (replay heals it and welds).

## Open questions

- In-game confirmation of G3/G5: the probe above.
- Does a replayed raise over an H1 ridge look acceptable? The owner decides, as with the D4-09 identity of the
  ridges.
- What the 9012 cutscene state and the region-key defaults do on disc 4. Which story beats actually land in 9009
  rather than 9008 decides how live T3/G8 is in normal play, as opposed to the debug switch.
- Rendering effect of buffer order on coplanar overlaps (z-fighting) for strategy (i). Ground is shown to be
  measure-zero; render order is not measured.
- An interior (non-border) T-junction census of disc-4 re-cut seams. A replayed smooth reshape opens a second-order
  gap at any T-junction inside its support on either disc. The border census found none added on disc 4, but the
  interior was not counted.
