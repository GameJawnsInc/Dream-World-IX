# Story-write trace -- handoff (2026-09-27)

Rewritten at the end of the facing-gate session so the next session (possibly on another account) can pick up
without its context. The study's own record is [`PLAN.md`](PLAN.md) (rungs 0-3, every session's result and
diagnosis); this file is the open work and where the research lives.

## Where things stand

- **Merged to master** (branch `claude/story-trace`, worktree `C:\gd\Dream-World-IX\.claude\worktrees\story-trace-walk`)
  after the full suite: rung-3 retrodiction build, sessions 1-3, the walker fixes (boxed-by-walkers, door pin), the
  facing-gate fix and its s90 closed loop, predictions v2, PLAN/brief/memory updates.
- **Rungs 0-3 in-game PROVEN.** Rung 3 = session 3 (`story-rung3c`, predictions v2 sha `d6dd541c`): 17/18 + one
  VOID (R3-NULL-PRE: no stock run gave 355 before 450 -- a Dali child at its door). R3-MIRROR clean once the F0
  side REPLAYS its stock partner's walk. Session 2 (`story-rung3b`, v1 sha `220532a8`) is the 16/18 that found the
  order confound. Both prediction files are sha-frozen (`.gitattributes -text`); never edit them -- a change is a
  new version registered before its session.
- **Engine:** s88 (story trace) + s89 (harness publishes field objects) + s90 (harness publishes the facing, `turn`
  in place) are in the LIVE install DLL (sha `ba9762423da8f3d7`, backups `20260926-171239`, built by the owner),
  NOT in the shipped engine bundle yet. s90 is proven in the game (`story-facing-check` 8/8, 2026-09-27).
