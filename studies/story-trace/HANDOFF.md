# Story-write trace -- handoff (2026-09-26)

Written when the session's usage ran out, so the next session (possibly on another account) can pick up without
this one's context. The study's own record is [`PLAN.md`](PLAN.md) (rungs 0-3, every session's result and
diagnosis); this file is the open work, where the research lives, and the one spec that exists nowhere else yet.

## Where things stand

- **Branch `claude/story-trace`** (worktree `C:\gd\Dream-World-IX\.claude\worktrees\story-trace-walk`; if the
  worktree was pruned, the branch is the truth: `git worktree add .claude\worktrees\story-trace-walk claude/story-trace`).
  **NOT merged to master since `be9b47b0`** (rung-3 step 1). Everything after it is on the branch only:
  rung-3 retrodiction build, sessions 1-3, the boxed-by-walkers fix, predictions v2 (the replay), the door-pin fix,
  PLAN/brief/memory updates.
- **Rungs 0-3 in-game PROVEN.** Rung 3 = session 3 (`story-rung3c`, predictions v2 sha `d6dd541c`): 17/18 + one
  VOID (R3-NULL-PRE: no stock run gave 355 before 450 -- a Dali child at its door). R3-MIRROR clean once the F0
  side REPLAYS its stock partner's walk. Session 2 (`story-rung3b`, v1 sha `220532a8`) is the 16/18 that found the
  order confound. Both prediction files are sha-frozen (`.gitattributes -text`); never edit them -- a change is a
  new version registered before its session.
- **Engine:** s88 (story trace) + s89 (harness publishes field objects) are in the LIVE install DLL (sha
  `f1fcea745aa651d2`, backups `20260925-152631`), NOT in the shipped engine bundle yet.
- **Deployed in `FF9CustomMap`:** 23 fork ids -- 30830 (rung 2's verbatim 552) and the rung-3 chains 30831-30841
  (F0) / 30842-30852 (F4), `studies/story-trace/rung3_forks.json`. Every session's pre-flight re-verifies them.

## Open work, in order

1. **The facing-gate fix -- BUILT on the branch** (what landed, and what it still does not cover: THE FACING GATE,
   below). Not yet walked in the game: the next session's first crossings of 350 -> 351 are its in-game check.
2. **Full suite, then merge.** `content/pathfind.py`'s shared `route()` changed on this branch (`leave_wall`, the
   unlinked-edge check), and `build.py` / the behavior autoroute call it, so run the FULL suite `-n 6` before
   merging (this worktree has extracted templates -- `provision.templates_present()` was True; a fresh worktree
   needs `py -m ff9mapkit extract-templates` or it silently skips the core). Domain tests alone:
   `cd ff9mapkit && py -m pytest -q -p no:cacheprovider -n 6 tests/test_harness.py tests/test_route_avoiding.py tests/test_storytrace.py tests/test_eventscan.py tests/test_doorface.py`
   and `py studies/story-trace/rung3_dryrun.py` (80/80; it reads session 2 from the main repo's
   `.harness-runs`). Merge from the main repo (`git -C C:\gd\Dream-World-IX branch --show-current` first -- it was
   `master`), `--no-ff` like `be9b47b0`; read `.test-gate/latest.json` before and heed the post-merge ledger.
3. **Optional session 4 -- needs the OWNER's go (the standing rule: never launch the harness without it).** On the
   fixed walker (door pin + facing), for three stock runs that enter 355 before 450, turning R3-NULL-PRE's VOID
   into a verdict. `PYTHONUNBUFFERED=1 py tools/play.py studies/story-trace/rung3_trace.py --label story-rung3d
   --timeout 240` (v2 is the default predictions file; ~1.5 h; the analysis alone, offline:
   `py studies/story-trace/rung3_trace.py --analyse <run dir>`). Archive the run dir to the main repo's
   `.harness-runs` the moment it ends (the install is shared).
4. **Later:** rung 4 (`fork-report`'s story-writes axis -- PLAN.md "Rungs"); s88/s89 into the next engine-bundle
   re-cut (a release -- outward-facing, confirm first); keep or revert the 23 fork ids (owner's call). Unrelated arc
   still pending from this session: the owner playtest of photo-mode bench 30956 (`studies/photo-mode/PLAN.md`).

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
- **Still open.** (1) The prediction is open-loop: reading s90's `player.face` (and its `turn` verb, an in-place turn)
  would make it measured -- the harness side of s90 is unbuilt. (2) The walk's finish still targets the kit's quad:
  a walk can end in a 5-point region's dead middle, which the step reads LIVE (no Dali gated door has standable dead
  middle; 8 stock gated rows elsewhere do). (3) At 350's door to 353 the wall-slide bound refuses every press from
  the tour's goal pocket (LIVE; a replay steps back and walks in again) -- a slide bound that knows the wall's line
  would open it. (4) Not modelled: the class-3 fixed-window doors (Lindblum cabs, castle lifts -- most need a
  Confirm tap), 1458 e11 / 3057 e10 (whose gate is live only on the polygon tag 0 switches to), and the ~40 other
  region sites that read the facing some other way. (5) WALK_SPEED is a 60 fps bench constant: on another refresh
  rate the calls a frame spends differ (the press check catches a free press that ran short, not one into a wall).

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
