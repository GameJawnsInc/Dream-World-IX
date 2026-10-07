# Vehicles under the in-game harness: route, input map, and four sessions

Lane "veh" of the terrain-malleability in-game round. Covers README section 7.1: rank 5 (the flight part), rank 7
(the (12,10) free-ride with a boat drive, hypothesis H1), and rank 12 (the no-fly topograph). It also adds a chocobo
control for vertical V3 and the chocobo limit mask.

Nothing here has run in game yet. Every prediction below was registered from source and from an offline
simulation over the live mesh before any run.

Engine cites are `file:line` under `C:\gd\FFIX\Memoria\Assembly-CSharp` (the patched working tree). `.eb` cites
name the dispatcher, entry and function. To regenerate them, disassemble the live `us` world `.eb` with
`ff9mapkit.eb.ebsrc.write_source`. `veh_prep.py` re-derives each fact it relies on from the live bytes.

## 1. Verdict

**Route (i) works with no DLL and no `~` menu.** The vehicle the player controls is decided once, when the world
loads, from `gEventGlobal[190]`. The harness can already set every input to that load:

- the ScenarioCounter, through `warp(..., scenario=N)`;
- the bytes, through `poke`;
- the load itself, by walking out of field 6603's door.

This is the same load-time binding that a save made aboard a vehicle uses, and the same one a bridge-interior exit
uses. No engine patch is needed. Route (iii), the agent verb, is sized in section 2.4 as an optional convenience.

## 2. The route, with evidence

### 2.1 What binds control (the live bytes, `out/veh_prep.json["route"]`)

| dispatcher | Main_Init spawns the vehicle actor if | vehicle Init binds control if | placed from |
|---|---|---|---|
| 9003 WORLD03 | `Global.UInt16[0] >= 9400` (entry 0 func 0) | `Global.Byte[190] == 7`, then `AttachObject(12, 6, 0)` + `DefinePlayerCharacter()` (entry 6 func 0) | `Int24[74] Int16[77] Int24[79]`, facing `Byte[82]` |
| 9007 WORLD07 | `>= 10400` | `[190] == 8` (Hilda Garde III, entry 6) | same record |
| 9008 WORLD08 | `>= 11100` | `[190] == 9` (Invincible, entry 6) | same record |
| all three | chocobo entry 5 if `Global.Byte[191] != 0` | `1 <= [190] <= 6`, then `AttachObject(12, 5, 23)` + `DefinePlayerCharacter()` | `[83] [86] [88] [91]` |

- `DefinePlayerCharacter` sets `controlUID` to the running object (`EventEngine.DoEventCode.cs:1033`, CC 0x2C). The
  harness publishes the controlled actor: `world.x/z` come from `ff9.w_moveActorPtr` (`HarnessAgent.cs:1550-1551`),
  and `w_moveActorPtr = GetControlChar()` (`ff9.cs:5157-5162`, `:6102-6103`). Once a vehicle is bound, every world
  verb therefore reads and moves the vehicle, not the anchor.
- **The proof signal for R0 / B0 / N0.** The anchor (entry 12) is placed from `[64..72]`, which 6603's exit writes
  as the landing (68, 4, −444). The vehicle is placed from the record we poke, so a bound vehicle publishes the
  poked position, not the landing. On foot, entry 12's Init case 0 binds the anchor instead, and its per-frame loop
  re-asserts `DefinePlayerCharacter` every frame (entry 12 func 1, case 0).
- **The chocobo is invisible unless bit 810 is set** (entry 5 func 0: `if !Bit[810] SetObjectFlags(14)`). An
  invisible object is skipped by `w_movementUpdate` (`ff9.cs:5171` → `EventEngine.cs:1173-1177`, flags bit 0), so
  the chocobo session sets bits 809 and 810. This is the Chocobo Hot & Cold recipe's pair.

### 2.2 How the world gets loaded

Field 6603 (FARSHORE, served by `FF9CustomMap-world`) has an exit trigger at entry 3, tag 2. It writes:

- `[64..72]` and `[83..91]` = (17408, 1024, −113664, 64), i.e. the landing;
- region key `Int16[2] = 35`.

