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
tail (tag 1). A kit-built player has no such call, so nothing re-attaches it after the coroutine. It is still
unconfirmed why the kit-built player's `isPlayer` is false at the 0.5 s mark. It is true during play, because
input movement is gated on it.

## The fix: a re-attach guard in the kit-built player's Loop

**First attempt: a fixed one-shot, which raced the pass.** `Wait(30); SetPathing(1)` went at the head of the
player's Loop. It passed one launch: 30990 ended at the real field's spot and its HUD read `P 121`. It failed
the next: 30990 and 30992 ended off the walkway at (2242.9, -990.6) and the HUD read `P -1` after the walk. The
pass lands at a moment that depends on the load, so a fixed delay can come before it.

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
