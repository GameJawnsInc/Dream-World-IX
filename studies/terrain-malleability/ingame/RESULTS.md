# In-game results: terrain malleability study, harness sessions 1-7

Experiments from the study's ranked list (`../README.md` section 7.1), run under the in-game test harness against the
live install. The harness kept saves in its sandbox (`x64/ff9harness/save`), and every prediction was registered in the
scenario docstring before the run. Run artifacts (frames, state rings, both logs) are in the gitignored
`.harness-runs/` folders named below.

**Sessions 1-3 wrote no file to any mod folder.** Sessions 4-7 deployed only into a scratch folder, `FF9CustomMap-lab`,
with the owner's approval (2026-10-07):
- It sat first in `Memoria.ini` FolderNames for the duration; the ini was backed up to
  `backups/Memoria.ini.pre-terrain-lab.20261007-133301`.
- One change was deployed per run.
- At the end the ini was restored byte-exact (sha256 `0b5a4985…`, the same as the backup) and the lab folder was removed.
- No live Southern Ring folder was touched.

| session | run dir | checks |
|---|---|---|
| 1 | `.harness-runs/20261007-125119-terrain-session1` | area part partly, then a zone-5 battle → GameOver |
| 1b | `.harness-runs/20261007-125638-terrain-session1b` | 7/8 (A4 timing artifact, see below) |
| 2 | `.harness-runs/20261007-130347-terrain-session2` | 4/5 (F-M1 proved nothing, see below) |
| 3 | `.harness-runs/20261007-130728-terrain-session3` | 6/7 (R3 instrument failure, see below) |
| 4 | `.harness-runs/20261007-133403-terrain-session4` | 3/4 (the miss = the lattice-edge teleport trap, see section 5) |
| 4b | `.harness-runs/*-terrain-session4b` | 2/2 |
| 5 (+3) | `.harness-runs/*-terrain-session5-raise3` | 1/2 (descent refused at 2 of 3 lines: a new finding) |
| 5 (+1) | `.harness-runs/20261007-134218-terrain-session5-raise1` | recovered from the state ring (a battle ended the run) |
| 6 | `.harness-runs/*-terrain-session6-crack`, `*-terrain-session6-replay` | 3/3, then 2/2 |
| 7 | `.harness-runs/*-terrain-session7-under`, `*-over`, `*-max65535` | 2/2, then CAP-1 refuted (section 8) |

Rerun order:
1. The offline preps, which read the live mesh: `area_prep.py`, `vertical_prep.py`, `forms_stock_prep.py`,
   `disc4_prep.py`. For the deploy sessions also `forms_build.py`, `vcap_build.py`, and the `world-terrain` commands
   in each scenario docstring.
2. `py tools/play.py studies/terrain-malleability/ingame/terrain_session<N>.py --label terrain-session<N>` (the
   phase-selecting env vars are named in each docstring).
3. `py studies/terrain-malleability/ingame/session1_post.py <run dir>` for the height scoring.

## 1. The area layer (experiment rank 1): area bits drive the camera and the labels

Spots picked offline from the live Disc1 `Block[19][18] Terrain` (Southern Ring), via `area_prep.py`:
- **P12** (1248.18, −1191.31): stock Cleyra entrance tile, IDALL 19620 = event 1, area 12, topo 41.
- **P14** (1252.68, −1194.81): area 14 (the safe road).