It then runs the shared cascade. Decoded per ScenarioCounter band for key 35 (`decode_switch` on the live bytes):

| ScenarioCounter | world loaded |
|---|---|
| < 5990 | 9011 |
| 5990-10399, but not 9615-9790 | 9003 |
| 10400-11089 | 9007 |
| ≥ 11090 | 9008 |

So the scenario counters used here are 9500 for the boat (9003, disc 1), 10650 for Hilda Garde III and the chocobo
(9007, disc 1), and ≥ 11101 for the Invincible (9008, disc 4). Avoid exactly 11100: at that value, entry 5 moves the
chocobo once (bit 851).

The trigger first calls `WorldMap(Global.Int16[1062])` when that word is nonzero. It is a kit variable. Every
session reads it back before the door and records it. Nothing writes it in a new game.

Field 6603 never writes `[74..82]`, `[190]` or `[191]`, so a poke made in the field survives to the world load.
Every poke is also read back from watched bits before the door (`veh_lib.reach_world_as`).

### 2.3 Route (ii): the save file

A vehicle survives a save because all of its state lives in `gEventGlobal`: `[190]`, `[191]`, and the records at
64-91 (memory `project-ff9-overworld-vehicles`). That is the same mechanism as route (i). The save route needs a
sandbox save at the right story state, plus title-screen Continue, which loads only the sandbox autosave. It is
strictly more fragile than (i) and buys nothing. **Not used.**

### 2.4 Route (iii): an engine patch (not needed; sized for the record)

The `~` menu's vehicle swap, `Ff9mkDebugMenu.SetVehicle` (`:1640-1687`), only sets `[190]` and calls
`w_movementChange()`. That swaps the physics profile and does not rebind the actor (memory: "Zidane keeps his
model"; flying modes never leave the ground). A harness verb built on it would be worse than route (i).

The faithful equivalent is "set `[190]`, then reload the current dispatcher": `ArmWorldReload(wldMapNo)`
(`:1595-1606`), which is already in-game proven by the reload button.

- **Size:** about 25 lines. That is a public static `HarnessWorldReload(int id)` beside `HarnessWorldTeleport`
  (`:485-489`), a `worldreload` case in `HarnessAgent.Execute` (beside `teleport`, `:670-674`), and a driver
  `Session.world_reload(id)`.
- **Gain:** about 40 s saved per reload, and any dispatcher becomes reachable regardless of the ScenarioCounter
  band, including 9009, which has every vehicle.
- **Risk:** a DLL rebuild auto-deploys over the live install with no backup unless it goes through
  `tools/build_memoria.py`, so it needs the owner's go. **Not recommended now.**

## 3. Inputs: what is hooked, and how each vehicle moves

The harness injects input through `HonoInputManager.IsInput` (`HonoInputManager.cs:906`), the direction-key probe
(`:578`) and `GetAxis` (`:954`). `UIKeyTrigger.GetKey` ends at `IsInput` (`UIKeyTrigger.cs:104`), and so does
`EventInput.GetKey` (`EventInput.cs:351-355`). The ini values that matter here are `AlternateControls = 0`,
`InvertedFlightY = 1` and `RightStickCamera = 1`.

| vehicle (type) | forward / back | turn | vertical | hooked? | world_face / world_approach |
|---|---|---|---|---|---|
| chocobo (0, human operation, `ff9.cs:6110-6113`) | `up` along camera + stick (`:6165-6166`) | camera bumpers (`:6137-6148`) | none | yes, identical to on foot | **yes, unchanged** |
| Blue Narciss (2, ship, `:6201-6261`) | `up` (LY, `:6205-6206`); also `confirm`/`special` through `w_moveGetPadStateR` | `left`/`right` turn the HULL (LX, `:6204`, `:6212-6214`, `:6240-6244`); the bumpers turn only the camera (`:6216-6225`) | none | yes | **world_face: no** (use `veh_lib.hull_steer`). **world_approach:** holds `up`, but its bursts restart the smoothed throttle, so it misreads acceleration as a stall. Use `veh_lib.hold_until` (one continuous hold, measured on progress along the bearing). |
| Hilda Garde III / Invincible (1, plane, `:6263-6439`) | `confirm` = full throttle, `special` = reverse | `left`/`right`, or L1/R1 → ±127 (`:6283-6289`) | LY × InvertedFlightY (`:6278`, `:6310-6312`): `down` climbs here, calibrated per session | yes | **no** (`up` dives); throttle with `hold_until` and place with `teleport` |

**Why the "dark throttle" entry in INPUT-COVERAGE does not bite.** That entry is `ff9.cs:6652`, and it is only half
of the function. `w_moveGetPadStateR` reads the raw right stick only when the stick is past the threshold
(`:6652-6664`). Otherwise it falls through to `UIManager.Input.GetKey(Special / Confirm)` (`:6665-6672`), which is
hooked. With no physical pad the stick is idle, so `hold confirm` is the airship's forward throttle. The airship
climb reads the raw right stick only under `AlternateControls` (`:6268-6276`), which is 0 here.

**Landing and dismounting** go through Cancel KEYON `0x10000` in each dispatcher's entry 3, func 1 (Map.Byte[35] == 0
arm). `GetKeyMaskFromControl(Cancel)` sets the logical `0x10000` bit (`EventInput.cs:484-485`, `:521-533`), so
`press cancel` reaches it. Triangle (`menu`) is entry 3's `0x1000000` arm, which sends the ship to its bridge
interior. **Never press `menu` while aboard.**

