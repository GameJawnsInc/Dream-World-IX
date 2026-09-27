**Miss diagnosis, rung-3 sessions 1–3: the walker pinning at 350's door to 355, and every other miss so far**

There are 116 miss records so far: 20 in session 1, 73 in session 2 and 23 in session 3 (up to its run 5). Only 2 are the walker case, and both are the stock run's two attempts at 350's door to 355 in session 3. The walker case is lost at one place in the code: the smooth walk's last-leg zone finish in `session.py`. When the walk can't get into the zone but is within 45u of the goal point, the finish reports "arrived". So the 695db9f4 walker-box handling, the stall handling (waits, push, unseen blockers) and the tour's LIVE rule never run. Separately, 23 other misses are a larger problem I found along the way: every stock 350 door fires only when Zidane faces it (section 4).

## 1. Every miss, by class

Instances are written session.run.crossing. "Door" is the place and exit index; fork ids are mapped to their donor (30833/30844 → 350, 30835/30846 → 353).

| Class | Door | Count | Cause | Instances |
|---|---|---|---|---|
| **(a) walker** | 350.4 → 355 | 2 | A Dali child walked into him at the door and stayed there; its body held him short of the zone's only standable patch. Record says reached true, inside false. Frames 13 and 16 show the blue-hat child in contact at his front-right, facing him; frame 13 shows the "!" talk prompt. Crossing 13's record lists uid 13 as a body the plan went round; crossing 16's record names no body, because nothing asks at the finish. Most likely uid 13. | s3.r1S.n13, s3.r1S.n16 |
| (b) bounce room | 350.2 → 353 | 26 | The gateway fired; 353's arrival scene put him back before he got control ("never became playable"). | s1.r1S.n13, s1.r2F0.n9/n12, s1.r3F4.n9/n12, s2.r1S.n15, s2.r2F0.n9/n12, s2.r3F4.n10/n13, s2.r4S.n7, s2.r5F0.n10/n13, s2.r6F4.n10/n14, s2.r7S.n10, s2.r8F0.n10/n13, s2.r9F4.n10/n13, s2.r10F0.n10/n14, s3.r1S.n12, s3.r3F4.n9/n12, s3.r4S.n13 |
| (b) bounce room | 356.1 → 353 | 28 | Same as above. | s1.r1S.n19/n21, s1.r2F0.n18/n20, s1.r3F4.n18/n20; s2 runs 1,4,5,6,7,8,9,10 (two each: n17/19, n19/21, n20/22, n21/23); s3.r1S.n18/n20, s3.r3F4.n18/n20, s3.r4S.n19/n21 |
| (b) bounce via object 34 | 350.5 → 358, attempt 1 | 16 | No route stayed clear of object 34's trigger radius, so the plan entered it. Object 34's Range is the real 358 door at scenario 2600 (entry 34 tag 2: `Field(358)` at .eb offset 24570). 358's scene then returned him to 350. | s1 r1/r2/r3; s2 r1–r10; s3 r1/r3/r4 (the attempt-1 crossing of each) |
| (b) scene-gated | 350.5 → 358, attempt 2 | 16 | He stood in region 25 and nothing fired. Its tag 2 only acts when the scenario counter is in [2650, 2710) (.eb offset 13922), and its `Field(358)` is only in tag 3, which needs Confirm. | the attempt-2 crossing of the same 16 runs |
| (b) facing gate | 350.0 → 351 | 12 | He stood inside the zone facing away from the door, and nothing was pressed (section 4). | s2 r1,3,4(n3,n6),5,6,7,8,9,10 at n3; s3.r3F4.n39; s3.r4S.n3 |
| (b) facing gate | 350.2 → 353 | 2 | Same (frames show him facing right and down). | s2.r1S.n10, s2.r4S.n10 |
| (b) facing gate | 350.3 → 356 | 9 | Same (frames show him facing left or down-left). | s1.r1S.n10 (frame ambiguous), s1.r3F4.n42, s2.r1S.n11, s2.r2F0.n17/n18, s2.r3F4.n18/n19, s2.r6F4.n11, s2.r10F0.n11 |
| (c) planner geometry | 350.2 → 353 | 5 | He ended on the door step outside the zone, whose only standable part is a ~34u wedge. The frames show no body near him. | s1.r1S.n9, s2.r7S.n13, s3.r1S.n9, s3.r4S.n10, s3.r5F0.n12 |

