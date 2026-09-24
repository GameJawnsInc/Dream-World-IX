# Computed prop motion — the sine kit (board entry #7)

**Status:** rung 0 ★ PASSED in-game (harness, 15/15, every claim backed by a check that can fail). Rung 1 (the kit
feature, `[[prop]] motion`) ★ PASSED in-game (harness, 26/26 on bench 30946/30947). It adds no `[[prop]]` emitter change: the
prop loop only records each mover's seat.

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

Rung 0's proposals. Rung 1 replaced law 1 with THE ORDER LAW, subsumed law 3 into ZERO SHARED STATE, widened law 4
to 0x87 and corrected law 6 to 26 bits; see "Corrections to the rung-0 design" below.

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

## Rung 1 — the kit feature: `[[prop]] motion`

**Status:** implemented in the kit (`content/motion.py`, five `build.py` hooks, the campaign guard,
`ff9mapkit motion`, `tests/test_prop_motion*.py`). **Rung 1 in-game proof: ★ PASSED, 26/26.** The user reference is
[`ff9mapkit/docs/FORMAT.md`](../../ff9mapkit/docs/FORMAT.md) § Computed motion.

### The surface

`motion` is an optional `[[prop]]` table (inline, or `[prop.motion]`). The prop's `pos` anchors it: the orbit centre,
the shuttle start, or the bob/spin spot. The channels compose.

| key | range | meaning |
|---|---|---|
| `radius` | 1..8191 world units | orbit about `pos`; exclusive with `to` |
| `to` | `[x, z]`, each axis at most 16382 from `pos`, not `pos` | sine-eased shuttle; the far end is `pos + 2·trunc((to − pos)/2)`, 1 short on an odd axis difference |
| `period` | 2..8192 ticks | one orbit / shuttle round trip / spin turn / swing cycle; required with `radius`, `to` or `turn` |
| `phase` | [0, 1) | `round(phase·4096) mod 4096` angle units; refused without `radius`, `to` or `turn` |
| `reverse` | bool | counter-clockwise; an orbit or `turn = "spin"` only |
| `height` | ±16383, ABSOLUTE, up-positive | the `0xAD` operand is `−height`; 0 is a flat novel floor |
| `bob` | `{ amp 1..8191, period 2..8192 (default: period), phase }` | vertical sine on its own clock, rising first |
| `turn` | `travel` (needs `radius`) / `spin` (refuses `radius`) / `swing` | absent = no `0x87` at all; the prop keeps its `face` |
| `swing` | 1..127 facing bytes | if and only if `turn = "swing"` |

**Facing.** The prop's `face` (`& 0xFF`) is added to the computed facing: travel `face + 192 + θ/16` (reversed
`face + 64 + θ/16`), spin `face + θ/16`, swing `face + 256 + trunc(SIN[θ]·swing/4096)`. The swing's `+256` centres it
ON `face` and keeps every operand non-negative (≤ 702, so `(Int16)(v << 4)` cannot wrap); the engine takes it mod 256.

**Compass.** Angle 0 is due north of the centre (+z, the far side of an unyawed room), rising clockwise seen from above
(N, E, S, W). Facing bytes also rise clockwise (0 S, 64 W, 128 N, 192 E), so the travel tangent is angle + 192 (C6).
Recipes: facing the centre = travel with `face = 64` (192 reversed); facing outward = `face = 192` (64 reversed).

### The compile model

- **One daemon per field**, only when some `[[prop]]` has `motion`: a type-0 code entry with ONE tag-0 function at
  fpos 4, seated by `object.seat_entry` with `loc = 2K` for K clocks.
- **State:** clock k is `Instance.Int16[2k]`, a BYTE offset (the platform-land lesson). One clock per DISTINCT period,
  horizontal and bob periods pooled in first-use order, `c = n mod P`. Periods are exact in ticks and equal periods
  are phase-locked by construction. Nothing lives in Global, Map, flags, the Blackboard or gScriptVector, so nothing
  collides with a flag lane or a donor's Map, and nothing reaches a save.
