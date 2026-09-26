**The stock door facing gate: engine rule, census, harness code map (rung-3 follow-up to the 116-miss diagnosis)**

Five read-only research passes (workflow `wf_0c8b27cc-198`), kept as written. THE CROSS-CHECK comes first because it
settles the rule and corrects the other four where they disagree (player.dir is always 0 on a field; the turn is
per MovePC call, not per render frame; the window is strict, [-47, +47] of 256). What was built from it is in the
code and `../PLAN.md`. Scratch paths name the session scratchpad (machine-local, archived under `<archive>`).


# THE CROSS-CHECK (read first: it settles the rule and corrects the others)

**Facing gate on stock Dali doors: where the four reports disagree, and the settled rule**

The engine report holds up. The census and code map both size the turn press in render frames when the turn happens per MovePC call. `player.dir` carries no facing in a field. The q0→q1 edge order is preserved from the SetRegion bytes all the way to `route_cross`. An opt-in FakeGame gate leaves all 494 existing tests passing, as long as the standing re-test only runs for a gated region.

## Disagreements and corrections

**D1. "player.dir is the facing"** (the task text, the handoff, and the census's "record the facing error from player.dir")
- **Wrong.** The engine report and code map are right.
- The agent publishes `po.rot[1]` (`HarnessAgent.cs:1170`). `PosObj.rot` is an Int16 array zeroed at `PosObj.cs:11,26`.
- A grep of every `.rot[..] =` finds only two writers: `WMActor.cs:101` (world map) and `PosObj.copy` (`PosObj.cs:45`).
- The gate reads `rotAngle[1]` in degrees (`EBin.cs:1816`), which is written at `FieldMapActorController.cs:764`.
- So in a field, `faced` can only be a prediction. Measuring it needs an agent patch; `po.rotAngle[1]` needs no Actor cast (`PosObj.cs:165`).
- On the world map, `dir` = `ConvertFloatAngleToFixedPoint(rot1)` in 4096ths, so the facing is `(dir>>4)&255`.

**D2. Turn rate in frames vs MovePC calls** (census: "≥2 frames … 0.36×128=46", "keep holds to 2-4 frames"; code map: "4 walked frames, 180·0.6⁴=23.3°", and a FakeGame lerp of 40% per pressed frame; handoff: "40% per moving frame")
- **Wrong unit.** The engine report is right.
- The 0.4 lerp is per MovePC call (`FieldMapActorController.cs:759`). There is one call per `UpdateMovement` (`:336`). Walking runs one `UpdateMovement` per tick; running runs two (`:198-209`).
- Ticks run at 30 Hz on wall-clock time (`FPSManager.cs:78-110`; `Memoria.ini` `FieldTPS=30`). Harness holds count render frames (`Time.frameCount`). `FieldFPS=-1` with `VSync=1` means the render rate is the monitor's rate.
- The harness's own calibration (RUN 30u/frame, WALK 15u/frame, `session.py:1135-1136`) at 30u per call gives **0.5 calls per walked frame and 1 per run frame** on this machine. FakeGame already counts it this way (`fakegame.py` comment near line 262).
- The code map's 4 walked frames are 2 calls. The worst case is 64.8° left over plus 22.4° of pad offset, about 87°, which fails. The census's "46" also ignores the pad offset of up to 16 units.
- My positive controls on the real 350→351 zone, arriving at yaw 69°: 2 and 4 walked frames miss, 6 fire.

**D3. "±48/256 (±67.5°)"** (task, handoff; code map's "under 67.5°")
- **Exclusive bound.** B_LT is `_v0 < t3` (`EBin.cs:743`); B_GT is `t3 < _v0` (`EBin.cs:758`).
- The door counts as faced only for a signed error in [−47, +47], which is ±66.1°. Plan against 66.1°. The engine report and census agree on this.

**D4. The two "<56 || >200" sites**
- The engine report says both are in field 1460. **The census is right:** 1460 @8065 and 3059 @4885.
- A byte scan of all 818 scripts finds the idiom's assignment 114 times in 83 scripts: 112 use (48, 208) and 2 use (56, 200) (`bytes56.py`).

**D5. "The bearing is almost constant per door; one fixed press per door"** (engine report, which covers 350 only)
- **True for 350, 351 and 353:** the first edge lies 252-1597u off the standable part.
- **False for 356 e15 (356→358):** its first edge is on walkable ground (56 of 57 probes past it are on the walkmesh). Standable points are 0-734u from it, and the bearing ranges over 0..192 near the edge.
- The tour meets **9** gated doors, not 4: 350 e18, e19, e20 (= e21), e22, e23; 351 e18→352; 353 e15→356; 356 e15→358.
- Best press at the tour's own goal point (my table from `goals.py`):

| Door | Best press | Error at the goal | Note |
|---|---|---|---|
| 351 e18 | U | 1 | |
| 353 e15 | U | −5 | twist_d 10 = 15.47° |
| 356 e15 | UR | −12 | |

**D6. FakeGame: "do not turn on coast frames"** (code map)
- **Wrong.** Rotation (`:749-764`) keys on the same pressed booleans that produce the step.
- Any frame the fake translates by a press, coast frames included, should turn by a factor of 1−0.6^calls. `_move_to` already receives `calls`. This is the engine report's spec.

**D7. "FakeGame's twist has the opposite sign"** (engine report, open question 5)
- **Already handled, not a bug.** FakeGame rotates counter-clockwise (`fakegame.py:707-712`), and `_dali_fake` passes the negated angle `atan2(−v.x, v.z)` (`test_harness.py:3502-3504`).
- The fake's post-twist `(vx, vz)` is therefore the engine's world press. Compute the fake's facing from that.

**D8. "`_StoryFake._enter_regions` (5381-5391)"** (code map)
- That override belongs to `_MissOnceFake` (class at 5370).
- `_StoryFake` overrides `_step_exit_now` (5356) and calls `super()` first, so an `arrive_face` set in the base class composes.

**D9. Region membership is described as "a fan"** (task, handoff, engine report)
- It is the triangles `(q[i], q[i+1], q[i+2])` mod n (`TreadQuad.cs:26-37`). The side-findings report is right.
- Membership uses `po.go.transform.position` (`TreadQuad.cs:9-10`). The exit calculation uses `po.pos` (`DoEventCode.cs:2259`). They agree after `SyncPosToTransform` (`FieldMapActorController.cs:402`).

**D10. "Arrival (258,−58) is 18u outside the door zone"** (code map)
- That is outside the kit's 4-point quad. The engine's pentagon edge (253,−87)→(325,122) puts him only about 5u outside.
- No effect on the fix, but it matters for what `inside` means.

**D11. `_MissOnceFake`'s docstring** ("a gateway that fires on the way in, never for someone standing in it")
- **Contradicts the engine.** `CollisionRequest` runs every tick with control (`ProcessEvents.cs:183-188` → `EventCollision.cs:300-303`), so an ungated region does fire for someone standing in it.
- The misses that double models were the facing gate. Keep the test as a regression; its stated rationale is superseded.

## The five questions, settled

1. **Rule consistency.** The engine rule and the census classification are consistent. `player.dir` is not the gate's facing (D1). I re-derived the conversions in the settled rule below from `EBin.cs` and `FieldMapActorController.cs:751`. The engine report's conversions and worked numbers are correct.
   - I reproduced the worked case exactly. At (289,−74) the errors are U −48, UR −16, R +16, DR +48, L −112.
   - The lerp sequence from 69° gives yaws 6.0°, −31.9°, −54.6°, with errors +83, +56, +40.
2. **Yes, a press into a wall turns him.**
   - The rotation at `:749-764` precedes `WalkMesh.Collision` (`:765`), the push-out revert (`:786-790`, position only) and `ServiceChar`. None of these writes `rotAngle`.
   - In-game corroboration: the s83 note in `HonoInputManager.cs:946-950` says the actor rotated while the axis was zeroed and never translated. The diagnosis's probe pressing right from the 351 door spot fired the door.
   - Offline, the fake with a walkmesh edge at x=290 fires the door after the press is blocked.
3. **Yes, q0→q1 is preserved.**
   - I decoded the raw SetRegion bytes for all six of 350's gated regions. They equal `_region_points`, and `_zone_quad` keeps points 0-1.
   - From there the zone passes unchanged: `scan_gateways` → `Tour._scan` (`dali_tour.py:262-268`) → `_cross` (`:393-395`) → `route_cross` (`session.py:4414-4416`) → `route_to`'s `zpoly` (`:2826`).
   - Outside Dali, 1458 e11 and 3057 e10 are exceptions (the census's polygon B).
4. **Yes, when opt-in and restricted.**
   - I monkeypatched it in with a scratch plugin: the turn model, `face: True`, "the first containing region answers", and a standing re-test only when that first region is gated. Result: **494 passed**. The worktree is still clean.
   - The same plugin makes 6 of 6 positive controls pass; without it, 4 of 6 fail. So a facing test can fail.
   - The unrestricted variant (re-running `_enter_regions` on every standing frame) breaks 3 tests: both `test_route_to_goes_round_a_gateway_the_straight_walk_takes` parameters and `test_a_smooth_route_holds_whole_legs_in_fewer_requests`.
5. **What none of the reports says:**
   - **Turning costs distance, not time:** each call moves him 30u, walked or run, unless blocked.
   - **A turn-in-place primitive exists engine-side.** Holding the key booleans without feeding `TryGetAxis` rotates him with zero translation: `:736-737` zeroes the move, while rotation keys on `movingX` at `:749`. It needs a harness-agent verb, which means a DLL rebuild (confirm-first).
   - **Shadowing at 350 depends on the scenario.** Entry 26 covers every standable point of the 353 and 356 doors, and entry 24 covers 1577 of 2084 points of the 356 door. Neither is armed at scenario 2600 (engine report's arm list).
   - **356 e15 is armed only on one branch.** Main_Init arms e15 or e12 depending on a flag test (356 .eb 661-679), and e12 is not a gateway.
   - **351 e18 and 353 e15 have no overlapping tag-2 region.**

## The settled rule

**Units:** 256ths of a turn. **Convention:** 0 = −z, 64 = −x, 128 = +z, 192 = +x, which is `atan2(−dx, −dz)`, clockwise seen from above.

```
# q0 = zone[0], q1 = zone[1] (ints); px, pz = float position; yaw = Actor.rotAngle[1] in degrees, in [-180, 180]
ex, ez = q1x-q0x, q1z-q0z;  d = (ex*ex + ez*ez) >> 8;  t = 0
if d: t = clamp(ctrunc(trunc(ex*(px-q0x)) + trunc(ez*(pz-q0z)), d), 0, 256)   # C# truncating division; onto the SEGMENT
jx, jz = (t*ex >> 8) + q0x, (t*ez >> 8) + q0z                                  # DoEventCode.cs:2252-2266
bearing = angleAsm4096(jx - rhe(px), jz - rhe(pz)) >> 4    # in [-128, 128]; dx = dz = 0 gives 0; EBin.cs:1207-1216, 1583-1614
facing  = (rhe(float32(yaw/360*4096)) >> 4) & 255          # EBin.cs:1811-1824, 1273-1284 (rhe = round half to even)
v = (facing - bearing) & 255
faced = v <= 47 or v >= 209                                # strict 48 / 208
```

- Use `angle_asm_fixed` from `facing_engine/facing_rule.py` with the math table. It differs from the game's table by at most 1/4096 of a turn. Never ship the game's table.

**When the gate runs:**
- Every tick while he has user control and stands inside the first armed tag-2 region (activeObj order).
- The region is skipped that tick if a Confirm/Special press started a tag-3 talk.
- There is no latch: a failed gate just re-tests next tick.

**How facing moves:**
- On every MovePC call with a direction held under control, whether or not he moves: unwrap the target to within 180° of the yaw, then `yaw += 0.4·(target − yaw)`, then wrap into [−180, 180].
- The target is `atan2(−mx, −mz)` of the pressed direction after twist. Harness keys read twist.y, i.e. SetControlDirection's second argument, because `UseAbsoluteOrientation=3`.
- Walking makes 1 call per 30 Hz tick; running makes 2. Per harness frame, calls = calibrated speed per frame ÷ 30u, which is 0.5 walked and 1 run at 60 Hz.
- No press, or no control, leaves the yaw unchanged.

**What the harness must press:**
- From an unknown yaw, press the eight-way pad nearest to P′ (at most 22.5° off).
- The worst case after k calls is 180·0.6^k + 22.5° + about 1.4° of quantization:

| Calls (k) | Walked frames | Run frames | Worst error | Result |
|---|---|---|---|---|
| 3 | 6 | 3-4 | 62.8° | Passes with only 3.3° to spare |
| 4 | 8 | 4 | 47° | Passes comfortably |
| ≥6, same direction | — | — | ≤31° | Effectively certain |

- Press for at least 4 calls. Or use two bursts and score a REAL miss only after at least 6 cumulative calls in the same direction.
- Budget 30u of travel per call.

**FakeGame:**
- Keep a private `_face_deg`. In `_move_to`, turn it toward the intended step by a factor of `1 − 0.6**calls`.
- Region keys: `face: True` gates the region; `to: None` is a dead region that still shadows later ones.
- A failed gate returns without trying later regions.
- Re-test while standing only when the first containing region is gated.
- Keep publishing `dir: 0`.

## Open risks

- **The prediction is open-loop.** There is no facing telemetry. Tick jitter or a monitor that isn't 60 Hz changes calls per frame, so derive it from the calibrated speeds rather than hard-coding it.
- **The press can carry him out of the zone.** At 356 e15 he can walk out across the first edge. The tour's goal there is 222u in, so 4 calls (120u) fit. Some in-zone points have only about 2u of free travel toward P′. The code map's `poly_gap` fan check assumes free space, not sliding along a wall. The code map verified only 1-6 walked frames fit, which is shorter than 8.
- **An agent rebuild would close both gaps**: a turn-in-place verb, plus publishing `rotAngle[1]`. It auto-deploys over the live install, so it is confirm-first.
- **Region order.** FakeGame's region order is scan order, while the engine's is arm order. Recheck shadowing at any scenario other than 2600.
- **Not covered:**
  - class-3 doors that need a Confirm tap;
  - about 40 other facing-read sites;
  - polygon B for 1458 e11 and 3057 e10.
- **Game data in scratch.** `eb350.bin`, `ratan_tbl.bin` and `stock_eb.pkl` are Square Enix bytes and must never be committed.

Everything is in `C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\41f3dc78-9483-401b-b2a5-cbad59f947cb\scratchpad\facing_cross\`:
- `order350.py`
- `dali_doors.py`
- `goals.py`
- `bytes56.py`
- `overlap.py`
- `init356.py`
- `gw356.py`
- `facing_optin.py` (the pytest plugin)
- `test_facing_control.py`
- `optin_suite.txt`
- `optin_standing_all.txt`

# THE ENGINE RULE

**Facing gate on stock doors: the exact engine rule, and why `player.dir` can't supply the facing**

Everything below comes from the install's US `.eb` for field 350 and Memoria 6b8bb2d5. Nothing in the worktree was edited.

## Four findings that change the fix

1. **`state.json` `player.dir` carries no facing in a field.** The agent publishes `PosObj.rot[1]` (`HarnessAgent.cs:1170`). That is an `Int16`, zeroed in the constructor (`PosObj.cs:11,26`). Its only writers are the world-map setters (`WMActor.cs:87,101,115`) and `PosObj.copy`. Every archived field sample reads it as 0: 15,484 of 15,484 non-null `"dir"` values across `.harness-runs`. The gate reads a different value, `Actor.rotAngle[1]` (`EBin.cs:1811-1826`). FakeGame publishing `dir 0` happens to match the real agent. The driver cannot compute "faced" from `state.json` today (open question 1).
2. **The first edge lies far off the walkmesh**, 252 to 887u beyond the standable part of every gated 350 door. So the bearing is almost constant for each door, and one fixed eight-way press per door works (table in section c).
3. **The bounds are strict and the boundaries are real.** At (289,-74) at door 351, pressing up gives a gate value of exactly 208 and does not fire. Pressing down+right gives exactly 48 and does not fire either.
4. **350 has six gated regions, not four.** Entry 19 (to 354) and entry 21 (to 353, armed when the scenario counter is at least 2990) are gated too.

**Census across all 818 unique US scripts:**
- There are 1,486 `CalculateExitPosition` sites. 1,360 are followed by `ExitField` with no gate.
- 114 sites in 83 fields carry this gate. 112 use `<48 || >208`. The other 2 are in field 1460 and use `<56 || >200`.
- About 40 more region tag-2 sites read the facing in other ways: absolute windows (e.g. 602 accepts a facing between 160 and 224), or a bearing to a constant point or to an object (908, 909, 951, 1909).
- Gated fields: 51, 53-55, 101, 106, 150, 200, 202-205, 207, 350, 351, 353, 356, 455, 505, 552, 555, 556, 570, 619, 660, 707, 752, 762, 763, 900, 902, 904-907, 912, 915, 1055, 1105, 1204, 1207, 1213, 1214, 1224, 1302, 1305, 1450, 1451, 1458, 1460, 1802, 1803, 1806, 1820, 1821, 1851, 1900, 1902, 1904-1907, 1912, 1915, 2001, 2102, 2105, 2152, 2170, 2253, 2254, 2364, 2406, 2708, 2803, 2853, 2906, 2916, 2918, 3050, 3051, 3057, 3059.

## 1. The `.eb` side (field 350, entry 18, tag 2; the others are byte-identical)

```
11106  SET {B_SYSVAR[2]}                 ; usercontrol (GetSysvar.cs:17-18)
11110  JMP_IF +1 -> 11114                ; else
11113  RET
11114  Map.Bit[164] = 1
11122  CalculateExitPosition
11123  Map.Int16[6] obj(250).f[3] SYSVAR[10] obj(250).f[0] B_MINUS SYSVAR[11] obj(250).f[2] B_MINUS B_ANGLE2 B_MINUS const(255) B_AND B_LET
11149  Map.Int16[6] 48 B_LT  Map.Int16[6] 208 B_GT  B_OROR
11164  JMP_IFNOT +300 -> 11467
11467..11499  Map.Bit[162]=0 Map.Bit[163]=0 Map.Bit[165]=0 Map.Bit[164]=0 RET
```
(The kit's disassembly of the install's bytes; the raw bytes are not reproduced here -- PROVENANCE.md.)

**Opcodes and operators:**
- `0x02` JMP_IFNOT, `0x03` JMP_IF, `0x04` RET, `0x05` SET (`EBin.cs:1471-1494`).
- `0x15` B_MINUS, `0x18` B_LT, `0x19` B_GT, `0x24` B_AND, `0x28` B_OROR, `0x2C` B_LET, `0x66` B_ANGLE2, `0x78` B_OBJSPECA, `0x7A` B_SYSVAR.
- Each binary operator pops the right operand first. B_MINUS is `v0 - t3` (`EBin.cs:707`). B_ANGLE2 pops dz, then dx, then calls `angleAsm(dx, dz)` (`EBin.cs:1207-1216`).
- `obj(uid=250)` is the control character (`EventEngine.cs:950-951`).

**Every gate site in 350 (the four offsets are A4, the assignment, the compare, and the JMP_IFNOT; the arrow is where a failed gate jumps):**

| Entry | Door | Offsets | Notes |
|---|---|---|---|
| 18 | 351 | A4 11122; 11123 / 11149 / 11164 → 11467 | |
| 19 | 354 | A4 11550; 11551 / 11577 / 11592 | |
| 20 | 353 | A4 12109; 12110 / 12136 / 12151 → 12454 | Two branches come first: `Global.Byte[263]==1` goes to `RunScript(6,250,27)`, and scenario ≥ 2730 goes to `RunScript(6,250,28)`. Neither is gated. |
| 21 | 353 | A4 12548; 12549 / 12575 / 12590 | |
| 22 | 356 | A4 12978; 12979 / 13005 / 13020 → 13323 | |
| 23 | 355 | A4 13406; 13407 / 13433 / 13448 → 13751 | |

**What `CalculateExitPosition` computes** (`DoEventCode.cs:2247-2275`):
- `q0`, `q1` are the region's first two `SetRegion` points, stored X then Z (`DoEventCode.cs:938-952`).
- With `ex = q1x - q0x` and `ez = q1z - q0z`:
  - `t = [trunc(ex·(px-q0x)) + trunc(ez·(pz-q0z))] / ((ex²+ez²)>>8)`, using C# truncating division.
  - `t` is clamped to [0, 256], so the projection is onto the **segment**, not the line.
- The exit point is `((t·ex)>>8 + q0x, (t·ez)>>8 + q0z)`, written to `EventEngine.sMapJumpX/Z`, which are SYSVAR 10 and 11 (`GetSysvar.cs:39-42`).
- An edge shorter than 16u gives the exit point `q0`.
- `p` is the control character's float `pos[]`. Field 552 has a hard-coded override.

**The bearing:**
- `dx = sMapJumpX - RoundToInt(pos.x)`, `dz = sMapJumpZ - RoundToInt(pos.z)`. `f[0]` and `f[2]` go through `CastFloatToIntWithChecking` (`EBin.cs:1778,1802`), which amounts to RoundToInt.
- `angleAsm` (`EBin.cs:1583-1608`) works in 4096ths of a turn. It equals `atan2(-dx, -dz)`: 0 points toward −z, +1024 toward −x, ±2048 toward +z, −1024 toward +x. That is clockwise on a top-down plot with +x right and +z up.
- B_ANGLE2 returns `num5 >> 4`, floored to 256ths, in the range [−128, 128]. A zero delta gives 0.
- The atan table is `ratan_tbl.bin` in `resources.assets`. It matches `round(atan(i/1024)·2048/π)` in 836 of 1,025 entries; the rest are off by exactly 1/4096 of a turn. That changes the 256ths bearing in 1.3% of random directions.

**The facing:**
- `f[3] = (RoundToInt(rotAngle[1]/360·4096) >> 4) & 255`, a value from 0 to 255 in 256ths.
- It uses the same zero and handedness as the bearing, because the controller sets `rotAngle` from `atan2(-moveVec.x, -moveVec.z)` (`FieldMapActorController.cs:751`).

**The compare:**
- `v = (facing - bearing) & 255`. This is an `Int32` AND, so it wraps correctly: a facing of 250 against a bearing of 5 gives 245, which is faced (error −11).
- The door is faced if `v < 48 || v > 208`. That is `v` in [0, 47] or [209, 255], which is a signed error in **[−47, +47]**. The values 48 and 208 fail.
- In degrees, 47/256 is ±66.1°. The true continuous tolerance falls between 66.1° and 67.5° depending on sub-unit phase.

## 2. When the gate is tested

- **Every 30 Hz field tick**, and only when all of these hold:
  - The player has user control (`ProcessEvents.cs:185-187`, plus the tag's own `SYSVAR[2]` check).
  - No Confirm/Special press started a tag-3 region talk this tick (`EventCollision.cs:298-299`).
  - The region is the first object in `activeObj` order that has a tag-2 function and whose triplet fan contains his transform position (`TreadQuad.cs:6-22`).
  - The region's level is above 1 (`Request(obj,1,2)`, `EventEngine.cs:339-349`). An idle region sits at level 7 (`EventEngine.cs:1266-1271`).
- **"Armed"** means created by `InitRegion`, which appends to the list tail (`Obj.cs:33-37`), and having a tag-2 function. A first region whose tag 2 immediately returns still wins and blocks the regions after it.
- **"Reset and return"** only clears `Map.Bit[162/163/165/164]` and returns. `Map.Int16[6]` keeps its last value. There is no latch or cooldown; the region re-tests every tick while he stands inside.
- **350 at scenario 2600:** the arm order is 17, 25, 29, 28, 19, 18, 22, 23, 31, 32, 20, 27. No standable point of any gated door zone is shadowed by an earlier region.

## 3. Facing dynamics (`FieldMapActorController.cs:584-796`)

- **One `MovePC` call:** unwrap the target to within 180° of the current facing, then `rot = Lerp(rot, target, 0.4)`, then wrap into [−180, 180] (lines 747-764).
- **The target is the pressed direction:** `moveVec` after the twist rotation, before any collision or walkmesh handling.
- **Blocked presses still turn him.** The push-out revert at 786-790 restores position only. The s83 comment in `HonoInputManager.cs:946-953` confirms the actor rotates even when he doesn't translate.
- **No turn without control:** `movingX &= GetUserControl` (line 638), plus early returns at 586-589.
- **Standing keeps the facing exactly.** `ProcessNeck` restores `rotAngle` after using it.
- **Walking vs running:** running calls `MovePC` twice per tick (lines 198-204). With the default `cfg.move=1` (`FF9CFG.cs:14`), running means Cancel is not held. So walking is 1 lerp per tick and running is 2.
- **No snapping.** Harness keys give exactly 8 directions: `TryGetAxis` returns components in {−1, 0, 1}, normalised (`HarnessAgent.cs:103-121`). This install runs the analog path (Enabled=1). The keys read as keyboard (s83), so with UseAbsoluteOrientation=3 the rotation uses `twist.y = (arg2+1)/256·360` (`FieldState.cs:11-17`).
- **350 has a small twist.** `SetControlDirection(0,0)` gives 1.40625°, so pressing right yields a yaw of −88.59°.
- **Swing time:**
  - From 180° away: 108°, then 64.8°, then 38.9° after 1, 2 and 3 calls.
  - Two calls reach ±66° for a perfectly aimed press. Three calls cover any start, allowing for the up-to-22.5° eight-way offset and 2 units of quantization margin.
  - At the harness's calibrated 60 fps (WALK_SPEED 15u per frame = 30u per tick), that is a walked hold of at least 6 frames, or at least 4 frames running. Add up to 1 tick before tag 2 runs.

## 4. Conversions for the driver

| Quantity | Conversion |
|---|---|
| `player.dir` in a field | None: it is always 0. On the world map it is `ConvertFloatAngleToFixedPoint(rot1)` in 4096ths, so `(dir>>4)&255`. |
| Engine yaw (degrees) → `.eb` facing | `(round_half_even(deg·4096/360) >> 4) & 255` |
| World (dx, dz) → `.eb` bearing | `angleAsm4096(dx,dz) >> 4`, which is about `floor(atan2(-dx,-dz)·128/π)` |
| World move direction u → the yaw a press converges to | `atan2(-ux, -uz)` in degrees; the calibrated basis gives u directly |

## (a) The rule in plain words

A gated door fires on the first tick that all of these hold:
- He has user control.
- He stands inside the region's triplet fan.
- The region is the first armed tag-2 region containing him.
- His model yaw, in 256ths, is within 47/256 (strictly under 48) of the bearing from his rounded position to his projection onto the segment q0→q1, clamped at its ends.

Otherwise the region re-tests on the next tick. Each held-direction `MovePC` call turns him 40% toward the pressed eight-way direction plus the field's twist, whether or not he moves. Walking is one call per tick, running is two. Standing changes nothing.

## (b) Reference implementation

This is bit-exact apart from the atan table (`load_ratan()` reads the exact table from the user's own install at runtime). Full file: `C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\41f3dc78-9483-401b-b2a5-cbad59f947cb\scratchpad\facing_engine\facing_rule.py`. The core:

```python
RATAN = [round(math.atan(i/1024)*2048/math.pi) for i in range(1025)]
def _cdiv(a,b): q=abs(a)//abs(b); return q if (a>=0)==(b>=0) else -q
def angle_asm_fixed(dx,dz,tbl=RATAN):            # EBin.cs:1583-1608, 4096ths, == atan2(-dx,-dz)
    n1,n2=int(dx),int(dz)
    if n1==0 and n2==0: return 0
    n3,n4=n2<<10,n1<<10; T=lambda i: tbl[i]
    if n2>=0:
        if n1>=0: return -1024-T(_cdiv(n3,n1)) if n1-n2>=0 else T(_cdiv(n4,n2))-2048
        return 2048-T(-_cdiv(n4,n2)) if -n1-n2<0 else 1024+T(-_cdiv(n3,n1))
    if n1>=0: return -T(-_cdiv(n4,n2)) if n1+n2<0 else T(-_cdiv(n3,n1))-1024
    return 1024-T(_cdiv(n3,n1)) if n1-n2<0 else T(_cdiv(n4,n2))
def eb_bearing(dx,dz,tbl=RATAN): return angle_asm_fixed(dx,dz,tbl)>>4
def eb_facing(yaw_deg): return (round(yaw_deg/360.0*4096.0)>>4)&255      # banker's rounding, as Mathf.RoundToInt
def calc_exit_position(px,pz,q0,q1):                                       # DoEventCode.cs:2247-2275
    ex,ez=q1[0]-q0[0],q1[1]-q0[1]; val=(ex*ex+ez*ez)>>8
    if val: val=max(0,min(256,_cdiv(int(ex*(px-q0[0]))+int(ez*(pz-q0[1])),val)))
    return (val*ex>>8)+q0[0], (val*ez>>8)+q0[1]
def door_faced(player_x,player_z,yaw_deg,q0,q1,*,lo=48,hi=208,tbl=RATAN):
    """yaw_deg = Actor.rotAngle[1] (NOT state.json player.dir). -> (faced, signed err in 256ths)"""
    jx,jz=calc_exit_position(player_x,player_z,q0,q1)
    v=(eb_facing(yaw_deg)-eb_bearing(jx-round(player_x),jz-round(player_z),tbl))&255
    return (v<lo or v>hi), (v-256 if v>=128 else v)
def turn_step(facing_deg,pressed_deg):            # one MovePC call; None = no press
    if pressed_deg is None: return facing_deg
    m=pressed_deg
    if abs(m-facing_deg)>180: m = m-360 if m>facing_deg else m+360
    r=facing_deg+(m-facing_deg)*0.4
    while r>180: r-=360
    while r<-180: r+=360
    return r
```

`press_yaw_deg(up,down,left,right,twist_deg)` in the file gives the target yaw for a key press, using Unity's `Euler(0,t,0)` rotation. That rotation matches the kit's `movement.key_move_basis`, which was measured in-game.

## (c) Worked check (stock 350, entry 18 → 351; q0=(569,195), q1=(662,-63); real table)

**At the tour's zone target (289,-74), which is inside the fan:**
- The exit point is (622,46). The bearing is −79, stored as 177 (−111.1°), pointing along world (+333,+120).
- Hold right: yaw −88.59, facing 193, v=16. **Faced.**
- Hold up+right: v=240 (error −16). **Faced.**
- Hold up: v=**208**. Not faced.
- Hold down+right: v=**48**. Not faced.
- Hold left: error −112. Not faced.

**Arriving from 351** (he walked out of the door away from it, yaw 69°): v=128, error −128, not faced. That matches 10 of 10 unfired arrivals in session 2.

**Then pressing right while walking:**

| MovePC call | Yaw | Error (256ths) | Faced |
|---|---|---|---|
| 1 | 6.0 | +83 | no |
| 2 | −31.9 | +56 | no |
| 3 | −54.6 | +40 | yes, at walk tick 3 (about 6 frames) |

**Every standable fan point on a 4u grid, per gated door:**

| Entry → door | Distance from first edge | Bearing (256ths) | Best press | Worst error |
|---|---|---|---|---|
| 18 → 351 | 252u | 177-178 | up+right, or right | 16 |
| 19 → 354 | 557u | 68-74 | left | 9 |
| 20 → 353 | 605u | 95-96 | up+left | 2 |
| 22 → 356 | 364u | 94-95 | up+left | 3 |
| 23 → 355 | 887u | 145 | up | 16 |

For entry 19, the exit point is clamped to an end of the edge at 494 of the 1,466 points. The press names assume 350's 1.4° twist; the driver should pick presses from its calibrated basis.

**Implementation notes for the next change:**
- **FakeGame:**
  - Keep a private yaw for the player and keep publishing `dir` 0.
  - Each frame a direction is held under control, turn toward `atan2(-vx,-vz)` of the world press. Use factor `1-0.6**calls`, with calls = speed/RUN_SPEED as the frame already computes, and turn even when the move is blocked.
  - Test the regions in arm order, first fan match only, and apply `door_faced` to that one region.
  - Add an arrival yaw.
- **Walker:** the facing is unknown after any loss of control. Once a hold has lasted at least 6 calls, his yaw is the press's yaw to within 8.4°. Record `faced` and `bearing_err` from that estimate.

## (d) Open questions

1. **No facing in `state.json`.** Publishing `((Actor)po).rotAngle[1]` (and optionally `(ConvertFloatAngleToFixedPoint(yaw)>>4)&255`) next to `dir` would let the driver compute "faced" directly. That needs an engine rebuild, which is your call. Without it, the driver has to dead-reckon from its own presses.
2. **Frames to MovePC calls** (0.5 per walked frame, 1 per run frame) is inferred from WALK_SPEED at 60 fps. It depends on render rate (`FieldFPS=-1`, `FPSManager.MainLoopUpdateCount`), and I have not measured it for turning.
3. **Order within a tick** of `MovePC` and the region's tag-2 run is not traced. I assumed up to 1 tick of latency.
4. **Rounding:** `f[0]` and `f[2]` are rounded while the exit point uses the float position. That only matters within a few units of the first edge, which no standable point at 350 comes near.
5. **FakeGame's twist has the opposite sign** to the engine's (`fakegame.py:709-712` rotates counter-clockwise). This matters only if a test passes the engine's twist value; I haven't confirmed which meaning FakeGame intends.
6. **The ~40 other f[3]-reading region sites** (absolute windows, bearings to constant points or objects) need their own per-site rule. The q0→q1 rule does not cover them.
7. **The atan table** is Square Enix data and must never be committed. The math approximation differs from it by at most 1/4096 of a turn.

Files are in `C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\41f3dc78-9483-401b-b2a5-cbad59f947cb\scratchpad\facing_engine\`:
- `facing_rule.py`
- `check.py`
- `doors350.py`
- `shadow350.py`
- `dis350.py`
- `census.py`
- `census2.py`
- `census.txt`
- `eb350.bin` (game bytes)
- `ratan_tbl.bin` (game data)

# THE STOCK CENSUS

The facing gate is a whole-game door idiom, not something special to Dali. Of 1393 walk-in gateways, 122 (8.8%) check facing, in 98 of the 663 fields that have gateways. Dali's Village Road (350) has the most in one field: 6 of its 9 walk-in doors.

The harness would not let me save `REPORT.md` (subagents may not write report files), so the report is below. The scratch scripts and data are in `C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\41f3dc78-9483-401b-b2a5-cbad59f947cb\scratchpad\facing_census\`. The main files are `census.json`, `facing_gateways.csv` (every facing gate) and `idiom_all.json`. `stock_eb.pkl` holds game bytes, so never commit it. Engine citations are to `C:\gd\FFIX\Memoria\Assembly-CSharp` at commit `6b8bb2d5`.

## Answers to your questions

- **How common:** 102 gateways use the exact Dali idiom (class 2), in 81 fields across 18 locations and all four discs. Another 21 use a fixed absolute facing window (class 3). One gateway, 2253 e4, has one of each on different scenario branches.
- **Tolerance:** class 2 is always 48. All 109 gating instances are `V < 48 || V > 208`, so he fires when the error is −47..+47 units (±66.1°). 48 itself fails, so the handoff's "±48 (±67.5°)" is the exclusive bound. A tolerance of 56 appears only on two regions that don't warp (1460 e11 @8039/8065, 3059 e12 @4859/4885, Black Mage Village events that open a path).
- **Facing away:** no gate anywhere asks for it. All 241 facing gates must be TRUE to pass, every window is centred on "toward", and no let adds 128.
- **Reference edge:** always q0→q1 of the region's live polygon, in SetRegion argument order. The engine hardcodes `((Quad)gCur).q[0]` and `.q[1]` (`DoEventCode.cs:2252-2253`), and SetRegion stores vertices in argument order with no reordering (`:938-952`).
  - All 109 gating lets sit in the region's own tag 2, after a CalculateExitPosition (0xA4) in the same function.
  - The kit's `zone[0]`/`zone[1]` match that edge for 100 of the 102 class-2 regions.
  - The two exceptions are 1458 e11 and 3057 e10 (Mage Village/Water Mill → Entrance). Their tag 0 picks one of two polygons by arrival entrance (`Global.Int16[2]` ∈ {5,2}, or ==5 for 3057): A @15856, else B @15878.
  - Tag 2 makes the same test. Arrivals by those entrances take an ungated exit branch; everyone else takes the gated branch (1458: 16127/16153/16168; 3057: 10691/10717/10732). So the gate only applies when polygon B is live.
  - B's first edge is (2162,−1774)→(2008,−1627). `scan_gateways` takes A: (2049,−1842)→(1988,−1641). The kit's edge is wrong exactly when the gate is live.
  - In 97 of 102 regions q0→q1 is also the dead-end door threshold. In 5 it is not (356 e15, 619 e7, 2170 e7, 1458 e11, 3057 e10), so use the stored edge, never "the wall edge".

## How I matched, and the false-negative guards

- **Corpus:** all 818 ids in `extract.ID_TO_EVT`, read through `extract.EventBundle` (US) and decoded with `eb.EbScript` and `disasm.instr_expr_tokens`. There were 0 decode failures.
  - 2104 entries call SetRegion, in 686 fields; none has a computed polygon.
- **Gateway:** a region whose tag 2 reaches `Field` (0x2B) or `WorldMap` (0xB6), directly or through a chain of `RunScript*` (0x10/0x12/0x14) and `RunSharedScript` (0x43) calls.
  - Uids resolve through `eventscan.resolve_uid`. Party uids 251-254 resolve to every player-character entry, which leaves 0 unresolved calls in any tag 2.
- **Gate:** for each function I built a control-flow graph. A branch edge counts as a gate if removing it makes the warp unreachable, and that also fixes which way the test must go. This is chained through every call site on the way to the warp, so a check inside a called function still counts.
- **Direction reads:** player facing (`B_OBJSPECA` field 3, `EBin.cs:1811-1826`), the angle operators `B_ANGLE`/`B_ANGLEA`/`B_ANGLE2` (`EBin.cs:1207-1216`), system variables 4 and 10/11 (`GetSysvar.cs:39-42`), and pad keys. Any variable assigned from one of these carries the taint forward.
- **Class 2 match:** CalculateExitPosition, then the 13-token let `V = obj250.f3, sys10, obj250.f0, −, sys11, obj250.f2, −, B_ANGLE2, −, 255, &, LET`. The accepted window is computed by evaluating the condition for all 256 values, not by string matching.
- **Guards:**
  1. I listed every facing or angle condition in all 818 scripts. Of the 319 outside any region's reach, only 2364 e6 gates a warp: a scripted door, the idiom in tag 24, run from e7 tag 22. The others test an object's own facing (1060 e25, 2711).
  2. Of 1486 CalculateExitPosition calls, only 2 are outside region reach (356 e9 tag 21, 2364 e6 tag 24).
  3. All 158 facing-minus-bearing lets were enumerated; the 111 inside gateways all gate a warp.
  4. Inside every gateway, every player-facing condition gates a warp (the one exception is menu field 2950).
  5. `scan_gateway_entries` misses 136 gateways whose warp sits in a called function or is a world-map exit. 19 of those are facing-gated.
  6. The 4 object-contact warps (105 e7, 350 e34→358, 2951 e13, 2952 e9) have no facing gate.

## Counts by class

Of 1394 walk-in region gateways in 664 fields, 1 only leads to menu fields (2955 e24), leaving 1393 in 663 fields, with 2757 warp sites. 57 of these only exit to the world map.

| Class | Gateways | Fields |
|---|---|---|
| 1: no facing check | 1271 | 640 |
| 2: Dali idiom only | 101 | 80 |
| 2 and 3 (2253 e4) | 1 | 1 |
| 3: another form only | 20 | 18 |
| **Facing-gated total** | **122 (8.8%)** | **98 (14.8%)** |

- 1247 of the class-1 gateways still run CalculateExitPosition for the exit walk; they just never compare facing.
- Of the 122, 112 gate every warp site and 10 gate only one branch: 203 e4, 619 e7, 912 e10, 1214 e6, 1450 e8, 1458 e11, 1806 e6, 1912 e11, 3050 e8, 3057 e10.
- By warp site: 230 of 2757 (8.3%).
- Confirm-button doors in tag 3 (where tag 2 doesn't warp): 81 in 63 fields; 73 are class 1 and 8 are class 3.
- All walk-in and Confirm gateways together: 130 of 1474 (8.8%), in 104 of 671 fields.

Class 2 by location (idiom gateways / all walk-in gateways there):

| Location | Class 2 / all |
|---|---|
| Treno | 20/70 |
| A. Castle | 19/146 |
| Mage Village | 15/44 |
| Prima Vista | 12/24 |
| Dali | 9/36 |
| Lindblum | 8/107 |
| Burmecia | 5/38 |
| Memoria | 4/37 |
| Alexandria | 3/92 |
| L. Castle | 3/91 |
| Cleyra | 3/100 |
| Oeilvert | 2/25 |

Mountain, Cargo Ship, Marsh, Gizamaluke, Pandemonium and Daguerreo have 1 each. Most are doors into buildings in towns.

## The variants, with examples (field, entry, .eb offsets let / cond / jump)

**Class 2 — the Dali idiom.** The bytes are identical everywhere; V is always `Map.Int16[6]`.
- Dali 350: e18→351 11123/11149/11164, e19→354 11551/11577/11592, e20→353 12110/12136/12151, e21→353 12549/12575/12590, e22→356 12979/13005/13020, e23→355 13407/13433/13448. Also 351 e18→352 @17129, 353 e15→356 @6741, 356 e15→358 @7897.
- Elsewhere: 51 e11→53 4119/4145/4160 (Prima Vista), 101 e17→112 7755/7781/7796 (Alexandria), 900 e9→912 8579/8605/8620 (Treno), 2906 e9→2905 6527/6553/6568 (Memoria).
- The same idiom guards two world-map exits: 707 e7 @4591 and 2152 e5 @1856.
- The full list of 102 is in `facing_gateways.csv`.

**Class 3a — fixed facing window in tag 2 (21 gateways).** The form is `obj250.f3 LO > obj250.f3 HI < &&`.

| Window (facing units) | Gateways (cond/jump offsets) |
|---|---|
| [16..112] | 551 e13 13988/14005, 1301 e9, 2101 e8 |
| [17..111] | 563 e15 17650/17667, 572 e15, 1310 e11, 2110 e8 |
| [1..127] | 610 e7 6541/6558, 1360 e4, 2160 e6 |
| [154..248] | 601 e5 7046/7063 |
| [161..223] | 602 e14 12026/12043, 603 e6, 2152 e12, 2153 e6 |
| [33..95] | 603 e7 3934/3951, 1353 e6, 2153 e7 |
| [140..202] | 605 e6 2646/2663, 2155 e4 |
| [80..144] | 2253 e4 2616/2633 (Oeilvert, the scenario==9740 branch) |

These are Lindblum air-cab stations and L. Castle lifts and gates. All except 2253 e4 are interaction doors, not walk-in:
- the facing window passes, `Bubble(0)` shows the "!" icon, and Confirm or Special must be pressed that frame (`B_KEYON` 0x20000/0x80000);
- then 19 of the 21 show a choice window (sys9, `ETb.GetChoose`);
- 601 e5 is detected by a circle, not its polygon (`EventEngineUtils.cs:1722-1738`).

**Class 3b — tag-3 Confirm doors (8 gateways):**
- Fixed windows: 603 e3 [80..174] @2087, 2103 e8 [160..222] @2790, 2114 e10 [64..128] @13866, 2151 e3 [154..248], 2153 e3 [80..174], 2552 e5 [64..153] @2974.
- Bearing to object 6 within ±55 units (±77.3°): 553 e9 4182/4210/4225 and 1303 e9 3458/3486/3501 (Lindblum Inn).
- The engine duplicates some of these checks through `QuadTalkableData` (`EventCollision.cs:461-507`, `EventEngineUtils.cs:1687-1715`).

**Found only on regions that don't warp:**
- The idiom at 56: 1460 e11, 3059 e12.
- The idiom at 48 on event regions: 2853 e6/e7.
- Bearing to a fixed point: 908 e15, 951 e7, 1908 e13.
- Bearing-to-object checks on talk and Special-button quads: 34.

**Not found on any door:** a pad-direction check, a bearing to the region centre, any edge other than q0→q1, or facing away.

## What a walker must do

These preconditions apply to every class:
- He has user control: the engine only calls `CollisionRequest` then (`ProcessEvents.cs:185-187`), and 1391 of the 1393 tag-2 functions also open with a user-control check.
- His position is inside the live polygon's fan of vertex triplets (`TreadQuad.cs:24-39`).
- It is the first active region with a tag 2 that contains him (`TreadQuad.cs:12-19`).
- He is not pressing Confirm inside a tag-3 region that frame (`EventCollision.cs:298-299`).
- The door's other gates hold (next section).
- Engine hardcodes: tag 2 never fires for field 2802 region 24 or field 2914 region 13, and field 2108 region 6 needs facing (`EventCollision.cs:382-412`).

The facing byte is f = (round(rotY·4096/360) >> 4) & 255. Direction convention: 0 = −z, 64 = −x, 128 = +z, 192 = +x (`FieldMapActorController.cs:751`, `angleAsm` at `EBin.cs:1583`).

**Class 2:**
- Let P′ be his position projected onto the live q0→q1 (the parameter t is clamped to 0..256, so near the ends he aims at the endpoint), and B the bearing from him to P′.
- He fires when (f − B) mod 256 is within −47..+47.
- **Press toward P′ for at least 2 frames while inside.**
  - Facing turns 40% of the way toward the pressed direction each frame (`FieldMapActorController.cs:749-765`), even when a wall blocks the step.
  - From any start the error after 2 frames is at most 0.36 × 128 = 46, which passes.
  - Standing still never turns him.
- Keep holds to 2-4 frames: in the 5 regions where the ground continues past q0→q1, a long press walks him out of the zone.
- If he stands exactly on the edge line, B = 0 and he must face −z.
- The better fix is to make the final approach arrive heading within ±66° of the bearing to P′.
- For 1458 e11 and 3057 e10, use polygon B, not the kit's zone.

**Class 3a:**
- Stand inside with f in the window. Facing the q0→q1 projection lands in the window at 90-100% of standable points for all 21.
- Tap Confirm (it must be pressed that frame; 20 of 21 need it, 2253 e4 is walk-in).
- Then answer the choice where there is one (19 of 21).

**Class 3b:**
- Face the window, or object 6 within ±55. For 2103 e8 the q0→q1 rule lands in the window 0% of the time, so use its own window [160..222].
- Then tap Confirm; most then show a choice window.

## Other gates on the same tag 2 (class 4)

| Gate | Gateways (≥1 site / every site) |
|---|---|
| User-control check | 1391 / 1391 (missing only on 2753 e14 and e16) |
| Scenario counter ranges | 132 / 132 (e.g. 350 e20 needs scenario < 2730) |
| Player height | 92 / 90, plus position in 10 |
| Arrival entrance | 73 / 12 (picks the branch or the polygon) |
| Map variables | 55 / 55 |
| Choice window (sys9) | 27 / 24 |
| Story flags | 22 / 18 |
| Instance variables | 13 / 11 |
| Confirm/Special pressed | 22, plus 1 "not pressed" (2719 e7) |

## Implications for the fix

- **Harness rule:** when he stands in a zone and nothing fires, press toward the q0→q1 projection for 2-4 frames. That covers all of class 2. It also covers class 3, except the Confirm tap and choice those doors need, and 2103 e8's window.
- Record the facing error from `player.dir`.
- A class-3 door that stays shut while he faces it needs a Confirm tap; it is not a miss.
- `FakeGame._enter_regions` needs the first-armed-region rule plus a per-door gate class. Either feed it this census's (field, entry) classes or reuse the 13-token let match at load.
- `eventscan` should pick the polygon by arrival entrance for regions with more than one SetRegion (1458 e11, 3057 e10).

Files are in `C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\41f3dc78-9483-401b-b2a5-cbad59f947cb\scratchpad\facing_census\`:
- census.py
- classify.py
- facing_gateways.csv
- census.json
- idiom_all.json
- stock_eb.pkl

# THE HARNESS CODE MAP

The facing fix is mapped below, but one premise in the brief is wrong: `player.dir` does not report facing on a field. It is always 0 there, so it cannot confirm that he faced the door. Without an engine change, `faced` can only be a prediction. Nothing in the worktree was edited (git status is clean). The two baselines pass: **494 passed** (227.6 s) and **rung3_dryrun 80/80**.

## Three findings to read first

**A. `player.dir` reads 0 on every field.**
- The agent publishes `PosObj.rot[1]` (HarnessAgent.cs:1170). On a field nothing writes `rot[]`. Its only writers are the world-map actor (WMActor.cs:87/101/115) and `PosObj.copy` (PosObj.cs:45).
- Field facing actually lives in `PosObj.rotAngle` (PosObj.cs:165), in degrees. It is written at FieldMapActorController.cs:764, and it is what the `.eb` gate reads (EBin.cs:1811-1823, `gMode==1` → `rotAngle[1]`, converted to a 0-255 angle).
- The archived runs confirm it: 15,327 field-screen samples across 27 fields, 1,310 of them taken while he was moving, and `dir` is 0 in every one (−1 when there is no player). Script: `scratchpad\facing_codemap\dircensus.py`.
- A measured facing needs a new engine patch that publishes `rotAngle[1]`. Otherwise the fix works open-loop from the known turn rule.

**B. Why 350 → 351 missed 10 of 10.**
- The arrival from 351 is (258,−58), 18u outside the door zone. The door goal (289,−74) is 35u away.
- So the whole walk is the zone "finish": a walked press of 1-2 frames. `_plan_hold` sizes it at session.py:2363 and 2388.
- He starts facing back the way he came in. After 2 turning frames the leftover error can be 64.8°, plus the pad's 21.2° from the needed bearing. That is past the ±67.5° gate.
- `_walk_leg` then returns "arrived" (session.py:2526-2527) and nothing else is pressed. route_cross then waits the full 20 s timeout (4437-4439).
- The same applies to a retry that starts inside the zone: no press at all. This is dali_tour.py:539-540's "travelled 0 and missed".
- The diagnosis's line numbers are stale after 3641b126: the in-zone return is now 2526-2527, not 2462-2463.

**C. A default gate in FakeGame breaks 21 of test_harness.py's 366 tests, so the gate must be opt-in per region.** Method: I monkeypatched a gate onto every region with a scratch pytest plugin (details in section 4). One of the breaks is useful: `test_a_smooth_walk_on_stock_dali_never_enters_a_region_it_was_not_sent_to[350]` fails on place 0, which is the 351 door. That is the in-game miss reproduced offline, from real zones.

## Engine rule (verified)

- **Projection:** `CalculateExitPosition` (DoEventCode.cs:2247-2270) computes `t = clamp(int(qx·(px−q0x) + qz·(pz−q0z)) / ((qx²+qz²)>>8), 0, 256)` and `P = q0 + (t·q)>>8`. The result lands in system variables 10/11 (GetSysvar.cs:40/42).
- **The check in 350's script** (disassembly offsets 11123/11149/11164): `d = (facing − ANGLE2(Px−x, Pz−z)) & 255`; the door fires only if `d < 48 || d > 208`.
- **Angle convention:** ANGLE2 → `angleAsm` (EBin.cs:1207-1216, 1583) uses the same convention as the move angle, `atan2(−dx, −dz)` (FieldMapActorController.cs:751). So the harness bearing is `degrees(atan2(−dx, −dz))`, and facing θ points along (−sin θ, −cos θ).
- **Turning:** only while a direction is held with control (:638-641, :749). Each moving frame lerps 40% toward the pressed direction (:759-764). This happens before the wall/body collision, so pressing into a wall still turns him.
- **Region firing:** every tick under control, moving or standing (ProcessEvents.cs:183-188 → EventCollision.cs:296-303). CheckQuadPush is always true on 350. `TreadQuad` returns only the FIRST region containing him (TreadQuad.cs:12-19).

## 1. Where the "turn to face the door" step goes

**Recommended site: the end of `route_to`**, between session.py:3023 (`st = self.state`) and 3026 (`record["reached"]`).
- Run it only when: a zone was given, the walk ended normally (not "boxed"/"outside", not stalled), he is still on the field with control, and he stands inside the zone.
- Only there are all the inputs in hand:
  - the calibrated basis, `self._axes[origin]` (set at 2843-2846)
  - `spread` (2853)
  - `polys`, the other zones to keep out of (2825)
  - `watch`, the published objects (2839-2841)
  - `wmesh`, `origin` and `record`
- If he loses control during the step, reuse the walk's own landing code (2943-2949: `_npc_fired`, `_npc_tally`, `_await_landing`) with `during="face"`. route_cross's `pending` (4419) is then False, and its `inside` calculation (4420-4424) runs unchanged after the step.
- **Limitation:** route_cross passes the zone to route_to only when `smooth` is on (4416). The chunked `route_cross(zone=…)` path would need the same step at route_cross 4424-4437, with its context rebuilt. The tour always uses `smooth=True` (dali_tour.py:393-395).

**Steps in the helper:**
1. Wait a few frames: `wait_frames(n)` then re-check control. This follows the `ROUTE_OUTSIDE_WAIT` pattern at 4425-4436, which uses `wait_for` (956-1022; its timeout message contains "live samples").
2. Compute P, the engine's integer projection onto `zone[0]→zone[1]`, and the unit direction u from him to P.
3. Pick the pad: `max(_eight_way(basis), key=dot with u)` (6437-6450). It is at most 22.5° off by construction. On stock Dali it is 1.2-22.4° off.
4. Use **4 walked frames**. The movement reaches `(4 + PROBE_TAIL_FRAMES) × WALK_SPEED = 90u` (1415, 1136).
   - The worst leftover turn after 4 frames is 180°·0.6⁴ = 23.3°. Adding the pad error (≤22.4°) and the heading spread (≥2°) gives about 48° worst case, under 67.5°.
   - With 3 frames it is about 63°, which is too tight.
5. **Keep inside the zone:** check that every end of the press fan is inside the zone: `poly_gap < 0` at `_turn(u, ±spread)·reach`. Stock gateway zones are convex (1436-1437), so the whole fan is then inside. On every Dali door, all lengths from 1 to 6 frames fit from `region_goal` (`scratchpad\facing_codemap\pad350.py`).
6. **Keep clear of other zones and objects:** `_probe_is_clear(here, u, reach, polys, spread, discs=watch["discs"])` (1422-1473). Use `_walkers_let_press` (2422-2441) with a leg dict carrying `watch` and `spread`.
7. **Send:** the same code `_walk_leg` uses at 2586-2591: `steps = [f"hold {b} {n}" for b in buttons]`, insert `"hold cancel {n}"` first to walk, `send(*steps, f"wait {n+4}")`, then `settle()` (1317) and the control/field check (2592-2594).

**Record keys:**
- `faced`: None (no step taken), True (a 4-frame pad press toward P was sent), False (no press was clear).
- `face_err`: the predicted angle between pad and bearing plus the leftover-turn bound. It becomes a measurement only if the engine publishes facing.
- `face_to`: P.
- `face_frames`: frames pressed.

## 2. "Arrive heading at the door" instead

The last hold's direction comes from `_plan_hold`. It takes the two pads either side of the bearing to the target (2361-2362) and picks the one that gains most ground (2395-2397). The target is the goal (2532), or during the finish the nearest standable spot (`_finish_target`/`_zone_foothold`, 2533-2534, 2289-2295, 2270-2287). `leg["pressed"]` stores that last hold (2587).

To arrive heading at the door, `route_to` could add an approach waypoint A = goal − u·D at the waypoint list (2917), or in `_route_legs` (2215-2239).

It is not enough on its own:
- The finish presses are 1-2 walk frames long. That is exactly case B.
- The foothold's direction is set by geometry: 353's door is standable only in a 34u wedge by its corner.
- Waits for walkers, steps round them, pushes and replans all replace the last hold.
- A cannot always stand on the floor clear of other zones. 351's door is 18u from the arrival spot.
- A walk that starts inside the zone presses nothing at all.

The facing step is the guarantee; arriving heading is an optional improvement.

## 3. Every reader of the route records

| Where | Keys read |
|---|---|
| route_cross (4417-4449) | `from`, `landed`, `waypoints`, `during`; writes `inside`, `changed_to` |
| dali_tour `_cross` (396-409) | copies an explicit list: landed, changed_to, reached, inside, travelled, during, replans, route, waits, cleared, pushes, pushed, blockers, remembered, blocked, frozen, boxed, boxed_by, npcs, avoided, triggers, through, sealed, npc_replans, npc_waits, box_waits, box_cleared, boxers, held_by, pinned (plus `error`). **`faced`/`face_err` must be added here or they never reach the log.** |
| dali_tour `failure()` (150-166) | landed, blocked, sealed, route, boxed, npc_waits, boxed_by, **inside (line 158)**, error, during, held_by, reached, waits, pushes, blockers, frozen, npc_replans, box_waits. `faced` is read at 158-159: faced True stays a REAL "miss"; faced False needs a class decided. |
| dali_tour `run` (490-508) and `replay` (595-621) | `failure(rec)`; replay also reads `reached` (606) |
| `entered_field` (173-185) | error, landed, from, changed_to |
| rung3_trace.py (390, 694-702, 773, 1105) | only `D.entered_walk` keys (k, leg, place, exit, entered…) |
| rung3_step1.py | calls `_tour.run` (167) only |
| rung3_dryrun.py | synthetic records (262-267) |

rung3_trace and rung3_step1 never call route_cross themselves; they go through `Tour`. Tests that assert on these keys:
- `inside`: test_harness.py:3274, 3280, 3282, 5123, 5154, 5177
- held_by / pinned / boxed: 5076-5078, 5101-5104, 5123-5127, 5154-5158
- `failure()`: 5127, 5158, 5179, and 5188-5198
- replay verdicts: 5438-5620

## 4. FakeGame changes so a facing test can fail

**Census method:** a scratch pytest plugin (`scratchpad\facing_codemap\facinggate_plugin.py`) monkeypatched FakeGame so every region got the gate. Nothing in the worktree was edited.

**What the fake does now:**
- `_facing` snaps instantly to the step direction, including coast frames (fakegame.py:746-748). `_fire_contacts` uses it for talk triggers (923). Keep it as it is for talk.
- `_enter_regions` (969-984) fires the first region containing his centre, with no gate. It only runs after a step (704, 736). Standing still with nothing pressed returns first (696-700).

**Changes:**
1. **Region keys.** The documentation at 249-256 lists `zone`, `to`, `arrive`. Add opt-in:
   - `"face": True`: gate on `zone[0]→zone[1]`, ±48 of 256.
   - `"to": None`: a dead region that still counts as the first region but never fires.
   - `"arrive_face"`: the facing set on arrival, applied in `_step_exit_now` (986-993).
2. **Facing model.** Add `self._face_deg` beside `_facing` (296), settable by tests. Lerp it 40% toward `atan2(−vx, −vz)` only on pressed frames, after twist (after 707-712). Do not turn on coast frames (701-706), frozen frames (684-686) or without control.
3. **Gate.** In `_enter_regions`: find the first region containing him. If it has `"face"`, compute P with the integer projection and the byte check. If the check fails, return; do not try later regions. The test subclass `_StoryFake._enter_regions` (test_harness.py:5381-5391) calls `super()`, so the gate composes with it.
4. **Re-test while standing,** but only for gated regions: move the check into `_step_world` beside `_fire_contacts` (679-680).
5. **`_rect` pitfall:** `_rect` (test_harness.py:2785) always makes `q0→q1` the south (z0) edge. A gated east-wall door must list its door edge first, e.g. `[[600,-40],[600,40],[480,40],[480,-40]]` rather than `_DOOR` (5009).

**Tests that break with a default gate.** With the engine's turn model, 18 fail; with the fake's instant facing, 21 (a superset):
- 2935 walk_to_halts
- 2801 route_to_goes_round (both parameters)
- 3513 smooth_walk_dali[350]
- 2822 route_cross_from_an_arrival[False]
- 3394 smooth_hold_heading_error (3.0 and 6.3)
- 5064 walker_pins_door_step
- the replay/tour tests at 5438, 5455, 5475, 5508, 5531, 5547, 5567, 5589, and 5608 (on-tour, on-replay)
- instant-facing model only: 2851 probe_that_fires_a_gateway, 5488 replay_step_only_missed, 5608 [into him-replay]

**Tests to model new ones on:**
- 3547 (real 350 door, `_dali_fake` 3494-3509)
- 3512 (the offline 351-door reproduction, once gated)
- 3252 (`inside` semantics and the recorded waits)
- 5161 and 5182 (`failure()` classes)
- the door helpers at 5032-5055
- 3571 and 3792 (tests of the fake itself)

## 5. State and FakeGame publish

- **channel.py:** add `player_face` after `control` (280-283). It returns `raw["player"]["face"]`, or None when absent, like `player.listener` (additive, same protocol, 55-56).
- Expose `dir` only under a name that says it is dead, following the tri/floor precedent (324-366). Extend the bare-key guard `_BARE_TRI_READ` (test_harness.py:232, test at 248-259) to cover `dir`. The model test for State is 202.
- **FakeGame `_publish` (1170-1171):** keep `"dir": 0`, since that is what the real engine sends. Add `"face": self._face_deg` only when a new `publishes_face` flag is set.
- **Engine patch (only if you want a measured facing):** at HarnessAgent.cs:1170, publish `po.rotAngle[1]`, optionally with the byte `(ConvertFloatAngleToFixedPoint(...)>>4)&255` (EventEngineUtils.cs:1811). The DLL build auto-deploys over the live install, so treat it as a separate, confirm-first step.

## 6. Commands and frozen files

- Tests: `cd …\story-trace-walk\ff9mapkit && py -m pytest -q -p no:cacheprovider -n 6 tests/test_harness.py tests/test_route_avoiding.py tests/test_storytrace.py` → **494 passed**.
- Dry run: `cd …\story-trace-walk && py studies/story-trace/rung3_dryrun.py` → "base passes every check (v1 and v2): True; mutants and cases as registered: 80/80". The P-FROZEN check passes on `220532a8`.
- Frozen, never edit (`.gitattributes:22 -text`):
  - `rung3_predictions.json` sha256 `220532a859558b429aa83910749097c6984510b5435d3a75d1bfd0d5a8a35664`
  - `rung3_predictions_v2.json` sha256 `d6dd541c995a296fa449ad00681bf7c419059daeed9e66b3f36b272416b362f4`

Everything is in `C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\41f3dc78-9483-401b-b2a5-cbad59f947cb\scratchpad\facing_codemap\`:
- `dircensus.py`
- `facinggate_plugin.py`
- `geo350.py`
- `pad350.py`
- `pytest_baseline.txt`
- `dryrun_baseline.txt`
- `gate_lerp.txt`
- `gate_snap.txt`

# THE SMALLER FINDINGS

**(A)** `_zone_quad` is wrong for 5 to 8 point regions. The fix is a new key; keeping every vertex in `zone` would do harm. **(B)** needs no behaviour change, only (C) and a corrected docstring. **(C)** is a one-line rename that cannot change any frozen prediction or the dry run. Nothing in the worktree was edited.

## (A) Region membership and `_zone_quad`

**How the engine tests membership.** Engine refs are under `Assembly-CSharp/Global/`.
- `TreadQuad.cs:24-39` tests n triangles `(q[i], q[i+1 mod n], q[i+2 mod n])` for i = 0..n-1, wrapping round. It is not a fan from q0.
- The triangle test is XZ-only, barycentric, border-inclusive (`u+v <= 1.000001`, `Math3D.cs:41-42, 46-58`). A triangle with a repeated or collinear vertex divides by zero, gives NaN, and contains nothing.
- For a convex region:
  - 3 points: the triangle.
  - 4 points: the whole quad.
  - 5 or more points: the polygon minus the inner n-gon bounded by the diagonals (i, i+2). That inner n-gon is the dead zone.
- The kit's doubled trailing vertex `[a,b,c,d,d]` gives triangles abc, bcd and dab plus two empty ones, which is exactly the quad. It is harmless and unnecessary: 4 points already cover the quad.
- **Stock never doubles a vertex (0 of 2110).** The comment at `eventscan.py:91` saying "(kit + real)" is wrong about "real".
- Other engine details a membership helper would need:
  - `SetRegion` stores n points, at most 8 (`DoEventCode.cs:938-957`, `Quad.cs:40`).
  - `DoEventCode.cs:948` rewrites Z -257 to -157 in fields 1608 and 1707. That hits gateways 1608 entry 6 and 1707 entry 3.
  - `IsInQuadHotFix` (`TreadQuad.cs:41-54`, table at `EventEngineUtils.cs:1722-1738`) swaps 14 stock regions for circles. One of them is gateway 2222 entry 4. The table is keyed on the raw `fldMapNo`, so a fork id misses it.

**Census** (US install, all 818 field scripts; script `facing_side\census2.py`):

| Measure | Count |
|---|---|
| Static `SetRegion`s | 2110, all convex, no duplicate points, none computed |
| By point count | 3: 46 · 4: 1797 · 5: 212 · 6: 39 · 7: 12 · 8: 4 |
| Gateway entries | 1345 (1477 `scan_gateways` rows) |
| Gateway entries with 5–8 points | 149, in 105 of the 650 fields with gateways (158 of the 1477 rows) |
| …with standable dead-zone points inside the kit quad | 119, in 94 fields (8u grid, `PlayerWalkmesh`, at least 80u off walls) |
| …with standable live area outside the kit quad | 131 |
| `region_goal(kit quad)` lands outside the engine's area | 8: 1253 e11, 2207 e4/e5, 2211 e11, 2222 e4 (circle applies), 2714 e14/e16, 2800 e24. None in Dali. |

For the task's second question: `zone[0]` and `zone[1]` are the engine's q0 and q1 for every stock gateway, so the facing spec can use them as planned.

**Dali, per exit** (standable points in the quad but not the engine's area / in the engine's area but not the quad):

| Room, entry, exit | Dead zone in quad | Live area outside quad |
|---|---|---|
| 350 entries 18–23 | 0 | 19, 20, 1, 1, 43, 7 |
| 351 e16 → 350 | 584 | 13 |
| 351 e18 → 352 | 0 | 219 |
| 352 e14 → 351 | 525 | 252 |
| 353 e14 → 350 | 892 | 1163 |
| 353 e15 → 356 | 0 | 10 |
| 354 e10 → 350 | 471 | 164 |
| 356 e8 → 350 | 1464 | 341 |
| 356 e9 → 353 | 626 | 91 |
| 356 e15 → 358 | 0 | 15 |
| 358 e10 → 356 | 612 | 521 |

- The 350 doors are the diagnosis's "quad inside the fan" case, and the 1464/626 figures for 356 reproduce exactly.
- The live area also reaches past the quad plus the 56u keep-out margin in several rooms (standable 4u points beyond it): 353 → 350: 2073, 358 → 356: 658, 351 → 352: 387, 352 → 351: 192, 354 → 350: 139, 356 → 350: 21, 350 → 356: 3. So the tour's keep-outs don't cover the whole live area.
- Both effects are latent: no crossing in sessions 2 or 3 landed anywhere but its target.

**If `zone` kept every vertex, it would break things:**
- `test_eventscan.py:33` (`len in (3,4)`) and `:129` (`== 4`) fail, because stock 100 entry 17 has 5 points.
- Import output changes for 158 gateway rows. The 23 rows with 6–8 points emit zones that fail build validation (`build.py:1510-1511`, "4 or 5 points"). 16 of 96 ladders and jumps change shape, and jumps are capped at 3–5 points (`build.py:1815`).
- Decisively: `region_goal` over the full polygon lands in the dead zone for 51 gateway entries, including 5 Dali exits: 351 → 350, 352 → 351, 354 → 350, 356 → 350, 356 → 353. The tour would then miss those doors every time.

**If a separate key is added instead** (e.g. `region` = the raw points in engine order, plus one engine-exact membership function):
- No existing consumer changes. Every one reads by name: `extract.py:547-621, 979`, `cli.py:2403-2410`, `campaign.py:209-221`, `forkreport.py:671`, `logic_map.py:314`, `dali_tour.py:264-270` (builds 3-tuples), `rung3_dryrun.py:738`.
- No test compares whole dicts, nothing serialises them, and no golden changes.
- The real work is wiring it in:
  - the harness's membership checks at `session.py` 2254, 2526, 2619-2620, 2646, 2662, 3028, 3734, 4423;
  - `goal_for`, restricted to the engine's area;
  - `avoid_for`, which should use the full convex polygon because it contains the engine's area;
  - `fakegame.py:976` and `:1770`.

**Recommendation:** add the key and the membership function together with the facing-gate fix, because that fix already has to rewrite `FakeGame._enter_regions` (tested on hand-built pentagons). Defer rewiring `session.py` and `dali_tour`. None of the 116 misses trace to this, the 350 doors have no standable dead zone, and the facing fix's press toward q0→q1 should carry him out of a dead zone into a live triangle. Also correct the comments at `eventscan.py:91`, `pathfind.py:101` (true only of the truncated zones) and the "fan" wording in `content/gateway.py:9-11`.

## (B) 350 → 358 at scenario 2600

The recorded story traces settle it. In all 19 runs of sessions 2 and 3, object 34's tag 2 fired. Its writes are at .eb 24364: Bit 2055, 2051 and 2103, global byte 13, then entrance := 21 and `Field(358)` at 24570. Region 25 wrote nothing.

- Region 25 is armed at 2600 (Main_Init `841 → 861 InitRegion(25)` whenever the scenario isn't 2650). But both its tags return unless the scenario is in [2650, 2710) (.eb 13922 and 14032), so it can never fire at 2600.
- Object 34 is armed only while Bit 2055 is 0 and the scenario is below 2640 (Main_Init 779-807). After it fires once, the next load of 350 arms the children 4, 6 and 8 instead of 34, 12 and 13 (810-816). So it is a one-shot trigger, and the second attempt at exit 5 always misses.
- The docstring at `rung3_step1.py:37` ("the story shut the region") is imprecise. What the scene shuts is object 34, not region 25.

**Minimal correct change:** no change in behaviour. Apply (C), so attempt 1 reads "bounce", and correct that docstring. Any real change in when or whether object 34 fires would change which story keys each run writes and which children are walking about, which the frozen checks read in a new session. Exit indices are also part of the frozen walk format (`[place, exit index, entered place]`), so exits may only ever be appended, never removed or reordered.

None of this can affect the dry run, which reads recorded logs, never runs `failure()`, and whose `fixture_walk` still resolves 350 → 358 to exit 5. If this is taken further later, mark exit 5 as inert at the beat with no strike, after a census of the scenario-window guard idiom.

## (C) The 353 bounce labelled "miss"

At `dali_tour.py:150`, change `if rec.get("landed") is not None:` to:

```python
if rec.get("landed") is not None or entered_field(rec) is not None:
```

- **Unchanged:** strikes still go to the same tally with the same cap of 2, and `later` and `dead` are unchanged.
- **Changed:** the verdict text, and a bounce no longer takes a screenshot (`:507`).
- **Replay:** unaffected, because `failure()` only runs there when nothing was entered.
- **Analysis and frozen predictions:** no effect. The analysis reads only entered walks, crossing counts and the "replayed" verdict (`rung3_trace.py:499`). The v2 predictions already call it "the 353 bounce".
- **Dry run:** stays 80/80. The literal `"miss 1/2"` at `rung3_dryrun.py:278` becomes cosmetically stale.
- **Tests:** `test_harness.py:5198` still returns "miss", because its error text lacks "reached field N". Add an assertion that uses the real error string.
- **Archived runs:** 43 of session 2's 73 "miss" verdicts and 26 of session 3's 52 are these bounces (353: 33 and 20; 358: 10 and 6). The archived logs keep "miss".
- **Docstring:** `rung3_step1.py:35-37` names this case a MISS deliberately, so update it too.

Scratch files are in `C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\41f3dc78-9483-401b-b2a5-cbad59f947cb\scratchpad\facing_side\`: `census2.py` and `rows.json` (every `SetRegion`), `standable.py` and `standable.json` (the walkmesh counts for the 149 entries).