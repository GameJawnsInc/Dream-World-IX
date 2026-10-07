# Terrain malleability: the vertical envelope (lane: vertical)

Question: how high and how low can overworld terrain go, and which engine systems set the limits?
This lane is read-only. Every number below comes from a script in this directory that was actually run.
Every engine line is cited live-clone line / stock-HEAD line. `engine_bounds.py` checks all 64 cited
anchors against `git show HEAD:` of `C:\gd\FFIX\Memoria` (stock 6b8bb2d5). **64 of 64 are stock Memoria.
None comes from our memoria-patches stack.** So the vertical envelope below is the same on stock and on the
DWIX engine.

## Scripts (rerun from the repo root)

| script | what it does | rerun |
|---|---|---|
| `engine_bounds.py` | Reads each constant out of the C# source and tags it stock or patch. Derives units: posstat table, sink table, limit masks turned into topo sets, per-mode step length and steepest slope. Writes `out/engine_bounds.json` | `py studies/terrain-malleability/vertical/engine_bounds.py` |
| `y_census.py` | Per-part and per-disc Y statistics (vertex and area-weighted), tallest blocks, land below 0, per-topo heights, area above thresholds, topo presence. Includes a calibration gate. The per-tri cache stays in the scratchpad, never the repo. Writes `out/y_census.json` | `py studies/terrain-malleability/vertical/y_census.py` (`--rebuild` re-extracts) |
| `sea_layer_probe.py` | Sea vertices off y=0 on every sea part, with terrain checked nearby. Writes `out/sea_layer_probe.json` | `py studies/terrain-malleability/vertical/sea_layer_probe.py` |
| `below_zero_probe.py` | The engine ground query, using the kit simulator in registration order, over every block whose terrain dips below 0. Records water sheets above, foot legality and depth. Writes `out/below_zero_probe.json` | `py studies/terrain-malleability/vertical/below_zero_probe.py` |
| `canopy_sink_probe.py` | Stock forest and hillside walk steps, run with and without the class-0 sink. Writes `out/canopy_sink_probe.json` | `py studies/terrain-malleability/vertical/canopy_sink_probe.py` |
| `camera_clip_census.py` | Rasterizes disc 1 at 1u under both query semantics (ANY and WALK), then evaluates the chase-camera eye at 83,278 standable points × 16 yaws. Also reports how much of the flight floor sits above each threshold. Writes `out/camera_clip_census.json` | `py studies/terrain-malleability/vertical/camera_clip_census.py` |
| `render_bounds_probe.py` | Checks world shaders for curvature and compares the text shaders with the bundle's own shaders. Reads the WorldCamera clip planes from the level files. Raw shader text goes to the scratchpad only. Writes `out/render_bounds_probe.json` | `py studies/terrain-malleability/vertical/render_bounds_probe.py` |

## Calibration (instrument agreement before any verdict)

* `y_census.py` reproduces the recorded census statistics using the same statistic
  (`overworld-topography/census.py:118-121`, unweighted p2/p98 of tri-centroid y):
  * topo-49 p98 is **37.1** (recorded ~37)
  * topo-5 p2 is **-3.6** (recorded -3.6)
  * topo-10 median is 26.87 and topo-13 median is 16.83 (recorded ~27 and ~17)
  * the sea4 donor rect (6,6)+2×2 has **3075/3075 verts at y=0** (recorded 3075)
  * Result: PASS 5/5. The extremes below are a different, stricter measure (vertices), not a disagreement.
* `camera_clip_census.py`: the WALK raster agrees with `placement.place` at **1143/1143** random points.
* `below_zero_probe.py`: open-ocean block (12,0) puts every sample on a Sea sheet at y=0 (True, 0 misses).
* `render_bounds_probe.py`: the bundle Shader objects for WorldMap/Terrain, Sea, Beach, River, ScrollTexture,
  TerrainQuicksand and VolcanoCrater1/2 match the `StreamingAssets/Shaders/WorldMap/*.txt` text byte-for-byte
  (whitespace-normalized SHA-1). The text files are what the blocks render with.

## (1) The stock envelope, measured (`y_census.py`, disc 1; disc 4 identical unless noted)