- **Body:** a prelude zeroes every clock (never relying on constructor zeroing). Then each tick, per mover in TOML
  order: `0xAD MoveInstantXZYEx(uid; X; B; Z)` for a position mover (a path, a bob, or height ≠ 0) and
  `0x87 TurnInstantEx(uid; F)` for a turning one; then every clock `c = (c + 1) % P`; `Wait(1)`; JMP. Write, then
  advance: tick n writes pose(n).
- **Angles:** `a = trunc(c·4096 / P)`, in [0, 4095] since c < P. Forward `(a + p) & 4095` (just `a` when p = 0);
  reverse `(8192 − p − a) & 4095`. Every `B_SIN2`/`B_COS2` argument lies in [0, 4095].
- **Positions:** orbit `X = cx + trunc(SIN[θ]·r/4096)`, `Z = cz + trunc(COS[θ]·r/4096)`; shuttle, per axis,
  `h = trunc((to − pos)/2)`, `m = pos + h`, `X = mx − trunc(COS[θ]·hx/4096)` (θ = 0 is exactly `pos`); `B = −height`,
  minus `trunc(SIN[β]·amp/4096)` with a bob.
- **Self-audit:** `motion.entry_bytes` audits the EMITTED bytes and raises: ops {SET, 0xAD, 0x87, Wait, JMP, RETURN};
  tokens {`const`, the daemon's own clocks at exactly byte offsets 0, 2, …, 2K−2, the arithmetic and trig operators};
  every expression leaves exactly one value (`eb.exprsem`); 0xAD/0x87 aim only at mover uids.
- **Arming:** `motion.arm` is the LAST pass of `build_script`, after every pass that mutates Main_Init (after the
  player-shadow pass). It finds each mover's single `InitObject` in Main_Init, inserts `InitCode(daemon)` right after
  the byte-last one with `edit.insert_in_function`, and re-proves THE ORDER LAW on the result. There is no
  `activate_block` / after-player path: `activate_block` prepends, and the player's `InitObject` precedes the prop
  fillers, so either would arm the daemon first.
- **Build hooks** (`build.py`): `validate` calls `motion.problems(raw, donor=donor_field_id(raw))`; the `[[prop]]` loop
  records `(prop, model, slot)` per seated part; `arm` runs last and its report lines join `warnings` once
  (`build_script` runs once per language); `lint_all` adds `motion.lint_notes`. `motion.py` is pure and never imports
  build.
- **Campaign:** `campaign.lint_campaign` refuses motion on a forked member (`real_id != new_id`). A campaign's
  ForkDonorPatch comes from the manifest, which `donor_field_id` cannot see; `build_campaign` runs that lint first.
- **Report:** the build prints a summary and one line per mover from the predictor: the path, the period in ticks and
  seconds, the bounds and the largest step per tick (each channel over its OWN period, never the lcm), ticks 0-3, a
  shuttle's far end, and `SNAPS` at ≥ 400 u or ≥ 32 facing bytes a tick (the smoother's limits,
  SmoothFrameUpdater_Field.cs:14-16; `lint` repeats it as an advisory). `ff9mapkit motion <toml> [--csv OUT]
  [--ticks N]` prints the same without a build and writes the per-tick path.

### The laws and where each is enforced