**Heading.** `player.dir` is useless aboard a boat or an airship. The plane and ship operations write
`w_moveActorPtr.rot` (the Vector3 setter, `WMActor.cs:65-75`), which does not update `PosObj.rot`; only the `rot1`
setter does (`:89-99`). Heading must therefore be measured from motion (`veh_lib.hull_heading`).

**Teleport works aboard.** `WorldTeleportTo` moves `GetControlChar()` (`Ff9mkDebugMenu.cs:1830-1845`), keeps the
height, then re-grounds through `w_movementChrInitSlice` (`ff9.cs:4596-4620`):

- **Airship:** this is the flyer branch of `w_movementSetheight`. It raises the airship to the ground if it is
  below, then clamps it to 42.1875 (`:5513-5521`).
- **Boat:** never teleport it onto land. The sky cast would set its ground to the land surface.
- **Coasting:** the throttle and climb are smoothed (`XZAlpha` and `YAlpha` move 1/8 of the way per tick,
  `:6236`, `:6311`, `:6314`), so a vehicle coasts after release. `veh_lib.tp` and `settle3` wait for x, z and y
  to stop before teleporting or reading.

**Encounters.** The vehicle rows have `encount 0` (`TransportControls.csv` col 13), so no session rolls a random
battle aboard. Only session 2's foot calibration walks, and it does so on the area-14 landing lawn.

## 4. The sessions (registered predictions are in each scenario's docstring)

**Prep:**

```
py studies/terrain-malleability/ingame/veh_prep.py
py studies/terrain-malleability/ingame/veh_build.py
```

- `veh_prep.py` reads the live install only and writes `out/veh_prep.json`, plus simulation meshes in the
  scratchpad. It takes about 45 s.
- `veh_build.py` writes `out/veh_build.json` and `out/veh_deploy/nofly/`.
- The helpers in `veh_lib.py` were dry-run against the harness FakeGame. That exercised settle, teleport,
  hold_until, byte read-back and hull heading.

### veh_session1: Hilda Garde III, rank 5 and V13 (no deploy, one launch)

- **Setup:** ScenarioCounter 10650 → 9007; pokes `[190]=8`, `[191]=0`, `[74..82]` = LOW (1207.37, −964.61) at
  y 2.777, facing 192.
- **R0 / R1 (route and instrument).** The published position equals the poked record, `vehicle == 8`, and y
  equals the ground at LOW. Holding `down` climbs.
- **S1 (instrument).** Teleport from a low altitude onto HIGH (1034.37, −823.61): y = 28.866 ± 0.05, the floor
  raise.
- **S2 (rank 5).** Teleport onto SUMMIT (1225.53, −926.47), ground 42.639, topo 49: **y = 42.1875 ± 0.004**. The
  floor raise happens before the ceiling clamp (`ff9.cs:5514-5521`), so the airship ends 0.45 u inside the rock. A
  reading of 42.64 would refute that order.