| check | result | evidence |
|---|---|---|
| A1 window title names the area's location text | **confirmed** | P14 `FINAL FANTASY IX - World Map: 9011, Lindblum Plateau`; P12 `... Vube Desert` (1b) |
| Main-menu LOCATION label | **confirmed** | 1b `shots/a12-menu.png` reads "Vube Desert" on P12 |
| A2 R2 toggles the camera on area 14 (instrument control) | **confirmed** | frame change 22.6 / 21.8 against no-input noise 0.0 (sessions 1 and 1b) |
| A3 entering area 12 forces the view back down | **confirmed**, by walking (s1) and by teleport (1b) | P12 frame vs P14 default 9.9 / 11.6, vs P14 high 26.1 / 19.7 |
| A4 R2 refused on area 12 | **confirmed** (s1) | change 0.003 against noise 0.0. 1b's "fail" (9.5) was the camera still descending: the post-R2 frame is *closer* to default (9.4) than the arrival frame (11.6) and far from high (24.8); confirmed by eye |
| A5 back on area 14, R2 works again | **confirmed** | change 22.6 (1b) |
| **zone-5 battle on the stock Cleyra tiles** | **confirmed, unplanned** | s1: a battle started at (1239.88, −1190.75) while the harness was turning the camera. Offline at that x/z: IDALL 19620, area 12, topo 41. The battle was **scene 174**, the only scene of record 57 = zone 5 / topo 41 / **fog 1**. The level-1 party lost (GameOver). |

**Verdict:** the README section 6 defect 15 is live and in-game proven. The stock Cleyra entrance tiles at Southern
Ring (19,18) lock the camera below scenario 4990, relabel the place "Vube Desert" in the title and the main menu,
and **roll zone-5 battles inside the area-14 safe road**. The area-12 direction is as GA3 corrected it: forced *down*
to the default view, with the toggle refused. Not checked: the save-slot Location channel, spawn weather.

## 2. The vertical envelope (experiment rank 5): canopy sink confirmed exactly

Session 1b, scored by `session1_post.py` against the live mesh at the exact x/z of each reading. The sky query is
the same rule arealib uses (calibrated against `placement.place`).

| site | readings | published y − ground | prediction |
|---|---|---|---|
| lawn (topo 0), (972.18, −996.30) | 4 | −0.0023 … −0.0035 | 0 (instrument check) |
| forest (topo 37), (982.68, −1003.30) | 4 | **−1.1724 … −1.1733** | −1.171875 |
| basin (3,7), (223.69, −463.81) | 4 | +0.0020 … +0.0036; y = **−5.762** on Terrain | V10: ≈ −5.77, no water |

**Verdict:**
- **V3 (canopy sink): confirmed in-game to 0.0015u.** On topo 36/37/38 the on-foot actor sits 1.171875u below the
  surface, so the step ceiling *from* canopy is 1.171875u, not 2.34375u. Memory's THE CANOPY STEP LAW and
  `placement.WALK_SPEED` (79.4°) need the canopy case (README section 5.1 and 5.3).
- **V10 (sub-zero basin): confirmed.** The actor stands at −5.76 on Terrain with no water sheet.
- Not run: the flight part (Hilda Garde over the 42.67 summit), because the harness cannot summon a vehicle.

## 3. The stock form switch (experiment rank 2, no-deploy half): proven, and decided per world load

Driven with the harness alone: the scenario counter (`warp ... scenario`, or a poke of gEventGlobal[0..1]) and
gEventGlobal bits. Cleyra (14,12) gives a numeric signal on walkable lawn, 10-12u from any event tile
(`forms_stock_prep.py`): (918.68, −776.80) reads Form 1 3.471 / Form 2 3.906; (920.18, −783.80) reads 2.923 / 3.309.

