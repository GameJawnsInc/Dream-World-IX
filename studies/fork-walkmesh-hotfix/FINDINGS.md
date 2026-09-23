# Field 2507's delayed walkmesh hotfix on kit-built forks: harness results

Field 2507 (Ipsen's Castle stairwell) has an engine hotfix, `FieldMap.DelayedActiveTri`. It runs 0.5 s after
load. In one frame it detaches every actor whose `isPlayer` is false from the walkmesh
(`BGI_charSetActive(fac, 0)`, which sets `activeTri` to -1) and deactivates the landing tris 174/175/177/178.
Memoria patch s29 gates it on `EffectiveFieldId`, so on a fork it fires only when ForkDonorPatch maps the
fork's id to 2507.

## Benches

All slots come from `import 2507` with the donor's `[encounter]` removed, and all were deployed to
`FF9CustomMap`.

| slot | built by | donor row |
|---|---|---|
| 30990 | `--editable`, which records `source_field` | `30990 2507` |
| 30991 | the same toml without `source_field` (the old `--editable` output) | none |
| 30992 | `--native` (records `source_field`) | `30992 2507` |

The 30990 and 30991 copies also carry the same `[[behavior.hud]]` instrument. It reads
`B_BGIID`/`B_BGIFLOOR` for the player (`B_PTR(250)`) and the two carried chests (entries 7 and 8), plus the
keeper NPC that the unit gate needs.

## Results

**The donor row fires the hotfix** (`editable_2507_ingame.py`). The HUD was read 3 s after arriving at
entrance 128:

| slot | player tri | chest A tri | chest B tri | chest A floor |
|---|---|---|---|---|
| 30991, no row | 122 | 178 | 174 | 4 |
| 30990, row | -1 | -1 | -1 | -1 |

The chest triangles match the offline geometry: (111, 2347) lies in tri 178 and (-219, 2347) in tri 174.

**The player is detached too, on every kit-built fork** (`editable_2507_detach.py`). From the entrance-128
arrival (2019, -1077), hold right for 12 run frames toward a platform edge about 150u east:

| field | entered from | end position | on the walkway |
|---|---|---|---|
| real 2507 | 30990 | (2157.431, -869.502) | yes, slid along the edge |
| 30991, no row | 30990 | (2157.431, -869.502) | yes, the same spot as real |
| 30990, row | New Game / real 2507 / 30991 | (2354.877, -947.438) | no, 360u into the void |
| 30992, native with row | 30990 | (2354.877, -947.438) | no |

Entry order makes no difference. The native result means the defect was already live on master before
`--editable` recorded its donor.

**Walking cannot observe the landing tris.** The first bench walked the walkway toward the landing. The
player stopped about 261u from the nearer chest in both slots: the chests' actor collision covers the whole
landing, and `BGI_charSetActive` leaves actor collision alone.

## Why the real field keeps its player

The real script ends its player setup with `SetPathing(1)`, in both the Init (entry 13, tag 0) and the Loop
tail (tag 1). A kit-built player has no such call, so nothing re-attaches it after the coroutine. Why the
kit-built player's `isPlayer` is false at the 0.5 s mark is answered below, in "Why the kit-built player is
not yet the player when the pass runs": its Init yields 48 ticks between `SetModel` and
`DefinePlayerCharacter`. The real player's Init has no such yields, so it is already the player when the pass
runs, and the pass skips it.

## The fix: a re-attach guard in the kit-built player's Loop

> **Superseded and removed.** The guard below was replaced by the root-cause template fix. See "The template
> fix (done; replaces the guard)" at the end. This section is kept as the record of what was shipped first.

**First attempt: a fixed one-shot, which raced the harness walk.** `Wait(30); SetPathing(1)` went at the head
of the player's Loop. It passed one launch: 30990 ended at the real field's spot and its HUD read `P 121`. It
failed the next: 30990 and 30992 ended off the walkway at (2242.9, -990.6) and the HUD read `P -1` after the
walk. This was first read as the pass landing at a load-dependent moment. That reading is wrong. The pass
always lands before the one-shot; the one-shot raced the scenario's walk, which started too early. See "The
one-shot raced the harness walk, not the pass" below.

**Shipped: a guard.** `content.walkmesh_hotfix.reattach_player` replaces the template's idle player Loop
(`Wait(1)` plus a jump back) with a loop that runs every frame:

    if (B_SYSVAR[2] != 0 && B_BGIID(player) < 0) SetPathing(1)
    Wait(1)

`B_SYSVAR[2]` is the engine's `usercontrol`. Every kit sequence that turns pathing off (ladders, platforms,
jumps, cutscenes) disables movement first, so the guard never fights one. The build adds it only where 2507's
pass will run: a recorded donor of 2507, the field forked in place, or a `borrow_bg` of 2507's scene.

