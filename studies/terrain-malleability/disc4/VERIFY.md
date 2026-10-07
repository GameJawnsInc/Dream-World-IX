# Adversarial verification of lane `disc4`

Read-only verification of `NOTES.md` and the lane's 20 findings. The game install, the Memoria clone, memory and
tracked repo files were not modified. New files are limited to `verify_*.py` in this directory and their
`out/verify_*.json` outputs.

## How it was checked

- **Re-run.** All 16 lane scripts were re-run in order from `ff9mapkit/`, and every one exited 0. Every JSON and
  PNG they wrote is byte-identical to the lane's original output, and the census stdout matches line for line.
  `calibrate.py` passes 12/12 synthetic checks and 7/7 known cases. The noise self-test also passes.
- **Instrument checks.**
  - `raw_sig` reads real vertex bytes: `m_DataSize` is `bytes`, 99,216 B for (4,7). So "IDENTICAL" is not a
    vertex-count proxy.
  - All 2,199 worldmap meshes and all 962 prefabs live in one serialized file (`CAB-2ab3…`). PathIDs are unique,
    so PathID-keyed material and mesh identity is sound.
- **Engine lines.** Every cited line was re-opened at the stock base `6b8bb2d5` (`git show`) and checked against
  the patch stack:
  - `WorldConfiguration.cs:207-212,223-232,234-240`
  - `WMWorld.cs:502,518-521,755,1060-1062`
  - `WMWorldPrefabMaker.cs:36,120-127,198-208`
  - `WMPhysics.Raycast`, which is first-hit in buffer order
  - `ff9.cs:2335` (`m_GetIDEvent` = bits 14-15)

  All of these say what the lane claims. `WMWorld.cs` is heavily patched (s34/s71/s73/s74/s75), but none of those
  hunks changes the disc-1/4 path, `GetDisc` or the prefab maker. The only `WorldConfiguration` hunk (s75) is a
  Path-D-gated early return in `UseMist`.

## Verdict table