| part | vertex y min | vertex y max | area-weighted centroid p50 / p99 |
|---|---|---|---|
| terrain | **-5.824** | **42.680** | 5.77 / 36.71 |
| object | -3.352 | **43.062** (disc 4: 40.605) | 23.81 / 39.93 |
| river / falls / riverjoint | 0.0-2.96 | 27.82 / 26.07 / 26.07 | |
| volcanocrater / lava | 8.84 | 17.51 / 9.36 | |
| stream | -0.215 | 2.738 | |
| beach1 / beach2 | 0 | 1.562 / 0.781 | |
| sea1 / sea2 / sea3 | 0 | **0.535 / 0.801 / 0.500** | |
| sea4 | 0 (disc 4: -0.055) | 0.023 (disc 4: 0.047) | |
| sea5 / sea6 / sea4f | 0 | 0 | |

* **Tallest terrain.** Three topo-49 summits reach 42.56-42.68, at blocks (19,14), (20,15) and (18,13), world
  (1225.5, −926.5), (1285.1, −980.0) and (1159.6, −892.4). 24 blocks have a block max of 40u or more.
* **Highest foot-legal surface: 34.07.** It is topo 36 (high forest), block (17,13), world (1144, −856).
  Plateau grass topo 10 spans 25.64-28.81 (p50 26.88).
* **Tallest object: 43.06**, disc-1 block (20,10), topo 59. It is gone on disc 4.
* **Land below 0: 246 tris** on disc 1 (259 on disc 4), in blocks (2,7), (3,7), (7-8,13-14) and (17,14).
  Detail in (2g).
* **Terrain above each engine threshold** (disc 1, ANY-semantics raster, `camera_clip_census.py`):

  | threshold | area above (u²) |
  |---|---|
  | 29 (mist) | 42,921 |
  | 33.2 | 18,528 |
  | 37.1 | 4,706 |
  | 42.1875 (flight ceiling) | **3 u², at 3 summit points** |

* **Flight-blocked topos.** None of the 14 flight-blocked topo ids appears in ANY part on either disc.

## (2) Engine bounds (all stock Memoria; live line / stock line)

### a. The ground ray

* **Ray origins.** The ray starts at actor y + 2.34375 when walking, or actor y + 400 for a sky cast
  (spawn/teleport `w_movementChrInitSlice` ff9.cs:4596 / 4560, flyers, NPCs, camera).
  Constants: `ff9.cs:1327-1330` / 1327-1330. Origin: `ff9.cs:7302` / 7147.
* **No reach limit.** `WMBlock.Raycast(.., Single distance, ..)` never reads `distance`. The script counts
  0 uses in the body (`WMBlock.cs:137`).
* **Nothing above the origin is ever hit.** `intersect3D_RayTriangle` rejects t < 0 (`WMPhysics.cs:96` / 96).
* **Terrain above +400.** Any surface more than 400u above the actor's current y is invisible to every sky
  cast. The ~ teleport keeps the current Y, so from sea level that cut is at y=400. Practically irrelevant:
  the camera (71.8) and the flight ceiling (42.19) bind ten times lower.
* **A miss sets ground to 0** (`ff9.cs:7306` / 7151).

### b. THE CANOPY SINK: the step ceiling depends on the class you stand on

This law is new to the recorded decode.

* **The ray starts from the actor's current y.** The walk probe uses `Vector3 pos = w_moveActorPtr.pos`
  (`ff9.cs:5554` / 5399).
* **Current y includes the sink.** Current y = ground + slice (`ff9.cs:5509` / 5354).
* **The sink on forest/hillside.** `w_movementSinkArray[slice_type 1, class 0]` = 400, which gives
  S(−300) = **−1.171875u** for topo 36/37/38 (`ff9.cs:19` / 19, class switch `ff9.cs:5636` / 5481). slice_type 1 covers
  status indices 1/2 (the party on foot) and 3-7 (chocobos) (status table `ff9.cs:1769` / 1769).
* **The sink applies at once.** Class 0 is the only class flagged immediate (`imd = (num2 <= 0)`,
  `ff9.cs:5666` / 5511), so the actor drops 1.17u the frame it lands.
* **Effective climb ceiling by standing class:**

  | standing on | ceiling |
  |---|---|
  | lawn, dirt, rock (class 8) | 2.34375 |
  | 36/37/38 | **1.171875** |
  | 53 | 2.148 |
  | 54 | 1.758 |
  | 55 | 1.953 |
  | 56/57 | 0.977 |
  | 51/48 | 1.5625 |