Frames read: session 3 run 1 crossings 9, 12, 13, 16, 24, 25; run 3 crossing 39; run 4 crossing 10; run 5 crossing 12. Session 2: run 1 crossings 3, 10, 11; run 2 crossings 17, 18; run 3 crossings 18, 19; run 4 crossing 10; run 6 crossing 11; run 7 crossing 13; run 10 crossing 11. Session 1: run 1 crossings 9, 10; run 3 crossing 42.

## 2. What the engine does with a non-solid body in contact

- **His own press** (`FieldMapActorController.cs:749-796`):
  - Each moving frame turns him 40% of the way toward the pressed direction.
  - If a body is within ±90° of where he faces, he is pushed straight out from its centre to `radius + 4*collRad`. Pressing off-centre therefore slides him round it.
  - If that pushed-out spot collides again (for example the door wall), both the push and the move are undone (`:786-790`) and he stops dead. That is the corner between the door and the child in both frames.
  - A body behind him (more than 90° off) is not pushed out at all.
  - He is never pushed while standing still; push-out only happens on his own moving frames.
- **CheckCollFallback** (`:800-822`): each colliding press adds 1 to `sLockTimer` (the children lack flag 16). At 25 it flips to −25, and push-out is off while it is negative (`:772`). An unbroken press of about 26 calls therefore walks him through the child, which is what `ROUTE_PUSH_LOCK_W` encodes.
- **The walker's own step**: a scripted walker stepping into him has the whole step undone (`EventEngine.MoveToward.cs:187-189`). The child stays held on him as long as he stands still, so waiting never frees him.
- **Which region fires** (`EventEngine.ProcessEvents.cs:183-188`, `EventCollision.cs:300-303`): only when he has user control, and only the first armed region containing him (`EventEngine.TreadQuad.cs:12-19`; the list is in Init order, `Obj.cs:31-37`). Membership is a fan of consecutive vertex triplets (`TreadQuad.cs:24-39`).

## 3. Where session.py loses the pinned end

1. `_walk_leg`, lines 2466–2472: once he is within 45u of the goal, `finish` is set and the target becomes `_zone_foothold` (lines 2237–2259). That foothold search ignores published bodies, so it can aim at the spot the child is standing on.
2. **Lines 2484–2486**, the finish gives up: `if hold is None: if finish or … <= tolerance: break`. The 695db9f4 walker-box handling (`_outwait_box`, then `_box_step`, lines 2487–2501) is only reached outside tolerance. Session 2's box at this door moved inside 45u and became this give-up.
3. **Lines 2548–2551**: two presses held by the child (moved under 1u, or no nearer the zone) → `break`, with no `_body_ahead` check.
4. **Lines 2553–2558**: the function returns "arrived" when he is within 45u, even though he is outside the zone.
5. `_route_leg` (lines 2927–2929) passes on "arrived". route_to only climbs the stall handling (`_unstick_leg`) on "stalled" (lines 2814–2815), so it never runs.
6. route_to sets `reached` true for "within 45u *or* in zone" (lines 2895–2897). route_cross then computes inside false and waits only `ROUTE_OUTSIDE_WAIT` (lines 4112–4128).
7. `dali_tour.failure()`: `reached` true skips the LIVE clause (lines 150–153), so the end is scored REAL "miss". Two of those made 355 unreachable for the stock run.

Crossing 13 also shows the stall handling can't help as it stands. It took 2 waits, which are useless against a held walker, and then `_push_through`'s 2-frame probe slid him at least 1u, so it returned "free" and never pushed. Only after that did the finish get within 45u and give up.

## 4. The facing gate behind the 23 inside-the-zone misses

Every stock 350 door's tag-2 checks, after `CalculateExitPosition`, that he faces within ±48/256 of a turn (±67.5°) of the bearing to his projection onto the region's first edge (q0→q1). If not, it resets and returns. The .eb offsets are:

