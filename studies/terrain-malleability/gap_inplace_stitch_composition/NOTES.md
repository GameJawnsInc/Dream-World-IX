# In-place edits of real overworld blocks: the stock stitch graph and whether edits compose

Lane `gap_inplace_stitch_composition` of the terrain-malleability study. This lane was set up to verify, or refute,
the unverified operators-lane claims F2, F3, F4 and F14 (`../operators/NOTES.md` §5).

It also measures two things no lane had measured:

- **The stitch graph.** These are the vertices that Terrain shares with every other part and across block borders.
- **The cost of a tear.** This is what happens when a Terrain-only edit pulls one of those shared vertices apart.

The work was read-only on the install, the Memoria clone, memory and tracked files. Writes went to two places only:

- this lane directory: scripts, `out/*.json` (derived counts and coordinates) and this file;
- an absolute scratch mod folder under the session scratchpad (`...\scratchpad\stitch\compose\*`).

The decoded vertex cache is a raw-derived dump. It lives in the scratchpad (`...\scratchpad\stitch\disc{1,4}_0_1.pkl`),
never in the repo. No live mod folder was read or written. No `.ff9deploy.toml` was consulted: library calls take
explicit `mod_folder=` / `game=`. Nothing was deployed. The game was not launched.

## 0. Scripts, in rerun order (each run from anywhere: `py <full path>`)

All paths are `C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/<script>`.

| script | what it measures | runtime |
|---|---|---|
| `stitchlib.py` | Shared loader. Reads exact-container `worldmap/disc{d}/0_1` meshes (the anchored d4lib regex, which avoids the sea4→sea4f / river→riverjoint prefix bug), with world-frame positions and a torus fold. | library |
| `calibrate.py` | C1 BERM LAW, C2 border reconciliation with `disc4/out/weld_gap.json`, C3 synthetic controls (tear detector vs `mesh.weld_audit`, T-junction, uncovered stretch) → `out/calibrate.json` | ~10 s |
| `stitch_census.py` | **Method A.** Exact welds, near-misses, XZ stacks, T-junctions, borders, discs 1+4, plus Terrain partner classes → `out/stitch_census.json` | ~10 s |
| `border_closure.py` | The stock border **closure** census (crossing edges + in-plane curtain tris + corner diagonals), with a calibration → `out/border_closure.json` | ~20 s |
| `calibrate_walk.py` | W1-W4: calibrates the walk-crossing instrument (stock baseline, the 2.34375 climb ceiling, the 1.171875 canopy ceiling, cache accounting) → `out/calibrate_walk.json` | ~2 s |
| `tear_sweep.py` | **Method B.** 5,292 Terrain-only reshapes centred at beach / object stitches; torn welds, slits, walk walls, entrances → `out/tear_sweep.json` | ~2 min |
| `tear_exposure.py` | Fraction of ALL land where a world-terrain edit tears a stitch, discs 1+4 → `out/tear_exposure.json` | ~25 s |
| `composition_probe.py` | **Methods C + D.** Composition pairs in fresh scratch folders, `.bak` parking, F3 on the real writer, F4 behaviourally, the VertexDisplace reach, a sys.setprofile gate trace with a transplant dry-run control → `out/composition_probe.json` | ~40 s |
| `gate_coverage.py` | **Method D (static).** AST reach of each writer to the gate functions; cross-checks the trace → `out/gate_coverage.json` | ~3 s |
| `engine_cites.py` | EVIDENCE LAW: verifies every engine cite, STOCK vs PATCHED, against `git diff HEAD` hunks and `memoria-patches/*.patch` → `out/engine_cites.json` | ~5 s |
| `probe_detail.py` | Prediction numbers for the two proposed in-game probes → `out/probe_detail.json` | ~2 s |

Order: run `stitch_census.py` before `calibrate.py`, `tear_sweep.py` before `composition_probe.py`, and
`composition_probe.py` before `gate_coverage.py`. The others are independent.

## 1. Engine anchors (`engine_cites.py`; all paths under `C:\gd\FFIX\Memoria\Assembly-CSharp`; working-copy line / stock HEAD 6b8bb2d5 line)

Each cite's anchor text was located inside the cited range. The cite was classified STOCK because its range intersects no
`git diff -U0 HEAD` hunk. The calibration rows pass: the s34 `WorldMeshOverride.TryLoad` hook classifies PATCHED (s34,
s74), and `WMPhysics.cs` classifies STOCK.