* **Step length** at full stick is speed_move/256 per tick (`ff9.cs:6165` / 6010, `moveSpeed=4096` `ff9.cs:6134` / 5979):
  0.4375 on foot, 0.78125 on a chocobo.
* **Steepest slope climbable head-on:**

  | mode | lawn | 36/37/38 |
  |---|---|---|
  | foot | 79.43° | **69.53°** |
  | chocobo | 71.57° | **56.31°** |

  The ±78.75° fan can still creep sideways up steeper ground.
* **Stock never exercises the difference** (`canopy_sink_probe.py`, 80 blocks):
  * 12,908 forest points and 206,528 steps
  * max forest→forest climb per step is 0.553 (p99.9 0.393)
  * steps that land without the sink but not with it: 0; trapped points: 0 under both readings
  * Control: 12,015 lawn points, max climb 0.333.
  * So stock is consistent with the sink, but cannot tell the two readings apart.

### c. Flight

* **Ceiling.** `kmovementMaximumHeight = 42.1875` (`ff9.cs:9487` / 9321) is enforced as
  `if w_moveActorPtr.pos[1] > 42.1875 → 42.1875` (`ff9.cs:5518` / 5363). This only applies to the CONTROLLED
  actor, and is skipped under `w_cameraFixMode` / `w_cameraFixModeY`.
* **Floor.** The floor is `ground + slice`, raised first (`ff9.cs:5513` / 5358). The flyer ground comes from
  a sky cast with IgnoreExceptions: no up-facing filter, 4078 tris count, first-in-buffer
  (`ff9.cs:5607-5627` / 5452-5472).
* **Order.** The raise happens first and the clamp last. Over terrain taller than 42.1875 the airship ends up
  INSIDE the rock at 42.1875. No collision exists except the topo limit mask and a MISS. Mask decode:
  `studies/path-d-new-world/walk-decode-claims.md:579` (settled). The flight-blocked set is
  {8, 9, 14, 15, 24, 25, 26, 29, 39, 40, 43, 44, 47, 63}.
* **Stock flight floor above the ceiling** is only 3 u², at the summits (1159.5,−892.5) 42.19,
  (1225.5,−926.5) 42.67 and (1285.5,−979.5) 42.52. **The stock world's tallest peaks were built to the
  airship ceiling, within 0.49u.**
* **Landing (Hilda Garde / Invincible).**
  * ring radius = radius/256: Hilda 2.5u, Invincible 2.8125u
  * every ring probe must be foot-legal and within S(350) = **1.367u** of the ship's ground
    (`ff9.cs:5887` / 5732)
  * topo 45/46/52 refused (`ff9.cs:5803` / 5648)
* **Boat.** The Blue Narciss lands only on topo 53 (`ff9.cs:5769` / 5614). When parked (not controlled) its ground
  is pinned to 0 (`ff9.cs:5205` / 5050).

### d. The camera (chase eye, `w_cameraSetEyeAim`)

* **Eye height** = max(actor_y + eye_h, cameraCorrect + min(H, **37.1**, or **33.2** for type-1 flyers))
  (`ff9.cs:2989` / 2981, raise `ff9.cs:3001` / 2993).
  * H is the max of 4 sky casts at ±5.5u (`ff9.cs:2948` / 2940) when fuzzy, i.e. on foot. The eye's own plan
    position is never sampled.
  * Flyers take one centre cast (`w_cameraFuzzy = !flg_fly`, `ff9.cs:5979` / 5824).
  * All casts use IgnoreExceptions (`ff9.cs:2945` / 2937).
* **Flyer eye floor.** Type-1 flyers have an eye of at least **17.578** (`ff9.cs:2778` / 2778, `3003` / 2995).
* **Absolute eye ceiling: 71.80859375** (`ff9.cs:3112` / 3104).
* **Framing follows actor height.** It blends from posstat 'down' to 'up' over actor y
  **[−3.906, 13.672]**: `hparam = (y*256+1000)*4096/4500` (`ff9.cs:3181-3191` / 3173-3183). Above 13.67u the
  framing is fixed.
