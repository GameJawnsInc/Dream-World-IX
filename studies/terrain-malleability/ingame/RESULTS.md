# In-game results: terrain malleability study, harness sessions 1-3 (no deploy)

Experiments from the study's ranked list (`../README.md` section 7.1), run under the in-game test harness against the
live install. **No file was written to any mod folder**: every run reads the install as it stands. The harness kept
saves in its sandbox (`x64/ff9harness/save`). Every prediction was registered in the scenario docstring before the run.
Run artifacts (frames, state rings, both logs) are in the gitignored `.harness-runs/` folders named below.

| session | run dir | checks |
|---|---|---|
| 1 | `.harness-runs/20261007-125119-terrain-session1` | area part partly, then a zone-5 battle → GameOver |
| 1b | `.harness-runs/20261007-125638-terrain-session1b` | 7/8 (A4 timing artifact, see below) |
| 2 | `.harness-runs/20261007-130347-terrain-session2` | 4/5 (F-M1 proved nothing, see below) |
| 3 | `.harness-runs/20261007-130728-terrain-session3` | 6/7 (R3 instrument failure, see below) |

Rerun order: `area_prep.py`, `vertical_prep.py`, `forms_stock_prep.py`, `disc4_prep.py` (offline, read the live
mesh), then `py tools/play.py studies/terrain-malleability/ingame/terrain_session<N>.py --label terrain-session<N>`, then
`py studies/terrain-malleability/ingame/session1_post.py <run dir>` for the height scoring.
(`forms_build.py` and `forms_prep.py` prepare the deploy-gated rung F1 and were not run in-game; see "Not run".)

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

## Not run (needs a deploy into a shared mod folder, so the owner's go)

The auto-mode classifier refused the build step of the deploy-gated form rung ("modify shared resources"). Every
experiment below writes files into the live install, so none was attempted:
- **F0/F1, the data-driven form switch.** An `Environment.txt` flag condition plus a `Block[22][14] Terrain2.ff9mesh`.
  This is the story-terrain authoring lever, and the `Terrain2` key (F13) has never been loaded in-game.
  `forms_build.py` holds the exact files and predictions; it writes only to the session scratchpad.
- Rank 3 beach-seam tear, rank 4 disc-4 crack and replay, rank 6 per-cell PNG, rank 7 the (12,10) free-ride,
  rank 8 the vertex-cap window, rank 9 rock stretch, rank 10 the cost budget.
- Rank 1(b), the Disc9 battle walk: bench field 30950 is not registered in any live folder now, so there is no way in.

## Instrument lessons (for the next scenario)

- Memoria retitles the window `FINAL FANTASY IX - <message>` (`PlayerWindow.cs:51`); match by substring.
- Walking on encounter tiles at level 1 ends in GameOver; teleport onto them instead (encounters need movement).
  `world_face` probes walk ~30u, so face on a known-safe lawn (the 6603 landing, (68, −444)). The yaw survives a
  teleport, but not walking toward the camera.
- After a teleport the camera eases for more than 90 frames when it has to come down from the high view. A frame
  comparison needs a longer settle, or a third frame.
- A frame difference across two world entries mixes in camera easing. Use a numeric (height) signal when one exists.
