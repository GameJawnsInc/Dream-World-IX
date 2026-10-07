# The descent stall at the +3 beach tear: mechanism, law, confirmation run

Lane "stall" of the in-game terrain round. It answers the open item in `RESULTS.md` section 6.

In session 5, (7,17) was raised +3 with `world-terrain --at 480 -1120 --radius 16 --raise 3`. Walking south off the
raised terrain onto the beach, the actor crossed at x = 476.28. At x = 479.64 and 480.18 it "stalled": the steps
shrank to about 0.06u, and the walk ended at z ≈ −1119.80, 3u above the beach.

Files:
- `stall_sim.py`: the offline simulator, plus its calibrate / map / predict / replay commands.
- `stall_session.py`: the confirmation scenario.
- `stall_dryrun.py`: runs the scenario offline against the harness FakeGame, driven by the simulator.

Derived numbers go to `out/stall_*.json`, which is gitignored. The regenerated mesh lives in the session scratchpad;
nothing is written to a mod folder.

---

## 1. Verdict

**The engine never stalled.**
- At those two lines, the full-speed probe landed across the tear. `w_movementControl` therefore shrank the tick's
  step to s²/√(s² + dy²) = 0.062u. This is the step normalisation, see section 2.
- The actor **crept** toward the edge at that speed. It needed 7 shrunken ticks in all, and the last one drops onto
  the beach at tick 13.
- After 3 of those ticks, `world_approach` ended the walk. It judges every burst on its own, and this burst moved
  less than 0.35 × the commanded distance (`tools/harness/session.py:2877`, fraction `:2614`).
- The ring shows the stick being released at that point (`key_up` false, then a teleport to the next line). It does
  not show the actor stopping on his own.

**Line 476.28 passed by phase, not because its drop was smaller.**
- Its last full step ended 0.029u from the edge, which is closer than one shrunken step (0.073u). So it crossed on
  the very next tick, with no creep.
- On the same seam, a line at x = 483.9 has the same drop (2.54u) and is read as "blocked" (section 5).