* **Posstat table in units** (`ff9.cs:148` / 148):

  | posstat | eye height | distance | cameraCorrect | flat pitch |
  |---|---|---|---|---|
  | foot 'up' (2) | 9.38 | 21.48 | 11.72 | 19.1° |
  | 'down' (0/1/3) | | | 11.72 / 11.72 / **1.95** | |
  | airships (4/5/6) | 1.56 | 26.37 | 13.3-14.1 | 3.4° |

  Areas 40-45 use down = posstat 3 (`w_cameraArea2Place`, `ff9.cs:81` / 81; element table `ff9.cs:231` / 231).
* **Clip thresholds** (terrain under the eye above cameraCorrect + clamp):

  | case | threshold |
  |---|---|
  | on foot, above 13.67 | **48.8** |
  | low actor in areas 40-45 | down to ~39-41 (min 39.053 measured; area-place 1 = 22,932 of 83,278 standable points, `camera_clip_census.py`) |
  | flying | **46.5-47.3** |

* **Clip planes.** WorldCamera is near **0.3** / far **1000** / fov 45 (level7 and level19 prefab,
  `render_bounds_probe.py`). The fov is overridden by config at `ff9.cs:2676` / 2676.
  * The custom PSX projection (near 0.86 / far 1172.7) is editor-only: `[ContextMenu]` at
    `WMScriptDirector.cs:352`.
  * No world-camera clip plane is changed at runtime (grep).
* **Stock census** (`camera_clip_census.py`, disc 1, 1,332,448 actor×yaw evaluations).
  * Approximations: steady state, no easing, no camera tri-cache.
  * The probe ring is centred on the eye plan point. The engine adds `w_cameraDirVector/4`, which is not
    modelled.
  * Results:
  * **1 clip**, eye-terrain margin p0.01 = 5.34u, p1 = 6.88, p50 = 13.76
  * 0 within the 0.3 near plane
  * **2.65% of evaluations have terrain occluding the eye-to-player segment.** The camera has no occlusion
    handling.
  * The single clip is a centre-spike case: probes 22.65, Object 35.22 at eye (767.94, −319.94), actor
    (752.5, 10.57, −304.5). It sits **exactly at `w_effectLastPos` (767.98, 42.51, −320.32)** (`ff9.cs:337` / 337).
* **The engine's only two hard-coded camera-vs-geometry hacks sit at that same spot:**
  * (i) Hide the Object meshes of blocks (11,4), (11,5), (12,4) and (12,5) when an airship camera comes within
    12u of (768, 27.36, −320) (`WMWorld.cs:928-939` / 790-801). This is absolute-domain and LIVE.
  * (ii) A camera floor dome, radius 54.6875, floor sqrt(r²−d²)−8.59 (46.09 at centre), centred at
    eye (−767.46, −320.19) (`ff9.cs:3075-3081` / 3067-3073). WMWorld.Wrap re-centres the player's transform
    to (800, −672) ±32 (`WMWorld.cs:392-398` / 366-372; `Wrap()` `WMWorld.cs:1114` / 976), so the free-roam eye can never meet
    |x+767.46| < 54.7. **The dome is unreachable in free roam.** A PSX absolute-coordinate check, dead after
    the port's re-centring. Scene worlds: OPEN.

### e. Planet curvature: none on PC

* **No bend code in C#.** No bend, curve, horizon or custom projection in WM/ff9.cs. `WMPsxCamera` is
  unreferenced and not a MonoBehaviour.
* **No bend in the shaders.** The check is `strict_mvp` in `render_bounds_probe.py`. oPos may only be
  written by dp4 against the four `glstate_matrix_mvp` rows, applied to v0 or its (x,y,z,1) copy, possibly
  staged through a register that stays untouched, and all of xyzw must be covered.
  * The instrument passes its NEGATIVE CONTROLS. An injected position-dependent y-drop (the classic
    curved-world bend) is REJECTED, and so is a clip-space tamper. The pristine Terrain program is accepted.
    The first version of the check wrongly failed pristine Terrain (a scratch reuse of r0 after the MVP).
    The control caught it, and it was fixed before any verdict.
  * Result: 19 of 19 shaders bound by worldmap-bundle materials pass, except `Standard`. Standard is
    UNVERIFIED (no d3d9 vs program to parse) and is used only by the WaterShrine, the Arch/Sky effect objects
    and the quicksand overlay, never by Terrain/Object/Sea/Beach/River.
  * The Terrain/Object/Beach/River/RiverJoint materials all use `WorldMap/Terrain`, and the sea materials
    use `WorldMap/Sea`.
  * Fog is linear in eye distance.
