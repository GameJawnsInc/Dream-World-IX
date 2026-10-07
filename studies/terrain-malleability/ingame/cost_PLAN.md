# Experiment rank 10: the in-game cost budget of refined walkable terrain

Lane "cost" of the in-game round for the terrain malleability study (`../README.md` section 7.1, rank 10; capacity
findings CAP-10 and CAP-12). Nothing here was run in game. The orchestrator runs it, one launch at a time.

**The question.** Capacity CAP-10 says the overworld ground query is a linear scan, so uniform refinement multiplies
the per-probe cost (about k^3, then k^2). CAP-12 says no in-game frame budget exists. This experiment measures what
refining one walkable cell costs in frames and in world-entry time, at x1, x4, x16 and x64 triangles.

**The answer it can give.** For each arm, one of three verdicts:
- COST: frames are lost while walking on the cell;
- FREE: no loss above the measured noise floor, with a positive control that proves the instrument would have seen one;
- INCONCLUSIVE.

It also gives a numeric bound on the world-entry hitch. An optional second launch with VSync off measures milliseconds
per tick directly.

## 1. Files (all under `studies/terrain-malleability/ingame/`)

| file | job |
|---|---|
| `cost_build.py` | Writes the four arm meshes and the manifest to `$COST_SCRATCH/arms`, never the repo. Self-checks everything in section 2. |
| `cost_predict.py` | Offline model of the exact in-game workload over the exact arm meshes, using the engine's query and cache rules. Writes `out/cost_predict.json`. This is where the numbers in section 5 come from. |
| `cost_lib.py` | Shared code: the state poller, window metrics, circle fit, and the pure decision rule (section 6). |
| `cost_session.py` | The in-game scenario: `run(g)`. |
| `cost_post.py` | Re-scores a run directory offline from its own dumped samples. `--unlocked` gives ms per tick for launch U. |
| `cost_dryrun.py` | Part A: the decision rule on synthetic tables, including one deliberately broken rule. Part B: the whole scenario end to end against the harness FakeGame. |

## 2. Design

### 2.1 The cell and the arms (`cost_build.py`)

- **Cell: Disc1 (21,1).** An isolated IsSea cell: all 8 neighbours are sea, and no live mod folder has a file on it
  or on any neighbour (checked).
  - Its `Terrain.ff9mesh` arms the s34 sea divert onto `Block[12][10]` (`WMWorld.cs:532`,
    `WorldMeshOverride.HasLandOverride`, `WorldMeshOverride.cs:80-83`).
  - The bind oracle (254/254 disc-1 receipts) predicts the walk list `[Terrain (lab), Sea1, Sea3, Sea4, Sea5]`.
    There is no Object, so our Terrain is the **first** walk mesh every scan iterates (`WMBlock.cs:185-200`).
  - Session 7 proved this cell renders and walks up to 65,535 vertices (`RESULTS.md` section 8).
- **Base mesh:** a 13 x 13 quad grid over the whole 64 u cell, pitch 4.923 u (diagonal 6.96 u), 338 tris, emitted
  row-major. Stock Terrain has a median of 314 tris and a median 3D edge of 4.38 u (CAP-6, CAP-7).
- **Arms:** in-place midpoint subdivision, applied 0 to 3 times.

  | arm | tris | verts | file size |
  |---|---|---|---|
  | x1 | 338 | 1,014 | 52,748 B |
  | x4 | 1,352 | 4,056 | 210,932 B |
  | x16 | 5,408 | 16,224 | 843,668 B |
  | x64 | 21,632 | 64,896 | 3,374,612 B |

  - x64 is inside the s34 loader's 65,535-vertex bound (`WorldMeshOverride.cs:186`). It is written by the kit's own
    `ff9mesh_bytes`, which validates it; nothing is hand-packed. x64 is geometrically session 7's proven 104 x 104
    plane.
  - Children are emitted in place of their parent, so a point's scan-depth **fraction** is the same in every arm.
    This is the model of `capacity/walk_cost_sim.py`.
  - Midpoint subdivision of a planar triangle is exact: same surface, same texture mapping. Only the count differs.
