# Verifying lane `gap_disc4_edit_reach`

This is an adversarial verification pass. It was read-only on the install, the Memoria clone, memory and tracked
files. Nothing was deployed or built. The only writes were `verify_*.py`, `out/verify_*.json` and this file, plus
scratch trees under the session scratchpad (`verify_gap_disc4/`).

## Reproduction

**Every lane script was re-run** (`s0` through `s8`) against an **independently rebuilt decode cache**:
`GAP_DISC4_CACHE=<scratch>/verify_gap_disc4/cache`, via `s0 --rebuild`.
- All 12 `out/*.json` came back **byte-identical** to the lane's originals. The originals were snapshotted first.
- All asserts pass.
- `s7` finished well inside its 600 s wall-clock guard: all 145 refused coastal cells were scanned, and 129 of them
  have a certified window.

**Every cited engine and kit line was re-opened.**
- Engine: stock `git show 6b8bb2d5` vs the patched working tree.
- Patches: `memoria-patches/*.patch`.
- Kit: `ff9mapkit/ff9mapkit/world/*`, `cli.py`.

## Verdicts

| id | verdict | note |
|---|---|---|
| G1 | corrected | All counts reproduce. The breakdown wording is wrong, though. Of the 24 Terrain-IDENT/PERM refused cells, **10 are refused only by the Terrain permutation itself** (they are the order-invariant flips, with no other part differing). The parts sea1 3 / sea3 1 / sea4 5 / sea5 4 / object 2 are **15 refusing parts across the other 14 cells** ((15,7) has two). So the per-part gate's increment over the order-invariant gate is +14, not +24. |
| G2 | confirmed | Reproduced exactly: 56 lattice samples, min barycentric weight 0.0, sheets_max 1, dy 0. Jitter gives 0/163,840; the controls give 185 and 237. `WMPhysics.cs:6-47` is stock, and no patch touches it. `WMBlock.cs:210,231` is stock (s71/s75 mention it only in comments). Caveat: "measure zero" assumes continuous positions. Spawn or teleport points on round coordinates can sit exactly on an edge. The cost there is benign either way: the engine picks one of the two adjacent stock IDALLs. |
| G3 | confirmed | `s5b` reproduces the 4.0u step over 10 coincident verts, and its 3 controls read 0.0. Population numbers: 4,079/54,131 = 7.54%, ≥1u 2,954, orderinv 6,170 (11.4%), partgate 6,760 (12.5%). `auto_mirror` passes one cell set (`discmirror.py:202-232`), and `mirror` gates each cell independently (`:273-289`). The rate is conditional on the synthetic population: edits centred on refused cells. **Counterexample hunt made it worse; see A1:** the writer itself is not edit-atomic either. |
| G4 | confirmed | `reach_summary.json` reproduces byte-identically: replay 0.998, clean 0.6373, 174/185 cells all-lawful, RIDGE 17.4/38.2/57.0%. The 4 missing cells are exactly Shimmering (6,4), (6,5), (7,4) and (7,5). Retarget's replay "lawful" (≥1 tri) is trivially 100%, as stated. |
| G5 | confirmed | T-junctions: disc 1 has 11, disc 4 has 10, and 0 pairs have more on disc 4. The weld-gap check (0.0 over 220 edits) is near-tautological, because the deform is a pure function of world XZ (`mesh.py:1258-1306`). The T-junction census is the substantive part. |
| G6 | confirmed | 37.5% / 34.1% / 25.8% / 19.3% reproduce. `s7`: 116 / 55 / 55/55, 74 refusals all at XZ distance 0, minimum lawful clearance 2.08u, 0 of the 13 rescued. Stock terrain meshes are unindexed (0 of 520 share a vertex), so `retarget_tiles` cannot spill IDALL onto a neighbouring unmatched tri. That makes the "never retypes" claim sound for retarget too. Population note: the "129 refused coastal cells" are the 129 of 145 that carry a disc-1-certified cliff-bump window. |
| G7 | confirmed | 8,616/13,746 tris have ≥1 new corner. 4 floating components / 41 tris. K5 shows 1/288 wrong under vertex-only closure. Refinement (`verify_newpos_blind.py`): only **3,583 (26.1%) have all 3 corners at new positions**, and those are invisible to vertex closure whatever the edit is. Tris with 1-2 new corners are caught whenever an old corner moves, so 63% is an upper bound on the blind class. The law (an XZ footprint is required) stands. |
| G8 | corrected | The core result reproduces and the counterexample hunt strengthened it. 24 lost cells, WORLD08 0, WORLD09 22. The cell-tag packing matches stock `ff9.cs:2233`. `verify_w08_cases.py` finds **no Map.Byte[39]=case ASSIGNMENT for any of the 18 lost-place cases anywhere in WORLD08**. A first pass that matched the bare `D5 27 7D` prefix wrongly picked up entry-1 tag-11's `Byte[39] <= 16/32/48` range comparisons; that was fixed. Corrections: (a) **9** free-roam dispatchers carry the AREA switch (cases 2-60), not "all 13"; WORLD01/04/06/12 have none. (b) The working-tree WorldEvent call is `ff9.cs:5352`, not 5351. (c) Of the 22 WORLD09 triggers, **16** carry only the stock guard (`Map.Byte[24]==100 && !Global.Byte[190]`). Desert Palace (37,8) is also gated on SC>=9890 (`B_GE`: stock `EBin.cs:755-762`, working tree :776-784), which is true on disc 4. Fossil Roo (28,12) is gated on sysvar210==3. The 4 Cleyra cells share one SC-branched body for case 93, which has no arm. So "live arms" holds for about 17-18 of 22. |
| G9 | corrected | Counts reproduce, and they are robust: a per-geometry-key multiset compare gives the same 44 blocks / 1,191 tris, with 0 duplicate geometry keys. The region is one 8-connected cluster (7 components 4-connected). **Citation fix:** `ff9.cs:9229-9262` and `:3752-3759` are WORKING-TREE lines, and the encounter function there includes the s60 patch. In stock they are `ff9.cs:9074-9104` and `:3744-3751`; `:2771-2772` matches both. The area semantics are stock. `entrance.py:1027` (`area=the_case if set_tile_area`, default True) confirms the overwrite. |
| G10 | confirmed | Reproduces: RiverJoint ×2, River ×0. The (19,11) River differs across discs (69 vs 68 tris), so an unpinned River does render differently. Scope: `read_block(part='river')` mis-resolves at disc-1 (19,11) and at disc-4 (5,16). The documented Daguerreo donors (5,15)/(5,16) resolve correctly on the disc-1 read the pin path uses. |
| G11 | corrected | `cli.py` 4090/8973, 4265/9022, 9877 and 4802-4811, plus `discmirror.py:178`, all verified. One overstatement: `world-entrance` does **not** read pristine disc-4 stock. `author_entrance` reads `read_block_stacked` (`entrance.py:996`), so it stacks on any deployed Disc4 override unless `--fresh` is passed. `world-terrain` (`terrain.py:141`) and `world-retarget` (`cli.py` `W.read_block`) do read pristine. |
| G12 | confirmed | `s5d` reproduces 1,987/2,000 (99.35%) on its proxy sample: any lattice point, single block. **On s5's actual population** (`verify_wallgate_population.py`; 50,911 refusals, matching s5 exactly), the worst edge was pre-existing in **98.9%**, and every over-ceiling edge was pre-existing in **93.5%**. A gate that refuses only edges made steeper would pass **62.6%** (r8 78%, r16 66%, r24 54%). "Most" holds, but the unlock is about 63%, not about 99%. |
| G13 | confirmed | 51/44/11 reproduce from the operators JSON (index-aligned, `disc_tree_channels.py:25-52`). The perm overlaps 11/14/0 reproduce. The order-invariant counts 44/11/7 (1,191/36/32 tris) are robust to pairing (see G9), and the overlap with F18's area blocks is 17. D4-01 census on 0_1 Terrain: ATTR:id 3 + ATTR:id+uv 3, RETOPO 143. The lane is right that F18 over-counts through permutations. |
| G14 | corrected | (16,5) shipped PASS reproduces, and `s7` part A gives a clean disc-1/disc-4 replay with delta==replay on all 5 parts. That is trivial here: every part has 0 unmatched tris. The README text is at `studies/overworld-topography/README.md:768-769`, not 764-766. `auto_mirror` landed at b7d243511 (2026-07-19), after the (16,5) deploy at b055ab8c9 (2026-07-15), so the README predates it, as claimed. |