* **What forms the horizon.** It is fog plus height-blind block streaming: Chebyshev ≤ maxDist blocks around
  the sky dome, clamped [2, 8] (`WMWorld.cs:1636-1667` / 1478-1509; plan-only marking `WMWorld.cs:1662` / 1504). Tall distant features beyond the
  streaming radius are simply not loaded. The 1000u far plane never binds.
* **The mist height-fog plane** (GlobalFog, mist discs) is at **y = 29** (`ff9.cs:8553-8554` / 8398-8399).
  The fog's camera-height lerp is referenced to 52.1875 (`ff9.cs:8567` / 8412). Plateau grass (topo 10) tops out
  at **28.81**, 0.19u under the mist plane. Lowland (2-8) is deep in the mist; high forest (36, to 34.07)
  and rock pierce it.

### f. Shadows

* **Height.** The blob shadow sits at ground_height + 0.1, or + 0.6 for indices 8/9 (`ff9.cs:5146` / 4991, `5144` / 4989).
  For flyers ground_height is the IgnoreExceptions first-in-buffer hit, so the shadow drops onto whatever
  that tri is.
* **Altitude effect.** Size and alpha scale with (ground − actor y). This is not a terrain bound.

### g. Land below Y=0 (`below_zero_probe.py`)

* **The basin.** The only WALKABLE sub-zero ground is the (2,7)/(3,7) basin.
  * 2,985 foot-legal samples, about 746 u², topo 19 and 5
  * deepest point **−5.774** at (223.75, −464.25), with the rim at about 5.1 within 12u: a dry pit about
    11u deep
* **Other sub-zero spots:**
  * (7-8, 13-14) is foot-illegal topo-59 building footprint, to −2.2
  * (17,14) is a stream dip, −0.18
  * the disc-4 extras are sea4 residuals
* **No water above sub-zero ground: 0 samples** on either disc, with any Sea/Beach sheet above sub-zero
  ground. This confirms placement rule (c) map-wide. Such an overlay would put the walker underwater,
  because Terrain is scanned before Sea.

## (3) The lawful Y bands

The binding constraint at each edge is given in the right-hand column.

| Y band | status | binding constraint at the edges |
|---|---|---|
| < −5.8 | unproven, no stock precedent | No engine floor exists. Lower edge: none in the query. Practical limits: the framing stops changing below −3.9 (t=0), and any hole drops ground to 0, so the actor floats then re-drops. |
| −5.8 to 0 | **walkable** (stock basin), provided no Sea/Beach sheet covers it | Water sheets live at 0 and Terrain wins the scan. Stock: 0 overlays. |
| 0 to ~0.8 | the sea layer itself (sea1-3 rims reach 0.80) | the SEA-LAYER contradiction, below |
| 0 to 34.07 | **walkable on foot / chocobo** in stock: lowland 2-8, terraces 10-17, plateau 25.6-28.8, high forest to 34.07 | The climb ceiling per step is 2.34 (1.17 on 36/37/38), not an altitude. The walker itself has NO y ceiling. |
| 13.67 | camera framing stops adapting | `w_cameraGetHeightParam` |
| 29 | mist height-fog plane | GlobalFog `height=29` |
| 34.07 to 42.19 | **flight-legal, visible.** Stock rock (49) and objects only. Walkable is lawful but unprecedented. | foot-camera ride clamp 37.1 (= stock topo-49 p98 exactly); flyer ride clamp 33.2 |
| 42.19 | **flight ceiling** | Above it the airship is clamped INTO terrain. Stock exceeds it by ≤0.49u on 3 u². |
| 42.19 to ~46.5 | visible; flyers pass through it | |
| ~46.5-47.3 | flyer camera eye enters terrain | cc + 33.2 |
| ~39-48.8 | foot camera eye can enter terrain under it. Lowest for low actors in areas 40-45 (posstat 3, cc 1.95); 48.8 for actors above 13.67. | cc + 37.1. The 4-probe ring also misses spikes narrower than about 11u (the one stock clip). |
| ≥ ~62.4 to 71.8 | **breaks** for walkers | The eye is capped at 71.8. Above about 71.8 − 9.4 = 62.4 the camera can no longer sit above the walker; above 71.8 the eye is below the walker's feet. |
| > actor y + 400 | invisible to all sky casts | `rayStartOffsetYFromSky` |