- **Lawful attributes:**
  - IDALL: `encode_id(area=14, topograph=0)` = 3584 on every corner. Tangent is `[3584, 0, 0, 0]`, matching stock,
    where tangent y/z/w are 0.
  - Area 14 is zone 6, camera place 0 (the same as the surrounding area-0 sea), with no lock, no spawn weather and no
    beach arm.
  - (zone 6, topograph 0) has no record at fog 0 or fog 1 in the live `discmr` table. Under s60 a roll there finds a
    hole and no battle starts (gap_area_layer GA1, `ff9.cs:9237`/`:9264`). This is checked from the live table, not
    assumed.
  - UVs use the stock grass mains language (`world/grassland.py`): one full quadrant per base quad, with a
    checkerboard of quadrants. Every corner falls inside the main grass rect (checked), and children interpolate.
- **Arm tag:** the plane height is 6.000, 6.125, 6.250 and 6.375 for x1, x4, x16 and x64. The published `world_y` on
  the plane names the arm the engine actually loaded, on every load. Session 1b read `world_y` to within 0.0035.
- **Self-checks:**
  - the engine's sky query (`arealib.raster`, calibrated against `placement.place`) reads the tag at all 4,096
    off-lattice samples, with 0 misses;
  - plan area is exactly 4,096 u^2;
  - every triangle faces up;
  - IDALL is none of the 10 special full values.

### 2.2 The walk: a circle, not a line

- **Inputs:** hold "up" and L1 together.
  - L1 turns the camera `PsxRot(32)` = 2.8125 degrees per world tick (`ff9.cs:6137-6141`).
  - "up" walks along the camera rotation plus the stick direction (`ff9.cs:6166`).
  - The walk step is 0.4375 u per tick.
- **Shape:** a circle of radius **8.913 u**, one lap per 128 ticks, centred on the cell centre
  C = (1376.37, −96.61), which lies off the x64 lattice.
- **Why a circle:**
  - It is one continuous hold, with no teleports during measurement.
  - It is self-contained.
  - It keeps every ground probe on the refined cell.
- **The camera's probes:**
  - The eye trails the walker by the camera distance (`ff9.cs:2688-2689`). That is 19.53 u for posstat 0, and up to
    27.34 u.
  - The camera's 4 fuzzy sky probes (`ff9.cs:2946-2962`, on foot `ff9.cs:5979`) ride a circle of radius
    sqrt(r^2 + D^2) ± 5.5 u.
  - `cost_predict.py` confirms the walker and **100%** of camera probes stay inside the cell for D from 19.5 u to
    27.3 u.
- **Placing the circle:**
  - On each load, `world_probe("up")` at C measures the heading h. The walker is then teleported to
    S = C − r·u(h + s·90°), so the circle is centred on C.
  - The turn sign s and the measured radius come from one calibration circle in the warm-up load W0.
  - The debug teleport re-grounds the walker with a sky cast (`Ff9mkDebugMenu.cs:1836-1852`,
    `w_movementChrInitSlice`), so arriving from the 3.2 u landing onto the 6.x u plane is safe.

### 2.3 What the engine does per world tick (the cost being measured)

- `WMScriptDirector.Update` runs `FPSManager.MainLoopUpdateCount` ticks a frame (`WMScriptDirector.cs:299-304`;
  `FPSManager.cs:77-111`), at `WorldTPS` = 28 (`Memoria.ini:55`, `WMScriptDirector.cs:39`).
- Each tick runs movement and the camera (`ff9.cs:3809-3813`):
  - the walker makes 2 cached probes (`ff9.cs:5547-5603`, `:5682-5698`);
  - the camera makes 4 cached, unfiltered sky probes (`ff9.cs:2935-2988`);
  - every visible non-player actor re-grounds with a **null** cache (`ff9.cs:5170-5203`).