| Region entry | Door | Offsets |
|---|---|---|
| 18 | 351 | 11123 / 11149 / 11164 |
| 20 | 353 (the one armed below scenario 2990) | 12110 / 12136 / 12151 |
| 22 | 356 | 12979 / 13005 / 13020 |
| 23 | 355 | 13407 / 13433 / 13448 |

Engine sources: `DoEventCode.cs:2247-2275`, `EBin.cs:1811-1826` and `1207-1216`, operator codes 0x18 `B_LT`, 0x19 `B_GT`, 0x28 `B_OROR`.

The harness's `_walk_leg` returns "arrived" the moment he stands in the zone (lines 2462–2463) and never turns him toward the door. The strongest evidence is 350's door to 351. After arriving from 351 he stands in that zone facing away. In session 2 he stood there the whole 20 s wait, unfired, in 10 of 10 runs. In session 3 run 1, a calibration probe pressed right from the same spot and the door fired: "probing right … took control away".

These are real strikes today. Two strikes each made 351 unreachable in session 2's stock run 4, and made 356 unreachable in session 1 run 3 and session 2 runs 2 and 3.

## 5. Fix plan (diagnosis only; nothing is edited)

1. **Pressing into the zone** (lines 2484–2501): when the finish has no allowed press and there is a published-object view, call `_outwait_box(basis, target, leg, exclude, field)` with the foothold target and the finish's excluded pads, exactly as outside tolerance. Give up only when the box is the spot itself (`boxed_by` "spot").
2. **Two held presses** (lines 2548–2551): if `_body_ahead(after, u, watch)` names a body in contact, return "short" so route_to runs its stall handling. For a walker held on him, `_box_step` must come before `_outwait`; waiting on a held walker waits on himself. Otherwise `_push_through` along the pressed line into the zone. Solids are never pushed.
3. **The return value** (lines 2553–2558): with a zone, "arrived" should mean standing in the zone. Enforce that at the return.
4. **`_zone_foothold`**: skip spots inside a published body's radius plus `ROUTE_BODY_PAD`. If every foothold is covered by bodies, that is a box by those bodies, and `_outwait_box` should get them as its boxers.
5. **route_to's record**: with a zone, `reached` means in the zone. Add a `pinned` field (uid, moving, solid) from `_body_ahead` at the end.
6. **`dali_tour.failure()`**: an end outside the zone, with control, that is `pinned` or has walker boxers is LIVE, never a REAL miss.
7. **Tests** in `tests/test_harness.py`, using the existing held-walker helper `_creeping` / `_step_in_front`:
   - a walker held on him within 45u of a zone that can only be stood in at a corner: he must step away or push, and the door fires;
   - with `_box_step` disabled: the record names the body as `pinned`, and `failure()` returns "live".
8. **Facing** (separate change): in route_cross, or where `_walk_leg` returns because he's in the zone, if nothing fires within a few frames, press one short walked hold toward the q0→q1 projection. `scan_gateways` keeps q0 and q1 as `zone[0]` and `zone[1]`; the hold's line must stay in the zone. For this to be testable, `FakeGame._enter_regions` (`fakegame.py:969-985`) must learn the facing gate and the first-armed-region rule; it currently fires on centre-inside, so a test of this fix could never fail.

## 6. Smaller findings

- `eventscan._zone_quad` cuts 5-point SetRegions down to 4, but the engine tests the fan of consecutive triplets.
  - For 350's doors the kit's quad lies inside the fan on the walkmesh, so no effect there.
  - 356's exits to 350 and 353 include 1464 and 626 standable 8u-grid points that are in the fan's dead zone. That is a latent (c) waiting to happen.
- The tour models 350's exit 5 as region 25, but at scenario 2600 the working 358 door is object 34, which the planner avoids as a trigger. It only costs two strikes on a one-way door that goes last anyway.
- `failure()` labels the 353 bounce "miss" rather than "bounce", because the scene puts him back and `landed` stays None. The cap is the same; this is only the name.

The two scratch scripts that build the table and the exit geometry: `<archive>\scratchpad\missdiag\classify.py` and `...\missdiag\fan.py`.

