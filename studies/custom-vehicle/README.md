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

## ⚠ The board gate was a NO-OP until 2026-07-26 (a 256× unit mismatch)

The board arm always had a proximity term — a two-sided `B_MINUS`/`B_LT` difference test on X and Z —
but it compared **world-unit** differences against `const4(25600)`, a constant authored as "100 u × 256"
in the **fixed-point** domain that `MoveInstantXZY` args and the gEventGlobal position record use.
`obj(uid).f[0]`/`.f[2]` do **not** return fixed point: `getvobj` case 0/2 (`EBin.cs:1751-1793`) returns
`CastFloatToIntWithChecking(pos[i])`, and that cast (`EBin.cs:1830-1840`) is a plain round-to-int with
**no scaling**.

The overworld spans ~1536 u × ~1280 u, so the largest possible |Δ| anywhere (~2000 u) is still far below
25600 — **every term was unconditionally true, everywhere on the map.** Rung 1's "I boarded at the islet"
proof was consistent with this: it boarded everywhere, and nobody pressed Confirm far away until the
Southern Ring quays existed. Owner symptom: pressing Enter at a quay teleport-boarded the boat.

**Fixed** by replacing that term with an absolute window on the player's position, in the domain the
source proves — inclusive **[452, 532] × [−1170, −1090]**, an islet-sized box around the mooring that
reaches no event tile (nearest quay trigger is 125 u away). `wu()` now sits beside `fp()` in the build
script with the domain trap spelled out. Offline verification replicating the decompiled ops over five
probe points: `range_gate/eval_gate.py`. Full record: REVERT.md §20.

Proper boarding UX — a prompt instead of a bare-Confirm radius, plus shore-legality — is **R5**.

## KNOWN BROKEN (2026-07-26, owner playtest): boarding at the islet no longer fires

The range-gate fix cured the global Confirm hijack (confirmed in-game: no board fires at any quay or in
the open), **but Confirm at the beached boat now does nothing** — the corrected window's TRUE branch
fails in-game even though the offline eval (range_gate/eval_gate.py) passes at the mooring and dock.
Owner ruling: leave it — the boat is DORMANT until the R5 proper-entry rung. Whoever picks that up:
re-derive the window against the player's ACTUAL in-game standing positions at the beach (the offline
eval replicated the engine ops but fed AUTHORED coordinates; the live avatar's f[] values at the
beach were never measured — capture them first, e.g. via a temporary probe arm or the debug menu),
and re-check every eval assumption against a live reading before widening the window. The dismount arm
and moor-home behavior are unaffected.