- **A probe** (`WMBlock.cs:137-183`):
  - It tests the 10-slot ring newest-first, one triangle test per slot.
  - On a miss it does a full scan in buffer order (`WMBlock.cs:185-200`).
  - Every iterated triangle costs 3x `Transform.TransformPoint` plus a ray/triangle intersect
    (`WMPhysics.cs:13-46`). Our triangles all face up, so the cheap filters never skip one.
- **The unit of cost is one triangle test.** The seconds per test (c) are unknown. They are bracketed from 0.1 to
  1.0 µs, with 0.25 µs as the central guess: three Mono icalls plus about 25 non-inlined `Vector3` operations.

### 2.4 One launch, A/B alternation

Every reload is a field round trip:
1. `world_warp(6603)`;
2. `swap()` the lab file while standing on the field;
3. `calibrate_axes(hazards=[DOOR])`, which is cached;
4. `walk_to(EXIT_AT, strict=False, halt_on_transition=True)`;
5. `wait_world`.

This is the idiom sessions 4b and 6 proved.

The file is read only inside the world's LoadBlocks frame (`ff9.cs:3703`, then `WMWorld.cs:823`, then
`WorldMeshOverride.TryLoad`, `WorldMeshOverride.cs:31-55`). `TryLoad` checks `File.Exists` and re-reads the file on
every call; it keeps no cache. Session 5 logged the Terrain2 load line on every world load.

**Schedule "full" (default, 18 loads, about 21 minutes):**
`1w, 1, 64, 1, 16, 1, 4, 1, 64, 1, 16, 1, 4, 1, 64, 1, 16, 1`
- Every test arm is bracketed by x1 references.
- W0 is the launch's cold first world entry. It calibrates the circle and is never scored.
- **Short schedule** (14 loads, about 16 minutes): `1w, 1, 64, 1, 16, 1, 64, 1, 16, 1, 4, 1, 4, 1`.

**Per load, all on the plane:**

| window | timescale | what happens |
|---|---|---|
| probe, teleport to S, settle 3 s | 1 | camera eases after the teleport (RESULTS: more than 90 frames from the high view) |
| `idle_pre`, 4 s standing | 1 | within-load control |
| `walk`, the circle, 600 ticks after a 1.5 s lead-in | 1 | the measurement, about 21.4 s |
| `idle_post`, 3 s | 1 | within-load control |
| re-probe, teleport, `timescale 4` | 4 | |
| `idle4`, 2 s | 4 | within-load control at timescale 4 |
| `walk4`, 600 ticks | 4 | the positive control (about 5.4 s at 112 ticks/s) |
| `timescale 1` | 1 | |

- **Why idle is the control:** idle probes are cache hits, 6 tests per tick in every arm (`cost_predict`
  idle_per_tick). Idle therefore pays the regime, the render of the extra triangles, and everything else except the
  scan.
- **`timescale 4`** is the harness verb (`HarnessAgent.cs:864-877`). `Time.timeScale` scales `deltaTime`, so it
  multiplies the ticks per frame (`FPSManager.cs:94`).
- **`stateevery 1`** is set while on the world, for per-frame resolution. It is reset to 2 before every field trip.

## 3. Instruments and their calibration