| check | result | evidence |
|---|---|---|
| F-C0 / F3a: scenario 0 → Form 1 | **confirmed** (s2, s3) | 3.4727 / 2.9219 |
| F-C3: field round trip at scenario 10650 → Form 2 | **confirmed** (s2) | 3.9063 / 3.3086. The walk geometry switched with the form (F1). |
| Water Shrine at scenario 10650 | **confirmed by eye** (s2) | `s3-WaterShrine.png` shows the spire, the whirlpool and the reshaped water; scenario 0 (`s0-...`) shows open, misty sea. The mist also lifts, because it is its own toggle (D4-15). |
| **F3b: a mid-visit scenario change does nothing until the world reloads** | **confirmed** (s3) | poked gEventGlobal[0..1] = 10650 on the world map: the counter published 10650 at once, Cleyra stayed 3.4727 / 2.9219 (Form 1). Mechanism: `w_frameScenePtr = ushort_gEventGlobal(0)` is copied only at world init (`ff9.cs:3652`). |
| the world a door leads to depends on the scenario | observed | the 6603 door went to 9011 at scenario 0, **9007** at 10650, **9008** at 11100 |
| F-M1/M2: Mognet bits 815/814 poked mid-visit, then a reload | **proved nothing** | the 8.6 "change" in S1 is the whole frame shifted ~12 px vertically (the camera eye easing from a different teleport origin), not a form. Mognet's 2→44-tri Object is not distinguishable from the vantage 46u away (S2 vs S0 0.15). Superseded by F3b, a numeric test of the same law. |

## 4. The disc-4 crescent ridge (experiment rank 11)

Disc 4 is reachable without the `~` menu: a field round trip at scenario 11100 loaded world 9008 on disc 4.
The ridge is `disc4/out/rock_ribbons.json[0]`: centroid (1144.4, −395.2) near the Earth Shrine, axis 131.4°.

| check | result | evidence |
|---|---|---|
| R1: crossing A → B blocks at the foot | **confirmed** | blocked after 5.03u of 14, at 1.97u from the axis (the rock core is ±1.5u); he climbed the walkable lower flank first (y 2.89 → 4.42) |
| R2: crossing B → A blocks at the foot | **confirmed** | blocked after 5.54u, at 1.46u from the axis, after sliding 1.8u along it |
| R3: walkable alongside | **proved nothing** | walking "down" toward the camera in R2 swung its yaw, so the later left/right presses did not run parallel to the crest (moved 10.9u total, only 4.6u along the axis). The offline prep says the ±8u strip alongside is all walkable. |
| LOOK | for the owner | `ridge-from-A.png`, `ridge-A-stop.png`: a raised ribbon of fibrous, moss-flecked bark texture, ~1-3u tall, laid across unchanged sand and grass. Consistent with "Iifa roots" (D4-09); the owner names it. |

## 5. The data-driven form switch (rank 2, rungs F0 + F1): story-driven terrain with no DLL, proven

The lab folder carried two files:
- `Environment.txt`, with `Place WaterShrine` and `Place BlackMageVillage` both conditioned on
  `(GetEventGlobalByte(1089) & 1) != 0` (flag 8712);
- `Block[22][14] Terrain2.ff9mesh`, the Black Mage Village cell's stock Form-2 terrain with a radius-12 disc around
  (1440, −928) flattened to y 26.0 (`forms_build.py`).

| check | result | evidence |
|---|---|---|
| E0: flag off, scenario 0 → stock ground | **confirmed** | centre 21.5625 (stock 21.5625); off-lattice m1-m4 (4b) within 0.003 of Form 1 |
| **E1: flag on + a world reload, still at scenario 0 → our Terrain2 is the walkable ground** | **confirmed** | centre **25.996** (pred 26.0); m1-m4 **24.375 / 22.965 / 26.4375 / 21.734** (pred 24.375 / 22.965 / 26.437 / 21.736) |
| E2: flag off + reload → stock again | **confirmed** | 21.5625 / 17.418: reversible on each load |
| LOG | **confirmed** | `[WorldMeshOverride] loaded 'WorldMap/Disc1/0_1/r14/Block[22][14] Terrain2'` on every world load |
| session 4's east point read y = 0.0 | instrument artifact | (1444, −928) sits exactly on the shared edge of tris 309/488: THE LATTICE-EDGE TELEPORT TRAP. 4b's off-lattice points all read correctly. |

**Verdict:** two forms-lane findings are now **in-game proven**:
- **F13:** a `Terrain2` override binds by its child name under `0_1`.
- **F6:** a mod-folder condition replaces a place's stock condition, and it is re-parsed on every world load.

