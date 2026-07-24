# Rung 0 — the design + the golden compile (2026-07-24, offline ★)

Built: **`ff9mapkit/eb/labelasm.py`** (the fort-condor `asm()` promoted verbatim — one
jump encoder for all authored logic) + **`ff9mapkit/content/behavior.py`** (the L1
compiler) + **`ff9mapkit/tests/test_behavior.py`** (12 tests). Full suite 4691 green.

## What compiles today

Nodes: `Selector / Sequence / Cond / Do / Invert / Once / Cooldown`.
Feed actions (ticker writes duty-walk targets): `WalkTo / Hold / Chase / Patrol`
(patrol = per-unit waypoint byte + arrival boxes, 2-8 points unrolled).
Dispatch actions (added per-unit functions, tags 15+, REQ level 4): `SwingAt / Die`.
Perception helpers (mirror-safe by construction): `near / near_point / active /
hp_gt / hp_le / flag / raw(unsafe_ok=)`.
`FieldBehavior.compile()` → `CompiledBehavior{ticker_body, duty_bodies, action_funcs,
main_init, report, stable_hash()}`. The report prints the full blackboard map + action
ids — the ~ Flags debugging guide.

## Design decisions locked at rung 0 (deltas vs the charter)

1. **The Instance-var correction:** the charter hoped unit-private state could live in
   Instance vars. WRONG for the central ticker — an Instance token reads THE EXECUTING
   OBJECT's locals, so anything the TICKER reads/writes (selected, running, timers,
   waypoints, mirrors, targets) must be GLOB. Instance vars remain available for
   BODY-private state only (none needed yet). The blackboard budget carries it fine
   (~24 bytes + 3 flags per unit; defaults start at byte 1220 / flag 8860, above the
   fort-condor hand map, as co-hosting insurance).
2. **THE SELECTED/RUNNING PROTOCOL** — race-free action switching on
   cooperative-abort-only hardware: the ticker writes `selected` (which doubles as the
   live node trace); every dispatch body's loop iteration exits unless
   `selected == my id`, managing `running` (set at entry, cleared at exit); the ticker
   dispatches only when `selected` names a dispatch action AND `running == 0`. A
   deselected body dies within one tick; the replacement starts the tick after. No
   same-level REQ on a busy object, ever.
3. **THE PLAYER STAGED-LATCH** — the generic form of the fort-condor armed-gate: the
   ticker latches a `player.staged` flag the first time `B_SYSVAR[2]`
   (IsMovementEnabled) reads true; the player mirror (uid 250) sits behind the latch.
   The player-ref eval law holds with zero author involvement.
4. **Reactive v1 semantics:** conditions re-read the world each tick; action results do
   not propagate (`Do` must be the LAST child of its Sequence — linted). Sequenced
   multi-action scripts are a later feature (or a custom dispatch body).
5. **The static-fallback lint:** every tree must bottom out in an unconditional
   `WalkTo/Hold/Patrol` so Main_Init can preset the duty target (no garbage-walk on
   frame 1).
6. **`Die` clears `active` BEFORE `TerminateEntry`** — mirrors stop the same tick; the
   dead-uid firewall is ordering, not luck.

## Verification (the golden compile)

`test_behavior.py` walks EVERY compiled body instruction-by-instruction
(`eb.disasm.iter_code`) and asserts every `0x01/0x02/0x03` target lands on an
instruction boundary — the eblint-grade structural check applied to raw bodies (it
immediately caught a test-side API misuse: `jump_target` is a jumps-only API). Plus:
determinism (stable_hash twice), duplicate-feed label uniqueness, decorator compiles,
and the LAW NEGATIVES: Cond refuses object references; `raw()` needs `unsafe_ok`;
Do-not-last refused; non-static fallback refused; `SwingAt(player)` refused; reserved
name + unknown-unit errors; blackboard dedup/alignment/exhaustion (an off-by-one in the
allocator died in this rung — the point of golden tests).

## Deferred to rung 1 (needs a host field)

`install()` — seating the ticker (`content.object.seat_entry` + `activate_block`),
replacing unit tag-1s with duty bodies, `add_function` for dispatch tags, the Main_Init
prepend, and the eblint baseline-diff gate: the exact `swarm_bench.patch_eb` shape,
generalized. Then the first tree in-game: patrol → notice → approach → resume, on a
fresh bench id.
