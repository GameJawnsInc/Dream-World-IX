# The walkmesh sensor — `B_BGIID` / `B_BGIFLOOR`: ask the engine which triangle an actor stands on

**Origin:** board entry #2 of [`../eb-uses-board/BOARD.md`](../eb-uses-board/BOARD.md) (also its cheap first move
#1), picked over the six other open entries by a grounded assessment (8 assessors + a judge): stock engine, no DLL,
provable unattended by the harness against an exact offline oracle, and it gates the most downstream work.

Two expression tokens, decoded and emitted by nothing in the kit, hand a script the walkmesh **triangle** and
**floor** under an actor — a value the engine already recomputes every frame. Path B was falsified on *computing*
point-in-region in RPN; this computes nothing, it reads the engine's own collision result.

## The mechanism (source-verified)

- `B_BGIID` (0x70) / `B_BGIFLOOR` (0x71), arity 1, READ (`eb/_exprtable.py`, `eb/exprsem.py`) →
  `EventEngine.DoCalcOperationExt.cs:37-44` → `BGI.BGI_charGetInfo(uid)` (`BGI.cs:11-20`) →
  `EventEngine.getActiveActorByUID` (`cid == 4 && obj.uid == uid`, `EventEngine.cs:397-406`) →
  `fieldMapActorController.activeTri` / `activeFloor`.
- **The operand is a RAW uid.** 250 is not translated there; only `B_PTR(n)` goes through `GetObjUID`
  (`EBin.cs:1138-1146`, `EventEngine.cs:946-958`). So the player is `B_PTR(250) B_BGIID`; a unit is
  `const(<its entry slot>) B_BGIID` (uid == entry slot for kit NPCs). **The board's own rung-0 line,
  `const(0) B_BGIID`, reads the Main entry (uid 0, cid 2) and returns −1 forever.**
- No match → the outputs keep their initial **−1** (`DoCalcOperationExt.cs:8-9`); `[NUMB]` renders "−1" literally
  (no clamp needed on a `[NUMB]` row — the clamp belongs to `[TEXT=]` indices only).
- `activeTri` is the triangle's **file-order id** (`BGI_DEF.cs:52`), GLOBAL across floors; `activeFloor` the
  floor's list position. The engine indexes `WalkMesh.tris` by id, so a `.bgi` must list its triangles **floor by
  floor** (the kit keeps OBJ face order — author faces floor by floor, never reopen an `o`).
- The engine re-triangulates every frame while pathing is on (`UpdateActiveTri`); with two or more containing
  triangles (an edge, an XZ overlap) it keeps the **previous** one — history, not geometry.
- **The harness's `state.player.tri/floor` are dead**: PosObj fields written only by the battle backup
  (`EventEngine.cs:1441`) — 0/0 before any battle, frozen after one.

## Rung 0 — read it back in-game

Bench [`bench/bgi0.field.toml`](bench/bgi0.field.toml) (30910): two floors split at x = 0 (16 triangles, floor 0 =
0..7, floor 1 = 8..15; separate vertices + a links file, the stock seam shape), a parked-then-wandering rover
(uid 2), a static statue (uid 3), and a HUD strip reading the triangle/floor of the player, the rover and the
statue plus two negative controls (`const(250)`, `const(0)`). `rung0_bgi.py`'s oracle is the kit's
`BgiWalkmesh` point-in-triangle over the DEPLOYED `.bgi` at each actor's true position (the settled published
player x/z; the rover's `.eb` position mirrors), scoring only points ≥ 3u from every triangle edge.

**Rung 0 ★ PASSED in-game (43/43, one launch, unattended).**

