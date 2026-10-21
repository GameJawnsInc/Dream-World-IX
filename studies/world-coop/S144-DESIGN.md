# World-map co-op: wait, then rejoin (s144)

The owner's call (2026-10-20): on the world map the HOST drives. Following on your own would fight the vehicles (one party
per chocobo, ship or airship), the world map's state for each disc, and every world script that fires on position. A
ride-along view (the guest's world map tracking the host's position and vehicle) stays a later option.

The recon (5 read-only lanes plus a critic, all with file:line evidence) is in the session scratchpad as `recon144.json`.
The sites below are its settled answers; the build re-finds each one in the live clone.

## What happens today (s143)

- The host on the world map sends field 0 on the position lane, and the guest's follow ignores it: the guest stays where
  it is.
- The guest's own field doors are bounced (`RedirectGuestFieldJump`, from the MAPJUMP handler), but WMAPJUMP (0xB6,
  `EventEngine.DoEventCode.cs:2502`) has no hook. A guest reaches its own world map by walking out, or when its cutscene
  ends there, and can roam it. Its random encounters are off while it follows.
- On the world map `fldMapNo` is the field the guest LEFT, so the follow logic takes the "arrived" branch whenever the host
  stands on that field. Even otherwise, `FollowHostTick` needs a field plus FieldHUD.
- The diorama only boots on a field, so a guest on the world map gets only the old digit panel.
- `NetSyncClient.Ensure` has one caller (`HonoluluFieldMain.cs:29`): a player who Continues a world-map save has no co-op
  until they walk into a field.

## The decisions (s144)

1. **Freeze, don't block.** A following guest may reach the world map (bouncing WMAPJUMP would replay cutscenes that end
   there), and there it has no actor control: no walking, no vehicle, no entering locations, no airship autopilot. Its own
   camera freezes with it: the one input gate also holds L1/R1/right stick/R2/L2, and a stationary walker gains little from
   a free camera. The minimap and the world HUD still draw. The full-map view is refused while frozen, because opening and
   closing it rewrites usercontrol.
2. **Who is frozen:** `NetSyncField.SpectatorField`, the same predicate the field gates use (a live followed session, a
   mirroring guest, or the selftest role under `bench 1`). For a mirroring guest it holds through the session grace until
   the exit ramp reloads its own save, so a blip never leaves it free to walk the host's world. The bee scene never freezes.
3. **Rejoin:** when the host stands on a field the guest's install has, a guest on the world map warps into it. It arrives
   the way a field follow does: the host's snapshot, applied at the field load.
4. **The source-field hold:** after the guest's own WMAPJUMP from field X, the rejoin into X waits up to 15 s, or until the
   host leaves X. A guest that finished a cutscene first (one that ends on the world map) then doesn't replay it in a world
   round trip. A guest that walked out on its own while the host idles in X is pulled back after the hold.
5. **A field-side guest stays put.** When the host walks out to the world map, a guest left on that field waits on the field,
   as today. Both kinds of waiting show the same line.
6. **A world script's own Field() on a following guest** (event worlds, control-off sequences) is never bounced to
   `fldMapNo` in mode 3, because that would be a jump INTO the field the guest left, carrying a foreign FieldEntrance:
   - if dest is the host's field, it passes;
   - if the host is on another registered field, it is redirected there (an instant rejoin through the world's own funnel);
   - if the host is off-field, it passes through.
7. **The waiting line:** section 7's flags byte gains b6 `HfWorld` (the host is on the world map) and b7 `HfTitle` (the host
   is at the title). The wire stays v14 with no version bump: unknown bits are ignored by old readers. The guest's overlay:
   - host on the world map: "Your partner is on the world map. You'll rejoin them at their next stop."
   - guest on the world map and the host on a field: the rejoin line (Rejoining your partner ...), or the hold.
   - host at the title: Your partner is at the title screen.
   - an old host (no bits): a debounced field-0 fallback, "Your partner is away."
8. **Escapes** (the freeze must never strand):
   - F11 / held L3 (TeleportToHost) on the world map re-arms the rejoin at once, clearing the hold and the debounce;
   - a ~ menu lever, Release world freeze, lifts the freeze until the next field load (live followed session only, logged);
   - unfollowing, peer loss and the exit ramp end it, as decision 2 says.
