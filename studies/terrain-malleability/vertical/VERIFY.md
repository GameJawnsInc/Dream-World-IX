# Adversarial verification: the vertical lane

This verification was read-only. It covers the Memoria clone `C:\gd\FFIX\Memoria` (HEAD `6b8bb2d5` plus the working-copy patch stack), the game install, and memory.

## Re-runs

All seven lane scripts were re-run. The six data and render outputs are **byte-identical** to the lane's own `out/*.json`; that was checked with `cmp` against a scratchpad backup. `engine_bounds.py` reproduces 64 of 64 anchors and every derived number.

### Patch-stack check

`engine_bounds.py` marks an anchor "stock" whenever its exact text appears anywhere in HEAD. Three table anchors are hard-coded "stock". On their own, neither check could catch a patch.

I checked this independently. `git diff HEAD` on `ff9.cs` (8 hunks) and `WMWorld.cs` (13 hunks) touches **none** of the cited lines. So the "64/64 stock" conclusion holds.

## New verifier scripts

All three are in this directory and write `out/verify_*.json`.

| script | what it tests |
|---|---|
| `verify_camera_render_eye.py` | Re-runs the chase-camera census with the camera that actually **renders**, plus the canopy sink, the engine's probe-centre shift, the R2 high camera, and disc 4. |
| `verify_sea_rim_and_subzero.py` | Checks raised sea vertices against terrain in the 3x3 block neighbourhood. Scans every block where *any* part dips below zero, not only the blocks where terrain does. |
| `verify_form2.py` | The lane read only the `0_1` mesh set. The bundle also ships a `0_2` set for 26 blocks per disc. These are the FORM-2 walk meshes of switchable blocks (`WMWorldPrefabMaker.cs:36`, `WMWorld.cs:853-856` `AddWalkMeshForm2`), which become active after story events. This script checks them. |

## Verdicts