| id | verdict | why |
|---|---|---|
| D4-01 | confirmed | 672/20/72/3/226/3/2 of 998 keys; 85 identical, 10 reorder-only and 180 real-change blocks; terrain 81/260 identical. All reproduced. Caveat: 6 of the 180 blocks count as changed only through UV nudges of 1/256 or less (14 keys, e.g. (8,15), (4,10), (11,12)), so 174 have more than texel-level edits. Memory's "mostly byte-identical" is wrong. |
| D4-02 | confirmed | `WMWorldPrefabMaker.cs:36` builds the 0_2 path; `:120-127` binds Terrain2/Object2; `:198-208` gives TerrainForm2/ObjectForm2; `WMWorld.cs:518-521` registers Form-2 walkmeshes. Shipped slots reproduce. `extract.py:11` and `cli.py:8960` are wrong. **Fix to the implication:** the engine never reads loose files under `0_2`. The s34 override key is `WorldMap/Disc{d}/0_1/r{y}/Block[x][y] {transform.name}`, so a Form-2 override would be `0_1/... Terrain2`. |
| D4-03 | corrected | The six prefab diffs, identical transforms and shared materials (same CAB plus PathID) all hold. But "disc-4 prefabs reference their own disc-4 mesh copies" is false for the 205 open-ocean prefabs. Their Sea4 and Sea6 children (410 refs) point at the **disc-1** (12,0) meshes on both discs. `prefab_census.py` hides this because it normalises the `disc` segment. |
| D4-04 | corrected | 68,168→69,204 tris, 88.3/3.8/7.9%, median 9.3%: all reproduced. But "88.3% kept **byte-exact**" counts position-only matches. 4,727 of those carry id, uv or normal edits; **all-channel byte-exact is 81.4%** (`verify_kept_exact.py`). The grammar conclusion (local re-cut) stands. |
| D4-05 | **refuted** | The 40-68% "on disc-1 XZ" pool mixes in trivial corners: 28.4% are corners of re-heighted triangles (same XZ by definition) and 21.7% are cut-boundary corners shared with kept triangles. The **interior** new corners (13,493) land on disc-1 vertex XZ only **18.6%** of the time, on the 4u lattice **11.7%** and on integers 12.6%. The stock baseline is **35.4%** on 4u over all 251,817 disc-1 vertices. New interior geometry is *less* on-grid than stock, i.e. largely free-form (`verify_lattice.py`). |
| D4-06 | corrected | 774/774 calibration, 67 changed edges, 63 gap-0 and none worse: all reproduced. But `weld_gap.gap()` silently skips along-coordinates that one side does not cover. All 5 "exact→open T-junctions" have uncovered stretches of 4-7u: one side's terrain border extends where the other has none. A ground probe shows the neighbour covers those stretches with Sea3 (y=0), River (y 15.23) or the new Cleyra Object (5.69-5.80 vs terrain 5.56). These are terrain-meets-other-part seams with steps of 0 to about 0.24u, **not T-junctions**. Likewise 26 of the 37 disc-1 "gap-free" open edges are uncovered extent mismatches, so only 11 are covered T-junctions (`verify_weld_uncovered.py`). |
| D4-07 | **refuted** | `uv_coverage.py` prints only topographs with 50 or more new triangles, and its own JSON contradicts the law. Topographs **30, 48, 53, 54, 55, 56 and 57** (52 triangles at (3,9), (4,9), (6,4), (7,5), (21,10), (16-17,9), (17-18,15) and elsewhere) are **100% virgin**. The virgin union is **19,265** painted texels, not 346. Even against disc-1 Form-1 *plus* Form-2 terrain coverage, **10,372** texels are used only by disc-4 terrain (`verify_virgin_art.py`, `verify_virgin_form2.py`). The topo-49 rock figure (0.18%) is right. Whether that art was painted *for* disc 4 cannot be decided offline: the atlas is shared. |
| D4-08 | corrected | 53 components, median elongation 6.4, peak rise 1.22-2.97u, the 64.1% bark window, and 34→116 blocks / 502→2,095 tris all reproduce. Three bounds are overstated. 4 of the 15 profiled cross-sections are **6.5-12u** wide at half height, with 0.67-1.38u of change beyond ±6u. One narrow ridge (1313.6, −358.7) shows 0.64u beyond ±6u. The disc-1 bark-tile triangles are **not all topo 49**: 101 of 502 are topo 59/58 (Wind Shrine (8,14), Conde Petie Mountain Path (13,3), Earth Shrine (18,5), (14,6)). |
| D4-09 | unverifiable | A hypothesis that only the owner or an in-game look can settle. Weak counter-evidence: on disc 1 the same tile also textures topo-59 place footprints, so it is not root-exclusive. |
| D4-10 | corrected | Entrances 489→1,662 with none lost, every dy up (mean +1.08 to +1.28, max 2.92), 59→60 on exactly 98 samples per block: all reproduced. Two corrections. The **re-heighted** area share is 48/82/85/82%; 56-97% is the cut-plus-re-height ("touched") share. The (11,4) tree Object also shifts up to 3.4u in XZ, so it is not a pure lift. |
| D4-11 | confirmed | 1,856 samples Terrain→Sea4; terrain 287→80 and 187→58; Sea4 +25/+30/+83/+51; dy mean −3.9 to −4.2 (max 11.0); event ids 1→2; no prefab diff. All reproduced. |
| D4-12 | corrected | (13,11), (13,12) and (14,12) lose every entrance tile, the topo 59→41 retype and the 212 blocked→walk samples reproduce, and both objects are ADDED. But **(14,11) keeps 19 of 36** entrance samples (its verdict is "reshaped"), so "every in-block entrance tile is removed" is false for one of the four blocks. (14,12)'s added Object shares 11/36 triangles with disc-1 Form 2, not 15. |
| D4-13 | confirmed | (20,10) object 180/180 against disc-1 Form 2 vs 116/232 against Form 1; (14,17) 121/121 vs 65/113; (21,10) loses 35 samples, now topo 57. The match is by position; UVs were not compared. |
| D4-14 | confirmed | The 16 CLOSED blocks reproduce exactly. "Most non-Cleyra lost tiles are topo 49 with a rise" holds for 9 of 13. Exceptions: (16,11) and (18,11) go to topo 0, (21,10) goes to sea 57, and (18,13) is a minority-49 case. Several of the rises are small (+0.19 to +0.5u), i.e. a retype rather than burial under a 1-3u ridge. Block closure is not place closure (P2 is open). |
| D4-15 | confirmed | `UseMist` is stock (`:223-232`); s75 only adds a Path-D early return; `w_frameFog` feeds the encounter key (`ff9.cs:9248`). |
| D4-16 | confirmed | Gate: 84 PASS, 186 SKIP, 5 SKIP(part sets); 189/260 land cells (73%); census agrees on 274/275; 10 reorder-only SKIPs. No kit writer authors Disc4 directly: every world writer goes through `auto_mirror`. The prefix bug also misreads river at (5,16) and (19,11), but both cells SKIP for other reasons, so 274/275 holds. |
| D4-17 | corrected | The bug is real and wider than claimed. A full sweep (`verify_prefix_collision.py`) finds **3** mismatches over **two** prefix pairs: disc-4 (12,0) `sea4`→Sea4f, disc-4 (5,16) `river`→RiverJoint (3 vs 6 verts), and **disc-1 (19,11) `river`→RiverJoint (51 vs 207 verts)**. Disc 1 is therefore not safe either. Reach includes `water.py:463/504`, `transplant.py:127`, the discmirror pin path `:323`, and `palette.py:51`. P4's prediction ("sea4f is the only collision") fails. |
| D4-18 | confirmed | 23/23 full-channel permutations, including the (9,17) Object; reorder-only ground diffs reproduce ((7,3) 24, (21,13) 16, (22,11) 8, (22,13) 8; dy 0). `WMPhysics.Raycast` is first-hit in buffer order. Caveat: "only shared-edge ties change the readout" holds for these blocks. In general a permutation can change which sheet grounds where sheets overlap in XZ. |
| D4-19 | corrected | No clobbers, all Disc1/Disc4 pairs identical, the one Disc4-only pin, 128 land\|land sides: all reproduced. Free-ride check: of 255 donor part slots on 82 sidecars, the only non-identical one is the pinned (9,17) Object. But the live tree holds **82 cells**, not 93. 728 is the Disc4 file count and the (cell, part) key count; Disc1 has 727 live files plus 234 `.bak` backups, which the engine ignores. |
| D4-20 | corrected | The river-family list is exact, and memory's "river" at Daguerreo is wrong. It is probably *caused* by the D4-17 bug, since disc-4 (5,16) `river` resolves to RiverJoint. But sea re-cuts are not confined to "Shimmering; (13-20,15-16)". Re-cuts of 4u or more also hit the Water Shrine (3-4,9), Alexandria Harbour (21,10), (12,11), (13-14,10), (16,6), (16,7), (10,5) and (18-20,3). **5 of 46** non-trivial sea/beach re-cuts sit in blocks with **no terrain re-cut**: (10,5) and (16,7) Sea4 at 4u or more with byte-identical terrain, (18,3), (12,17) and (13,16). So the coupling is strong but not absolute. |