**Correction to RESULTS section 6:**
- The sentence "it can also trap a player who walks to the edge from above" is predicted false.
- Holding the stick crosses a 3u tear in at most 7 ticks (about 0.25 s at the world's 28 ticks a second).
- The instrument lesson there also misstates the stall detector: it is **one** burst under 0.35 × commanded, not
  "two bursts under 0.3u".
- The quoted step series "0.81 → 0.06 → 0.05 → 0.075" is read from the smoothed `world.x/z` publish. The per-tick
  `player.*` positions give 0.0622 / 0.0624 / 0.0627.

The rest of this plan proves this offline and registers a single-launch in-game confirmation.

## 2. Mechanism, from source

All citations are to stock Memoria code paths in `C:\gd\FFIX\Memoria\Assembly-CSharp`, at the working tree's line
numbers.

### Each tick of `w_movementControl` (`ff9.cs:5533-5603`)

1. At the start of the update, `w_movementUpdate` stores the actor's position as `last` (`ff9.cs:5159-5162`).
2. Sweep θ = 0, 11.25, …, 78.75° (`:5552`, `PsxRot(128)` = 11.25°). For each θ:
   - Probe 1 is `w_movementRoundCheck` at full speed s = 0.4375 along RotTrue + 180 + θ.
   - Only if probe 1 fails is the same probe tried at −θ (`:5558-5563`).
3. When probe 1 passes, compute `num8` = |probe1 − last|.
   - This is a **3D** distance: the planar form applies only when the slice height of the landing topograph is
     nonzero (`:5566-5578`). For beach topograph 30 and terrain topograph 31 the slice height is 0 (column 8 of
     `w_movementSinkArray`, `:5636-5680`).
   - `num9` = s² / `num8` (`:5579-5591`).
4. Probe 2 is `w_movementRoundCheck` at `num9` along the same rotation (`:5593`). If it passes, the actor moves there
   and takes the ground height found there (`:5594-5601`).
5. If no θ succeeds, the actor does not move that tick. This is the only way the engine stops him.

### `w_movementRoundCheck` (`ff9.cs:5682-5718`)

- The probe point is the actor's position plus (rsin, rcos)(RotTrue + 180 + rot) × speed. **The probe keeps the
  actor's own y.**
- The ground query goes through `w_cellHit` with the actor's triangle cache, unless the actor stands on topograph
  49 or 52 (`:5690-5699`).
- The probe passes if the ray hit something (`pno` ≥ 0) and the topograph hit is in the control row's `limit` mask.
  - On foot that mask is `0x0010667F / 0xD8FF3CFF` (`ff9.cs:1487-1491`, identical to `TransportControls.csv` row 0).
  - On foot `flg_gake` = 0, so there is no water/ground gate.

### The ground query

`w_nwpHit` (`ff9.cs:7296-7324`):
- Casts straight down from y + 2.34375 (`rayStartOffsetY`, `:1328`).
- Passes `rayDistance` = 2.8 (`:1329`), but **`WMBlock.Raycast` never reads its `distance` argument**
  (`WMBlock.cs:137-183`).
- So a downward probe finds any surface below the actor, however far down.

`WMBlock.Raycast`:
- First it walks the 10-slot triangle cache (`:145-162`). That check has no up-facing filter and no skip-id filter,
  and it accepts any intersect code other than 0 (`WMPhysics.cs:63`).
- Otherwise it scans the meshes in registration order. Within a mesh it takes the **first** passing triangle in buffer
  order, not the nearest (`WMPhysics.cs:13-41`, `WMBlock.cs:185-199`). A 0x31EE first hit abandons that mesh
  (`:202-215`).
- Every full-scan hit is pushed into the cache (`:171-178`).

`intersect3D_RayTriangle` returns 0 when the hit is behind the ray origin (`WMPhysics.cs:96-99`). This is what makes
an upper surface more than 2.34375u above the actor invisible, and so makes a climb fail.

### Applied to the +3 descent

Probe 1 lands on Beach1 3.05u below the actor. That surface is visible and its topograph (30) is legal, so probe 1
passes. Its 3D length is √(0.4375² + 3.05²) = 3.08, so `num9` = 0.1914 / 3.08 = 0.062. Probe 2 at 0.062u lands on
the terrain and passes, so the actor creeps 0.062u. Each later tick repeats this until probe 2 itself lands past the
edge, and the actor drops.

Nothing in this chain can refuse the descent:
- The first probe always sees the lower surface.
- Every shorter probe lands either on the terrain or on the beach, because a reshape that changes only y welds
  Terrain and Beach1 exactly in plan. The shared verts are at (476, 480, 484; −1120), confirmed in calibration C0.

### Facts the simulator also carries

- On foot, s = S(112·4096 >> 12) = 0.4375 (`ff9.cs:1473`, `:6165`).
- RotTrue is set from the camera immediately (`:6166`). The yaw ease only affects the drawn model.
- The harness teleport truncates x/z to 1/256 (`Ff9mkDebugMenu.cs:1837`). It then re-grounds with a sky cast that
  uses no cache (`:1852`, which calls `ff9.cs:4596-4618`).
- The published `player.y` is `(Int32)(y × 256)` (`WMActor.cs:37-47`).

## 3. The simulator and its calibration

`stall_sim.py` ports the code path above line for line, in float32 like the engine:
- Unity's `Vector3 ==` epsilon.
- Normals computed in `AddWalkMesh` from the local verts.
- The cache order: slot `Number`, then `Number + 1` … `+9`.
- Probe 1 tried again at −θ.

The walk meshes are the (7,17) list in registration order, from the consumption bind oracle via `arealib`: Terrain,
Beach1, Sea1-5. The Terrain is **regenerated** with the kit's own reshape step (`extract.read_block` →
`mesh.deform_radial` → `mesh.ff9mesh_bytes`). These are the bytes `world-terrain` deploys: sha256 `c9bea91f…452e`,
18,272 bytes.

`py stall_sim.py calibrate` (about 45 s) gives:

| id | what | result |
|---|---|---|
| C0 | regenerated +0 Terrain == stock arrays | **equal** (verts, ids, triangle order) |
| C0 | seam drop at +3 (terrain edge − beach) | 476.28: 2.565 / 479.64: 2.958 / 480.18: 2.979 |
| C1 | the 6 teleport grounds of session 5 (+3) | **6/6 equal the published y exactly** |
| C2 | +3 south 476.28: every ring position matches a simulated tick | **12/12** within 0.002u. d0 = 0.029, one collapsed tick (0.073), beach at tick 8 |
| C3 | +3 south 479.64 / 480.18 | **9/9 and 9/9**. Creep from tick 7: 0.0622 / 0.0624 / 0.0627 / 0.0630 / 0.0632 / 0.0635; beach at tick **13**. The 3-tick-burst `world_approach` model returns "blocked" at **(479.5694, −1119.7969)** and **(480.1122, −1119.7988)**; the ring ends were (479.5691, −1119.7969) and (480.1121, −1119.7984) |
| C4 | +3 north (climb refusal), no ring rows, start and end only | **one** fitted heading (φ = 358.55) reproduces all three ends to **0.0003u**, including line 480.18 sliding to −x while the other two slide to +x. Each walk truly stalls from tick 2, 0.003-0.027u short of the seam |
| C5 | +1 control climbs (session 5 +1 ring) | **2/2, 8/8, 6/6** positions match. The +1 climb also collapses its first steps, to 0.165-0.19u |
| C6 | stock (unraised): both directions at all 3 lines | crossed 6/6, 0 collapsed ticks, 0 stalls (simulation only; no stock ring exists for this seam) |

Calibration lessons:
- Use the COMMANDED teleport target, not the published start, which is rounded to 3 decimals. Line 480.18 north
  needs the exact −1120.359375: the −θ choice flips at a 0.004u difference.
- Measure the heading once per leg from the full ticks. All three lines of a leg share one `world_face`.

## 4. The law

### 4.1 The descent creep law (on foot, stock engine)

When a tick's full-speed probe lands on walkable ground dy below the actor, the tick's step is

    v_c = s² / √(s² + dy²)        s = 0.4375; dy = actor y − ground y at the probe

dy is the probe's own vertical gap, about 3.05 at 479.64. That is slightly more than the edge drop of 2.96, because
the actor stands up-slope of the edge.

The walker creeps at v_c until it is within v_c of the edge, then drops. The number of shrunken ("collapsed") ticks,
the crossing tick included, is about **n = ⌊d0 / v_c⌋ + 1**.
- d0 is the edge distance when probe 1 first crosses the edge. d0 lies in (0, s].
- On a slope the full step taken is s² / |Δ| < s. So if d0 falls between that full step and s, the creep starts
  even though a full step would not have crossed.

The `drop_sweep` in `py stall_sim.py map` checks the law on this site:

| raise | edge drop | v_c from the law, at the edge drop | v_c simulated (at the larger probe drop) | n | beach tick | descent stalled |
|---|---|---|---|---|---|---|
| 1.0 | 0.99 | 0.177 | 0.160 | 3 | 9 | never |
| 2.0 | 1.97 | 0.095 | 0.090 | 5 | 11 | never |
| 3.0 | 2.96 | 0.064 | 0.062 | 7 | 13 | never |
| 6.0 | 5.92 | 0.032 | 0.032 | 12 | 18 | never |
| 10.0 | 9.86 | 0.019 | 0.019 | 22 | 28 | never |

The law column uses the edge drop. The simulated step uses the probe drop, which is larger, and the two converge for
large drops.

**The engine refuses no descent onto walkable ground, at any drop.** A held stick crosses within
⌈√(s² + dy²) / s⌉ + 1 ticks.

### 4.2 When does a descent truly stall?

The creep turns gaps narrower than one full step into traps:
- A true stall needs a non-walkable plan gap of width w at the edge, with **v_c < w < s**.
  - The gap is either a slit where neither mesh is hit, or a strip of refused topograph.
  - Probe 1 clears the gap, so the step shrinks. Every shrunken probe 2 then lands in the gap, so every θ fails.
- The `slit_corollary` in `map` demonstrates this on synthetic geometry: the Terrain seam verts are pulled north by
  w, and the walk runs at 479.64 with v_c = 0.062.
  - w ≤ 0.05: the actor still crosses.
  - w = 0.07, 0.1, 0.2, 0.3, 0.42: the actor **stalls** (ticks 12 / 12 / 10 / 8 / 7).
- At w ≥ s the gap is an ordinary wall.
- The same slit at a small drop is jumped, because v_c ≈ s there.
- `terrain.reshape` changes y only, so the kit's Terrain-only tears never open such a gap. An operator that moves
  x/z at a seam could (`transplant.morph_in_place`, `VertexDisplace`). This is a lead for the stitch gate, not a
  finding about any live cell.

### 4.3 The climb, for contrast

A climb is refused when the upper surface at probe 1 is more than 2.34375u above the actor, because the triangle is
behind the ray origin.

The sweep then slides the actor along the seam. Each tick needs s·cos θ < the remaining gap. When the remaining gap
is under s·cos 78.75° = **0.0854u**, all 15 probes fail, and that is a true stall. C4 measured gaps of 0.003-0.027u.