9. **Pairing from the world map:** `Ensure` also runs when the world scene starts, and the transport dials on WorldHUD, so
   either player can Continue a world-map save. A guest that pairs on the world map is frozen, and rejoins at the host's
   first field with the host's snapshot.
10. **No new ini knobs** (the Diorama-knob verdict). Calibration is a selftest-only lever: `netsync bench worldfreeze on|off`.
11. **Battles from the world map are s145, not s144.** A world-booted diorama round trip has never run in any form. Its
    riskiest unknown is where a COLD world reload lands a guest (and whether it stays aboard its vehicle), which needs an
    in-game observation first. s144 builds the shared world-transition latch it will plug into, plus the harness's world
    battle verb, so a real host-on-world battle tape can be recorded on s144 before s145.

## The engine pieces

**A. World observability and the world battle verb (harness only, no co-op behaviour).**
- `WMScriptDirector.cs:150`: read the `w_frameMainRoutine()` result into a local; a one-shot
  `Ff9mkDebugMenu.TakePendingWorldBattle()` turns a 0 result into 3. Case 3 is the native world encounter start. Writing
  `nextMode = 2` from outside strands the world, so never do that.
- `Ff9mkDebugMenu.StartWorldBattle`, a sibling of `StartBattle`. It validates:
  - WorldHUD, `sys.mode == 3`, `!IsBeeScene`;
  - no transition pending, a controlled actor;
  - the topograph is not 52, and the scene is in `mapName`.
  It then writes what a real encounter writes. `battle <scene> [group] [rand]` on WorldHUD routes there. On s143 it fails
  closed ('battle: field only').
- Read-only keys, additive under protocol 5, with sentinels in the catch literal:
  - top-level `gmode`;
  - world `area`, `topo`, `move`, `phase`, `next_mode`;
  - `field.entrance`;
  - `netsync.world` {freeze, rejoin, waitline};
  - a `netsync.session` follow block {pending, warped_to, candidate, world_armed, on_world, host_world, host_title, hold};
  - `netsync.session.overlay_text` (the selftest role forces the overlay off, so its words are published as text).

**B. The freeze.**
- `ff9.cs:5539`, the single movement-input dispatcher for every travel mode: add the live conjunct
  `!NetSyncField.WorldFreezeHold()`. The speeds stay at the per-frame zero, so the actor idles. Camera follow, collision,
  WorldEvent, the scripts and the minimap all run untouched. Never freeze through usercontrol, PSXCntlPadMask or
  IsProcessingInput: scripts and WorldHUD rewrite all three.
- `WorldFreezeHold` is read live at the call site and never throws:
  `WorldFreezeRule(SpectatorField, BenchWorldFreezeOff, IsSelfTestRole, released) && !IsBeeScene`.
- On the rising edge (the first frozen frame per world load): the autopilot off, plus the ship and plane inertia reset (the
  semantics of `w_frameSetParameter` 37/38). Verify that the inertia really persists before relying on it.
- `FilterScriptButtons`, control-ON branch: on gMode 3 while frozen, mask `HostOwnedKeys`. This closes Cancel
  (dismount/land) and Triangle (deck -> the interior Field()). Control-off polls pass untouched.
- WorldHUD: refuse opening the full map and `ProcessTouchedLocation` while frozen, with the stock buzz (FF9Sfx 102) and one
  latched line each.
- A gMode-aware `DeclineOnceHere`: on the world map, latch on `wldMapNo` and name the world map. Today's world-side declines
  are misattributed to the departed field.
- `ENCOUNT` / `ENCOUNT2` on gMode 3: skip a guest's own scripted world battle under `SpectatorField`, not only
  `IsMirroringStory`. That closes Ragtime Mouse and WORLD03 area-52 before the mirror arms.
- The lever, its release on every harness release path, the keys, and `world freeze selftest: OK (N rows)` (a truth table
  with mutants).