| Law | Rule | Enforced at |
|---|---|---|
| NOVEL-FIELD | motion only where the engine's effective id is the field's own. 0xAD's 1207/2456 and 0x87's 103/2456 branches dereference a code entry's null `actor` under a donor id; 0x87 remaps at 504. A custom id never matches a stock id, so the rule is table-free | `motion.problems` from `validate` (so lint, build and the CLI agree); `campaign.lint_campaign`; `arm` re-parses |
| NULL-TARGET | 0xAD has no null guard: every mover exists for the whole visit (no `requires_flag`, `requires_flag_clear`, `attach_to` or `holds`, no composite); mover and daemon slots in 1..249 (250-255 alias the player, the party and self; 0 is Main) | `motion.parse`; `motion.arm` |
| SLOT-MAP | each recorded slot's SetModel is the recorded model: the daemon never moves the wrong object | `motion.init_problems`, in `arm` |
| STRAIGHT-LINE INIT | every op of a mover's Init is in `MOVER_INIT_OPS` (an allowlist, sound where a yield denylist is not); one SetModel before one CreateObject; ends in RETURN | `motion.init_problems`, in `arm` |
| ORDER | exactly one `InitCode(daemon)`, in Main_Init; one `InitObject` per mover, in Main_Init; each mover's `InitObject` dominates the `InitCode` (earlier when in the same block); the `InitCode` dominates every reachable exit; a CfgError refuses | `motion.arming_problems` on the FINAL bytes, in `arm` |
| 64-STRIDE | a STARTSEQ (0x43) from entry S−64 creates a Seq at uid S and disposes what holds it; no mover or daemon slot may sit 64 above an entry that runs one (a ladder climb in the player entry does) | `motion.arm` |
| ZERO SHARED STATE | the daemon's only state is its own clocks: no `obj()` reads, no sysvar, no Global or Map | `motion.audit_body`, via `entry_bytes` |
| REDUCTION + ENVELOPE | trig arguments in [0, 4095]; radius, amp and half-extent ≤ `EXPR_VALUE_MAX // 4096` = 8191; period ≤ 8192, so c·4096 ≤ 2^25−1; every `const` a signed Int16 | `motion.parse` (caps derived from `opcodes.EXPR_VALUE_MAX`); the emitter makes only reduced angles |
| CO-RULES | a position mover needs `collision = false`, an airborne one `shadow = false`; no airborne mover on a `[field] mapconfig` field; ≤ 16 movers, ≤ 8 periods; `[[npc]] motion` refused | `motion.parse`, `motion.problems` |
| PREDICTOR IS THE ORACLE | `motion.pose` is the one owner of the math; the report, CLI, tests and harness all read it | by construction |
| BYTE IDENTITY | a field without motion never reaches `arm`; the prop loop only appends to a Python list | the `any_motion` guard |

### Corrections to the rung-0 design

- **THE ORDER LAW instead of ready bits and a latch.** New objects are appended to the activeObj tail, and an object
  created during a ProcessCode pass first runs the NEXT frame, in list order (Obj.cs:31-46, EBin.cs:115-120). A daemon
  created after every mover therefore runs tick 0 after each mover's straight-line Init has run SetModel and
  CreateObject, so pose(0) lands before the first render. The daemon reads nothing outside its own locals, so the
  latch law holds vacuously. An `IsMovementEnabled` latch would freeze props through every entry cutscene; stock's
  field-64 pulse daemon runs through them too.
- **Per-period clocks instead of one unbounded T.** One tick count grows without bound and, unreduced, feeds `rsin`
  the arguments where float32 and the exact sine disagree. A clock per period, wrapped by `% P`, makes every period
  exact and keeps the predictor an integer table.
- **26-bit, not Int24.** The expression decode is signed 26-bit (`(t0 << 6) >> 6`, EBin.cs:1682); law 6's
  `expr_Push_v0_Int24` is a name, not the bound. The caps derive from `opcodes.EXPR_VALUE_MAX` = 2^25−1.
- **0x87 has donor branches too**, not only 0xAD: 103 and 2456 dereference the null `actor` of a code entry, and 504
  remaps (DoEventCode.cs:1204-1208). Law 4 named only 0xAD's 1207/2456.
- **`edit.insert_in_function` FIXES jumps that straddle the insert point** rather than raising, so a successful insert
  proves nothing about order. Dominance is checked on the final bytes.
- **The reduction census.** On [0, 4095] the engine's float32 `rsin`/`rcos` equal `trunc(4096·sin)`/`trunc(4096·cos)`
  at every angle (0 of 8192 differ), so the reduced path does not depend on the float model. Unreduced they do: the
  first disagreement is 6684, and 433 arguments in [4096, 70000) differ (218 sine, 215 cosine). For A and B the kit's
  reduced model equals rung 0's in-game-proven unreduced formula exactly for n in [0, 770]; they first diverge at
  **n = 771** (B.x: kit −44, rung 0 −43), where rung 0's unreduced angle first reaches a disagreeing `rsin`.
- **Swing is centred on `face`** (`face + 256 + …`). A `face + 128` draft rocked about the opposite direction, and
  every test that only compared the daemon with the predictor passed it. The centre needs a test of its own.