This is the only stall observed in session 5. It is a genuine one-way wall from the beach side.

### 4.4 What the harness reads (the instrument law)

`world_approach` returns "blocked" when **one** burst's progress along the bearing is under 0.35 × commanded
(`session.py:2877`).

With B ticks per burst, a burst is read as blocked when it falls inside the run of collapsed ticks:
- B = 3: always when n ≥ 5, and for n = 3-4 depending on alignment.
- B = 4: only when n ≥ 6-7.
- B ≥ 5: almost never at this drop.

B is not a constant. The world ticks at `WorldTPS` 28 (`Memoria.ini [Graphics]`; FieldTPS is 30) against a ~60 fps
render, so a 6-frame burst holds 2 OR 3 ticks (2.8 on average) depending on its phase. The session-5 +1 ring shows
both: seqs 45 and 50 are 2-tick bursts. (The +3 south leg happened to get 3 every time.) Which creep tick ends a
`world_approach` therefore varies from run to run (`predict` → `irregular_burst_mc`: L2 ends on tick 8/9/10/11 in
12/55/13/20 % of runs). That the walk ends **inside** the creep run does not vary.

So the old verdict depends on the drop, the phase of the start point, and the render rate. It is not a property of
the terrain. A creep-tolerant reader is needed (section 6, `creep_walk`).

## 5. Predicted creep and verdict map along the seam

From `py stall_sim.py map` (+3 mesh, the session-5 heading φ 181.388, every line starting at z −1117):

| x range | edge drop | d0 | collapsed ticks | engine | old reader (B = 3) |
|---|---|---|---|---|---|
| 476.1-477.5 | 2.54-2.71 | 0.029-0.017 | 1 | beach at tick 8 | **reached** |
| 477.7-481.1 | 2.73-2.99-2.87 | 0.436-0.388 | 7 | beach at tick 13 | **blocked** |
| 481.3-483.9 | 2.85-2.54 | 0.388-0.384 | 6 | beach at tick 12 | **blocked** |

**The engine crosses at all 40 lines.**
- The old reader's boundary at x ≈ 477.6 is where the accumulated phase of seven slope-shortened full steps wraps.
  The step is 0.4246u near x 476 and 0.4352u near x 480.
- x = 483.9 has the same drop as 476.1 (2.54) and the opposite verdict.

Phase map: one line, with the start z swept over one full step in 1/128u increments.

| x | starts read "blocked", B = 3 | starts read "blocked", B = 4 | starts where the engine fails to cross |
|---|---|---|---|
| 479.64 | 41 of 56 | 16 of 56 | 0 of 56 |
| 476.28 | 37 of 56 | 9 of 56 | 0 of 56 |

The start z of −1117.00, which happened to be the one used, sits at the edge of the narrow "reached" band at 476.28.
The same band at 479.64 is about 0.12u wide.

## 6. The confirmation run (`stall_session.py`)

### Deploy

This is exactly session 5's +3 change, into the scratch folder only. The orchestrator owns all of it.

1. Back up `Memoria.ini`. Put `"FF9CustomMap-lab"` **first** in `[Mod] FolderNames`.
2. `cd C:\gd\Dream-World-IX\ff9mapkit && py -m ff9mapkit world-terrain --mod-folder FF9CustomMap-lab --radius 16 --at 480 -1120 --raise 3`
   - This writes `FF9CustomMap-lab/FF9_Data/WorldMap/Disc1/0_1/r17/Block[7][17] Terrain.ff9mesh` and its Disc4
     mirror.
   - The file must hash to `c9bea91f0d32006e7f2492418202c14c010b9bd01fe572a620ea23199a07452e`. K0 checks this in
     game.
3. `py tools/play.py studies/terrain-malleability/ingame/stall_session.py --label stall-session`. This is one launch;
   the lab folder's first registration is read at that launch.
4. `py studies/terrain-malleability/ingame/stall_sim.py replay .harness-runs/<stamp>-stall-session`. This scores
   every ring position at the run's own measured heading.
5. Remove `FF9CustomMap-lab`, restore `Memoria.ini` byte-exact, and check the sha256 against the backup.

### Lines

Run in this order, which is also the simulator's cache order. Every world-face runs on the 6603 landing lawn
(68, −444).