| instrument | what it reads | calibration / control |
|---|---|---|
| poller (`cost_lib.Poller`) | `state.json` read directly every ~6 ms on its own thread; per frame, the earliest mtime (the method `tickrate.TickClock` uses). It does not feed `Channel.observer`, because TickClock is not thread-safe and the field verbs plan by it. | Frame is `Time.frameCount` (`HarnessAgent.cs:1509`). Archived rings show 2-frame mtime pairs are noisy (p10 30 / p90 72 fps around about 55), so fps is the **span** rate of a window: frames over seconds between its first and last publish. |
| arm binding | median walked `world_y` against the tag | x1 loads must read 6.000. A mismatch excludes the load and fails P1. |
| log receipt | one `[WorldMeshOverride] loaded '...Block[21][1] Terrain' from FF9CustomMap-lab/...` line per world load | Memoria.log has 1-second timestamps, so it is a receipt, not a clock. |
| circle fit | Kasa least-squares fit of walk positions | P2: r = 8.91 ± 0.6, centre within 1.5 u of C. Identical across arms, because the geometry is identical. |
| tick rate | walked path / 0.4375 / seconds (exact on a flat plane) | P3: 28 ± 1.5 at timescale 1 in every arm (x1 is the control). |
| world-entry hitch | the longest gap between the first WorldMap-scene publish and the first WorldHUD publish: the synchronous LoadBlocks frame, where every override is parsed (`ff9.cs:3703`; `ReadMesh` reads each vertex through BinaryReader, `WorldMeshOverride.cs:172-235`) | Archived: 1,218 to 1,488 ms; two same-launch loads differed by 74 ms. Noise floor from consecutive x1 loads. |
| regime | idle fps: "60" if ≥ 45, "31" if 24 to 40 | A within-load switch (`idle_pre` vs `idle_post`, or the walk's two halves, differing by more than 15%) invalidates the load. |
| positive control | x64 at timescale 4 | It must read COST. Otherwise every FREE becomes FREE-UNPROVEN. |

## 4. The confounds and how each is defeated

- **The ~31 / ~60 fps regime, which flips mid-launch for an unproven reason.** Memory notes it is not CPU load. It is
  handled in layers:
  1. alternation: each test load is bracketed by x1 loads;
  2. the within-load idle control: Q = walk fps − idle fps;
  3. regime matching: all three loads of a bracket must share the idle regime;
  4. switch detection within a load.

  Dry run A5 shows layer 2 alone cancels a whole-load flip: the residual was −0.5 to +1.1 fps with the regime guard
  removed. Layer 3 also drops the occurrence. A deliberately broken rule (walk fps alone, no control, no brackets)
  calls COST on the same table.
- **Encounters.** A level-1 party loses any battle. The plane's (zone 6, topograph 0) is a hole at both fogs. Teleports
  go straight from the landing to the cell. The walk never leaves the plane: a drift beyond 22 u from C stops the hold.
- **The lattice-edge teleport trap.** C is off-lattice, and S is a computed generic point.
- **Camera easing after a teleport.** A 3 s settle, plus a 1.5 s lead-in that is discarded.
- **The state ring is only 5 s at 60 fps with stateevery 1.** The measurement does not use the ring; the poller keeps
  every frame, and `cost_samples.jsonl` is dumped to the run directory.
- **Parse-time noise:** disk cache and GC. Measured, not assumed: the x1-versus-x1 floor.

## 5. Registered predictions (before any run)

From `cost_predict.py`, using the circle walk and camera distance D = 23.44 u (D from 19.5 to 27.3 u in brackets):

| arm | tris | tests per tick (walker + camera) | vs x1 | camera share | idle | parked actor, per tick | straight walk, per tick |
|---|---|---|---|---|---|---|---|
| x1 | 338 | 389 (311 to 534) | 1.0 | 90% | 6 | 170 | 176 |
| x4 | 1,352 | 2,435 (2,231 to 3,038) | 6.3 | 89% | 6 | 678 | 1,177 (6.7x) |
| x16 | 5,408 | 12,808 (12,399 to 14,169) | 32.9 | 87% | 6 | 2,709 | 7,954 (45x) |
| x64 | 21,632 | 55,552 (55,302 to 60,468) | 142.7 | 81% | 6 | 10,833 | 40,083 (228x) |

The other turn sense agrees within 3% at every arm. The straight-walk column is the translation to ordinary play: its ratios (6.7x, 45x, 228x) independently reproduce capacity CAP-10's walker-only simulation (7x, 45x, about 240x), now with the camera included.

Milliseconds per tick are tests x c. Every frame that runs a tick carries the cost:

| arm | c = 0.1 µs | c = 0.25 µs | c = 0.5 µs | c = 1.0 µs |
|---|---|---|---|---|
| x1 | 0.04 | 0.10 | 0.19 | 0.39 |
| x4 | 0.24 | 0.61 | 1.22 | 2.44 |
| x16 | 1.28 | 3.20 | 6.40 | 12.81 |
| x64 | 5.56 | 13.89 | 27.78 | 55.55 |

**New, against the README's rank-10 line ("dominated by parked-actor full scans"):** on foot, the camera's 4 fuzzy sky
probes are the dominant consumer, at 81% to 90% of all tests. Their rings miss on 99% to 100% of probes from x16 up.
That is because on the circle they move about 1.05 u per tick, against the walker's 0.4375 u. A parked actor costs one
null-cache scan per tick: 2,709 tests at x16, which is less than the camera's 11,093.

**Registered checks** (they are also the scenario's `g.check`s):

| id | prediction |
|---|---|
| P1 | Every load's walked y equals its arm tag within 0.03, with one lab log line per world load. |
| P2 | The circle fit has radius 8.91 ± 0.6 u and its centre within 1.5 u of C; WorldHUD throughout. |
| P3 | Every walk at timescale 1 runs 28 ± 1.5 ticks per second, **in every arm**. x64 at 0.25 µs is 0.39 s of CPU per second: frames pay for it, the world clock does not. |
| P4 | Idle render: no arm lowers idle fps beyond the floor. The GPU cost of 21k triangles is about 0. |
| P5 | x4 is FREE: 0.6 ms per tick frame. |
| P6 | x16 in the 60 fps regime: COST, D in [−10, −2] fps (3.2 ms per tick frame on frames that already miss vsync about 5% to 15% of the time). A FREE verdict bounds c below about 0.12 µs. In the 31 fps regime: FREE. |
| P7 | x64 is COST in either regime. In the 60 regime, D is in [−30, −8] and the walk runs at about 30 to 45 fps (14 ms per tick frame pushes every tick frame past 16.7 ms). In the 31 regime, D is in [−12, −3]. |
| P8 | Positive control: x64 at timescale 4 cannot hold its clock, reading below 15 fps and below 80 ticks per second (x1 at timescale 4 reads about 112). That is 1.56 s of scan per wall second at 0.25 µs, and still 0.62 s at 0.1 µs. x16 at timescale 4 is COST (0.36 s per second at 0.25 µs). |
| P9 | The x64 world-entry hitch grows by +20 to +120 ms, with the mean of its occurrences at most 120 ms. That is about 65k vertices through BinaryReader, at roughly 0.5 to 1 µs per vertex, against a 1.2 to 1.5 s frame. The verdict is probably BELOW-FLOOR. x16 and x4 are never LOAD-COST. |
| P10 | The tick rate never drops at timescale 1, so there is no "slowdown" flag in any arm. |

## 6. The decision rule (`cost_lib.decide`, `decide_load`, `score`)

- **Per load:** Q = walk fps − pooled idle fps, at the same timescale.
- **Per test load:** D = Q(test) − mean(Q(previous x1), Q(next x1)).
- **Validity:** D counts only if both references exist, all three loads bound their arm, all three share the idle
  regime, and none switched regime inside the load.
- **Noise floor:**
  - σ is the SD of one Q, from consecutive valid x1 pairs of the same regime.
  - T = max(1.5 fps, 3 × 1.22 × σ). The 1.22 is √1.5: one test minus the mean of two references.
  - At timescale 4, the minimum is 3.0 fps.
- **Per arm (at least 2 valid occurrences):**
  - COST if every D < −T.
  - FREE if every |D| < T and the positive control fired. Otherwise FREE-UNPROVEN.
  - Otherwise INCONCLUSIVE.
- **Secondary metric:** the long-frame fraction (frames longer than 1.5x the load's idle median), with the same rule
  and a threshold of 0.03.
- **Idle level (the render question):** the same rule on pooled idle fps. Here the regime is the measured value, so a
  test whose regime differs from both agreeing references is a REGIME SHIFT, not a confound. An arm that shifts every
  occurrence is COST.
- **Load:** D_E = blocks_ms(test) − mean of its references.
  - T_E = max(40 ms, 3 × 1.22 × σ_E).
  - LOAD-COST if every D_E > T_E.
  - BELOW-FLOOR if every |D_E| < T_E.
  - Otherwise INCONCLUSIVE.
- **How a verdict becomes a budget:**
  - A FREE at x16 and a COST at x64 brackets the per-tick scan budget between 12.8k and 55.6k tests at this cell's
    camera geometry.
  - A COST at x16 puts it below 12.8k.
  - Launch U turns these into milliseconds.

## 7. Deploy steps (the orchestrator; owner-approved lab protocol of sessions 4 to 7)

1. Run `py studies/terrain-malleability/ingame/cost_build.py` with `$COST_SCRATCH` set to the orchestrator's
   scratchpad. It must print 4 arms, 0 raster misses, encounter hole {0: True, 1: True}, walk
   `[('Terrain','override'), ...]`, and "live files on (21,1): none".
2. `py studies/terrain-malleability/ingame/cost_predict.py`, then
   `py studies/terrain-malleability/ingame/cost_dryrun.py`. Both parts must pass.
3. Back up `Memoria.ini` to `backups/Memoria.ini.pre-cost-lab.<stamp>` and record its sha256.
4. Create `<game>\FF9CustomMap-lab\FF9_Data\WorldMap\Disc1\0_1\r1\`.
5. Copy `$COST_SCRATCH\arms\cost_x1.ff9mesh` to
   `<game>\FF9CustomMap-lab\FF9_Data\WorldMap\Disc1\0_1\r1\Block[21][1] Terrain.ff9mesh`.
6. Prepend the lab folder to FolderNames:
   `FolderNames = "FF9CustomMap-lab", "FF9CustomMap", "FF9CustomMap-world", "MoguriMain", "MoguriVideo", "FF9CustomMap-schema", "FF9CustomMap-msgs"`.
   A new folder in FolderNames needs a launch, and every run here is a fresh launch.
7. **The scenario itself swaps that one file between world loads.** It does so only while standing on field 6603,
   with an atomic `os.replace` and a sha256 read-back. It refuses to start unless the lab folder exists and is first in
   FolderNames. It never writes anything else.
8. **Teardown:** delete `FF9CustomMap-lab`, restore `Memoria.ini` byte-exact from the backup, and verify the sha256.

## 8. Run commands

```
$env:COST_SCRATCH = "<orchestrator scratchpad>\cost"
py studies/terrain-malleability/ingame/cost_build.py
py studies/terrain-malleability/ingame/cost_predict.py
py studies/terrain-malleability/ingame/cost_dryrun.py
py tools/play.py studies/terrain-malleability/ingame/cost_session.py --label cost-session
py studies/terrain-malleability/ingame/cost_post.py .harness-runs/<stamp>-cost-session
```

**Options** (environment variables):
- `COST_SCHEDULE=short`, or an explicit list such as `1,1,64,1,...`.
- `COST_TICKS` (default 600), `COST_AMP` (4; 0 disables the positive control), `COST_AMP_TICKS` (600),
  `COST_IDLE_S` (4).

**Optional launch U (needs the owner's go):** VSync is the confound's likely amplifier. Memoria quantises frames to
the refresh rate (`FPSManager.cs:43-47`; `Memoria.ini:71` VSync = 1, `:54` WorldFPS = −1). With `[Graphics] VSync = 0`
set in the shared `Memoria.ini` (backed up first, restored byte-exact after), WorldFPS −1 is uncapped, so every frame's
time is work.
- Run: `py tools/play.py ... cost_session.py --label cost-session-unlocked`, then `cost_post.py <run> --unlocked`.
- It prints ms per tick per arm, `(1 − f_walk / f_idle) / ticks_per_second`, and c in µs per triangle test, taken
  from x64 − x1 against the predicted tests.
- That is the number a "dense terrain" feature needs.

## 9. The parked-actor angle: not run

- A non-player world actor re-grounds every tick with cache = null (`ff9.cs:5191-5199`). Over our cell that is one
  full scan per tick per actor: 170, 678, 2,709 and 10,833 tests for x1 to x64 (`cost_predict`
  parked_actor_tests_per_tick).
- No proven harness verb can make one present on the cell:
  - there is no vehicle summon (RESULTS "Not run");
  - the chocobo needs the story and a minigame;
  - the state document does not publish world actors, so presence could not even be verified.
- Placing one by editing a world `.eb` dispatcher is out of scope.
- The README's "dominated by parked-actor full scans" is superseded by the camera finding in section 5. Three parked
  actors at x16 would add 8.1k tests to the camera's 11.1k.

## 10. Dry run (offline, against the FakeGame; it proves the driver, not the engine)

- **Part A** (`cost_dryrun.py --part a`): **12/12.** Covered: null, effect, missing positive control, a regime flip
  (the bracketing occurrences are flagged and the arm is still decided), the BROKEN rule fooled while the real rule is
  not, render-only shift, and load hitch at σ 8 and σ 90.
- **Part B** (`cost_dryrun.py --part b`, about 320 s real time): **17/17, twice.** The second run was on the final code. `cost_session.run` ran end to end against
  `FakeGame(publish=("mtime",))`.
  - The scenario's own swap wrote a throwaway lab folder 14 times.
  - A stand-in world entry injected the scene-switch frame, the LoadBlocks frame (+60 ms for x64) and the HUD.
  - The fake walked the circle at the world tick rate, with an injected per-tick walk cost (x16 3 ms, x64 12 ms, x4
    none).
  - Results:
    - calibration lap radius 8.913, sign +1;
    - every load bound its tag;
    - one log line per load;
    - circle centres within 0.3 u of C;
    - 28.0 ticks/s in every arm;
    - x64 COST (D −15.1), x16 COST (D −4.65), x4 FREE;
    - positive control fired (x64 at timescale 4: 25.6 fps);
    - x64 LOAD-COST (+69 and +71 ms; the A-A σ was 4.4 ms);
    - idle render FREE.
  - `cost_post.py` reproduces every verdict from the dumped samples alone.
  - **Limit:** the fake has no VSync, so its frames stretch evenly and the secondary long-frame metric never fires
    there (frames of 1.34x the idle median). That metric is exercised only in game.
  - The dry run proves the DRIVER and the rule, nothing about the engine.

## 11. Risks

- **Run length:** 18 loads, about 21 minutes. Every round trip walks out of 6603; a `walk_to` that misses the door
  stops the schedule. Partial data is scored, and a "schedule completed" check fails honestly.
- **The 31 regime for the whole launch:** P6 flips to FREE by registration; the x64 effect is smaller.
- **Prediction miss on circle geometry:** if L1 plus up does not trace a clean circle (camera auto-follow fighting the
  bumper), P2 fails.
  - The calibration lap uses the measured radius.
  - The drift stop protects the walk.
  - The camera probes might then partly leave the cell, which lowers sensitivity equally in every arm.
- **The x64 positive control at timescale 4** may run frames of about 130 ms (up to about 9 ticks a frame, capped by
  `maximumDeltaTime`). Publishes thin out to about 4 a second, but the span rate stays exact. `timescale 1` is restored
  in a `finally`.
- **The circle overstates camera cost** compared with a straight walk (section 5, last column). The verdicts are for
  the circle; the straight-walk column translates them to ordinary play.
- **In-run swaps are a new protocol element** (sessions 4 to 7 deployed one change per launch). Each load's arm is
  identified numerically, so a broken load can always be attributed.