## Contradictions with recorded knowledge (high value)

1. **THE SEA-LAYER LAW is false at vertex level.** The recorded law says every sea sub-layer sits at
   EXACTLY Y=0 map-wide, coexisting by disjoint plan only (memory `project-ff9-overworld-audit-roadmap.md:104`;
   `studies/overworld-topography/AUDIT-AND-ROADMAP-2026-07-18.md:332`). Measured (`sea_layer_probe.py`):

   | layer | off-zero verts, disc 1 (disc 4 same) | max y |
   |---|---|---|
   | sea1 | 24 | 0.535 |
   | sea2 | 232 | 0.801 |
   | sea3 | 14 | 0.500 |
   | sea4 | 3 (disc 4: 22) | ±0.055 |

   * The raised verts are coastal rims, ramps toward land: e.g. sea2 (12,11) at 0.801 sits under terrain
     0.994, and sea3 (14,4) at 0.50 sits under 3.65.
   * The disjoint-plan half and the "≥0.05 floor" spirit hold for sea4.
   * **Restate the law:** open-water sheets are at 0; shallow layers (sea1-3) may ramp up to +0.8 at the shore
     under the land rim.
   * The local recorded measurement (sea4 rect (6,6)+2×2, 3075/3075 at 0) is reproduced exactly.
2. **The walk decode says slice is 0 on land.** `studies/path-d-new-world/walk-decode-claims.md:87,147,189`
   and `WALK-QUERY-DECODE.md:137` say slice_height is 0 on land classes and applies only to water.
   * Source: class 0 (topo 36/37/38, forest **and** hillside) sinks the on-foot party and chocobos by 1.171875,
     immediately (`ff9.cs:19` / 19, `5636-5666` / 5481-5511, `5509` / 5354).
   * So the 2.34375 contour and THE CANOPY STEP LAW (memory `project-ff9-overworld-interior-topography.md:94-103`,
     "step-up ceiling is 2.34375") hold for lawn → canopy. **Canopy/hillside → anything is capped at 1.17.**
   * The kit constant `placement.WALK_SPEED` docstring (79.4°) is right for lawn. It is 69.5° on 36/37/38 and
     56.3° for a chocobo on 36/37/38.
3. **Clarification, not a contradiction: topo 49 "h to 37u"** (interior-topography memory) is the p98 of
   centroids. The true vertex maximum is **42.68**, which reaches the flight ceiling.

## Open questions and the cheapest in-game probes

The harness reads only. Every probe below needs zero geometry edits unless it says otherwise.

* **P1, the canopy sink:**
  * Method: stand on a stock forest (e.g. donor (15,15) canopy) and read player y. Compare it with the offline
    sky-cast ground at that x,z.
  * Predicted: y = ground − 1.171875 (lawn control: y = ground).
  * Follow-up (bench edit): a 72° topo-38 ramp, climbable from lawn but not from canopy.
* **P2, flight ceiling over stock summits:**
  * Method: fly Hilda Garde at full altitude over (1225.5, −926.5) and read airship y.
  * Predicted: 42.1875 exactly (clamped 0.48u into the 42.67 summit). Not 42.67, and no stall.
* **P3, the one stock camera clip:**
  * Method: on disc 1, teleport off-lattice to about (752.6, y, −304.6). Rotate until the eye is over
    (767.9, −319.9). Snap a frame and read MainCamera y.
  * Predicted: eye y ≈ 34.4, inside the Object spike at 35.2. No dome lift (dome unreachable).
  * This also settles whether the dome is live.
* **P4, the 71.8 eye ceiling** (bench edit): a 70u walkable plateau. Predicted: the camera looks level or up
  at the player, and terrain sits behind the eye.
* **P5, sub-zero walking:** walk into the (3,7) basin at (223.75, −464.25). Predicted: player y = −5.77; no
  water, no strand.
* **P6, no-fly topo** (bench edit): retag a patch to topo 15 (flight-blocked, unused by stock). Predicted:
  the airship stops dead at its edge at any altitude (the fly branch has no fan), and it is foot-blocked too.
  Encounter and footstep side-effects are unknown.
* **OPEN:**
  * whether the camera dome is reachable in scene worlds (dummy actor, no wrap)
  * GlobalFog's enabled state in shipping config (MonoBehaviour has no typetree; runtime-only)
  * whether a walker above about 62u is acceptable visually
