# The custom-vehicle bench — the crimson Blue Narciss on WORLD11

A boardable custom boat authored into world state **9011** (`EVT_WORLD_WORLD11`), as the proving
ground for the overworld vehicle lane. Built by `build_boat_world11.py`; hull minted by
`mint_boat.py` (`GEO_SUB_W0_DWX`, model id **6321** — a crimson-shift of the stock Narciss on the
same rig, so clips 5143/5145 still resolve).

## What is on the bench

| piece | where |
|---|---|
| the boat actor | WORLD11 **entry 15**, uid 15 — Init (tag 0, verbatim-adapted from WORLD03 entry 6) + the board/dismount loop (tag 1, ours) |
| the shore-snap | entry 14 **tag 60** — `DetachObject(14)` + `MoveInstantXZY(DOCK)`, runs ON the player anchor |
| the spawn | entry 0 tag 0 gains `InitObject(15, 0)` |

Bench geometry, measured from the stock mesh (`find_dock2.py`): the block-**(7,17)** islet's land
spans z −1128…−1104; its sand (topo 31) runs x 478…502, z −1126…−1116 — a southwest-facing beach.
`BOAT_SPAWN = (492, −1130)` beaches the hull nose-on-the-sand (stock's own boarding model, per the
owner) and `DOCK = (493, −1114)` is the walkable land centroid.

**Position is hard-coded.** An earlier build persisted the parked position through the stock boat
record `Global[74..82]` behind a safe-band seed bit; that is only sound in a fresh session — a real
save holds live gameplay state in those bytes, and the boat parked at garbage after relaunch
(in-game 2026-07-22). Parked-position persistence returns in a later rung with kit-allocated storage.

## ⚠ v1 dismount = MOOR-HOME (as of 2026-07-26)

**v1 parked the boat WHERE IT FLOATED** and snapped only the player to `DOCK`. That left the boat's
own per-frame **bare-Confirm board check** (`0x24000`, ~100 u radius) sitting wherever the player had
last sailed — including alongside a Southern Ring quay, where it **raced that quay's confirm gate**:
pressing Enter at an entrance *sometimes* boarded the boat instead of entering the field (owner
playtest, 2026-07-26).

**v1.1 moors the boat home.** The dismount branch now also returns the BOAT to `BOAT_SPAWN` /
`BOAT_FACE` after the detach + player-snap, so the board check can only ever fire at the islet —
125 u+ from any quay, and the two gates can never overlap. Two ops, +24 bytes:

```
DetachObject(14)
RunScriptSync(6, 14, 60)                     # player -> DOCK  (unchanged)
MoveInstantXZY(492, 200, -1130)              # <-- NEW: the boat -> its mooring
TurnInstant(0)                               # <-- NEW
SET(Global.Byte[190] = 0)                    # (unchanged from here)
```

**The load path needed no change** — verified from the deployed bytes, not assumed. The Init's tail
`MoveInstantXZY` sits at the label **both** branches merge into (the mode-7 attach arm `JMP`s to it),
and there is **no `Global[74..82]` parked-record read anywhere in entry 15**, so a world load already
re-moors unconditionally.

Applied by **editing the live deployed dispatchers in place** (`eb.edit.replace_function_body`, entry
15 tag 1), each language patched from **its own** bytes — the deployed WORLD11 carries Southern Ring
R1/R2 surgery that this script's baseline predates, so a wholesale re-run would have clobbered it.
JP's file is legitimately 12 B smaller than the rest. Before/after disassembly and the write-set
proof: `moor_home/`. Full record: `studies/overworld-topography/southern-ring/REVERT.md` §19.

Proper boarding UX — a prompt instead of a bare-Confirm radius, plus shore-legality — is **R5**.