**C. The rejoin, world pairing and the shared latch.**
- In `Update`: `onWorld = gMode == 3 && loadedLevelName == "WorldMap"` (gMode stays 3 inside a world-booted diorama and
  through the world -> field fade, so gMode alone lies), and `followFld = onWorld ? -1 : fld`, passed to
  `ServiceIntentFollow` and `FollowHostTick`.
- World branches in both call a new `StartWorldFollowWarp(dest)` on the in-game-proven `Ff9mkDebugMenu.WorldWarp` levers:
  `SetNextMap(dest)` in mode 3, `World.map.nextMode = 1`, `attr |= 0x1000`. It must never touch the field follow's state:
  the field recipe is a no-op on the world map and strands a black screen. The gates:
  - WorldHUD, `sys.mode == 3`, `!IsFading`;
  - a fresh host snapshot (`GetRemoteState() != null`);
  - a registered destination;
  - raw usercontrol on (a control-off world script could overwrite `nextMapNo`);
  - `!IsEventWorldMap`;
  - the source-field hold;
  - the shared latch free.
- The arm latch is cleared at the field landing. A 5 s timeout re-arms it, because a Replace dropped while fading must not
  wedge the follow.
- **The shared world-transition latch**, one predicate for every world transition. It is gated on by the rejoin and the exit
  ramp now, and by s145's boot later:
  `(attr & 0x3001) != 0 || World.map.nextMode is 1 or 2 || IsFading || Booted || BattleReturnInFlight || rejoin armed`.
- `RedirectGuestFieldJump`: the mode-3 branch from decision 6.
- The exit ramp: the world branch uses the strict `onWorld` and the shared latch. On an event world it settles only with
  control on, still bounded by `ExitRampSettleMaxMs`.
- WMAPJUMP on a following guest: latch the source field and the tick for the hold.
- TeleportToHost: the world branch from decision 8. The ~ menu: the Release world freeze lever.
- World pairing: `Ensure` at the world scene's start (mirror the field call: idempotent, inert outside co-op), and the dial
  gate accepts WorldHUD. Audit every Update path for a client born on the world map.
- Host-side one-liner: in mode 3, `EmitFieldIntentIfHost` announces `ForkSiblingField(dest)`, where the host really lands
  (`ff9.cs:9330`).
- `world rejoin selftest: OK (N rows)` truth tables: the follow step's world branch, the hold, the redirect rule, and the
  latch.

**D. The waiting line.**
- `HostDialogFlags` b6/b7. First confirm the host emits section 7 off-field, and that every reader (`coop_peer`,
  battlewire, channel, fakegame) ignores or mirrors the new bits.
- The overlay states, texts and names for decision 7, and the world-guest chain ahead of the `local == null -> OvlOff`
  branch. Check the placement on the world HUD with `tools/game_snap.ps1`.
- `overlay text selftest` rows for the choice.

Every hunk is tagged `[ff9mapkit netsync s144]`, and each file keeps its own line endings.

## The bench

- **Solo, the selftest role:** newgame, warp to 6603 FARSHORE (FF9CustomMap-world; re-check its registration), walk out
  onto world 9011. Then `netsync selftest 1`, `bench 1`:
  - F1: hold a direction and the walker stays put;
  - F2: Confirm on the Ice Cavern tile stays WorldHUD;
  - F3: Cancel / Triangle / the full map do nothing;
  - F4: `bench worldfreeze off` walks and enters field 300 (the lever);
  - F5: `bench 0` walks (the control);
  - the keys and the proof lines.
- **The world battle verb:** `battle <scene> 0 rand` from WorldHUD starts a real own battle and returns to the world map.
- **T2, a real client replaying a tape:**
  - world-rejoin: the guest is pre-placed on the world map while the existing field-250 tape replays. On s143 it stays
    WorldHUD; on s144 it reaches FieldHUD 250 with the state mirror armed;
  - world-wait: an s144-recorded host-on-world tape (a new `COOP_TAPE_WORLD` variant of `coop_tape_record.py`). The guest's
    overlay text is the waiting line, on the world map and on a field.
- **The duo:** the host walks out of 6603, and the guest left on 6603 shows the line. The guest walks out too and is frozen.
  The host enters the Ice Cavern, and the guest rejoins from the world map.