| Check | Result |
|---|---|
| P1-P4 preflight | the DEPLOYED `.bgi` lists 16 triangles floor by floor (0..7, 8..15), `floor_ndx` == membership; the deployed `.eb` carries all eight HUD statements; the real build seats rover at uid 2 and statue at uid 3; both placements lie ≥ 177u inside one triangle |
| A0 negative controls | `const(0) B_BGIID` (the board's line — uid 0 is the Main entry) **−1**; `const(250) B_BGIID` (250 untranslated — the operand is RAW) **−1** |
| A0 the static statue | **10 / 1** — its placement triangle and floor, never having moved (CreateObject alone activates tracking) |
| A0 the parked rover / the player at spawn | **4 / 0** and **3 / 0** — the oracle's answers |
| A1 14 player stops, 13 triangles, the seam crossed both ways | every PTRI/PFLR == the oracle at the settled position (margins 144-181u); **floor-1 stops read 8..15 — the ids are GLOBAL**, a per-floor index would read 0..7 |
| A1 the `.eb`'s own `obj(250)` mirror | equals the harness position at every stop (to the unit) |
| A2 the seeded rover wandering | 20 dwell samples, all UTRI/UFLR == the oracle at its mirror, **both sides of the 4/5 diagonal** (margins down to 9.2u) |

Run 1 was 42/43: one check read the player mirror from a state sampled before the ticker's warmup (0, 0) — a check
ordering bug, fixed; the same mirror matched at all 14 stops. Artifacts: `.harness-runs/20260923-094949-bgi-rung0`,
`.harness-runs/20260923-095214-bgi-rung0-r2` (archived into the main repo's `.harness-runs/`).

**Free rider — #9's kit-wide question, answered:** actors on a kit-built field cast **no shadow** (no blob under
the player, the rover or the statue in `shots/1-spawn.png`, zoomed). The kit never emits `SetShadowSize` (0x81)
and `FF9Shadow` defaults to zero scale — a visual gap in every novel field, independent of this arc.

## Rung 1 — the kit feature ★ PASSED in-game (63/63)

Designed by a 3-angle panel + judge + completeness critic (14 findings folded in); built in three parallel
pieces (the sensor core here; the floor-major guard and the fork lint in isolated worktrees, each independently
reviewed and its minor defects fixed after merge).

**What shipped** (docs: [BEHAVIOR.md § Floors](../../ff9mapkit/docs/BEHAVIOR.md#floors--on_floor--same_floor--other_floor)):

- **`on_floor` / `same_floor` / `other_floor`** conditions and a **`floor:<who>`** HUD source. THE SENSOR-MIRROR
  LAW: `B_BGIFLOOR` runs only in the ticker's mirror block (the player via `B_PTR(250)` behind the staged latch; a
  unit via `const(uid)` inside its active gate, with an INACTIVE ARM writing −1); conditions read Int16 mirrors.
  THE UNKNOWN-FLOOR LAW: −1 is never a floor, `Invert` refuses a sensor, `not_*` forms are refused by name; Main_Init
  presets −1; a pooled unit's activation seeds its floor from the player's. Floor NAMES come from the OBJ's `o`/`g`
  lines and resolve against the SHIPPED mesh. Lazy: a field with no floor verb compiles byte-identically.
- **THE FLOOR-MAJOR TRIANGLE LAW:** the engine indexes its triangle list by id, so `bgi.build` now regroups an
  OBJ's faces floor by floor (identity on every existing mesh — 40 repo meshes byte-identical, 674/674 stock
  `.bgi` floor-major), a shipped non-floor-major `[walkmesh] bgi` is refused, `walkmesh verify` prints the floor
  table, and a multi-word floor name is kept whole (it used to truncate and silently merge floors).
- **THE FORK WALKMESH-LITERAL LINT:** donor code (every carried lane + the engine's per-field C# hotfixes that fire
  on forks) that keys on walkmesh triangle/floor literals warns when a fork's rebuilt mesh moved them — decoded,
  level-aware (a swap of stacked floors is caught), silent on a pure vertex-move reshape; field 116's 20 plank ids
  are all judged moved when one face below them is deleted.
- **Two law fixes:** the player-ref eval law's token list gains `B_ANGLE`/`B_DISTANCE`/`B_FRAME` (gCur casts that
  throw in a ticker Cond) and `B_ANGLEA`/`B_BGIID`/`B_BGIFLOOR`; `_one_verb` probes with `in`, so the field-schema
  harvest finally records the whole condition/action vocabulary (the shipped schema had called `not_near`,
  `any_active`, `have_item`, flee's `to` … unknown keys).
- `behavior lint` sweeps only same-floor pairs for a `same_floor`-gated chase and names cross-floor jams.

**The benches:** [`bench/bgi1.field.toml`](bench/bgi1.field.toml) (30911, v1, floor names) and
[`bench/bgi1b.field.toml`](bench/bgi1b.field.toml) (30912, brains + a class, int floors) on one mesh: rung 0's
vertices with the ground floor REOPENED in the OBJ (the regroup must restore rung 0's numbering) and only the SOUTH
half of the seam linked — the north half of x = 0 is the lip. [`rung1_floor.py`](rung1_floor.py), one launch.

| Check | Result |
|---|---|
| preflight | served by one folder; the deployed `.bgi` floor-major `[[0..7],[8..15]]` == `resolve_walkmesh`; the bench OBJ really is interleaved; the regrouped mesh == rung 0's in-game-proven BGI0 but for the two north-seam links; the deployed `.eb` reads the floor in ONE entry (player `B_PTR(250)`, units `const(uid)`); real uids; every post ≥ 177u inside one triangle |
| A0 boot | player mirror == `floor:player` == the live `B_PTR(250) B_BGIFLOOR` == the oracle; every unit mirror == its post's floor; **NC-UNKNOWN** the dormant ghost reads −1 and `on_floor(who = ghost)` never fires over 60 frames |
| A1 sweep | 15 settled stops (7 ground, 8 terrace, the seam crossed both ways): mirror == live read == oracle floor, PTRI == oracle triangle, and the bell/lamp watchers' `on_floor`/`same_floor`/`other_floor` flags follow the floor at every stop |
| **A2 THE FLOOR LAW** | the player on the terrace, within both ground chasers' near box: **NC-GATE** the ungated hound engages and runs into the lip (x ≤ −80, floor 0 throughout); **the `same_floor` sentry never engages and drifts 0u**; with the player back on the ground the sentry engages and closes 640 → 400 |
| A3 a moving unit | the ferry marches across the seam and back: its floor reads ground → terrace → ground (one rise at x = 80, one fall at x = −63 — AT the seam), its terrace dwell == the oracle, and the clerk's `on_floor(who = ferry)` flag follows |
| A4 pooled | spawned, the ghost reads the player's floor at once (the activation seed) and the lamp fires; killed, −1 (THE INACTIVE ARM) and the lamp stops |
| B brains + class | the pack's members read ground/terrace from their class cells; with the player on each floor EXACTLY the member on it engages (**NC-SWAP**: c0 closes 936u while c1 moves 0; then c1 closes 520u while c0 moves 0); the int-floor bell follows |
| NC-THROW | no NullReference/InvalidCast/IndexOutOfRange through the event engine, the evaluator or the BGI lookup (the ~26 `MovePC` NREs every harness run on this install logs, other arcs' controls included, are baseline) |

Runs 1-2 were 47 and 59/61: the scenario broke off waiting for the hound to walk home (run 1: it stayed wedged at
the lip after disengaging; run 2: home in 30 frames — intermittent, recorded not asserted), then its A3 dwell sample
was taken before the ferry stopped and NC-THROW counted the MovePC baseline — all three scenario faults, fixed.
Artifacts: `.harness-runs/20260923-123833-bgi-rung1`, `…124114-bgi-rung1-r2`, `…124439-bgi-rung1-r3` (archived).

## Rung 2 candidates

- **Region floor gates** (`[[event]]`/`[[gateway]] floor =`): IsInQuad treads fire through stacked floors; stock's
  2952 idiom `B_PTR(250) B_BGIFLOOR const(N) B_EQ` in the handler — with THE STACKED-ZONE LAW (TreadQuad returns the
  FIRST active region, `EventEngine.TreadQuad.cs:6-20`) and gate-before-latch.
- **Geometry-declared triangle zones** (`on_tri`, a tri mirror) — tri ids renumber on any topology edit; zones
  resolved at build from geometry, never hand-written ids.
- **`engage`'s acquire loop** has no floor filter (it pursues the nearest roster member across a terrace).
- The ungated pursuer that stayed wedged at the lip after disengaging (run 1) — a movement behavior to investigate.