- **S3.** Climbing on the summit cannot leave 42.1875.
- **S4 (control).** Over HIGH at the ceiling, y stays 42.1875; diving then stops at the 28.866 floor. This shows the
  clamp applies everywhere and only the summit case puts the airship below the ground.
- **S5.** Throttle across the summit. Scored offline by `veh_post.py`: no sample above 42.1875, and every sample
  over ground taller than 42.1875 reads exactly 42.1875.
- **V13 landing** (Cancel → `RunWorldCode(28)` → `w_movementGetGetoff`, `ff9.cs:5746-5917`, then WORLD07's
  topograph policy: lands only on topo 0..13). The simulator re-implements the 16-heading × 8-probe sweep over 72
  hull headings.
  - **L2, SEA (1161.9, −1036.71):** refused, because the own-tile foot check fails on topo 57.
  - **L3 (1284.37, −820.61), topo 42:** the engine accepts on every heading, but the `.eb` refuses. This separates
    the `.eb` policy from the engine law.
  - **L1 (1262.37, −930.61), topo 12:** it lands, and the player is put down **exactly 2.50 u** from the hover
    point. The first heading's 8th probe uses `num13 = 8` (`ff9.cs:5858-5866`), so its distance is radius × 8/8 =
    S(640) = 2.5 u. The simulation gives 72 of 72 headings → 2.5.

### veh_session2: chocobo, V3 and the chocobo's own limit mask (no deploy, one launch, three world loads)

- **F0 (instrument):** on foot at 9007, measure walk speed in u per game-second on the landing lawn. The lawn is
  clear for 40 u at bearing 270.
- **C0:** reload as the yellow chocobo (`[190]=[191]=1`, bits 809 and 810). The speed ratio chocobo/foot should be
  **1.79 ± 0.25** (speed_move 200/112, `ff9.cs:6165`). That shows the controlled actor is the chocobo.
- **C1 (V3 on a chocobo).** Forest (982.68, −1003.30), topo 37: y − ground = **−1.171875 ± 0.01**. Lawn: 0 ± 0.01.
  Chocobo indices 3-7 use slice_type 1, the same sink row as the party (`ff9.cs:5484-5509`).
- **C2 (mask, yellow).** Start on stock (7,17) Beach1 sand (480.37, −1120.61), topo 30, walking bearing 270, waterline
  3.5 u ahead. The chocobo is **blocked at the waterline**, progress in [2.4, 3.8]. Row 1 is exactly the walking
  mask: 53 is illegal. The slide simulator (`choco.edge.sim`) gives 3.28-3.42 for 2-6 tick bursts and a ±3° facing
  error, on shore topographs only.
  - **Why this start (review fix).** The first pick, (485.37, −1121.61), sat on a shoreline about 28° off square. A
    refused chocobo takes the first legal of 7 slide angles on each side (`ff9.cs:5552-5603`), so it crept east-south-east
    along the sand. It reached progress 7.2-7.5 before `world_approach` called it blocked, and never touched water. That
    would have failed C2 with the mask law intact, and it also passed C3's 5.0 bar, so C3 could not tell yellow from
    light blue. `veh_prep` now requires a straight shore square to the bearing: the waterline at lateral offsets −4 to
    +4 u must be within 0.3 u of the centre line's. It also requires the simulator to agree before it accepts an edge.
- **C3 (mask, light blue).** Reload with `[190]=[191]=2` and use the same start: it **passes**, progress ≥ 5.5
  (waterline + 2). 10.75 u of light-blue-legal topo-53 water lie beyond; the simulator reaches the 8 u goal in every
  case.
  - Row 2 adds 51, 53, 54, 55 and 61, and has `flg_gake 1`.
  - Shore topos 30-35 are neither ground nor water (status masks at `ff9.cs:9971-9975` and `:18`), so the
    ground→water refusal (`:5703-5717`) does not fire.
  - This start was chosen for exactly that reason. A light-blue chocobo starting on "ground" topo is refused at
    the water.

### veh_session3: rank 12, the no-fly topograph (deploy D1, one launch)

- **Setup:** Hilda Garde III on 9007; the record is poked to ring A's centre, so the airship **loads inside ring
  A**.
