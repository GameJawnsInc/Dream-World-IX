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
it into a fork problem.

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

### A template fix instead of the guard (not made; owner's call)

The root cause is in the kit, not the engine. `neutralize_player_audio_cruft` could remove the eight sound ops,
or overwrite each with a jump over its own bytes (`0x01` + a 16-bit offset; `bra()` returns 0, so it does not
yield) instead of zeros. The player would then bind on its first Init tick, as the real one does. That comes
before the coroutine can resume, so the pass would skip it and `reattach_player` would become redundant.

It moves the bind ~48 ticks earlier on **every** kit-built field, so it is not a local change:

1. **Control during the entry-settle black hold.** `Main_Init` runs its settle `DisableMove; Wait(N)` on the
   first pass. The player's Init then passes the `Map.Bit[159] == 1 && Map.Bit[156] == 0` check and runs
   `EnableMove`, which would hand back control during the black. Today that `EnableMove` lands at tick ~49,
   one tick before the settle's own at `Wait(50)`, so the current order is right by coincidence. A fix needs a
   gate, e.g. the settle holding `Map.Bit[156]` for its duration.
2. **Entry-settle calibration.** The camera cannot follow until `playerController` binds.
   `content/entry_settle.py` models a 10-tick bind delay, but the true bind is ~49 ticks. The in-game-proven
   holds (45–60) were measured after the zero fill existed (fill 2026-06-13, rung 7 2026-07-13), so they are
   partly covering this delay. An earlier bind lets the camera start converging ~48 ticks sooner, and the holds
   may carry slack. Needs a look in-game.
3. **Anything in the player's Loop** (the 2507 guard, arrival logic that runs there) would start ~48 ticks
   sooner relative to `Main_Init`.
4. Byte-exact build goldens and the tests pinning the zero fill change.

Suggested first check, one change per test: rebuild 30990 with the jump fill and **without** the guard. Expect
`player.x` right after the load hitch, the HUD at `P 122` after 3 s, and the walk stopping at the edge.

### The same zero-fill elsewhere

Each of these adds one tick per zero byte to its function. All are length-preserving, and all are commented as
no-ops:
- `eb.edit.nop_range` / `nop_cinematics`: the field-70 New-Game override delays its `Field()` warp by the NOP'd
  cinematics' byte count. Its docstring calls 0x00 "engine-confirmed do nothing".
- `eventscan.py:999`: the carried save-moogle director's `SetBackgroundColor` is zeroed in place, which adds
  ~5 ticks to the director.
- `content.npc`: a carried donor player's `DefinePlayerCharacter` NOP'd to make it an NPC (1 tick).

Harmless where measured, but "0x00 = no-op" is the law behind all four, and it is false.