| line | start | bearing | role |
|---|---|---|---|
| C | (479.64, −1120.18) | 90 | **Control.** The +3 climb is a true stall. A `creep_walk` (bursts, no early verdict, "stalled" after 3 bursts under 1e-4u) must report it. This proves the new reader can see a stall. |
| L2 | (479.64, −1117.0) | 270 | Session 5's line 2 exactly: `world_approach`, then **held on** with `creep_walk` |
| L4 | (479.64, −1119.105) | 270 | **The 4th line.** Same x and drop (2.96) as L2. The start is shifted so d0 = 0.036 < v_c |
| L5 | (476.28, −1118.78) | 270 | Mirror. The "passing" x (drop 2.57), with the start shifted so d0 = 0.37 |

### Registered predictions

These are in the scenario docstring and `out/stall_predict.json`. They hold across the `world_face` ±2° tolerance and
real bursts of 2-4 ticks, mixed within a walk, except where stated. The burst is sized to about 3 ticks from the
walk speed measured on the world map (section 7).

| id | prediction | what the stall/drop hypothesis predicts instead |
|---|---|---|
| K0 | lab Terrain sha256 == the simulated mesh's; teleport grounds publish y **4.08984375 / 3.87890625 / 3.23046875** exactly for L2 / L4 / L5 | (deploy identity: the instrument's own control) |
| K1 | C: at most 1 moving burst, then still; end z in (−1120.0854, −1120.0); y < 1.0 | (control) |
| K2 | L2 `world_approach` returns "blocked", ending **on one of L2's creep ticks 7-13** (`K2_CREEP_Z`, ± 0.01; tick 9 = −1119.797, session 5's end, is the likeliest) | stall: the same. Drop: blocked at the last full tick, −1119.610, which is not a creep tick |
| **K3** | L2 held on: the first continuation burst moves ≥ 0.06u (one or more creep ticks of about 0.063); **on the beach (z < −1120, y < 1.0) within 4 bursts** (tick 13 lands at (479.563, −1120.050), y 0.766) | no motion past the edge (z ≈ −1119.99); y stays about 3.72-3.77 |
| **K4** | L4 (**the 4th line**): `world_approach` returns **"reached"**, on the beach, with exactly one collapsed tick: tick 3 lands at (479.614, −1120.027), y 0.773 | "blocked", as at L2 (same x, same drop) |
| K5 | L5 `world_approach` returns "blocked", ending **on one of L5's creep/crossing ticks 3-8** (`K5_CREEP_Z`, ± 0.01); held on, it crosses (beach at tick 8: (476.246, −1120.059), y 0.363) | "reached" (drop 2.57, like the passing line) |
| ring | every published C / L2 / L4 / L5 position equals a simulated tick within 0.002u, and the L2/L4/L5 rings reach their predicted crossing tick (`replay`: `ring_reaches_crossing`) | the per-row match alone does not discriminate: a stalled walk publishes a prefix of the same path. Its ring stops short of the crossing tick |

The decisive pair is L2 against L4: same x, same drop, different phase.
- The stall hypothesis predicts both blocked.
- The drop hypothesis predicts both blocked.
- The creep law predicts L2 creeps and then crosses when held, and L4 crosses at once.

### Offline dry run (`stall_dryrun.py`)

The real harness `Session` drives the FakeGame. Its overworld on (7,17) is the calibrated simulator; off the cell it
is flat lawn, and walking there flushes the cache. It renders 60 fps against its own 28-ticks-a-second world clock
(the bumpers turn and "up" moves once per tick), so bursts hold 2 or 3 ticks as in the game. The scenario ran
against three engines, twice each, ending on different creep ticks (K2 on ticks 9/10/11, K5 on 5/6/7):

| engine | K0 | K1 | K2 | K3 | K4 | K5 |
|---|---|---|---|---|---|---|
| sim (the law) | pass | pass | pass (B = 3 fit) | **pass** | **pass** | **pass** |
| H_SEAM (creeps, but the crossing step is refused) | pass | pass | pass | **FAIL** | **FAIL** | **FAIL** |
| H_DROP (no step across a drop over 2.6u) | pass | pass | **FAIL** | **FAIL** | **FAIL** | **FAIL** |

The verdicts split as registered, so the checks can fail. `replay` scored all three dry runs: every ring row matches
a simulated tick for all three engines, but only the sim engine's L2/L4/L5 rings reach their crossing ticks.

## 7. Risks