Together with F3 (forms are decided once per world load, section 3), the kit has a working, DLL-free lever for terrain
that changes with the story on the 26 switchable cells.

## 6. The beach-seam tear (rank 3): a one-way wall at +3; the "descent stall" was a harness artifact

`world-terrain --radius 16 --at 480 -1120 --raise 3`, then `--raise 1` as the control, both into the lab folder.
Three lines cross the Terrain/Beach1 seam at x = 476.28 / 479.64 / 480.18; the beach is to the south, at z ≈ −1120.

| check | +3 | +1 control |
|---|---|---|
| beach → terrain (climb) | **REFUSED at all 3 lines**: progress 0.18-0.36u, height unchanged | **legal at all 3**: climbed 0.89 / 1.14 / 1.07u onto the terrain and walked on |
| terrain → beach (descent) | **legal** (see the correction below); session 5's harness read "blocked" at 479.64 and 480.18 | not reached: a battle (scene 828) began on line 2 |

**Correction: the descent stall was a harness artifact** (stall session, `.harness-runs/*-stall-session`, 8/8;
design and simulator `stall_sim.py`, `stall_PLAN.md`, adversarially reviewed). Session 5 saw the actor creep in
shrinking steps to the torn edge and "stop dead" there, 3.06u above the beach. What actually happens:
- The engine has no descent limit: `WMBlock.Raycast` never reads `distance`.
- `w_movementControl` normalises each step by the 3D displacement, `step = speed² / |Δxyz|` (`ff9.cs:5568-5593`).
  Near a ~3u drop the step collapses to ~0.06u per tick: a slow CREEP.
- `world_approach` judged the creep "blocked" after one short burst and released the stick. The final identical
  samples were simply no input.

The confirmation run:
- **Held on past the "stall"**, the actor crept on and dropped onto the beach within 2 bursts (K3).
- **A start shifted** so the last full step ends 0.036u from the edge crossed with no creep at all, at the same x and
  the same 2.96u drop (K4).
- **The "passing" x 476.28** reads "blocked" too, once its start is shifted into the creep (K5).
- **Instrument control:** the +3 CLIMB is a true stall that the creep walker does see (K1).
- **The simulated mesh is the live one:** the deployed mesh's sha256 matches it, and the teleport heights match it exactly (K0).

**Verdict:** a Terrain-only +3 edit at a beach is a ONE-WAY wall: beach → terrain is refused, and terrain → beach is
legal but slow at the edge. It does not trap a player. **Harness lesson:** `world_approach` must not call a single
short burst "blocked". Require consecutive sub-threshold bursts, or zero motion.

## 7. The disc-4 crack and its replay (rank 4, defect 8): both proven

`world-terrain --radius 16 --at 256 -872 --raise 4` logged `SKIP (4, 13): real cell differs across discs in
['sea1']` and mirrored only (3,13), exactly as G3 predicted.

| check | result |
|---|---|
| disc 1 is smooth across x = 256 | **confirmed**: W 5.195 / E 5.395 (pred 5.198 / 5.397) |
| disc 4 is cracked | **confirmed**: W 5.195 (raised) / E **1.746** (stock, pred 1.750); W2/E2 4.887 / 2.086 |
| walking west from the low side on disc 4 | **refused at x = 256.03**, the block border |
| after the `--disc 4` replay | **healed**: disc 4 reads the disc-1 hill at all four points (E 5.395) |

## 8. The vertex-cap window (rank 8): CAP-1 REFUTED in-game

A flat walkable plane on the isolated ocean cell (21,1). The hand packer was first calibrated byte-for-byte against
`ff9mesh_bytes` (`vcap_build.py`).