| id | verdict | note |
|---|---|---|
| V1 | corrected | The constants, ray origin, t<0 rejection, dead `distance`, and miss value of 0 are all exact. **Two errors.** (1) Non-flying NPCs and parked actors do **not** sky-cast. They cast from y+2.34375 (`CastRayFromSky = flg_fly!=0`, ff9.cs:5192). They fall back to the sky cast only on a miss (:5200). (2) For the **controlled** walker or flyer, a miss refuses the step: `pno=-1` is rejected at `if (num3 >= 0)` (ff9.cs:5700). Ground is set to 0 only for spawn, NPC and camera casts. |
| V2 | confirmed | Reproduced exactly on both discs. The form-2 (`0_2`) meshes stay inside the envelope (terrain -5.07..42.12, object -5.07..40.61), but they lower the object minimum below the lane's -3.352. |
| V3 | confirmed | Source verified end to end, all stock (live / stock): sink row 1 = {400,...} at ff9.cs:19. Class 0 is 36/37/38 and is immediate (:5666). The slice is applied at :5509. `w_movementSetheight` runs after `w_movementControl` (:5240), so the next frame's walk probe (:5554) starts from the lowered y. The probe numbers reproduce, but stock cannot tell the two readings apart; an in-game check (P1) is still needed. Of the contradicted records, `walk-decode-claims.md` ML-8 (:87, :189) is genuinely wrong. `WALK-QUERY-DECODE.md:137` is **not** wrong: rate-limiting really does apply only to water classes, because class 0 is immediate, not rate-limited. |
| V4 | confirmed | Floor raise at :5513-5516, then the controlled-only clamp at :5518-5520, which is skipped under FixMode/FixModeY. Over the 42.67 summit the airship settles at 42.1875 with slice -0.48. The 3 u² figure reproduces. `kmovementMaximumHeight` (:9487) is declared but never read; the clamp uses the literal. |
| V5 | corrected | The formula is right for the **internal** `w_cameraWorldEye`, but the rendered camera is `w_cameraWorldEye + b` (ff9.cs:2747). With FixTypeCam on by default (WorldState.cs:22), b.y = FixTypeCamEyeY/256 × CameraHeight/100 (:2743). The targets are 558 for foot and ground chocobos (+2.18u), 1419 for airships (+5.54u) and 320 for the Narciss (+1.25u) (:6061-6087). The live ini has CameraHeight = 100. The rendered-eye thresholds are therefore: on foot ≈ 51.0 (not 48.8), low actors in areas 40-45 ≈ 41.2 (not 39.05), airships ≈ 52.0-52.8 (not 46.5-47.3), eye cap 73.99 on foot (not 71.8), airship eye floor 23.1. The lane also omitted the R2 high camera (:6122-6123, posstat 7, eye height 29.3); in that mode the internal cap binds for walkers above ≈42.5, not ≈62. Clip planes 0.3 / 1000 / 45 are confirmed, and the custom projection is editor-only. |
| V6 | corrected | Under the lane's model, 1 clip reproduces. **With the rendered eye** (+2.18) there are **0** clips on both discs, minimum margin +1.33 (disc 1) and +0.96 (disc 4), p0.01 margin 7.5. Adding the engine's probe-centre shift (eye + dirVector/4 = actor + 0.75 × offset, :2940-2942) gives **35** clips on disc 1 and **21** on disc 4. Under every model, 100% of clips sit within 20u of the (768,-320) spike, so "the only clip site is the w_effectLastPos spike" is robust. The count and the "5.3u headroom" are not (the range across models is 5.0-7.5). Hack (i) gates on `w_movePlanePtr != null`, meaning any vehicle actor exists (:4567-4571), and on the rendered camera being within 12u. That includes the on-foot camera, not only an airship camera. The dome is unreachable in free roam, as claimed. |
| V7 | corrected | **No curvature: confirmed.** The negative controls re-run (pristine Terrain accepted; bend and clip tamper rejected). The world shaders carry only d3d9 subprograms, and all 19 bound shaders except Standard pass. **The streaming horizon is refuted.** Stock Memoria loads **all** blocks at map start (`ff9.world.LoadBlocks(false)`, ff9.cs:3703 / 3695) and never unloads them (`DiscardBlockWhenStreaming=false`, WorldState.cs:25). `IsInsideSight` only gates loading, and that is moot. Nothing pops at a 2-8 block edge. Distant terrain is limited by fog and the 1000 far plane, which is about the wrapped map's half-diagonal (√(768²+640²) ≈ 999.7). |
| V8 | confirmed | `heightFog=true; height=29f` (:8553-8554) and the 52.1875 lerp (:8567) are exact. GlobalFog `height` is the fog-top coordinate. Whether GlobalFog is enabled at runtime is still unverified (the code itself checks `globalFog.enabled`). |
| V9 | corrected | The vertex counts reproduce, and THE SEA-LAYER LAW ("exactly Y=0") is indeed false at vertex level. Every raised sea1-3 vertex lies within 6.3u of a terrain vertex (median 3.4-4.0u), so "shore ramp" holds. **But the restated law is wrong.** In the form-2 set, **sea4 rises to +1.527** (115 off-zero vertices, block (3,9)) and sea5 to +0.391. "Deep sea4/5/6 stay at 0" and "sea4 residuals ±0.055" hold only for form 1. The law's "disjoint plan coverage" half was not tested by the lane. |
| V10 | confirmed | Reproduced exactly. A wider scan (any part below -0.05) found no other sub-zero ground; only an object at (9,17) reaches -0.06, and engine ground there stays ≥0. Form-2 has no sub-zero foot-legal tris. **Implication fix:** a hole is a **wall** for the walker (step refused), not a drop to 0. Also note that stock hard-codes an airship no-disembark disc of radius 3.75 at (191.9,-474.3) (ff9.cs:5776-5784), inside this basin. It is a special site; P5 should check what lives there. |
| V11 | unverifiable | The number reproduces (p98 = 37.098), but it depends on which percentile you pick: p97 is 36.55 and p99 is 37.98. Measured against the rendered eye, the ride also sits at cc + 39.28, not 37.1. This is weak evidence of tuning. |
| V12 | confirmed | The mask decode was checked against `w_movementCheckTopographID` (topo = (id&0xFC)>>2, check[1] covers 0-31) and is exact. All 14 ids are absent from the `0_1` **and** `0_2` sets on both discs. The fly branch is one probe at rotation 0; a refused probe also blocks the Y move. Side effects remain a hypothesis (P6). |
| V13 | corrected | The Narciss topo-53 rule, the y=0 pin (:5205), shadows +0.1/+0.6 (:5141-5146), the S(350) tolerance and the 45/46/52 refusal are all exact. **The "probe ring" is a misread.** `w_movementGetGetoff` tries up to 16 headings. In each heading it casts **8 collinear probes** at radius × j/5 (j = 1..8), reaching **1.6 × radius = 4.0u for Hilda and 4.5u for Invincible**; only the first heading's last probe uses radius × 8/8. Every probe must be foot-legal, but **only the last probe's** height is compared (≤1.367) to the ship's ground (:5839-5889). One clear line in any direction is enough; relief between the probes is unchecked. Two further hard-coded no-land discs exist: r 10 at (896.4,-350) and r 3.75 at (191.9,-474.3). |
| V14 | corrected | Confirmed: there is no walker Y ceiling or floor, and the only actor Y clamp is the flyer clamp at 42.1875. **Two fixes.** (1) The keep-own-height idalls apply only to indices 1, 2, 11, 3-7 (party, mog, chocobos), not to generic NPCs or parked airships or boat (:5209-5232). (2) The framing band edges need the +2.18 render offset: about 41-51u, eye cap 73.99. |

## Additional findings

1. **The camera that renders sits +2.18u above the eye the census modelled** (+5.54 for airships, +1.25 for the Narciss). This is the largest error in the lane: it moves every camera threshold, removes the single stock clip, and probe P3's prediction of "MainCamera y ≈ 34.4" should be ≈ 36.55.
2. **The census omits the form-2 (`0_2`) walk meshes.** These are 26 switchable blocks per disc that are live after story events. They change the sea law (sea4 to +1.53), but no envelope extreme, flight-blocked topo or sub-zero result.
3. **There is no block streaming horizon.** All blocks load at map entry and are never discarded.
4. **The camera census ignores its own canopy sink.** Actor y on 36/37/38 is ground - 1.17. The effect is negligible: minimum margins are unchanged.
5. **Disc 4's (11,4) spike is taller** (topo 60, 38.19) than disc 1's (35.50). Disc 4 has its own clip set at the same site.

## What survives unchanged

- The engine constants are 64/64 stock.
- THE CANOPY SINK source chain.
- The flight ceiling, with the airship clamped into the rock.
- The stock Y envelope.
- The sub-zero basin with no water above.
- Unused flight-blocked topos, absent from both form sets.
- No vertex-shader curvature.
- The mist plane at 29.