**Verified in two separate launches** (`editable_2507_detach.py`, `DETACH_ORDER=fixed`). Both passed 5/5 with
no engine exceptions:

| field | end position | on the walkway |
|---|---|---|
| 30991, no row | (2157.431, -869.502) | yes |
| 30990, editable with row and guard | (2157.431, -869.502) | yes |
| 30992, native with row and guard | (2157.431, -869.502) | yes |
| real 2507 | (2157.431, -869.502) | yes |

On 30990 the HUD after the walk reads `P 121, CA -1, CB -1`: the hotfix still detaches the chests, and the
player is back on a triangle.

A bound player stops at one of two points along the platform edge from run to run: (2157, -870) or
(2142, -907). The unchanged no-row control has landed on both. So the check is "on the walkway, moved < 300",
not an exact position; a detached player moves the full 360u.

## Why the kit-built player is not yet the player when the pass runs

Found by reading the engine source and checking it against the harness state streams already archived for
the runs above. No new engine build and no new in-game run. The live `Assembly-CSharp.dll` is the s87 build
of the shared Memoria clone (sha `1b16d54f…`, the same as the README's s87 row), so the source read here is
the code that ran.

### The mechanism

1. **Opcode `0x00` yields.** Opcodes below 110 go through `EBin.jumpToCommand`. `0x00` falls to `default`,
   then `commandDefault`, then `DoEventCode`, where `case NOP` does `return 1`
   (`EventEngine.DoEventCode.cs:50`). `gArgUsed` stays 0, so `commandDefault2` backs the IP up to one byte
   consumed (`EBin.cs:1394`). A return of 1 makes `adfr` call `next0`, which ends the object's slice for this
   tick. So one zero byte stalls the function for one event tick.
2. **The kit puts 48 zero bytes in every synthesized player's Init.** The blank template's player Init carries
   eight `RunSoundCode(4616, 912)` ops, a sound-bank preload from its source field. Since `08917fac`
   (2026-06-13), `content.npc.neutralize_player_audio_cruft` (`build.py:8073`, on every synthesized field)
   overwrites each of them with `0x00`; its comment calls 0x00 a "safe skip". 8 ops × 6 bytes = 48 zeros,
   sitting between `SetModel` and `DefinePlayerCharacter`. They show in the disassembly as four runs of 12
   `NOTHING()` between the `RunModelCode` triplets. Real 2507's entry 13 has live `RunSoundCode(4616, 924)`
   pairs in the same slots, and no zeros.
3. **So the player's model exists ~48 ticks before it becomes the player.** `SetModel` calls
   `FieldMap.AddFieldChar(..., isPlayer: false)` (`DoEventCode.cs:1124`). `isPlayer` turns true only after
   `DefinePlayerCharacter` moves `controlUID`: `HonoluluFieldMain.updatePlayerObj` sees the control actor's
   game object still named `obj1` and calls `FieldMap.updatePlayer`. The kit's Init runs `SetModel` on its first
   tick. That is the first event pass after `Main_Init`, because a new object is only marked `stateInit` on the
   pass that creates it (`EBin.cs:115`). It then yields 48 times, and reaches `DefinePlayerCharacter` on about
   tick 49, ~1.6 s at 30 ticks/s.
4. **The pass always lands inside that window.** `FieldMap` is created, and `DelayedActiveTri` started, in
   `ff9InitStateFieldMap` just before `StartEvents` (`HonoluluFieldMain.cs:103–149`). The coroutine waits
   0.5 s of game time. Event ticks run on the same scaled clock, and `FPSManager.DelayMainLoop(load time)` only
   holds them back. So at most ~15 ticks can pass before it fires, against a bind at tick ~49. The player's
   controller is live, attached by `CreateObject`, and not yet the player, so the pass detaches it. At the bind,
   `updatePlayer` sets `isPlayer` but re-attaches nothing. The detach is deterministic, not load-dependent. That
   matches every row-carrying run: `P -1` each time on 30990 and 30992. The chests Init on tick 1 too, so the
   pass catches them attached and detaches them, as intended.

### The timing evidence

The harness publishes `player.x` from `EventEngine.GetControlChar()`, which is null until
`DefinePlayerCharacter` has bound control. It publishes every 2 frames. Measured from the end of the
load-frame hitch to the first non-null `player.x`:

| run | 30990 | 30991 / 30992 | real 2507 |
|---|---|---|---|
| `150848-editable-2507-detach` | 1.77 s | 30991: 1.77 s | 0.0 s |
| `154804-editable-2507-reattach` | 1.95 s | 30992: 1.73 s | 0.0 s |
| `154907-editable-2507-reattach` | 1.75 s | 30992: 1.79 s | 0.0 s |
| `155559-editable-2507-guard-1` | 1.93 s | 30992: 1.71 s | 0.0 s |
| `155634-editable-2507-guard-2` | 1.76 s | 30992: 1.74 s | 0.0 s |

A kit-built player binds a constant ~1.7–1.95 s after the load, with or without a donor row, `--editable` or
`--native`. That is 48 ticks plus the post-load hold-off. The real player binds in the first sample after the
load. On kit fields `player.control` also turns true in the same sample as the bind: the player's Init runs its
own `EnableMove` right after `DefinePlayerCharacter`, since `Map.Bit[159]` is already set and `Map.Bit[156]`
is 0. On the real field control follows a few ticks after the bind.

### The one-shot raced the harness walk, not the pass

The one-shot's `SetPathing(1)` ran from the Loop, which starts only when the Init returns (tick ~50). After
`Wait(30)` it fires at tick ~80, about 1.03 s after the bind, and the pass has long passed by then. What it
raced was the scenario's walk, which begins after `warp` (it waits for control) plus `wait_frames(60)`:

| run | bind | walk starts | re-attach (~bind + 1.03 s) | result |
|---|---|---|---|---|
| `154804` (passed) | +1.94 s | +2.90 s (bind + 0.96) | ~2 frames into the walk | first step straight like a detached player, then slides along the edge |
| `154907` (failed) | +1.75 s | +2.61 s (bind + 0.86) | after the 12 run frames | straight into the void, `P -1` |

`SetPathing(1)` sets the walkmesh flag but does not re-seat a detached controller: `BGI_charSetActive(1)` leaves
`activeTri` at -1. So a player re-attached off the mesh stays off it. The shipped guard is sound; its
docstring's reason ("the pass lands … varies with the load") should say that the Loop starts ~48 ticks late.

### What else keys on the window

For ~48 ticks after `SetModel`, a kit-built player has `isPlayer == false`, `FieldMap.playerController ==
null`, and `controlUID` still 0. This holds on every kit-built field, novel or fork. Only donor-id gates turn
it into a fork problem. (This describes the zero-filled template. After the template fix the player binds on
the first event pass after `Main_Init`, as the real player does. The kit player no longer opens a window the
real field doesn't have; the items below are what that window exposed.)

- **`FieldMapActorController`'s own `if (this.isPlayer)` sites** (input movement, `ccSMoveKey`, running, walk
  speed, ladder flag, virtual analog, `HonoOnGUI` marks, `LoadResources`): each asks about its own controller
  every frame. During the window the player acts as an NPC with no input. But `usercontrol` is 0 then, from
  `Main_Init`'s settle `DisableMove`, so nothing changes; after the bind they behave as on the real field. No
  misfire found.
- **Other code reading a controller's `isPlayer`**: only `DelayedActiveTri` (`FieldMap.cs:143`);
  `MoveToward.cs:141` is commented out. So 2507 is the only `isPlayer` misfire.
- **`playerController == null` crutches, which fire on a fork with a donor row:**
  - 2512 (`SceneService3DScroll`, every frame, `FieldMap.cs:1966`): while `playerController` is null, it sets it
    to `((Actor)GetObjUID(2)).fieldMapActorController`. On a kit-built fork, uid 2 is the first kit NPC or
    nothing, so the camera follows the wrong actor for the window. If entry 2 is absent or not an actor (a
    region), the cast or dereference throws every frame for ~48 ticks. `updatePlayer` overwrites it at the
    bind, so it recovers. Code-read only; no 2512 fork has been benched.
  - 1656 (`EBG_scene2DScrollRelease`, `FieldMap.cs:1495`): the same pattern with uid 8. It fires only if a
    script releases a 2D scroll inside the window.
- **`BgAttachService` (`FieldMap.cs:1611`)** dereferences `playerController` with no null check. It throws
  every frame if a background overlay is attached (`attachCount > 0`) before the bind. This is not a donor gate.
  Code-read only; kit content does not attach overlays in Main_Init.
- **`controlUID == 0`**: `B_PTR(250)` / `GetObjUID(250)` resolve to entry 0. On this bench the `[behavior]`
  code (entry 9) already waits on a flag, 14865, that the player's Init sets right after
  `DefinePlayerCharacter`. Any read of the player in the first ~1.6 s without such a gate (a HUD, a floor
  sensor) reads entry 0 instead. So does the harness, whose `player` is null for the whole window.

### The template fix (done; replaces the guard)

The root cause was in the kit, not the engine, so the fix is in the kit. Owner-approved; made in three parts:

1. **No yields in the player's Init.** `neutralize_player_audio_cruft` now overwrites each stale sound op with a
   `JMP` over its own bytes (`eb.edit.skip_range`: `0x01` + a 16-bit offset, then dead zeros). `bra()` returns
   0, so nothing yields. The player binds on its first Init tick, as the real one does, which is before the
   coroutine can resume. The pass then skips it.
2. **The settle hold moved ahead of Main_Init's `set MAP159 = 1`.** With the player ready on tick 1, its own
   handshake grant (`if (MAP159 == 1 && MAP156 == 0) EnableMove`) would have handed control back during the
   black hold. Previously that grant landed at tick ~49, one tick before the settle's own `EnableMove`, so the
   old order was right only by coincidence. Now Main is "not ready" (MAP159 is 0) for the hold, so the player's
   latch arms MAP158 without granting. Main's own `if (MAP158 == 1)` re-affirm grants when the hold ends. The
   settle adds no grant of its own, and `[player] locked_entrances` needs nothing new: `content.entrylock`
   already gates both template grant sites. A Main_Init without the full handshake keeps the old
   `DisableMove; Wait; EnableMove` before the reveal fade.
3. **The guard is removed** (`content.walkmesh_hotfix.reattach_player`, `build._apply_player_reattach`,
   `build.detaching_donor`). The catalog keeps `detaches_actors`, since it documents the engine pass.

What else it touches: every synthesized field builds different bytes; the vivi-hut golden is re-pinned. A
build with `skip_range` swapped back to the zero fill reproduces the old golden exactly, so the fill is the
only change there (the hut has `entry_settle = 0`). The Loop, where arrival logic runs, now starts right after
the Init instead of ~48 ticks later, still under the settle hold. `content/entry_settle.py`'s 10-tick bind
delay is now roughly true; the proven 45–60 holds were left alone.

Offline: the affected files, then the full suite in this worktree with templates extracted: **9559 passed,
23 skipped, 0 failed**. New pins:
- `test_npcparams`: no `0x00` or `Wait` is reachable before `DefinePlayerCharacter` in the neutralized or built
  player Init. This uses a control-flow walk (`tests/_ebwalk.py`), because a linear disassembly lists the dead
  bytes too.
- `test_entry_settle`: the hold sits before `set MAP159 = 1` with no added `EnableMove`, and the fallback shape
  holds without the handshake.
- `test_control_lock`: the template settle adds no grant; the fallback grant is entrance-gated.
- `test_walkmesh_hotfix`: a 2507 donor, an in-place fork, a BG-borrow and a novel field all build the plain
  idle Loop with a yield-free Init.

**In-game (`root_fix_2507.py`, run `20260923-173057-root-fix-2507`): 9/9, no engine exceptions.** The benches
were rebuilt with the fix and **no guard**, then reverted after the run:

| field | end position | on the walkway | bound → control |
|---|---|---|---|
| 30991, no row | (2173.901, -831.820), moved 290 | yes | 124 frames |
| 30990, editable with row | (2157.431, -869.502) | yes | 130 frames |
| 30992, native with row | (2157.431, -869.502) | yes | 110 frames |
| real 2507 | (2157.431, -869.502) | yes | 4 frames |

On 30990 the HUD reads `P 121, CA -1, CB -1`: the pass still fires and detaches the chests, while the player,
already the player, keeps its triangle. Each kit field publishes its player within 2–4 frames of the switch,
where it used to take ~1.7 s. Control comes back only when the settle hold ends. The 30991 control stopped at
a third edge point (290u, inside the < 300 check; a detached walk covers ~360u). The pass never runs there,
so that is edge-slide variance, as before.

Not covered by the harness: the look of the entry. The black still hides the camera, and the camera can now
start converging ~48 ticks sooner. Whether any hold now reads as too long is the owner's eye.

### The same zero-fill elsewhere

Each of these adds one tick per zero byte to its function. All are length-preserving, and all are commented as
no-ops:
- `eb.edit.nop_range` / `nop_cinematics`: the field-70 New-Game override delays its `Field()` warp by the NOP'd
  cinematics' byte count. Its docstring calls 0x00 "engine-confirmed do nothing".
- `eventscan.py:999`: the carried save-moogle director's `SetBackgroundColor` is zeroed in place, which adds
  ~5 ticks to the director.
- `content.npc`: a carried donor player's `DefinePlayerCharacter` NOP'd to make it an NPC (1 tick).

Harmless where measured, but "0x00 = no-op" is the law behind all four, and it is false.
