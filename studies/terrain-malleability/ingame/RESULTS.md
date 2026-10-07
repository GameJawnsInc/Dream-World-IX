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

## 6. The beach-seam tear (rank 3): a one-way wall at +3, and a descent stall nobody predicted

`world-terrain --radius 16 --at 480 -1120 --raise 3`, then `--raise 1` as the control, both into the lab folder.
Three lines cross the Terrain/Beach1 seam at x = 476.28 / 479.64 / 480.18; the beach is to the south, at z ≈ −1120.

| check | +3 | +1 control |
|---|---|---|
| beach → terrain (climb) | **REFUSED at all 3 lines**: progress 0.18-0.36u, height unchanged | **legal at all 3**: climbed 0.89 / 1.14 / 1.07u onto the terrain and walked on |
| terrain → beach (descent) | legal at 476.28, where the seam drop is 2.53u; **refused at 479.64 and 480.18**, where the drop is ~3.06u | not reached: a battle (scene 828) began on line 2 |

**The descent stall (new, not predicted).** On the two refused lines the actor crept in shrinking steps
(0.81 → 0.06 → 0.05 → 0.075u) to the torn terrain edge at z ≈ −1119.80, then stopped dead, 3.06u above the beach.
- The raycast imposes no descent limit: `WMBlock.Raycast` never reads `distance`.
- But `w_movementControl` normalises each step by the 3D displacement, `step = speed² / |Δxyz|` (`ff9.cs:5568-5593`),
  and that step collapses as the drop grows.
- **Leading hypothesis:** the collapsed step then lands on the seam line and misses both triangles, and keeps doing so
  every tick because the step is deterministic.

**Status:** observed twice in-game; the mechanism is OPEN and needs a source-level trace.
**Consequence:** a Terrain-only edit at a beach does not only make a one-way wall. Where the torn drop is about 3u, it
can also trap a player who walks to the edge from above.

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

## Not run

- Rank 1(b), the Disc9 battle walk: bench field 30950 is not registered in any live folder.
- Rank 5's flight part and rank 7's boat drive: the harness cannot summon a vehicle.
- Rank 6 (per-cell PNG overwrite), rank 9 (rock stretch, which needs the owner's eye on the Uaho bench) and rank 10
  (frame-cost budget): not attempted this round.

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