## Additional findings

**A1. The WRITER is not edit-atomic on disc 1. This is upstream of G3.**
- `terrain.reshape` deploys each block inside its loop, straight after that block's own wall gate
  (`terrain.py:126-167`). A later block that refuses raises `ValueError` after the earlier blocks were already
  written, and `auto_mirror` never runs.
- On s5's population (`verify_writer_atomicity.py`), **12,954 of 50,911 (25.4%)** disc-1-refused reshapes leave ≥1
  block written.
- End to end: a raise of +4 r16 at (180,-500) into scratch leaves `Disc1/.../Block[2][7] Terrain.ff9mesh` behind,
  refuses at (2,8), and opens a **0.62u disc-1 border step**.
- Implication for the design: edit-atomicity must be enforced by gating every touched block before writing any.
  Making only the mirror atomic is not enough.

**A2. Hazard T2 ("Form 2 never selected on disc 4") is overstated.**
- ChocoboParadise (0,0)/(16,14)/(9,17) and MognetCentral (16,1)/(13,4)/(14,5) gate on `gEventGlobal(101)` bits,
  not on `w_frameDisc` (stock `WorldConfiguration.cs:183-184, 189-190`; `ff9.cs:9196-9206`).
- So those 6 cells can render Form 2 on disc 4 (and on discs 1-3), and a Form-1 edit does not reach them there.

**A3. Two calibrations cannot fail, and one script has a latent trap.**
- K1/K2 (71/71 identity and raise) are tautological. Eligible cells are byte-identical by the gate's own
  definition, so these checks only test for code bugs.
- The informative calibrations are K4, K5, V2 and the s5b controls.
- `s7_morph_replay.py:207` has a 600 s wall-clock cut-off that would silently truncate the population on a slower
  host. It did not trigger in either run.

**A4. Minor citation drift.**
- The working-tree `ff9.cs` WorldEvent call is at :5352.
- Everything else cited was verified at the stated lines: `WMWorld.cs:502/755` (stock), `:540/893/823-825`
  (working tree), the stock `WorldConfiguration.cs` lines, `Ff9mkDebugMenu.cs:2006-2018`, s22 patch `:1648`,
  `discmirror.py:83-87/178/213-232/273-289/323`, `extract.py:335`, and `transplant.py:3303-3368`.

## Verify scripts

All run from `ff9mapkit/` with `GAP_DISC4_CACHE` honoured.

| script | output |
|---|---|
| `verify_area_pairing.py` | `out/verify_area_pairing.json` |
| `verify_writer_atomicity.py` | `out/verify_writer_atomicity.json`; scratch `verify_atomic/` |
| `verify_dispatch_triggers.py` | `out/verify_dispatch_triggers.json` |
| `verify_w08_cases.py` | `out/verify_w08_cases.json` |
| `verify_newpos_blind.py` | `out/verify_newpos_blind.json` |
| `verify_wallgate_population.py` | `out/verify_wallgate_population.json` |
