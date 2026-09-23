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

## Rung 1 — the kit feature

*Design pending.*