| part vertex count | result |
|---|---|
| 64,998 (kit-written) | renders, walks at y 6.0; the rest of the world loads |
| **65,001** (hand-packed; the kit now refuses it) | **renders AND walks** at y 6.0; no "Mesh.vertices is too large" in either log |
| **65,535** (the s34 loader's own maximum) | **renders AND walks** at y 6.0 |

**Verdict:** the study's CAP-1 law is **refuted**. It said Unity 5.2.3p2 refuses a Mesh over 65000 vertices natively,
so the per-part ceiling is 21,666 tris. In fact the binding ceiling is the s34 loader's 65,535 (16-bit indices), which
is 21,845 tris under the flat contract.
- The kit's original 65535 bound was right.
- The 65000 bound merged at `b68e1c6b` is over-strict by 535 vertices, and its comment states a false fact.
- It is functionally harmless (the largest deployed part is 4,647 vertices), but it should be corrected.

## Round 2 (2026-10-07, owner's go: "work on vehicles in the harness and the other items that don't need my eye")

Designed offline by a 5-lane workflow (`veh_*`, `png_*`, `stall_*`, `d9_*`, `cost_*`; each lane wrote `<lane>_PLAN.md`).
The vehicle and stall designs were adversarially reviewed, and the review fixed real defects in both before any run.
Deploys used the same scratch-folder protocol: the ini was backed up to
`backups/Memoria.ini.pre-terrain-lab2.<stamp>`; the lab was first in FolderNames, with one change per run, and was
removed after.

### 9. Vehicles under the harness: DLL-free, proven

**The route** (`veh_PLAN.md` section 2):
- The controlled vehicle is decided at world load from gEventGlobal[190].
- The harness warps to field 6603 at a chosen scenario counter, then pokes [190] (vehicle mode), [191], and the
  vehicle's position record ([74..82] for the boat and airship, [83..91] for the chocobo, plus bits 809/810).
- It reads every byte back, then walks out of the door.
- Proof of binding: the published world position equals the poked record (the on-foot actor would arrive at (68, −444)).

**Inputs:** "confirm" is the airship throttle, "down" climbs (InvertedFlightY = 1), and Cancel lands. On the boat,
"up" goes forward and left/right turn the hull. The chocobo uses the on-foot verbs.

| session | result |
|---|---|
| 1, Hilda Garde III (no deploy) | **13/13.** Bound at the poked record (0.001u). **RANK 5: over the 42.64 summit the airship reads exactly 42.1875 -- 0.45u INSIDE the rock** (the ceiling is applied after the floor raise). It never rises above 42.1875, and diving stops on the ground. **V13 landing:** Cancel over sea is refused; over topograph 42 it is refused (the engine accepts, the world .eb only lands on topographs 0-13); over topograph 12 it lands and puts the player down **exactly 2.50u** away. |
| 2, chocobo (no deploy) | 8/10. Bound as yellow (vehicle 1) and light blue (vehicle 2). **The canopy sink applies on a chocobo:** forest −1.1732, lawn −0.0035. The light-blue chocobo enters sea water (y −0.16), as its mask allows. **Misses:** (a) the speed ratio chocobo/foot is 2.24, not the predicted 200/112 = 1.79 (a real prediction miss, cause unknown); (b) the yellow "waterline" check proved nothing -- it slid ESE along the beach and stayed on Beach1 topograph 30, never touching water, and the progress metric counted the slide. |
| 3, the no-fly ring (lab: a `Block[1][13] Terrain` with a topograph-15 ring) | **7/7. A topograph-15 ring stops the Hilda Garde at its edge (r 8.24) at y 2.0 AND at the 42.1875 ceiling; climbing while pushing into it is refused too; a topograph-41 control ring is crossed at both heights.** A no-fly wall is authorable from topographs alone. |
| 4, the boat under a reclaimed cell (lab: `world-reclaim` on (21,1), no `Donor.txt`) | 6/6 for each of flat6, flat1.2 and island. **H1 CONFIRMED: with land at 6u, the Blue Narciss sails UNDER the reclaimed slab at water level (open lane, 44u in). On the rim lane it stops at 19.81u in (pred 19.75), on the hidden islet rim of the free-riding `Block[12][10]` water.** Slabs at 1.2u and the island profile stop it at the cell edge. The stock-coast instrument control stalled at 16.47u (sim 16.38) in every phase. The optional "none" phase did not run: field 6603's axis calibration failed twice on a frame hitch. |

**Verdict:** the harness can drive every vehicle class with no DLL. Defect 18 (a sidecar-less reclaim free-rides
`Block[12][10]`'s water) is now player-visible: boats sail under such land. `terrain.reclaim` should write a
`Donor.txt` or blank the water parts.

**Fixed after the round (blank, no sidecar):** reclaim now writes a hidden stub for each of 12,10's Sea1/3/4/5.
Offline, the same `veh_prep` boat simulator, fed the old shape, reproduces this session's registered numbers
exactly (flat6 open 123.81, rim 19.75; cliff crossing too). Fed the new shape it stalls at into −0.05 on both lanes,
at all 9 hull headings, for flat6, flat1.2, island and cliff. **Re-driven in game: section 14.**

### 10. The per-cell texture override (rank 6): 22/22, the clobber confirmed

Treatment cell (21,1) carried a magenta `Terrain.png`, a red `Sea4.png`, and a lime `Sea3.png` with no Sea3 mesh. The
control cell (0,13) carried the same meshes with no PNGs. All judging was numeric (vivid-pixel counts):
- **Terrain PNG:** loaded (the log has the receipt) but **NOT rendered**: the Moguri atlas from `SetupPreloadedMaterials` overwrites it.
- **Sea4 PNG:** **renders** (28-29% of the frame, static across the animated sea).
- **Sea3 PNG with no Sea3 mesh:** never opened.
- **Reload:** PNGs are re-read on every world load.

C10/CAP-9 are confirmed: per-block TERRAIN textures need the engine patch P2; per-block WATER textures work today.

### 11. The disc-4 ridge and the descent stall, revisited

The "descent stall" correction is in section 6 (a harness artifact).

### 12. The Disc9 walk (rank 1 b/c): carried encounter area proven, bind oracle calibrated off disc 1

Bench field 30950 plus its `WorldMap(9013)` splice were deployed into the lab, then reverted.

**Control loop** (area-0 landing lawn): the battle was scene 5 (Ironite), which is in zone 0's set.

**Carry loops** (Uaho cell (13,15), donor area 63):
- Battles were **778 (Adamantoise) twice on topograph 0** and **780 (Worm Hydra) on topograph 37**. Those are exactly
  zone 24's fog-0 records.
- So a verbatim carry imports its donor's encounter area onto the Path D world, and s75's mist suppression reaches
  `w_frameFog`.
- Heights matched the mesh, canopy sink included, in 52/52 bursts.

**Bind oracle on Disc9:** 65/65 cells, 238 lines per load, 0 mismatches over 4 loads -- its first receipts off disc 1.

The first attempt lost three loops to field 30950's calibration hitch. A retry fixed it (`d9_session.py`).

### 13. The in-game cost budget (rank 10): x4/x16 free at normal speed, x64 halves the frame rate

One launch with 18 world loads (`.harness-runs/*-cost-session`, 21 min).
- **Arms:** the same flat plane on cell (21,1) at x1 / x4 / x16 / x64 density (338 / 1,352 / 5,408 / 21,632 tris).
  Each arm is identified by its walked height tag; P1 passed 17/17, with one lab load line per world load.
- **Bracketing:** every test arm is bracketed by x1 loads, and the one lab file is swapped during field round trips.
- **Per load:** idle, a 600-tick circle walk at 28 ticks/s, then the same at timescale 4 (the positive control).

**The pre-registered verdicts were INCONCLUSIVE.** The decision rule counts only segments classed as the ~31 or ~60 fps
regime, and this launch ran steadily at ~40 fps ("other"), so the filter discarded almost every segment. **The
bracketed raw data below are a POST-HOC reading** (walking fps of each test load against the mean of its two x1
neighbours; the A-A noise sigma is 0.97 fps):

| arm | walk fps delta vs neighbours (1x ticks) | at timescale 4 (112 ticks/s) | idle (render) |
|---|---|---|---|
| x4 | +1.9, +1.1 → **free** | 39.7 / 39.1 fps (x1 ~37-42) → free | unchanged |
| x16 | −2.0, +1.4 → **free** | **14.4 / 15.4 fps** → costs at 4x the tick rate | unchanged |
| x64 | **−20.6, −22.2, −18.8** → **halves the frame rate** (~41 → ~21) | **0.93 fps**; only ~30 of 112 ticks/s run | unchanged |

- The extra triangles cost nothing to RENDER (idle fps is flat in every arm). The cost is the ground-query scan,
  paid per tick while moving: it is the walker's 2 probes plus the camera's 4 un-cached sky probes (CAP-10).
- Implied per-test cost: about 0.3-0.45 µs per triangle test (x64 at 1x: ~18 ms extra a tick for 55,552 tests;
  x16 at 4x: ~5.7 ms a tick for 12,808 tests). This agrees with the registered central c = 0.25 µs.
- World-load time shows no arm effect (the LoadBlocks frame is bimodal, 130 ms vs 1,600 ms, independently of the arm).
- The last pair (W16/W17) is contaminated: a system-wide slowdown hit the x1 reference too (23 fps). It is excluded.

**Verdict (post-hoc):** a walkable cell can be refined about 16x (5.4k tris) with no measurable cost in normal play.
At 64x (21.6k tris, near the per-part cap) walking on it halves the frame rate. The kit has no density gate. A soft
budget of about 5k tris per walkable part, or a lint warning above it, is justified. The decision rule needs a
regime-agnostic bracket test before it is reused (`cost_post.py`).

### 14. Defect 18 re-driven after the fix (2026-10-08): the boat stops at the cell edge, flat6 and cliff

Owner's go for both launches. Same scratch-folder protocol: ini backed up to
`backups/Memoria.ini.pre-d18-redrive.20261008-100040`, the lab first in FolderNames, one deploy per launch, then
the ini restored byte-exact (sha256 `0b5a4985…`, verified) and the lab removed. Kit at `519b5f83` (the fix).

- **Registered first** (`d18_predict.py` → `out/d18_predict.json`). It drives the real `terrain.reclaim` output
  through the round-2 simulator, after reproducing round 2's registered pre-fix numbers. Prediction: a stall at
  into −0.05 on both lanes, at all 9 headings. `veh_session4.py` gained the phases `flat6-fixed` and `cliff-fixed`,
  each judged as a stall at into −1.0..+0.1.
- **Lab contents per launch:** Terrain plus hidden Sea1/Sea3/Sea4/Sea5, and no `Donor.txt`. `Memoria.log` bound
  exactly those five files from the lab, the bind oracle's prediction, with 0 exceptions.

| launch | checks | OPEN lane | RIM lane | before the fix (round 2 / sim) |
|---|---|---|---|---|
| flat6-fixed (`.harness-runs/20261008-100049-…`) | **6/6** | stall at into −0.002 | stall at into −0.002 | crossed the cell under the slab / stopped on the hidden islet rim at 19.81 |
| cliff-fixed (`.harness-runs/20261008-100425-…`) | **6/6** | stall at into −0.002 | stall at into −0.002 | sim: crossed the cell (123.54 / 118.87) |

Instruments held in both launches: B0 bound the boat at the poked record (0.001u), B1 heading 0.0, and C0 stalled
at 16.47 (sim 16.38, round 2 16.47).

**Verdict: defect 18 is fixed in game.** A reclaimed cell carries no water, so the boat's sea-level probe misses at
the cell edge: the engine's vehicle wall.

**Seen in the frames.** The cliff edge reads clean: the rock wall meets the water, and the boat sits at its foot.
A raised `flat` slab shows open sky through the hole beneath its edge (`open-flat6-fixed.png`). It used to show the
free-riding sea there. That is a visual regression for raised flat slabs, and the island and cliff profiles do
not have it, since both come down to the waterline at the cell edge.

**Frame rate (the owner flagged a laggy overworld on the flat6 launch).** Overworld fps, median (10th–90th
percentile): flat6-fixed 40.9 (27.3–51.2), cliff-fixed 47.2 (37.6–57.4), round-2 flat6 46.4 (29.4–58.9). Fields
ran 51–57. Both fixed launches carry the same five files, and the fix replaces 501 free-riding water tris with
four 1-tri stubs. So the dip tracks the machine's background load (two Godot and three python processes held about
40% of the CPU), not the geometry.

### 15. Defects 15-17 fixed on the live Ring, verified in game (2026-10-08): 11/11

The fix is southern-ring `REVERT.md` section 32 (the host-area stamp): 18 live files, area bits only, both discs.
No deploy for the session itself; it reads the live install. `area_host_prep.py` reads every point off the stamped
mesh first; `area_host_session.py` reuses round 1's route (6603 door) and frame instruments.

| check | result | evidence |
|---|---|---|
| H0 scenario < 4990, so an area-12 tile would still lock | PASS | scenario 0 |
| H2 control: R2 on P14 | PASS | change 18.7 vs noise 0.002 |
| C1-C3 the title follows the tile: a stock area-12 control reads "Vube Desert" before each fixed point | 3/3 PASS | the window title |
| H1 P12, round 1's lock spot on the carried Cleyra tiles, now reads "Lindblum Plateau" | PASS | round 1: "Vube Desert" |
| H2 R2 on P12 now toggles the camera | PASS | change 22.4 vs noise 0.004; round 1: refused |
| H3 Sandreach Beach1 reads "Lindblum Plateau" | PASS | before: "Palmnell Island" |
| H4a Ashvale's trigger reads "Lindblum Plateau" | PASS | before: "Gunitas Basin" |
| H4b Confirm on the trigger still enters field 6601 | PASS | the dispatch rides the cell tag |
| H4c the Lantern Hall renders and grants control | PASS | mean luma 60.1, `shots/hall.png` |

Runs: `.harness-runs/20261008-104545-area-host` (7/7, no title control), `…-104834-area-host-controlled` (10/10),
`…-105035-area-host-hall` (11/11, the record of this section). Memoria.log: 0 exceptions.

**Two instrument lessons.**
- The first run's three title checks all expected "Lindblum Plateau", which the P14 control also shows. A title
  that never updated would have passed every one. Read a DIFFERENT name between the points.
- The first run's frame 60 frames after Confirm was black while the state said field 6601 and FieldHUD: the hall
  had not published the player yet. `wait_control` first, then judge the frame.

## Not run

- Rank 9 (rock stretch): needs the owner's eye on the Uaho bench.
- The boat "none" phase (see section 9).

## Instrument lessons (for the next scenario)

- Memoria retitles the window `FINAL FANTASY IX - <message>` (`PlayerWindow.cs:51`); match by substring.
- Walking on encounter tiles at level 1 ends in GameOver; teleport onto them instead (encounters need movement).
  `world_face` probes walk ~30u, so face on a known-safe lawn (the 6603 landing, (68, −444)). The yaw survives a
  teleport, but not walking toward the camera.
- After a teleport the camera eases for more than 90 frames when it has to come down from the high view. A frame
  comparison needs a longer settle, or a third frame.
- A frame difference across two world entries mixes in camera easing. Use a numeric (height) signal when one exists.
- A walk's stall detector (two bursts under 0.3u) cannot tell a slow, 3D-normalised creep from a block. Read the state
  ring before calling a descent "blocked".
- Pick teleport points off the 4u lattice. `forms_build.py`'s grid-aligned probe hit the lattice-edge trap.