| id | cite (working / stock) | claim | origin |
|---|---|---|---|
| E1 | ff9.cs:1326-1331 / 1328 | walk ray origin = actor y + 2.34375 (sky 400; `rayDistance` 2.8; `defaultHeight` 0) | STOCK |
| E2 | ff9.cs:1469-1491 / 1490 | on-foot control 0: limit mask {0x0010667F, 0xD8FF3CFF}, `flg_gake` 0 | STOCK |
| E3 | ff9.cs:5476-5510 / 5354 | actor y = `ground_height + slice_height` | STOCK |
| E4 | ff9.cs:5550-5600 / 5443 | the walk heading fan; ground commits only on a successful `w_movementRoundCheck` | STOCK |
| E5 | ff9.cs:5622-5666 / 5511 | slice class 0 = topo 36/37/38, `imd` (immediate canopy sink) | STOCK |
| E6a | ff9.cs:5687-5700 / 5537 | NO hit cache while standing on topo 49/52 | STOCK |
| E6b | ff9.cs:5695-5702 / 5545 | `if (num3 >= 0)`: a ray MISS refuses the step | STOCK |
| E7 | ff9.cs:3304-3314 / 3301 and 7296-7324 / 7166 | `w_cellHit` → `w_nwpHit`; pno -1 unless hit | STOCK |
| E8 | WMBlock.cs:137-180 / 147 | the 10-slot per-actor hit cache is tested BEFORE the scan | STOCK |
| E9 | WMBlock.cs:196-212 / 210 | mapid = `tangent.x` of the hit tri's corner 0; 0x31EE veto | STOCK |
| E10a | WMPhysics.cs:6-45 / 16 | scan skips idall 4078/4088/2040 and non-up-facing tris; first hit in buffer order | STOCK |
| E10b | WMPhysics.cs:47-66 / 50 | the CACHE path (`RaycastOnSpecifiedTriangle`) has NO up-facing or idall filter | STOCK |
| E11a/b | WMWorld.cs:588-591 / 515, 748-807 / 721 | registration order: Object, Terrain, Beach1, Beach2, Stream, River, RiverJoint, Falls, Sea1..6 | STOCK |
| E11c | WMWorld.cs:848-852 / 738 | every form-1 registered part joins the walk scan (`AddWalkMeshForm1`) | STOCK (sits inside s34's `RegisterBlockComponent`, whose override hunk is :820-847) |
| (prior) | consumption/VERIFY.md C12 | no world shader sets `Cull`, so Unity's default **Cull Back** applies | another lane's verified finding |

## 2. Calibration (before any verdict)

**C1, THE BERM LAW reproduced exactly (`calibrate.py`).** The recorded 664/702 reproduces as corner incidences:

- the corners of non-sand Terrain tris at sand-topo-31 vertices that also belong to a non-sand tri;
- counted over the **27 blocks whose Terrain carries topo-31 sand**, with foam-welded end verts **kept**.

The original census script was scratch-only (HANDOFF_BEACH_MINT_RUNG3.md 2a).

The definition differences are:

- `coastmorph.beach_mint`'s own L-chain excludes the foam-welded verts. That gives **621/630**.
- Scoping to the 40 Beach1 blocks gives 644/682.
- With desert/snow sand included, it is 664/1,203. The berm law is a grass-sand (topo 31) statement.
- 15 Beach1 blocks carry no topo-31 sand, and 2 sand blocks, (4,14) and (13,14), carry no Beach1.

This calibrates the loader: it reproduces a recorded census to the unit.

**C2, border reconciliation with disc4 D4-06 (`calibrate.py`, `border_closure.py`).** My land|land pair set is the
same 443 pairs as `weld_gap.json`. No land pair crosses a torus seam.

- **Their 17 "gap>0":** 13 have a top-polyline gap >0.01 in my re-derivation (1.95-3.39u). The other 4 read gap 0 here
  and are artefacts of their vertex-polyline metric.
- **Their 37 "gap-0 open":** 14 have uncovered Terrain stretches by edge coverage. They are not 26: VERIFY counted vertex
  extents. The other 23 are covered: the extra border verts are XZ stacks (vertical faces) or single-point contacts.
- **No T-junction anywhere.** The calibrated scan finds zero T-junctions on any border, or anywhere else.
- **The top-polyline metric is not a crack detector.** It reads an in-plane vertical "curtain" tri on one side as a
  1.95-3.39u gap. Examples: (17,14)|(18,14) and (7,10)|(7,11), where both sides share the base polyline exactly.
- **Real openings come from the closure census.** `border_closure.py` matches crossing edges across the border, and
  also accepts in-plane curtain tris and the diagonal corner partner. **436/443 pairs are closed on both discs.**
- **7 pairs have open crossing edges** (17.24u total, max opening 3.07u, 6 Terrain-owned). Each is a vertical wall edge
  that ends at the border with nothing on the other side:
  - three are top-polyline gaps: (13,5)|(14,5), (17,13)|(17,14) and (17,14)|(18,14);
  - four read gap 0 in the polyline: (7,11)|(7,12), (14,11)|(15,11) (non-Terrain), (15,5)|(16,5) and (17,3)|(18,3).
- **Every uncovered stretch is closed by another part.** That is 91.72u on disc 1 and 111.96u on disc 4. The closing
  parts are Sea3, Object, Sea4, VolcanoCrater, Beach1, River and RiverJoint.
- **The closure instrument detects a removed tri.** Deleting one real (7,11) border tri opens exactly its 4.311u edge
  (1.953 → 6.264u).

**C3, synthetic controls (`calibrate.py`).** Each control moves one Beach1 partner of a real (7,17) Terrain|Beach1 weld:

| control | tear detector (pre/post separation > 0.05u) | kit `mesh.weld_audit` (near-miss 0<d<0.05) |
|---|---|---|
| move 0.06u | **flagged (1)** | **0 pairs, blind** |
| move 0.01u | **passes (0)** | flags 1 |

So `weld_audit` cannot see any tear larger than its tolerance. It is a hairline detector, not a stitch gate.

- **T-junction scan:** a synthetic vertex at a real border-edge midpoint → `probe|terrain|border: 1`; stock → 0.
- **Coverage:** deleting a border tri → a 1.441u uncovered stretch; stock → 0.

**W1-W4, walk instrument (`calibrate_walk.py`).**

- W1: on stock (7,17), 62/67 Beach1|Terrain probe pairs cross legally in each direction. The 5 refused start on
  unwalkable ground.
- W2: a uniform Terrain lift refuses beach→terrain between **+2.2 (16 refused, 5 of them already refused on stock)
  and +2.34 (67/67)**, which is the 2.34375 origin less the probe's own rise. The terrain→beach drop stays legal at
  every height up to +6.
- W3: on (6,7), lifting the lawn tris refuses canopy→lawn between **+1.2 and +1.3, all by +1.6**. That is the
  1.171875 canopy sink, not 2.34.
- W4: the 10-slot cache decided 0 of 134 seam crossings. A Y-only edit keeps the XZ footprints, so a crossing leaves the
  cached start tri, and the cache can only decide where sheets overlap.

**Composition harness controls (`composition_probe.py`):**

- **Stacking control.** world-entrance twice on two cells of (17,11) **STACKS** (312/312 event-corner IDALLs kept), so
  the harness can see stacking.
- **Tracer control.** `transplant(dry_run=True)` (7,17)→(23,10) traces `weld_audit`, `_tjunc_gate`, `census` and
  `_mod_overwrite_gate`, so the tracer sees gates when they run.

## 3. Findings

**S1. [law, census] The stock overworld is one CONFORMING mesh across every part and block.**

- Every stitch is an exact shared vertex. The T-junction count is 0 on both discs (calibrated scan, 3D <1e-3, all parts,
  block + 4 torus neighbours).
- Near-miss pairs (0 < d < 0.05u): disc 1 has 1 (an Object self-pair at (13,5), 0.0039u). Disc 4 has 4: 3 Terrain pairs
  at (18,4), 0.0039-0.0398u, plus that Object pair.
- Near-T (1e-3 to 0.05u): disc 1 has 4 (Object self). Disc 4 has 15 (11 Terrain self, at (18,4) and nearby, plus 4
  Object).

The consequence is a clean law. A displacement that moves every coincident instance in ALL parts and blocks by the same
f(x,z) preserves the stitch graph exactly. A displacement that moves a subset tears exactly the welds it splits.

**S2. [measurement] The stitch graph Terrain participates in** (`stitch_census.py`; weld-position pairs, disc 1 / disc 4):

| class | same block | across a border |
|---|---|---|
| Terrain-Terrain | -- | 4,959 / 4,936 (+244 / 240 four-block corners) |
| Terrain-Sea4/5/6/4f (open water) | 2,527 / 2,533 | 359 / 347 |
| Terrain-Sea1/2/3 (shallow rim) | 2,054 / 2,083 | 272 / 274 |
| Terrain-Object | 589 / 615 | 101 / 109 |
| Terrain-Beach1/2 | 417 / 422 | 65 / 65 |
| Terrain-River/RiverJoint/Falls/Stream | 407 / 409 | 53 / 54 |
| Terrain-Volcano* | 29 / 29 | 8 / 8 |

Per land block, 5,648 of 49,419 unique Terrain positions (11.4%) are welded to a non-Terrain part on disc 1, and 5,704
of 49,950 on disc 4.

- **Block counts (disc 1):** Sea4 158, Sea3 134, Object 61, Beach1 40, Sea1 34, Sea2 27, River 10, Stream 7,
  RiverJoint 6, Beach2 4, Falls 3, Volcano 2. Neighbour Terrain: 254.
- **XZ stacks:** these are same XZ with |dy| ≥ 0.05. They are not welds, but they are orderings that a Y edit can
  invert. Counts: Terrain|Terrain border 209 (the in-plane curtains), Object|Terrain 134 + 31, Sea4|Terrain 47.
- **Torus seams:** no stock mesh exists in column 23 or row 19 on either disc, and 0 welds cross the x or z wrap. The
  seams carry no stock stitch. `terrain.reshape`'s off-grid skip (terrain.py:126-131) cannot tear stock geometry; it
  matters only for kit land placed at column 0/23 or row 0/19.

**S3. [law, probe] F2 CONFIRMED: four of the five in-place writers read pristine stock, so the last writer wins**
(`composition_probe.py`).

Each scenario was run three ways in fresh scratch folders: E1 alone, E2 alone, and E1 then E2.

| E1 then E2 on (17,11) | verdict | evidence |
|---|---|---|
| reshape → reshape (overlapping centres 8u apart, +3 r16) | **LAST-WRITER-WINS** | E1's 339 moved verts: 0 kept; final == single(E2) byte-for-value |
| reshape → retarget | **LAST-WRITER-WINS** | the hill is gone: 339/339 lost |
| retarget → reshape | **LAST-WRITER-WINS** | 147 retargeted IDALL corners: 0 kept |
| morph_in_place (VertexDisplace +1) → reshape | **LAST-WRITER-WINS** | 6 morphed corners: 0 kept |
| reshape → morph_in_place | **LAST-WRITER-WINS** | 318 verts: 0 kept |
| world-deploy --hill → world-deploy --hill | **LAST-WRITER-WINS** | 339: 0 kept |
| **entrance → reshape** | **LAST-WRITER-WINS** | the entrance's 312 event-tile corners are erased; its world `.eb` trigger stays, so the entrance is dead |
| **entrance → retarget** | **LAST-WRITER-WINS** | 312: 0 kept |
| reshape → entrance | STACKS | 318/318 hill verts kept (entrance reads stacked) |
| entrance → entrance (control) | STACKS | 312/312 |

The trace confirms each writer's read path:

- reshape, world-deploy, world-retarget and morph_in_place call only the pristine readers (`read_block`/`world_tris`);
- world-entrance calls `read_block_stacked` → `blockmesh_from_ff9mesh`.

The ownership ledger does not prevent this. On every overwrite `_ledger_shas` ran and allowed it (our own bytes are in
the ledger; mesh.py:491), and the previous bytes were parked as `.bak-<ts>`.

**S4. [law, probe] The two docstrings that say otherwise are wrong for reshape and morph.**

- mesh.py:347-351 (`mod_overwrite_gate`) lists `terrain.reshape` and `transplant.morph_in_place` as writers that "READ
  the deployed override and write it back".
- entrance.py:741-743 (`fresh_discard_note`) says the stacked read is "exactly as for `terrain.reshape`".

Both are true only for `entrance.author_entrance` and the interior verbs.

`terrain.py:98-104`'s own docstring is right. It says the pristine read is deliberate, so a re-run re-shapes from stock
instead of compounding.

A further consequence: on a real disc, `world-terrain` cannot touch a KIT island at all. A Terrain override deployed at
open-ocean (23,10) is skipped as sea (`skipped_sea [[23,10]]`, file unchanged), while world-entrance stacks onto the
same file (104 event tris).

**S5. [law, probe] F3 CONFIRMED and MEASURED: a Terrain-only Y edit tears exactly the non-Terrain welds it moves.**

The real `terrain.reshape` was run on (7,17) at (480,-1120), +3, r16. It wrote **only `Terrain`**, and 10 stock welds
are torn in the deployed bytes: Beach1 5, Sea2 3, Sea4 3, Sea1 1, Sea3 1, Sea5 1. These are counts per partner; one
position can weld to several parts. The `tear_sweep.py` model predicts **10** for the same edit, so the model is
calibrated against the writer.

Terrain|Terrain never tears inside the grid, because reshape displaces every in-range block with one world weight.

**S6. [measurement] What a tear costs: the reference sweep** (`tear_sweep.py`).

The sweep covers 44 beach blocks (154 centres) and 63 Object blocks (140 centres), with amounts ±1/±3/±6 at radius
8/16/24: 5,292 edits.

| class | torn welds per edit, median (max) | introduced WALLS (edits with ≥1 wall / 154 or 140) | entrance tris moved |
|---|---|---|---|
| beach ±1, r8/16/24 | 4 / 9 / 14 (6 / 17 / 26) | **0** at every radius: SLIT only (max slit 1.0u) | 0 |
| beach ±3 | 4 / 9 / 14 (7 / 17 / 31) | **149-154** (1,164-4,480 refused crossings per class) | 0 |
| beach ±6 | 4 / 9 / 15 (7 / 18 / 31) | **152-154** | 0 |
| object +1 | 8 / 16 / 25 (33 / 56 / 78) | 3 / 5 / 8: **origin-shift class** | 75 / 95 / 101 of 140 |
| object −1 | same | 0 | same |
| object ±3 | 8 / 17 / 25 (34 / 58 / 80) | 12-27 | 76-103 |
| object ±6 | same | 16-29 | 77-103 |

How the walls arise:

- **Direction.** A raise refuses beach→terrain climbs (24,580 Beach1, 1,806 Beach2). A lower refuses the climb back,
  terrain→beach (21,947 + 1,620). Every beach wall is a ray MISS: the new surface is above y+2.34375 and no lower sheet
  exists (E6b). These are one-way walls. A ±3u edit at a beach seam soft-locks one direction in essentially every case.
- **The origin-shift class.** Object walls on a raise include 604 "topo 59 on Object" and 18 "topo 48 on River". A
  raise of only **0.27-0.38u** at the seam lifts the actor, and the walk ray's origin y+2.34375 rises above a topo-59
  Object tri. That tri sits higher, but earlier in buffer order (E10a), so it now wins over the walkable tri below. The
  example is Treno's gate (19,14) (`probe_detail.py`): from terrain at 26.3-26.5, the step lands on the 28.6 topo-59
  sheet. A walkable object entry becomes a wall.
- **Partners torn** (beach +3 r16, summed over edits): Beach1 1,124, Sea3 198, Sea2 112, Sea1 111, Beach2 91, Sea4 75,
  Sea5 26. Object +3 r16: Object 2,334, River 135, Falls 125, RiverJoint 83, Sea3 61, Stream 51, Sea4 49.

**Render.** Every torn weld is an open slit of height |f| between two faces. No geometry spans it, and Cull Back (C12)
hides the back faces of both sheets. Max slit = the edit amount. A Y-only edit never opens an XZ gap. The XZ walk-wall
class (a ray miss over a hole) therefore does not arise. The only new walls are step walls.

**S7. [measurement] Exposure: how often an arbitrary edit tears something** (`tear_exposure.py`, 66,560 land samples
on a 4u lattice).

| radius | tears any non-Terrain stitch | tears a walkable-partner stitch (Beach1/2, Object) | moves an entrance tri |
|---|---|---|---|
| r8, ±1..6 | 26-28% | 4% | 3% |
| r16 | 46-50% | 9-10% | 6-7% |
| r24 | 63-67% | 15-17% | 10-11% |
| r48 | 90-92% | 37-41% | 26-29% |
| r96 (world-deploy's `--radius` default) | **99.5-99.7%** | **73-78%** | **59-65%** |

These are disc 1 figures. On disc 4 the tear fractions are within about 3 points. Entrance exposure is lower on
disc 4: 19-22% at r48 and 51-57% at r96.

**S8. [law, probe] F4 CONFIRMED behaviourally.** On a real entrance block (7,4) (91 event tris; reshape centred on
an event tri, +3 r12):

- `terrain.reshape` **did not refuse**: it wrote 3 blocks and moved 363 verts in (7,4).
- `transplant.morph_in_place` **did not refuse** (clean, wrote Terrain).
- Only `world-deploy` refused: rc 2, "REFUSED: this reshape touches place-ENTRANCE block(s)", nothing written.

**S9. [law, probe; CORRECTS F14] Gate coverage per in-place writer.** The table combines the dynamic trace with the
static reach (`gate_coverage.py`, an upper bound).

| writer | reads | MOD-OVERWRITE | weld_audit | T-junction | placement census | entrance guard | auto_mirror | own gates |
|---|---|---|---|---|---|---|---|---|
| world-terrain (`terrain.reshape`) | pristine | no | no | no | no | **no** | yes | one-way-wall `_walk_gate` |
| world-deploy (`cli._cmd_world_deploy`) | pristine | no | no | no | no | **yes** (cli.py:4154) | yes | -- |
| world-retarget (`cli._cmd_world_retarget`) | pristine | no | no | no | no | n/a (static hit is `block_summary`'s listing, not a guard) | yes | -- |
| world-transplant --in-place (`morph_in_place`) | pristine | no | no | no | no | **no** | yes | in-place-frame `_frame_set`, tweak gates |
| world-entrance (`author_entrance`) | **stacked** | warn row only with `fresh=True` | no | no | no | -- | yes | -- |
| CONTROL world-transplant | pristine (donor) | yes | **yes** | **yes** | yes | -- | yes | 15 gates |
| CONTROL world-island | n/a | yes | no | no | yes | -- | yes | island gates |

The ledger refusal (`_ledger_shas`, mesh.py:491) runs on every overwrite. It refuses only bytes that match no ledger
row, so it never stops one kit verb from erasing another kit verb's edit.

**Correction to F14:** `weld_audit` and the T-junction differential are called by `transplant` ONLY (transplant.py:3172,
:3890). Island and interior call the placement census but never `weld_audit`. The operators lane's own
`writer_gate_census.json` agrees; its prose does not.

**S10. [law, probe] VertexDisplace is weld-preserving only within the parts its caller loads.**

`morph_in_place` loads only `transplant.PARTS` = terrain, beach1, sea1-5 (transplant.py:46). Terrain welds to parts
outside that set cannot be co-moved. On disc 1 there are **1,222** such weld positions: Object 690, Stream 227,
River 147, RiverJoint 44, Falls 42, Volcano 37, Beach2 34, Sea6 1. On disc 4 there are 1,259.

Probe: a VertexDisplace (+1u) on a Terrain vertex welded to the Treno-gate Object (19,14). The gates are clean, only
Terrain is written, and the 3 Object instances stay put. That is a 1u tear that every morph gate passes.

**S11. [measurement] `.bak` parking loses bytes inside one second.**

`deploy_override` names the park `.bak-%Y%m%d-%H%M%S` (mesh.py:501; sidecar :284), at 1-second resolution, and
`shutil.copyfile` overwrites an existing park of the same name. In 5/5 trials of 3 back-to-back differing reshapes,
only 1 park survived where 2 were made. It holds the 2nd write; the 1st write's bytes are unrecoverable. Control: the
same writes 1.2 s apart leave 2 parks.

**S12. [measurement] Stock border seams (the corrected baseline).**

- 389/443 (disc 1) and 385/443 (disc 4) land|land borders have byte-identical border vertex sets.
- With the closure census, 436/443 are closed on both discs; the 7 open pairs are listed in §2 C2.
- Every uncovered Terrain stretch is closed by a NON-Terrain part across the border. Those cross-part border welds
  (Beach1 65, Sea 631, Object 101, River family 53 on disc 1) are exactly what a Terrain-only edit near a border tears.

## 4. Verdict table (VERIFY-style)

| claim | verdict | evidence |
|---|---|---|
| **F2** world-terrain (same-disc), world-deploy, world-retarget and --in-place morphs read pristine stock; a second edit clobbers the first | **CONFIRMED** (+ extended) | S3: 8/8 cross-writer pairs are last-writer-wins, final == single(E2). The entrance control stacks. Extension: a later reshape/retarget silently **kills a world-entrance** (312 event corners erased, `.eb` trigger left dangling). |
| mesh.py:347-351 docstring "terrain.reshape / morph_in_place READ the deployed override" | **REFUTED** for reshape and morph; true for entrance/interior | S3 trace + S4 |
| entrance.py:741-743 "exactly as for terrain.reshape" | **REFUTED** (the comparison) | S4; terrain.py:98-104 says the opposite and is right |
| **F3** Y displacement moves Terrain only, leaving coincident Beach1/Sea/Object/River behind | **CONFIRMED and MEASURED** | S5: the real writer writes Terrain only; 10 torn welds = the model. S2: 5,648 Terrain positions (11.4%) are exposed. S6/S7: costs. The weld-gap size F3 left OPEN is \|f\| exactly; walls appear above 2.34375u (1.17u from canopy), and object walls appear from 0.27u through origin shift. |
| **F4** only legacy world-deploy has a place-entrance refusal; terrain.reshape has none | **CONFIRMED** (+ morph_in_place has none either) | S8 behavioural; S6: 54-74% of object-centre edits and S7: 3-11% of random r8-r24 land edits move entrance tris |
| **F14** gates are per-operator; weld_audit / T-junction / census only in transplant / island / interior | **CORRECTED** | S9: weld_audit and T-junction are transplant-ONLY. None of the four pristine in-place writers runs MOD-OVERWRITE, weld_audit, T-junction or census. C3: weld_audit is blind to tears >0.05u anyway. |
| disc4 VERIFY D4-06 "11 covered T-junctions" on disc 1 | **REFUTED** | 0 T-junctions (calibrated); they are XZ stacks / point contacts (C2) |
| disc4 NOTES "stock disc 1 has 17 real border gaps" | **CORRECTED** | 7 open pairs, 17.24u, max 3.07u; 10 of the 13 polyline gaps are curtain-closed or corner-closed (C2) |

## 5. Ranked kit changes, each tied to a measured failure

1. **Stacking reads (or an explicit stock-reset flag) for the four pristine in-place writers.** Measured failure: S3,
   8/8 last-writer-wins, including two silent entrance kills. Change:
   - `terrain.reshape` (terrain.py:139-143): read via `entrance.read_block_stacked(mod_folder, ...)` on real discs too,
     with `fresh=` for the documented "re-shape from stock" intent;
   - `cli._cmd_world_retarget` (cli.py:4275) and `cli._cmd_world_deploy` (cli.py:4149): same;
   - `transplant.morph_in_place` (transplant.py:3305, `world_tris`): a stacked `world_tris` per part.

   Then fix the docstrings at mesh.py:347-351 and entrance.py:741-743.
2. **An overwrite gate for any writer that still reads pristine.** Measured failure: S3/S9, the ledger lets kit-on-kit
   erasure through. Call `mesh.mod_overwrite_gate(cells, mod_folder, disc=write_disc, parts=(written part,))` in the
   same four functions before writing. Refuse unless `--fresh` / `allow_overwrite`.
3. **An entrance guard in `terrain.reshape` and `transplant.morph_in_place`.** Measured failure: S8, plus S6/S7 at 3-74%
   exposure. Lift the cli.py:4154-4170 `block_mapids` event check into a shared `mesh.entrance_guard(bms)` and call it
   from both, plus `_cmd_world_deploy`.
4. **A STITCH GATE (pre/post weld preservation), not `weld_audit`.** Measured failure: C3, weld_audit flags 0 for a
   0.06u tear and passes any larger one.
   - New `mesh.stitch_gate(pre_parts_by_cell, post_parts_by_cell, tol=0.05)`: every stock exact-weld cluster
     (stitch_census instrument 1, including the 4 torus neighbours) must stay within tol.
   - Call it in `terrain.reshape`, `_cmd_world_deploy` and `morph_in_place`. Make it WARN by default and REFUSE on
     walkable partners (Beach1/2/Object) above 2.34375 / 1.171875.
5. **Multi-part co-displacement where it is lawful.** Measured failure: S5/S6, one-way walls in 149-154/154 beach edits
   at ±3; Object burial/float.
   - In `mesh.deform_radial` / `deform_ridge` / `flatten_region`, called from `terrain.reshape` and `_cmd_world_deploy`,
     move every exact-coincident vertex in Beach1/Beach2/Object/River/RiverJoint/Falls/Stream of the touched blocks
     **and** of their 4 neighbours by the same world weight, and deploy those parts. This is the VertexDisplace pattern
     widened to all registered parts.
   - Do NOT co-move Sea: water must stay at its layer (vertical lane V9 envelope: open sea 0, shallow rim ≤ +0.8u).
     **Pin** Sea-welded Terrain verts (weight 0) instead, and let the walk gate catch any slope this creates.
6. **Widen `morph_in_place`'s part set to every registered part.** Measured failure: S10, 1,222 weld positions
   unreachable and a 1u Object tear passing every gate. Change the `parts=PARTS` default in
   `transplant.morph_in_place` to the full `placement.REGISTRATION_ORDER` set present on the cell, or make
   `_frame_set` / the stitch gate cover intra-block cross-part welds.
7. **Collision-proof `.bak` names.** Measured failure: S11, 5/5 trials lost a park. In `mesh.deploy_override` (:501)
   and `deploy_donor_sidecar` (:284), add microseconds or an increment-until-free suffix.
8. **(Docs) "seam-continuous / nothing tears" is Terrain-only.** The module docstring at terrain.py:9-10 and the
   `_cmd_world_deploy` docstring (cli.py:4091-4092) should say so (S2/S5).

## 6. Proposed in-game probes (designed, NOT run; harness memory `project-ff9-test-harness.md`)

**P1: beach seam slit and one-way wall (one deploy, relaunch-free).**

Setup:
1. Into a scratch folder stacked on top of FolderNames, run `world-terrain --at 480 -1120 --radius 16 --raise 3` on (7,17).
   Alternatively use a revertable deploy to the world folder.
2. Apply with ~ → World → Reload overworld. Teleport to (476,-1120).

Predictions:
- `game_snap.ps1` shows a ~2.5-3u void slit along the foam/sand seam and the shallow-rim seam (10 torn welds).
- With the harness, walk from the foam (476.28,-1120.28; ground 0.36) north-west onto the terrain: **refused**. All 24
  probe crossings are predicted refused (`probe_detail.json` P1_A3).
- Walk the other way (terrain → beach): legal.
- Control: redeploy with `--raise 1`. The slit is still visible, and **0** walls.

**P2: origin-shift wall at Treno's gate.**

Setup: `world-terrain --at 1274.219 -954.016 --radius 8 --raise 1` on (19,14). The seam rise is only 0.27-0.38u.

Predictions:
- Walking from the terrain at (1277.6,-951.19) onto the walkable gate Object at (1278.38,-951.32) is **refused**.
- The ground under the target reads 28.6 on topo 59 (the overhang sheet), not the walkable ramp.
- The same walk on stock is legal.

This tests buffer-order first-hit plus the raised ray origin, a mechanism no gate models. One deploy, one walk, plus
a stock control.

## 7. Contradictions with recorded knowledge (both citations)

- **mesh.py:347-351 and entrance.py:741-743 vs terrain.py:139-143 / :98-104 and the probe in S3.** The code is right;
  the two docstrings are wrong.
- **operators F14 prose vs `operators/out/writer_gate_census.json` and transplant.py:3172/:3890.** weld_audit and the
  T-junction gate are transplant-only.
- **disc4/VERIFY.md D4-06 ("11 covered T-junctions"; "26 of 37 uncovered") vs `stitch_census.py`/`calibrate.py`.**
  There are 0 T-junctions, and 14 of the 37 are uncovered by edge coverage.
- **disc4/NOTES.md:191 ("stock disc 1 has 17 real border gaps") vs `border_closure.py`.** 7 open pairs, 17.24u.
- **mesh.py:1557-1559 (weld_audit: "The verbatim donor blocks have ZERO such pairs") vs `stitch_census.py`.** This holds
  for disc-1 carried parts. Disc-4 (18,4) Terrain has 3 near-miss pairs (0.0039-0.0398u), so a disc-4 carry of that
  block would fail transplant's 0-pair weld gate on stock bytes.
- **memory `project-ff9-worldmap-feasibility.md:349-351` ("there is NO slope/step gate ... a raised slope stays walkable
  at any grade") vs ff9.cs E1/E6b and calibration W2/W3.** A climb above 2.34375u per step is refused; above
  1.171875u when the climb starts on topo 36-38. The vertical lane V3 already sourced the canopy half. The kit's own
  `terrain._walk_gate` agrees with the engine, so the memory line is stale.
- **memory coast-mosaic BERM LAW (664/702).** Not a contradiction, but now reproducible, with its definition pinned (C1).
  The kit's beach-mint L-chain gives 621/630.

## 8. Open questions

- **Are the seam slits as visible in-game as the geometry says?** A 1u slit at a 30-60u camera distance may be a
  hairline. Needs P1's +1 control.
- **Is the world-deploy refusal text's spawn mechanism right?** It says the "stale pre-raise Y" makes the actor embed.
  The vertical lane V1 says spawn/teleport sky-cast from y+400. If so, an entrance raise embeds nobody, and the real
  entrance costs are the prop pit and the dead tiles in S3. Needs one harness field-exit onto a raised entrance tile.
- **Do the disc-4 (18,4) Terrain near-misses render as pinholes?**
- **Do the 7 stock open border edges** ((17,13)|(17,14) and the others) **show as seams in-game?** Possibly hidden by
  the camera.
- **Does the 10-slot cache matter anywhere a Y edit leaves overlapping sheets?** For example a raise that pushes Terrain
  above a stacked Object tri. The cache path skips the up-facing and idall filters (E10b). W4 saw 0 cache decisions at
  seams.
