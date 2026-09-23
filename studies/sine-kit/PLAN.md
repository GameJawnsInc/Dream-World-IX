# Computed prop motion — the sine kit (board entry #7)

**Status:** rung 0 ★ PASSED in-game (harness, 15/15, every claim backed by a check that can fail). Rung 1 (the kit feature) is designed
below; it edits the `[[prop]]` emitters, so it lands after the blob-shadow session's `[[prop]]` work merges.

Board entry #7 of [`../eb-uses-board/BOARD.md`](../eb-uses-board/BOARD.md): nothing in the kit moves by
computation. Cutscenes are keyframed walks and platforms ride authored waypoints. This arc makes props orbit, swing,
bob and spiral from `B_SIN`/`B_COS`, driven by one per-field daemon. The pick came from a 7-assessor and judge
workflow over the remaining board entries; the runner-up was #8 photo mode, reframed as the kit's first camera-pan
primitive.

## The mechanism (engine-read, Memoria `Assembly-CSharp`)

| Piece | Fact | Source |
|---|---|---|
| `B_SIN(v)` / `B_COS(v)` | `ff9.rsin(v << 4)`: **256 units a turn** | EBin.cs:1175-1190 |
| `B_SIN2(v)` / `B_COS2(v)` | `ff9.rsin(v)`: **4096 units a turn** (the smooth one for slow motion) | EBin.cs:1087-1100 |
| `rsin(a)` | `(Int32)(Mathf.Sin(a / 4096f * 360f * 0.0174532924f) * 4096f)`: single precision, truncated, amplitude ±4096 | ff9.cs:2124 |
| `B_DIV` | C# integer division, truncates toward zero | EBin.cs:653-665 |
| `B_CONST` | Int16, sign-extended through the Int26 decode | EBin.cs:1235, 1682 |
| `0xAD MoveInstantXZYEx(uid, a, b, c)` | `pos = (a, −b, c)`; turns pathing OFF first (`BGI_charSetActive(0)`); `SetActorPosition` runs OUTSIDE the null guard, so an absent uid throws | DoEventCode.cs:2179-2245 |
| `0x87 TurnInstantEx(uid, angle)` | null-guarded; `rotAngle.y = (Int16)(angle << 4)` as degrees, so the angle is mod 256 | DoEventCode.cs:1192-1213 |
| `obj(uid).f[0..3]` | `pos[0]`, `−pos[1]` (== `0xAD`'s `b` operand), `pos[2]`, facing byte. `f[0..2]` return 0 on a non-actor; **`f[3]` casts to `Actor` unguarded** | EBin.cs:1751-1810 |

## Rung 0 — the probe ★ PASSED (15/15)

The bench is [`bench/sine0.field.toml`](bench/sine0.field.toml) (field 30945): one flat floor, two plain kit
`[[prop]]`s (balloon, cask; `collision = false`, `shadow = false`). [`sine0_bench.py`](sine0_bench.py) deploys it and
then seats one code-entry DAEMON into every language's live `.eb`; it is study-local, with no kit code. Every tick the
daemon mirrors, BEFORE its writes, the clock value the previous writes used plus both props' `f[0..3]` and the
player's facing into Global Int16s. It then advances the clock and re-places the props:

- **A (balloon):** orbit r = 300 around (0, −800), 128 ticks a turn, height 150, facing `2t + 192`.
- **B (cask):** the same orbit half a turn behind A, plus a ±60 vertical bob every 256 ticks (`B_SIN2`).

Every published sample carries its own clock, so `sine0_bench.predict(t)` is an exact oracle.
[`rung0_sine.py`](rung0_sine.py) runs it in one launch.

| Check | Result |
|---|---|
| P0-P2 | 30945 served by FF9CustomMap alone; all 7 language `.eb`s carry the daemon aimed at the real uids (2, 3); the float32 `rsin` predictor is within one unit of float64 over a turn (a sanity check only) |
| LATCH | the gate tick each input first read true, MEASURED: **props ready at tick 2, player bound at tick 50, movement enabled at tick 50**; the latch opened at 50 |
| C0 | coverage: samples span 482 ticks and hit all 16 phase bins of the 256-tick bob cycle (312 distinct clock values) |
| **C1** | every sampled position of both props == `predict(t)`, **EXACTLY: 312/312, worst error 0**. Exact equality discriminates the truncating `B_DIV` (a floor divide differs at about half the samples) and the 256-unit `B_SIN` scale. It cannot discriminate float32 from float64 `rsin`: for t < 771 the `·r/4096` divides absorb every ±1 difference. That is C7's job |
| C2 | both facing bytes == `predict(t)` in every sample; with C6 this makes the +192 offset the tangent |
| C3 | operand order: A's height operand reads back −150 always; B's bob lives only in `f[1]`; both stay on the r = 300 circle |
| C4 | single-daemon phase lock: B is diametrically opposite A in every sample |
| C5 | a reading of C1, not its own check: the mirrors read the event engine's `pos`/`rotAngle` a full frame after the writes, so no walkmesh re-ground or default-position snap moved them. The smoother writes only `go.transform`, so the **rendered** pose is outside this oracle; it was judged by eye from two shots (both props render and move, on opposite sides of the circle) |
| **C6** | the angle convention, calibrated on the engine's own walk (straight stretches, the turn excluded): **east 192, north 128, west 64, south 0, each exact**. So `direction(a) = (−sin a, −cos a)`, and for `x = cx + r·sin θ, z = cz + r·cos θ` with θ rising the tangent is **θ + 192** (the board said +64) |
| **C7** | THE FLOAT MODEL, falsifiable: raw `B_SIN2` at 6684 / 10684 / 13892, where float32 and float64 disagree by one and no divide follows, reads **−3017 / −2579 / 2579 (float32)**, not −3018 / −2578 / 2578 (float64). The build's predictor can print exact paths |
| NC-THROW | no NullReference / InvalidCast / IndexOutOfRange through the event engine or the evaluator |

**Run 1 (11/12) threw at field entry.** The daemon's only guard was a bare `Wait(45)`. It threw 9 times
around the entry: an `InvalidCastException` in `getvobj`, whose `f[3]` cast is unguarded, then a
`NullReferenceException` in `DoEventCode`. The motion checks all passed once it ran.

The cause, found by the probe review (engine-read) and then measured by run 4's LATCH schedule:
- The kit's player Init yields 48 frames of `NOTHING` before `DefinePlayerCharacter`, so the player binds at frame
  about 50.
- The Wait(45) daemon read `obj(250).f[3]` at about 46, while `controlUID` still named Main, a non-actor.
- The props were ready from tick 2.
- Run 1 alone also logged a stray `Scenario counter: 1` line, which hints that the aborted expression left the calc
  stack dirty (not investigated). A daemon must never throw.

From run 2 on, the daemon latches like the behavior ticker's staged latch, plus per-target ready bits:
- `PBOUND` is set right after `DefinePlayerCharacter`;
- `READY_A` / `READY_B` are set right after each prop's `CreateObject`;
- all three are cleared first thing in Main_Init;
- the daemon polls for `PBOUND && IsMovementEnabled && READY_A && READY_B`.

**Run 2 (12/13):** C6's first cut treated `hold()` as blocking; it is not. So it measured through the player's
turning arc and mixed two headings. It passed in run 1 only by catching a mid-turn diagonal. Run 3 (13/13) holds 30
frames, lets the turn finish, and measures a straight stretch.

**A probe review** (2 lenses, 2 skeptics per finding; 4 confirmed, 8 refuted) then showed four claims were stronger
than their checks:
- C1's "float32" (the divides absorb ±1);
- the LATCH `gate > 0` (holds by construction);
- C5's "no smoother drift" (the mirrors never see the smoother);
- the "published transform" wording.

Run 4 added C7 and the measured latch schedule. Its C0 missed a raw count of 200 at 197 samples, because the bigger
watch set slows the polls, so C0 became a coverage check. Run 5: **15/15**. Artifacts:
`.harness-runs/20260923-175115-sine-rung0`, `…-r2`, `…180035-sine-rung0-r3`, `…183105-sine-rung0-r4`,
`…183254-sine-rung0-r5` (archived).

**Cadence:** 0.50 daemon ticks per published frame. A `Wait(1)` daemon ticks at 30 Hz, so 128 ticks ≈ 4.3 s.

## Laws for rung 1 (each enforced at the call site, with a test that bites)

1. **THE LATCH LAW (measured here):** a daemon is LATCHED on what it reads, never timed. The kit player binds at
   frame ~50 (48 `NOTHING` yields in its Init), and reading `obj(250)` before that is what threw. A rung-1 motion
   daemon need not read the player at all. It latches on each target's ready bit, set after its `CreateObject` and
   cleared in Main_Init, plus `IsMovementEnabled`, the settled field. This bench showed the props ready at tick 2,
   so it does NOT prove the ready bits are necessary. They are the cheap guard for a late or gated spawn, and law 2
   refuses those anyway.
2. **THE NULL-TARGET LAW:** `0xAD` has no null guard. A motion prop may not be gated (`requires_flag`), attached
   (`attach_to`), terminated, a behavior unit or a platform.
3. **THE FACING-READ LAW:** `obj(uid).f[3]` throws on a non-actor, so the daemon never reads a facing it did not write.
4. **THE DONOR-BRANCH LAW** (judge, source-read): from a non-actor entry `actor` is null, and `0xAD`'s effective-id
   1207 / 2456 branches dereference `actor.uid`. Refuse motion on forks of those donors, or seat the daemon in an
   invisible actor entry.
5. **Walkers are refused:** `0xBF` re-grounds, and an off-mesh point falls back to triangle 0.
6. `r · 4096` stays inside Int24 (`expr_Push_v0_Int24`); the per-tick step stays small.
7. Use `B_SIN2`/`B_COS2` for slow motion (4096 a turn); `B_SIN` (256) steps visibly at long periods.
8. A field with no motion builds byte-identically.
9. **The predictor is the build's oracle** (C1 + C7): float32 `rsin`, truncating `B_DIV`. A build can print every
   mover's exact path. Beyond t = 771 and at larger radii a ±1 in `rsin` survives the divide, so rung 1's tests pin
   the predictor over whole periods.

## Rung 1 — the kit feature (design)

`[[prop]] motion = { kind = "orbit" | "pendulum" | "bob" | "spiral", center, r, period, phase, height, tangent = true }`,
plus a row form `wave = { every, dphase }` for a phase-locked line. It compiles to the existing prop entries (a ready
bit after `CreateObject`) and ONE per-field motion daemon (latched, `0xAD` + `0x87`, `B_SIN2`/`B_COS2`). `behavior
compile`-style reporting prints each mover's predicted path, since the predictor is exact. Tests: byte pins of the
daemon, the predictor against an interpreter over a full period, a refusal per law, golden identity. The in-game proof
reruns this rung-0 scenario against the compiled daemon. The airborne shadow default is agreed with the blob-shadow
work (airborne kinds default `shadow = false`).

## Corrections to the board entry

- The tangent is θ + **192**, not + 64 (calibrated on the engine's own walk, C6).
- The mask-and-wrap rationale is moot: one daemon clock needs no per-prop MAP clocks, and the board missed
  `B_SIN2`/`B_COS2`, which slow motion needs.
- A daemon needs a **latch**, not a warm-up: the board's plumbing would have thrown at field entry exactly as run 1 did.