- **Bounds and max step run per channel over its own period, never the lcm.** Two coprime legal periods (8191, and a
  bob of 8192) make a cycle of ~67 million ticks. Facing steps are circular mod 256, so a travel or spin wrap is not
  a 255-byte jump.
- **Airborne movers are refused on an MCF field.** After a battle the engine rebuilds the actor, and `AddFieldChar`
  restores a script's shadow-off only on fields 1508 and 1706 (FieldMap.cs:582-583), so the MapConfigData would
  shadow the mover again.
- **The stale player-bind fact.** Rung 0 measured the kit player binding at frame ~50 (law 1). The kit's player now
  binds on its first tick. It no longer matters here: the daemon never reads the player.

### The in-game proof

Bench [`bench/sine1.field.toml`](bench/sine1.field.toml): field 30946, rung 0's room, authored only with kit `motion`
(A-B = rung 0's orbit pair, C a reversed non-divisor period with a face offset, D a floor shuttle with an odd axis
difference, E a solid reversed spin, F a swing, G the r 8191 26-bit edge, H a static control), and 30947 with the
daemon armed first (the calibration mutant). A study-side observer mirrors each mover's pose with its own tick count,
so every sample must equal `motion.pose(K)`.

**Rung 1 in-game proof: ★ PASSED, 26/26** (`py tools/play.py studies/sine-kit/rung1_motion.py`, run 2).

| Check | Result |
|---|---|
| P0-P3 preflight (served alone; the tested daemon is the shipped one; the ORDER LAW verdict per arm; the daemon interpreted == `path()`) | PASS: both arms served by FF9CustomMap alone; 30946 rebuilt from the toml == the deployed bytes in all 7 languages; the law holds on 30946 and refuses 30947; 512 interpreted ticks == `path()` |
| C0 coverage · C1 exact · C2 still · C3 phase lock · C4 first frame | PASS: 571 distinct K over 600 ticks, 16/16 bob bins; **979/979 samples exact, worst 0**; D, G and the control H never turn; B is A's antipode in every sample; the FIRST band == pose(0) |
| C5 26-bit edge · C6 cadence · C7 horizon · C8 re-entry · C9 battle | PASS: G (r 8191) 304/304 exact; 30.01 ticks/s at FieldTPS 30; 298/298 exact past K 1024; re-entry restarts at tick 0 (first K 4, 309/309 exact); after a battle Main_Init does not re-run and the clocks carry on (Main_Reinit resumes the daemon mid-cycle) |
| C-WALK · CAL · NC-THROW | PASS: the player walks through the shuttling chest (D 75/75 exact meanwhile); the daemon-first arm loses tick 0 to CreateObject and is exact from K 1; no NullReference / InvalidCast / IndexOutOfRange anywhere |

Run 1 was 25/26: CAL predicted the spawn height as the floor (0) but read -32768. 0x1D CreateObject parks a new
actor at y = `POS_COMMAND_DEFAULTY` (32768, `EventEngine.Constructor.cs:11`, `DoEventCode.cs:384`) until its
controller snaps it; the kit is unaffected (tick 0 writes y explicitly). The bench now predicts it; run 2 is 26/26.
After the adversarial review's fixes (no daemon byte changed; P1 re-derives the deployed bytes from the final
kit), run 3 was 25/26: C9's flee never rolled in 60 s and the Goblin won (Game Over), which no motion check depends
on. C9 now fights first (scene 67 is a lone 33 HP Goblin; a win returns through Main_Reinit like an escape) with
flee as the fallback. Run 4, the final code: 26/26 (969/969 exact; C9 via a win, K 230 -> 266).

## Corrections to the board entry

- The tangent is θ + **192**, not + 64 (calibrated on the engine's own walk, C6).
- The mask-and-wrap rationale is moot: one daemon clock needs no per-prop MAP clocks, and the board missed
  `B_SIN2`/`B_COS2`, which slow motion needs.
- A daemon needs a **latch**, not a warm-up: the board's plumbing would have thrown at field entry exactly as run 1 did.
  (Rung 1 needs neither: a daemon that reads only its own locals is ORDERED after its movers, THE ORDER LAW.)