- **Calibration:** every leg first runs on the deployed s143 (OLD_PREDICTED), then on s144 with the lever (LEVER_PREDICTED).
  Every check can fail, pinned by a fake-driven red test.

## Known limits (s144)

- The harness's input reaches GetAxis and the UIKeyTrigger keys only. Raw XInput (the right stick, the vehicle throttle) and
  raw WASD are covered by the gate's code read and an owner pad/keyboard check.
- A guest frozen aboard a vehicle stays aboard until the rejoin.
- The guest's world map runs on its last field-load story snapshot. Host story beats crossed on the world map reach it at
  the next field load.

## Next: s145, battles from the world map

The guest's diorama boots from WorldHUD behind the shared latch, and its Leave returns to the world map
(`Replace("WorldMap")` when the boot was on the world map). The pre-swirl block gets a world shape (`SetCenterPosition(1)`, no
double song suspend, `prevMode = 3`). The watcher treats `HfWorld` as the host-back over-signal. Before building, observe one
cold world reload aboard a vehicle (the ~ menu's world reload) to decide between cold-first and the warm world prime.

## Build and proof

- **Built** by a recon workflow (5 read-only lanes plus a critic) and a build workflow:
  - 4 engine stages, then the harness core and the bench;
  - two review rounds with two skeptics per finding.

  The patch has 12 files, +2521/-35, 70 hunks. `diag` reads 41 of 41. The compile has 0 errors (the 186 baseline
  warnings).
- **Calibrated on s143 first** (`be01339d49f6a87b`). Every leg failed exactly its predicted set:
  - the solo bench: 12 reds, S144-CAL green;
  - the T2 rejoin leg: 4 reds;
  - an s143 host-on-world tape: `where --want none`;
  - the T2 wait leg: 3 reds;
  - the duo: D1-D3. An s143 guest walked 6 units on the world map.
- **Deployed** 2026-10-20 (backup `20261020-234518`; Assembly-CSharp `be9abacbd7b11d64`; the owner said yes).
- **Proven on s144:**
  - **The solo bench, 18/18 on two runs:**
    - the freeze, judged on the walker's x/z;
    - the Ice Cavern tile's Confirm held;
    - the full map refused;
    - the edge on a second world load;
    - the lever and the control;
    - the world battle verb and its return to the world map.

    Under `bench worldfreeze off` it is red in exactly LEVER_PREDICTED.
  - **The T2 legs:**
    - rejoin 11/11: a real client on the world map rejoins field 250 off the field-250 tape, with the state mirror armed;
    - wait 8/8 on an s144 world tape (`host_world`);
    - wait 8/8 on the s143 tape (the old-host fallback);
    - the s144 tape carries b6 (`where --want world`).
  - **The duo, 16/16:**
    - the guest left on 6603 shows the line;
    - the guest walks out too and is frozen (0.00 units);
    - when the host enters the Ice Cavern, the guest rejoins field 300 from the world map.
  - **The regression:**
    - block A at baseline: wait parity 12/12 on a rerun, S9-C4L unreachable solo;
    - coop_leader_guard 19/19;
    - coop_self_dress 65/65 and 54/54;
    - the duo G9 22/22;
    - the tape legs and the T2 cut legs.
  - **The domain tests:** 2739 passed in one full run after the bench fix.
- **Two bench defects found in game,** fixed and re-proven. The engine was right in both cases.
  - **F3 pressed Select once.** A New Game's world map lands with the minimap off, and stock's Select cycle is
    HUD -> full map -> no minimap -> HUD, so the first press only turned the minimap on. A probe showed the second
    and later presses each refused and counted. F3 now drives the stock cycle.
  - **D3 required the "Rejoining ..." overlay on a sample.** The host's MAPJUMP intent arms the guest at once, so the
    window is shorter than a sample. D3 now follows the bracket law.
- **Known:** one of four starts of the world battle verb froze the game in the battle load, after the swirl. It is a
  harness-only path, and the freeze was inactive. The other three starts, two of them reruns, were clean. Watch for it.
- **Next:**
  - s145, battles from the world map: first observe a cold world reload aboard a vehicle;
  - the owner's two-PC check of the world map: walk out together, the line, the frozen guest, the rejoin at a town.