- **Random battles.** Area-50 topographs 30/31 here roll encounters: the +1 run met scene 828, and a level-1 party
  loses.
  - The scenario walks about 8u in total.
  - On a battle it flees (25 s), leaves the battle, and moves on to the next line, marking the interrupted one.
  - A final check fails if any line was interrupted. A GameOver ends the run and writes the partial record.
  - No harness verb toggles the no-encounter booster (`SettingsState.cs:53`, booster index 4).
- **Render rate.** At B ≥ 5 L5's old-reader verdict would flip to "reached". The scenario sizes bursts to ~3 ticks
  from the walk speed `world_face` measures on the world map: on the flat lawn one tick is exactly 0.4375u, so
  ticks/frame = speed / 0.4375. It re-sizes after each facing, because the render rate can flip mid-launch. A burst
  then holds 3 ± 0.5 × ticks/frame, never more than 4. It records `burst_frames` and `ticks_per_frame_n/_s`.
  `g.rate()` is a fallback only: it is measured on fields against FieldTPS 30.
- **Heading.** `world_face` tolerance is ±2°. K1-K5 are invariant across that band (`predict`). Exact tick positions
  are scored post hoc at the measured heading.
- **Deploy drift.** If the kit's reshape changes, K0's sha check fails before any judgment is made.
- **No owner eye needed.** Every check is numeric: positions, heights and a sha.

## 8. Rerun

```
py studies/terrain-malleability/ingame/stall_sim.py calibrate     # ~45 s: C0-C6 against the session-5 rings
py studies/terrain-malleability/ingame/stall_sim.py map           # ~20 s: seam map, phase map, drop sweep, slit
py studies/terrain-malleability/ingame/stall_sim.py predict       # ~10 s: the confirmation lines + band
py studies/terrain-malleability/ingame/stall_dryrun.py            # ~6 min: the scenario against sim / seam / drop
py studies/terrain-malleability/ingame/stall_sim.py replay <run>  # after the live run
```

`$STALL_SCRATCH` overrides the scratch directory used for the regenerated meshes and the fake install.

## 9. Adversarial review: what was fixed

The mechanism, the simulator and its calibration held up under review.
- The cited engine lines were re-read and match: `w_movementControl`, `w_movementRoundCheck`, `w_nwpHit`,
  `WMBlock.Raycast` (the distance is unread), `WMPhysics` (first hit; the cache accepts code ≠ 0), the teleport's
  InitSlice, and the sink-array column 8 = 0.
- `calibrate` was re-run with identical results. A planar-`num8` model scores 0/12, 0/9 and 0/9 against the same
  ring, so the calibration can fail.
- The session-5 ring shows the stick released after one creep burst (seq 88).
- The cache-flush assumption was tested: the cache after C holds a single Beach1 tri, and L2/L4/L5 come out the
  same whether the lawn walk flushes it or not.

The instrument had five defects, all fixed in place.
1. **Fixed-B end tables (K2, K5).** The world runs at WorldTPS 28, so a 6-frame burst holds 2 or 3 ticks. The first
   cut's per-B end z failed about one run in three for that reason alone (`irregular_burst_mc`: K2 34 %, K5 32 %).
   K2/K5 now accept any creep tick of the line (`K2_CREEP_Z` / `K5_CREEP_Z`, derived by `predict` →
   `creep_tick_table`; each tick's z is ± 0.002 over the ±2° band). With them, K2/K4/K5 pass 100 % of simulated real
   bursts at 6 or 7 frames (60 fps) and 3 or 4 frames (31 fps), at headings −2, 0 and +2°.
2. **The dry-run stand-in ticked every other frame**, so it could not show defect 1. It now runs a 28-TPS world clock.
3. **A battle read as evidence.** A battle mid-creep recorded K1/K3/K5 as FAIL, which is the stall hypothesis's
   signature, and an early return skipped the "no battle" check. An interrupted line is now NOT JUDGED and gets its
   own failing "interrupted" check. `battle_out` waits for the battle scene before deciding whether to flee.
4. **The ring scrolled away.** The harness ring holds about 10 s, so C and L2 would have been gone by the final
   flush. Each line now flushes `states-line-<name>.jsonl`. `segments` also splits at each line start: L4 starts
   only 1.4u from L2's beach end, and `replay` had glued them together, scoring L4 as zero rows.
5. **The ring match did not discriminate.** A stalled walk matches row for row, as the dry run showed for all three
   engines. `replay` now reports `ring_reaches_crossing`.

Burst sizing moved from the field-measured `g.rate()` to the world-measured walk speed (section 7, Render rate).