- **Lab cell:** Disc1 (1,13), an isolated open-ocean cell. It holds a slab at y 2.0 with two r 8..12 rings:
  - A = topo 15, flight-blocked and also blocked for every ground row and the boat (computed mask table);
  - B = topo 41, legal (the control).
- **N0:** the airship loads at A's centre with **y = 2.0**. Stock sea there reads 0, so this also proves the lab
  file loaded.
- **N1 / N3:** full throttle from A's centre, at y 2.0 and then at 42.1875, stalls at radius **6.3-8.4**. The
  simulation, from rest over 36 headings, gives 6.65-8.02 in 8-9 ticks. A flyer makes one round check per tick, a
  sky cast with IgnoreExceptions and no slide, and altitude is never consulted (`ff9.cs:5605-5633`).
- **N2:** pushing into the ring while also holding climb leaves y unchanged (± 0.01). The vertical step sits inside
  the same refused `if (flag3)` (`:5615-5629`).
- **K1 / K2 (controls):** from B's centre at both altitudes, radial progress is ≥ 16. The simulated minimum is
  28.2, on the heading aimed at ring A.

### veh_session4: rank 7 and H1, the boat under a sidecar-less reclaim (`$VEH_PHASE`, one launch per phase)

- **Setup:** ScenarioCounter 9500 → 9003; `[190]=7`; the record is the OPEN lane start (1324.37, −67.39), y 0,
  facing 192.
- **Mechanism.** The boat's round check casts down from hull y + 2.34375. The hull rides at water − 0.703, so the
  cast starts about 1.64 u above open sea (`ff9.cs:1328`, `:5489-5491`, `:7296-7322`). The cast takes the first
  registered mesh, and the first tri in buffer order whose hit is below the origin. The block's 10-slot cache is
  tested first (`WMBlock.cs:137-212`), and `WMPhysics.Raycast` never reads `distance` (`WMPhysics.cs:6-47`). The
  boat moves only onto topo 53, 54 or 57, and tries 7 slide angles on each side (`ff9.cs:5549-5603`). The +rotation
  side is tried first, and with `x += rsin(RotTrue+180+rot)` (`:5688-5689`) that is bearing − k·11.25, toward −z on a
  +x hull. The simulator originally tried the mirror side first; it was fixed in review. Results at heading 0 are
  unchanged.
  - A slab above the origin is never hit, so the cast falls through to Block[12][10]'s free-riding water.
- **B0 / B1:** the boat publishes the poked record at y −0.703. `up` drives the hull along bearing 0; if not,
  `hull_steer` fixes it and records that it did. The lanes are judged against this **measured** hull heading.
- **C0 (stock control, every phase):** from (113.63, −582.39), +x, it stalls after **16.4 ± 1.5 u**, stopped by
  stock topo-56 water. This is the same class that stops the RIM lane. Over the ±2° hull band the session accepts,
  the simulator gives 16.37-17.40 (`boat.stock_control.heading_scan`).

