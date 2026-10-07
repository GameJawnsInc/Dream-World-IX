# Adversarial verification: lane `gap_inplace_stitch_composition`

This verifies the lane's findings S1-S17 (`NOTES.md`; structured result S1-S17).

The verification was read-only on the install, the Memoria clone, memory and tracked files. Nothing was deployed or
built. Writes went to two places:

- `verify_*.py` and `out/verify_*.json` in this directory;
- a fresh scratch cache at `...\scratchpad\verify_stitch\` (env `STITCH_SCRATCH`). The lane's `out/` was snapshotted there
  before any re-run.

## 0. Receipts

**Re-run from a FRESH decode cache.** `STITCH_SCRATCH` pointed at a new dir, so the meshes were re-decoded from p0data;
the lane's pickles were not reused. Every lane script exited 0.

- These outputs are **byte-for-value identical** to the lane's originals: `stitch_census`, `border_closure`,
  `calibrate_walk`, `tear_exposure`, `probe_detail`, and the `tear_sweep` distribution.
- `calibrate`, `engine_cites`, `composition_probe` and `gate_coverage` reproduce every number quoted in NOTES. Only
  timestamps and paths differ.

**Engine cites.** I re-opened every one by hand, not only through `engine_cites.py`:

- The Memoria clone HEAD is `6b8bb2d5` (= `memoria-patches/BASE_COMMIT`), and the patches are uncommitted
  working-tree hunks.
- The `ff9.cs` hunks before line 5476 add exactly +155 lines (8+2+7+2+5+15−3+119). That accounts for the working/stock
  pairs 5700/5545, 5666/5511 and 7321/7166.
- None of the cited ranges intersects a hunk. `WMWorld.cs:588-591` and `:848-852` sit just outside the s34 hunks
  (`+592,5` and `+820,28`).

**Kit cites.** All re-opened (section 3).

**New verifier scripts** (each runs with `py <path>`, with `STITCH_SCRATCH` optional):

| script | what it hunts |
|---|---|
| `verify_tjunction_numpy.py` | An INDEPENDENT brute-force numpy T-junction / near-T scan, using 8 torus neighbours, no spatial hash and a positive control. |
| `verify_claims.py` | S2 sums; S11 units; S15; S13 (uncovered-stretch closure, open-edge geometry); S7 with an engine-faithful re-implementation of `WMBlock.Raycast`/`WMPhysics.Raycast`/`intersect3D_RayTriangle`; S8 restricted to samples that actually lie on Terrain; S17 on every disc-4 block; S5 recounted with rounded keys; `WALK_OK` vs the engine mask. |
| `verify_object_walls.py` | What geometry the Object-seam "walls" of `tear_sweep.py` actually sit on. |
| `verify_baseline_artifact.py` | Nudges each wall's target ±0.02/±0.1u across the target face: does any walkable AREA change, or only a zero-width line? Env: `VB_AMOUNTS`, `VB_ALL`, `VB_PARTNER`, `VB_OUT`. |

## 1. Verdict table

| id | verdict | note |
|---|---|---|
| S1 | **confirmed** | The independent numpy scan (8 neighbours, brute force, positive control `terrain<-probe: 1`) finds **0 T-junctions on both discs** and nothing within 1e-3 of an edge interior. Its near-T counts match the lane exactly: disc 1 = 4 Object self; disc 4 = 4 Object + 11 Terrain. The co-displacement law follows: identical positions map to identical images, and with no T-vertices a nonlinear f cannot open a T-crack. |
| S2 | **confirmed** | 5,648/49,419 and 5,704/49,950 re-summed from the census. The class table reproduces. The per-partner block counts are **same-block** counts: Sea4 158, Sea3 134, Object 61, … (Sea5 78 is omitted from the prose list). Counting neighbour partners too gives Sea4 160, Object 64. The class figures are weld-PAIR counts, as labelled. |
| S3 | **confirmed** | Re-run in fresh scratch: all 8 pairs end LAST-WRITER-WINS with final == single(E2), and both stacking controls stack. The read paths were re-read: terrain.py:141 (`read_block` unless `target_disc != disc`), cli.py:4149, cli.py:4275, transplant.py:3305. `_ledger_shas` is traced on every composed overwrite and allows it, because our own sha is in the ledger (mesh.py:491). The mesh.py:347-351 docstring is wrong for real-disc reshape and for morph_in_place. It is right only for reshape's Path-D `target_disc` branch. |
| S4 | **confirmed** | Re-run: reshape on the kit override at (23,10) gives `blocks []`, `skipped_sea [[23,10]]` and an unchanged file. author_entrance stacks (104 event tris). Code: terrain.py:132-143. The entrance.py:741-743 comparison is wrong for real discs. |
| S5 | **confirmed** | Real writer re-run: parts = ['Terrain'], 10 torn positions, model 10. An independent recount from the deployed bytes, using rounded 1e-4 keys and a 3×3 partner neighbourhood, also gives **10**: Beach1 5, Sea2 3, Sea4 3, Sea1 1, Sea3 1, Sea5 1. Cite nit: "so nothing tears" is at **cli.py:4093** (docstring 4091-4093), not 4091-4092. |
| S6 | **corrected** | **Beach: exact.** Every beach wall is an AREA wall: nudged targets change too (149-154/154 per class, reproduced). **Object: wrong at +1u.** All 3/5/8 "edits with walls" at +1u are zero-width-line artifacts (S7); edits with a real wall = **0**. Real-wall edits are **15/19/19 at +3, 12/16/16 at −3, 19/19/21 at +6 and 16/16/18 at −6**, not "12-27 / 16-29". Also, the 18 "topo 48 on River" refusals all occur on **lowers**, not raises. Torn-weld medians and maxima, partner sums and the entrance 54-74% all reproduce. "Soft-locks" overstates a one-way wall; the player can still climb where \|f\| is below the ceiling. |
| S7 | **refuted** | See §2. The Treno-gate target does not ground on a walkable Object entry. At stock it grounds on **Terrain tri 328 (26.07, topo 12)**, at a point exactly on the base line of a vertical Object face (tri 32: all corners at z = −55.3203). Everything ≥0.01u to the south is already topo-59 Object or a MISS at stock: the gate pillar is already a wall. **All 112 A=+1 topo-59 walls (and all 232 vertical-target topo-59 walls at +1/+3) are LINE-ONLY.** Nudging the target ±0.02/±0.1u gives the same verdict before and after, so no walkable area changes. The engine mechanism is real code (WMWorld.cs:588-591 order; WMPhysics.cs first hit). The measured instances, the "new wall class" and P2's prediction are not. Separately, the published P2 coordinates are rounded to 0.01: re-querying (1278.38, −951.32) grounds on Terrain only, so the probe sits on a sheet boundary. |
| S8 | **corrected** | The numbers reproduce, but the "land samples" are every 4u lattice point of a land-BEARING block. Only **33,331/66,560 (50%)** lie on a Terrain tri. Restricted to points on Terrain (disc 1): tears-any 25.2/44.6/99.1% at r8/r16/r96 (lane: 25.7/46.4/99.5); walkable-partner **4.9/11.2/82.7%** (lane: 3.9/8.6/72.9). The headline ("about half at r16, ≈99.5% at r96") holds. The walkable-partner exposure is understated by 1-10 points. Disc 4 behaves the same (r96 walkable 85.5% vs 75.6%). The r96 default is confirmed at cli.py:8985. |
| S9 | **confirmed** | Re-run on (7,4) (91 event tris): reshape refused=False and wrote (6,4)/(7,4)/(7,5), moving 363 verts in (7,4). morph_in_place refused=False, clean. world-deploy rc 2 "REFUSED". The guard is at cli.py:4154-4165. |
| S10 | **confirmed** | The traces reproduce. Grep: `weld_audit` is called only at transplant.py:3172/:3890, and `_tjunc_gate` only at **transplant.py:3192/:3912** (the lane cites the weld_audit lines for both). The census is called at island.py:824 and interior.py:3242. entrance.py:994-995 runs the overwrite note only `if fresh`. weld_audit's blindness above tol is true by construction (near-miss 0<d<tol) and was reproduced (C3a). On F14: the operators prose is a collective statement that is not strictly false. The lane's version is a sharpening, not a contradiction. |
| S11 | **corrected** | The mechanism and probe reproduce: clean=True, touched ['terrain'], and the in-place-frame gate even reports `welds: unchanged` while 3 Object instances are torn by 1u. But **1,222 / 1,259 are weld-PAIR counts**. The **unique Terrain positions** welded to a part outside PARTS are **952 (disc 1) / 984 (disc 4)**; Object 607, not 690. |
| S12 | **confirmed** | mesh.py:501 and :284 use `%Y%m%d-%H%M%S` with `shutil.copyfile`, so a same-second park overwrites. Re-run: 5/5 trials kept 1 park, and the spaced control kept 2. |
| S13 | **corrected** (minor) | Every count reproduces: 389/385 exact, 436/443 closed, 7 open pairs, 17.24u, max 3.07u, 6 Terrain-owned. Every uncovered stretch is closed by another part: recomputed by interval union, the residual is 0 on both discs. But "each is a vertical wall edge" is true for 8 of 9 open edges and 6 of 7 pairs. The **(13,5)\|(14,5)** opening is a **slanted** in-plane edge: along −11.27→−12.12, y 12.97→14.81. |
| S14 | **confirmed** | Reproduced under `sandblocks_sand31_foamkept`/incid = 664/702. The other variants match as stated (621/630, 644/682, 664/1,203). |
| S15 | **confirmed** | No mesh of any part in column 23 or row 19 on either disc. Column 0 has only (0,0); row 0 has (0,0), (7,0), (8,0), (9,0), (10,0), (12,0) across all parts. There are 0 wrap welds. |
| S16 | **corrected** | The gate exists and every engine cite is right: ff9.cs:1328; :5509 `pos1 = ground + slice`; :5666/5667 the sink (row 1 = 400 → −1.171875 for the player's `slice_type 1`, ff9.cs:1787); :5700. WMBlock.Raycast never reads `distance`. So memory feasibility:347-351 ("NO slope/step gate … at any grade") is stale. But the lane's phrase "a raised slope is therefore not walkable at any grade" overstates in the other direction. A CONTINUOUS slope stays walkable up to about 79.4° (2.34375 per 0.4375u tick; terrain._walk_gate). The ceiling bites at seam DISCONTINUITIES (torn welds) and at slopes steeper than about 79°. |
| S17 | **confirmed** | weld_audit on the stock disc-4 (18,4) PARTS (terrain, sea3) gives 3 pairs, all **interior** by `transplant._split_frame_pairs`. Disc 1 gives 0. A sweep of every disc-4 block finds (18,4) is the **only** block whose stock PARTS fail the interior weld gate. |

## 2. The S7 counterexample in detail (`verify_claims.py` V-S7, `verify_object_walls.py`, `verify_baseline_artifact.py`)

**Why the instrument misfires.** The lane's walk instrument puts a crossing probe 0.4u from the welded vertex, along
the incident tri's centroid direction. For a VERTICAL tri (zero XZ area) that point lies on the tri's base line, not
inside anything the tri covers.

**What sits under the Treno target.** At the exact (unrounded) Treno target (62.3766, −55.3203) local, the sheets are:

- Object tri 27: y 28.617, topo 59, n.y 0.616;
- Terrain tri 328: y 26.07, topo 12.

**Before and after the raise.**

- Stock: the origin is 26.07 + 2.34375 = 28.41, below 28.617. The ray grounds on **Terrain**, which is legal.
- After the raise: the origin is 28.84. Object is scanned first, so the ray hits topo 59 and the step is refused.

**But the area is already blocked at stock.** A nudge 0.01-1.2u south of the line is a MISS or topo-59 at stock. North
of the line it is legal both before and after. So nothing walkable changes: the gate pillar was already impassable.

**Across the whole sweep:**

- 358 of 358 topo-59 walls (A +1/+3) had the stock step grounded on Terrain, never on a walkable Object sheet.
- 232 of those walls sit on vertical Object tris.
- 112/112 at +1 and 120/120 at +3 vertical are LINE-ONLY.
- The ±3 misses (579 + 558 + …) and every beach wall are genuine AREA walls.

**Consequence: withdraw P2.** As designed it would observe no change.

**A residual caveat.** Even where a topo-59 overhang does sit over walkable ground, the engine's 10-slot cache tests
recently-hit tris BEFORE the scan (WMBlock.cs:145-162). V-S7 shows the stock step tri would still be hit after the
raise, so in-game outcomes there depend on walk history. The model seeds the cache with the start tri only.

## 3. Kit cites re-opened

All of these say what the lane claims:

- **terrain.py:** 9-10, 34-85, 98-104, 126-131, 132-143, 141, 159.
- **mesh.py:** 284, 347-351, 491, 501, 1557-1559.
- **entrance.py:** 606-625, 741-743, 953 (backup default), 994-996.
- **transplant.py:** 46, 817-834, 3172, 3286, 3305, 3890.
- **cli.py:** 4149, 4154-4165, 4275, 8985.

Line-number nits:

- The "nothing tears" phrase is at cli.py:4093.
- The T-junction gate calls are at transplant.py:3192 and :3912.

## 4. Recorded-knowledge arbitration

- **memory feasibility:347-351 vs the lane (S16).** The lane is right that a step ceiling exists, so the memory line is
  stale. But the memory's practical rule ("smooth reshapes stay walkable") holds below about 79°. Neither statement is
  right as worded.
- **memory coast-mosaic:146 BERM LAW.** Reproduced (S14). There is no contradiction.
- **disc4 VERIFY D4-06 ("11 covered T-junctions").** Refuted. The independent scan finds 0 T-junctions.
  - "26 uncovered" vs "14" is a definition difference. D4-06 used vertex extents (`verify_weld_uncovered.py`), so
    single-point contacts count as uncovered.
  - Edge coverage (this lane) is the meaningful measure.
- **disc4 NOTES:191 ("17 real border gaps").** Corrected to 7 open pairs (17.24u) by the closure census. Of the 17, 13
  top-polyline gaps are confirmed; 10 of those are curtain-closed or corner-closed.
- **operators F14 prose.** It is not falsified; S10 sharpens it.
- **mesh.py:1557-1559 (weld_audit "ZERO such pairs").** False for disc-4 (18,4) only (S17).
- **Not re-verified here:** consumption/VERIFY C12 (Cull Back). This lane inherits it.

## 5. What to change in the lane's write-up

1. **S7.** Retract the "origin-shift wall class" and probe P2. If the mechanism is still wanted, re-site a probe where a
   topo-59 sheet overhangs WALKABLE ground that is legal at stock. Find such sites with a sweep that nudges off the
   vertical-tri base lines.
2. **S6.** Object +1u walls → 0. Restate the ±3/±6 real-wall counts, and move the 18 River refusals to lowers.
   - Fix the tear_sweep probe: skip or offset probes of zero-XZ-area tris, or nudge the probe off the base line.
3. **S8.** Restrict the samples to Terrain-covered points, or relabel them "lattice of land-bearing blocks". Restate
   the walkable-partner exposure.
4. **S11.** Say "1,222 weld pairs (952 unique Terrain positions)".
5. **S16.** Replace "not walkable at any grade" with "unclimbable at a seam step > 2.34375u (1.171875u from canopy) or a
   slope steeper than about 79°".
6. **S13.** "Six of the seven openings are vertical edges; (13,5)|(14,5) is a slanted in-plane edge."
7. **Line nits.** cli.py:4093; transplant.py:3192/:3912.