## Contradictions with recorded knowledge: who is right

- **`project-ff9-overworld-worlds.md:23`, "mostly byte-identical": the lane is right.** Only 85 of 275 blocks are
  identical.
- **`:24`, "river" differs at Daguerreo: the lane is right.** The river parts there are identical. The memory's
  error is reproducible as the `read_block('river')`→RiverJoint prefix bug at disc-4 (5,16).
- **`:23-31`, (9,17) as the skip example: the lane is right.** Skipping is the majority case, 73% of land cells.
- **`extract.py:11` and `cli.py:8960`, "0_2 = far LOD": the lane is right.** `0_2` is the Form-2 tree.
- **`GROUND-FAMILY-DECODE-2026-07-19.md:741`, "geometry != disc4 donor Object": the lane is right.** It is a byte
  permutation with identical geometry. The pin is redundant but harmless.

## Additional findings

1. The `read_block` substring match also collides `river`/`riverjoint` on disc 1 at (19,11), a real land block.
   Any kit carry or read of that River gets the 17-tri RiverJoint.
2. `uv_coverage.py` drops topographs with fewer than 50 triangles from its printout. Every disc-only atlas use sits
   in those hidden rows.
3. `weld_gap.gap()` excludes uncovered along-coordinates, so terrain-extent mismatches read as gap 0. A gate built
   on it ("no edge worse than stock") cannot see a terrain-edge retreat.
4. `prefab_census.py` normalises the disc segment of mesh containers, so cross-disc references are invisible. 205
   disc-4 ocean prefabs (410 refs) read the disc-1 (12,0) Sea4 and Sea6 meshes.
5. The s34 Form-2 override key is `0_1/... Terrain2` / `Object2` (`transform.name`), never a `0_2` path.
6. `mirror_risk.py`'s live audit regex ignores the 234 `.bak-*` files in the live `Disc1/0_1` tree. The engine
   ignores them too, but they make the Disc1 and Disc4 file counts differ (961 vs 728).

## Verifier scripts (all read-only)

| script | what it checks | output |
|---|---|---|
| `verify_prefix_collision.py` | `read_block` lookup vs the exact container, every (disc, lod, block, part) | `out/verify_prefix_collision.json` |
| `verify_lattice.py` | splits the D4-05 corner pool into re-heighted, boundary and interior corners | `out/verify_lattice.json` |
| `verify_prefab_refs.py` | PathID uniqueness, serialized files, FileIDs, cross-disc mesh refs, material identity | stdout |
| `verify_freeride.py` | donor free-ride parts of the live sidecars across discs | `out/verify_freeride.json` |
| `verify_weld_uncovered.py` | uncovered stretches on changed edges, and a ground probe on both sides | `out/verify_weld_uncovered.json` |
| `verify_kept_exact.py` | position-kept vs all-channel-kept triangles | `out/verify_kept_exact.json` |
| `verify_virgin_art.py` | locates the 100%-virgin topograph triangles | `out/verify_virgin_art.json` |
| `verify_virgin_form2.py` | virgin texels against disc-1 Form-1 plus Form-2 terrain | `out/verify_virgin_form2.json` |
| `verify_attr_nrm.py` | magnitude of the ATTR (uv/normal/id) edits | `out/verify_attr_nrm.json` |

Run each from `C:\gd\Dream-World-IX\ff9mapkit` as
`py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/<script>`.
