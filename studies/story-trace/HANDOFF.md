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

1. **The facing-gate fix** -- spec below. A workflow was building it when usage ran out; it was stopped before it
   edited anything (the worktree was clean at handoff).
2. **Full suite, then merge.** `content/pathfind.py`'s shared `route()` changed on this branch (`leave_wall`, the
   unlinked-edge check), and `build.py` / the behavior autoroute call it, so run the FULL suite `-n 6` before
   merging (this worktree has extracted templates -- `provision.templates_present()` was True; a fresh worktree
   needs `py -m ff9mapkit extract-templates` or it silently skips the core). Domain tests alone:
   `cd ff9mapkit && py -m pytest -q -p no:cacheprovider -n 6 tests/test_harness.py tests/test_route_avoiding.py tests/test_storytrace.py`
   (494 at handoff) and `py studies/story-trace/rung3_dryrun.py` (80/80; it reads session 2 from the main repo's
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

## THE FACING-GATE SPEC (from the 116-miss diagnosis, workflow `wf_e30deb95-606`, section 4-6)

Of 116 misses in sessions 1-3: 2 were the walker pinning him at 350 -> 355 (fixed, `3641b126`); **23 are the facing
gate**; the rest are real (353 is a bounce room -- its arrival scene puts him back, 54; 350 -> 358 is object 34's
Range at SC 2600 then scene-gated region 25, 32; 5 are the 353 door step's ~34u standable wedge).

- **The gate.** Every stock 350 door's region tag 2 checks, after `CalculateExitPosition`, that the player FACES
  within +-48/256 of a turn (+-67.5 deg) of the bearing to his projection onto the region's FIRST edge (q0 -> q1);
  if not, it resets and returns -- nothing fires, and the region re-tests while he stands in it.

  | Region entry | Door | .eb offsets |
  |---|---|---|
  | 18 | 351 | 11123 / 11149 / 11164 |
  | 20 | 353 (the one armed below SC 2990) | 12110 / 12136 / 12151 |
  | 22 | 356 | 12979 / 13005 / 13020 |
  | 23 | 355 | 13407 / 13433 / 13448 |

  Engine: `DoEventCode.cs:2247-2275`, `EBin.cs:1811-1826` and `1207-1216`, operators 0x18 `B_LT`, 0x19 `B_GT`,
  0x28 `B_OROR`. A region fires only under user control and only the FIRST armed region containing him
  (`EventEngine.TreadQuad.cs:12-19`, Init order `Obj.cs:31-37`); membership is a fan of consecutive vertex
  triplets (`TreadQuad.cs:24-39`). Facing turns 40% toward the pressed direction per moving frame and holds while
  he stands (`FieldMapActorController.cs:749-796`).
- **The harness defect.** `_walk_leg` (tools/harness/session.py) returns "arrived" the moment he stands in the
  zone and never turns him, so he stands facing wherever the walk left him; `dali_tour.failure()` then scores a
  REAL miss (inside, nothing fired). 350 -> 351 missed this way in 10 of 10 session-2 runs; a calibration probe that
  pressed toward the door from the same spot fired it at once. It made 351/356 "unreachable" in whole runs.
- **The fix plan.** In route_cross (or where `_walk_leg` returns in the zone): if nothing fires within a few
  frames, press ONE short walked hold toward the q0 -> q1 projection, its line kept inside the zone (better: make
  the final approach arrive heading at the door). `eventscan.scan_gateways` keeps q0/q1 as `zone[0]`/`zone[1]` --
  verify end to end. **Test first:** `FakeGame._enter_regions` (`tools/harness/fakegame.py` ~969-985) fires on
  centre-inside today, so a facing test could never fail -- teach it the facing gate and the first-armed-region
  rule first. A door that stays shut while he stands inside FACING it stays a REAL miss; record `faced` / the
  bearing error so a reader can tell the two. Worth a census first: how common the idiom is across the ~674 stock
  fields (and its variants), so the harness rule is the stock rule, not Dali's.
- **Smaller findings from the same diagnosis:** `eventscan._zone_quad` cuts 5-point SetRegions to 4 while the
  engine tests the triplet fan -- 356's exits to 350/353 have 1464/626 standable 8u points in the fan's dead zone
  (a latent miss); at SC 2600 the working 358 door is object 34 (a Range the planner avoids), not region 25;
  `failure()` labels the 353 bounce "miss" (same cap, wrong name).

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