**Lanes** (start at x 1324.37, 19.63 u west of the cell; "into" = x_max − 1344; "unslid" = no sample 0.5 u or more
off the hull's own measured line, `veh_lib.first_deflection`):

| phase | OPEN (z −67.39) | RIM (z −89.39) |
|---|---|---|
| none (no deploy) | passes, into ≥ 30, unslid | passes, unslid |
| **flat6** (H1) | **passes under the y-6 slab**, unslid, in-cell y −0.703 ± 0.05 | **contact with Block[12][10]'s hidden topo-56 islet rim** at into 18.5-21.5, under the slab: either a stall there or a first slide there |
| flat1.2 (control) | stalls at into −1.0..+0.1: the slab is below the 1.64 ray origin | same |
| island (the kit default) | stalls at the border: the sand ramp meets the waterline | same |
| cliff (exploratory) | the simulation tunnels the 0.5 u-wide wall foot after a slide; depends on the step's phase; recorded, not judged | same |

**Why RIM is judged as "contact" (review fix).** The original claim was "stalls at into 19.75 ± 1.0". That only
holds at heading 0. The hidden rim is a wall about 4 u wide. Whether the boat stalls on it depends on step phase:
it stalls if the residual distance is under the 0.18 u reach of the 78.75° slide; otherwise it slides round the islet
and passes. Over the ±2° hull band the session accepts, re-driving the lane (`boat.heading_scan.rim.flat6`) gives:

- a stall at 0°, −1° and −2°;
- a slide round the islet and a pass at −0.5° and at +0.5° to +2°;
- first contact at into 19.59-20.49 at all nine headings.

The old claim would therefore have "refuted" H1 on a hull just 0.5° off. Contact is the robust signal. The stock
baseline (`none`) never slides on either lane, and neither does flat6 OPEN, at any heading in the band.

**Post-scoring:** `py studies/terrain-malleability/ingame/veh_post.py <run dir> [--phase-mesh <mesh>]`.

## 5. Deploys (the orchestrator performs these; scratch folder only)

`FF9CustomMap-lab` must be **first** in `Memoria.ini` `FolderNames` for the launch. Back up the ini first and
restore it byte-exact afterwards, exactly as in sessions 4-7. Only Disc1 files are written, because every session
runs at ScenarioCounter < 11090.

| id | session | contents |
|---|---|---|
| none | veh_session1, veh_session2 | nothing (the lab folder is not needed) |
| D1 | veh_session3 | copy `studies/terrain-malleability/ingame/out/veh_deploy/nofly/FF9_Data` to `<game>\FF9CustomMap-lab\FF9_Data`. The one file is `FF9_Data/WorldMap/Disc1/0_1/r13/Block[1][13] Terrain.ff9mesh`: 8192 tris, 24576 verts, unindexed, validated by `mesh.validate_blockmesh`. |
| D2 | veh_session4 `VEH_PHASE=flat6` | `cd ff9mapkit && py -m ff9mapkit world-reclaim --mod-folder FF9CustomMap-lab --cells 21,1 --profile flat --height 6 --skip-mirror` |
| D3 | `VEH_PHASE=flat1.2` | same, `--profile flat --height 1.2` |
| D4 | `VEH_PHASE=island` | same, `--profile island` (defaults: height 6, beach 22, shore topo 20) |
| D5 | `VEH_PHASE=cliff` (optional) | same, `--profile cliff` (defaults: 3.2, rim-run 1.0) |

**Notes on the deploys:**

- **No `Donor.txt`.** `world-reclaim` writes none (README defect 18). That is the condition H1 needs, so do not
  add one.
- **Between phases,** delete `FF9CustomMap-lab\FF9_Data\WorldMap\Disc1\0_1\r1\Block[21][1] Terrain.ff9mesh`
  together with the kit's ledger and `.bak` beside it, or pass `--allow-overwrite`. The overwrite gate refuses
  otherwise.
- **No relaunch between phases.** Overrides are read at world load. Adding the lab folder to `FolderNames` does need
  a relaunch, and each phase is its own launch anyway.
- **Isolation:** (1,13) and (21,1) each have 8 stock-sea neighbours and no live override on disc 1 or disc 4
  (`veh_prep.isolated_sea_cells`). Re-run `veh_prep.py` immediately before deploying: live folders change.
- **Teardown:** remove `FF9CustomMap-lab`, restore `Memoria.ini` byte-exact, and verify the sha256.

## 6. Run order

1. `veh_session1` (no deploy). It proves the airship route plus rank 5 and V13.
2. `veh_session2` (no deploy).
3. D1, then `veh_session3`.
4. D2, then `veh_session4` with `VEH_PHASE=flat6`.
5. D3, then `flat1.2`.
6. D4, then `island`.
7. Optional: `VEH_PHASE=none` with no deploy (baseline), and D5 `cliff`.

Use one change per launch. Each run is `py tools/play.py studies/terrain-malleability/ingame/veh_session<N>.py
--label veh-session<N>[-phase]`, then `veh_post.py` on the run dir.

## 7. Risks

- **The route on 9003 and 9007 is new in game.** Vehicle-at-load binding was owner-confirmed only through the `~`
  reload onto 9009. The R0/B0/N0 checks make a failure loud: the position would be the landing, not the record.
- **If a vehicle mode is set but its actor is never spawned** (the ScenarioCounter gate not met), no Init binds
  control. The patched engine's `w_worldSelfHealControl` (`ff9.cs:4630`, called at `:3797` when `GetControlChar()` is null) should recover on foot. The pre-door
  read-back of the ScenarioCounter guards against this.
- **Unknown arrival events.** Arrival at 9003 at ScenarioCounter 9500 with key 35 has never been played. 9007 at
  10650 was walked in sessions 2-3.
- **`Global.Int16[1062]` nonzero** would make 6603 call `WorldMap(that)` first. It is read back and recorded.
- **The cliff phase depends on step phase.** It is exploratory and not judged.
- **The boat cache is modelled.** In-game cache state after a slide could differ from the simulation; the stall
  windows allow one step.
- **Session 2's foot calibration walks on foot,** which has `encount 1`. It stays on the area-14 landing lawn.
- **Never press `menu` (Triangle) aboard a vehicle.** It warps to the bridge interior.
- **The sandbox autosave.** It ends in a vehicle state inside `x64/ff9harness/save`. That is harmless: every
  session starts with New Game, and Continue is not used.
- **Window-focus stray input** (memory: a stray left-click once mattered). Leave the window alone during runs.

## 8. Needs the owner's go

- Adding `FF9CustomMap-lab` to the shared `Memoria.ini` `FolderNames` for sessions 3 and 4. This is the same
  approval pattern as sessions 4-7, but it is per round.
- Route (iii), only if wanted: a DLL rebuild (about 25 lines) for a `worldreload` harness verb.

## 9. Adversarial review

The review re-opened the engine cites and the live world `.eb`, and re-ran the simulators. It found the following.

**Holds:**

- **The route.** Every vehicle Init is as quoted.
  - The airship Init only replaces its record with the default when `Int16[2] == 0`. 6603 writes 35, so the poked
    record is used.
  - World load reads `[190]` (`w_frameMapConstructor` → `w_movementChange`, `ff9.cs:3675-3678`, `:5941-5951`).
  - Cancel KEYON reaches the script through Memoria's buffered `ETb.KeyOn` (`FPSManager.Collect/FlushDelayedInputs`),
    so a 2-frame press is not lost between world ticks.
- **The SC-gated area events.** None of WORLD07's area events gated on ScenarioCounter 10640-10659 with `[190]==8`
  lies within 32 u of any session point or path. Every event tri near the session points is an on-foot nameplate,
  `!Byte[190]`-gated. The landing tag 36105 sets `Int16[1062] = 9007` and re-enters 6603 only on a Confirm press on
  foot, which no session makes there.

**Fixed:**

- the C2 edge, the RIM verdict, and the simulator's slide order (above);
- `reach_world_as` now refuses to walk out of 6603 when the pre-door read-back fails. It raises `HarnessError`, which
  `play.py` reports, instead of only recording a failed check. Without the read-back, a `[190]` whose actor the
  ScenarioCounter or `[191]` gate did not spawn would reach the dispatchers' `obj(uid=6)` / `obj(uid=5)` arms. That
  is the `~` menu's "forced mode crashes the event script" state, which strands the run.

**Still open (residual, not defects):**

- The chocobo slide simulator approximates the current tile with the window ray and ignores the 0.195 u water sink
  in the probe origin. Against the simulated 3.28-3.42, the registered C2 window [2.4, 3.8] leaves 0.88 u of
  margin below and 0.38 u above.
- The boat cache was checked by carrying one shared cache through C0, OPEN and RIM in session order, with the
  engine's newest-then-oldest slot order. No lane result changed.

## 10. Files

- `veh_prep.py`: offline route evidence, point picks, the getoff and boat simulators. Writes `out/veh_prep.json`.
- `veh_build.py`: the no-fly ring mesh (D1) and its flight simulation. Writes `out/veh_build.json`.
- `veh_lib.py`: the harness helpers: `reach_world_as`, `settle3`, `tp`, `hold_until`, `plateau_y`,
  `calibrate_climb`, `hull_heading`, `hull_steer`, `first_deflection` (shared by the simulator's heading scan and the
  session's lane judge).
- `veh_session1.py` … `veh_session4.py`: the scenarios.
- `veh_post.py`: offline scoring of a run's samples on the live mesh and the lab mesh.