- **Deployed in `FF9CustomMap`:** 23 fork ids -- 30830 (rung 2's verbatim 552) and the rung-3 chains 30831-30841
  (F0) / 30842-30852 (F4), `studies/story-trace/rung3_forks.json`. Every session's pre-flight re-verifies them.

## Open work, in order

1. **DONE: the in-game check** (owner's go, 2026-09-27): `studies/story-trace/facing_check.py` 8/8
   (`.harness-runs/20260927-110005-story-facing-check`) -- the rung-3 miss measured at 350's door to 351 (inside the
   region 113/256 off, shut 90 frames), then the closed loop turned him in place (0.0u) and crossed; and one tour on
   the fixed walker, `rung3_step1.py` 7/7 (`20260927-110443-story-facing-tour`), no facing miss. PLAN.md has the
   numbers and the honest limits (the tour's gated doors all opened DURING the walk; the render rate, below).
2. **Optional session 4 -- the owner's go.** On the fixed walker (door pin + the closed-loop facing), for three
   stock runs that enter 355 before 450, turning R3-NULL-PRE's VOID into a verdict. `PYTHONUNBUFFERED=1 py
   tools/play.py studies/story-trace/rung3_trace.py --label story-rung3d --timeout 240` (v2 is the default
   predictions file; ~1.5 h; the analysis alone, offline: `py studies/story-trace/rung3_trace.py --analyse <run
   dir>`). Archive the run dir to the main repo's `.harness-runs` the moment it ends (the install is shared).
3. **Later:** rung 4 (`fork-report`'s story-writes axis -- PLAN.md "Rungs"); s88/s89/s90 into the next engine-bundle
   re-cut (a release -- outward-facing, confirm first); keep or revert the 23 fork ids (owner's call); the facing
   gate's open items below. Unrelated arc still pending: the owner playtest of photo-mode bench 30956
   (`studies/photo-mode/PLAN.md`).

## THE FACING GATE (landed on the branch; the settled rule and what is still open)

Of 116 misses in sessions 1-3: 2 were the walker pinning him at 350 -> 355 (fixed, `3641b126`); **23 are the facing
gate**; the rest are real (353 is a bounce room -- its arrival scene puts him back, 54; 350 -> 358 is object 34's
Range at SC 2600 then scene-gated region 25, 32; 5 are the 353 door step's ~34u standable wedge).

- **The rule** (`ff9mapkit/content/doorface.py`, engine lines cited there at STOCK 6b8bb2d5). On 102 stock gateways
  in 81 fields -- 6 of 350's 9 walk-in doors (regions 18-23: to 351, 354, 353 twice, 356, 355), and 351 e18,
  353 e15, 356 e15 -- the region's tag 2 computes the exit position (his projection onto the region's FIRST edge
  q0 -> q1, clamped to the segment) and runs the warp only while his yaw is within 47/256 of a turn of the bearing
  to it: `v = (facing - bearing) & 255`, fired iff `v < 48 || v > 208`, both strict (+-66.1 deg). The yaw turns
  40% a MovePC CALL toward the pressed direction -- one call a 30 Hz tick walking, two running, in WHOLE calls --
  before the walls have their say (a press into a wall turns him), and holds while he stands. Region membership is
  the triangles `(q[i], q[i+1], q[i+2])` mod n, NOT a fan from q0: a 5- to 8-point region has a dead middle. The
  gate is re-tested every tick he stands in the region with control. `player.dir` is 0 on every field; memoria-patch
  s90 (now live) publishes the real yaw as `player.face`, which the harness does NOT read yet.
- **What landed.** `content/doorface.py` (the engine math, the math atan table -- never the game's);
  `eventscan.scan_gateways` rows carry `region` (every SetRegion point) and `face_gate` (per warp, by control flow);
  FakeGame models the gate opt-in (`regions` `"face"`, `"points"`, `"to": None`, `tick_phase`); route_cross takes
  the door's `gate` and `region` (the tour reads both from the running bytes, `Tour.door`) and route_to ends a walk
  that stands IN a GATED door's region with nothing fired with a press that turns him to face it
  (`Session._face_the_door`). The press counts only the whole calls it is sure of, keeps him in the region to the
  call that faces it (a wall slide bounded), keeps every zone and object clear over its whole travel (tail and
  slides included), and is checked against what it moved him. Ungated doors are never turned to. `failure()` reads
  a gated door he stood in and never faced as LIVE (`unfaced()`), a replay steps back before retrying it (LIVE of
  them fail the step), and a faced door that stayed shut is the door's MISS; the 353 bounce reads "bounce".
- **The closed loop (s90).** On an engine that publishes `player.face` (State.facing_status "known") the step turns
  him IN PLACE (`Session.turn_in_place`, the agent's `turn` verb: the direction keys held, no analog axis, so the
  engine lerps his yaw and zeroes the step) and judges the door by the MEASURED byte in `turn_end` (polled past the
  ack, never read before its own request's receipt): the field changing is the door; in the strict window and still
  shut is the door's MISS (`face_measured` True); out of it turns again; a cut or a refusal a press would share is
  waited out, never a strike; control gone on an unchanged field is no door. The walked press above stays as the
  fallback only for a pre-s90 engine or `[AnalogControl] Enabled=0` (an overlapping body is waited for once first).
- **Still open.** (1) THE RENDER RATE -- addressed by the driver's tick clock (`tools/harness/tickrate.py`): the
  steady rate is ~31 or ~60 fps per launch (the quoted 28-53 were ring averages over field loads), and the driver no
  longer holds movement per frame -- it measures the rate from the state file's write times and plans every press in
  30 Hz ticks (sized at the average, rules at the most a press can reach, sure counts in whole ticks, a run's calls in
  pairs), the turn's calls read off its yaws where the heading allows. In the game at ~60 fps (2026-09-28, the tick
  clock measured 59.9, band 55.9-65.9 from mtimes): `facing_check.py` 8/8 and a tour 7/7 (holds reversing 6.6%, no
  waits, no cleared stalls, never boxed -- as clean as the best 58 fps run). NOT YET in the game at ~31 fps, the
  regime the old constants got 2x wrong: that launch ran at 60 (the regime varies by launch, cause unknown); a
  launch with `[Graphics] FieldFPS = 30` (the shared install's ini -- owner's call) or the next natural ~31 one shows
  it. (2) The walk's finish still targets the
  kit's quad: a walk can end in a 5-point region's dead middle, which the step reads LIVE (no Dali gated door has a
  standable dead middle; 8 stock gated rows elsewhere do). (3) On a pre-s90 engine, 350's door to 353 is still
  refused from the tour's goal pocket by the wall-slide bound (LIVE; the in-place turn faces it). (4) Not modelled:
  the class-3 fixed-window doors (Lindblum cabs, castle lifts -- most need a Confirm tap), 1458 e11 / 3057 e10
  (whose gate is live only on the polygon tag 0 switches to), and the ~40 other region sites that read the facing
  some other way. (5) (WALK_SPEED, the 60 fps bench constant, is gone with (1): a walked press's calls are the whole
  ticks its frames are sure of at the measured rate, and the movement cross-check raises on three presses in a row
  outside it.) (6) The tour's goal for 350's door to 353, (-1188, 2307), is 77.5u off a wall -- inside the 80u collision
  radius, so the engine pushes him out on his first moving call.

## Where the research lives

- **Committed:** `PLAN.md` (the record), `rung3_trace.py` (module docstring = the session design), the two
  prediction files, `dali_tour.py` / `rung3_step1.py` (the strike rules in docstrings), `rung3_dryrun.py`, and
  [`research/`](research/README.md) -- the design research (the store choke point, the harness agent/API, the
  claim checks), the rung-3 research (the chain and its seeds, the stock Dali morning, the retrodiction design and
  its adversarial check) and the full 116-miss diagnosis.
- **Memory** (shared store): `project-ff9-story-trace.md` (THE PAIRED-WALK LAW and the rung results) and
  `project-ff9-test-harness.md` (the unattended-route laws: walkers, door pins, the facing gate).
- **Machine-local archive, gitignored** -- `C:\gd\Dream-World-IX\.harness-runs\`:
  - `20260926-024923-story-rung3b\` (session 2) and `20260926-101447-story-rung3c\` (session 3): traces, tour logs,
    `rung3_session.json`, reports, frames (`shots\`), the scripts snapshot (game bytes -- never commit).
  - `story-trace-archive\scratchpad\` -- a full copy of the session's scratchpad: `trace\` holds every rung's run
    dir (rung 0 through session 3), the live session logs (`rung3_session.log`, `rung3b_`, `rung3c_`), the rung-3
    design research (`trace\rung3\`, and the `*_v2_*.md` notes), `pred_n1.json` (session 1's exploratory N=1),
    `r4kit\` (the round-4 kit export F4 was built from); `missdiag\` (`classify.py`, `fan.py` -- the 116-miss
    table); `eb350.txt`..`eb450.txt` (Dali disassembly); the review/fix probes of every workflow.
  - `story-trace-archive\workflows\` -- every workflow this session ran: its script (`.js`), `journal.jsonl`, and
    `<id>.results.md` (each agent's full report, readable). The recent ones: `wf_f5fe8160-2ee` boxed-by-walkers,
    `wf_55559065-206` predictions v2 / the replay, `wf_e30deb95-606` the 116-miss diagnosis + the door-pin fix,
    `wf_b4d457ce-760` the facing fix (stopped, empty); earlier ids are rung 0-3 builds and reviews -- the
    `results.md` headers say which.
  - `story-trace-archive\facing-session\` -- the facing-gate session (2026-09-26/27): `workflows\` (the understand
    `wf_0c8b27cc-198`, the build + five-lens review `wf_0a36f57d-e49`, engine patch s90 `wf_5c7015d9-2df`, the s90
    driver `wf_75e5a330-185`: scripts, journals, readable results) and `scratchpad\` (the census data -- game bytes
    in `stock_eb.pkl`/`eb350.bin`/`ratan_tbl.bin`, never commit -- the s90 gate logs, DRIVER.md, the mutation plugins).
