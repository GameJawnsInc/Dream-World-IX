# Story-write trace -- handoff (2026-09-28)

Rewritten at the end of the facing-gate session, and updated after rung 4 and session 4, so the next session
(possibly on another account) can pick up without its context. The study's own record is [`PLAN.md`](PLAN.md)
(rungs 0-4, every session's result and diagnosis); this file is the open work and where the research lives.

## Where things stand

- **Merged to master** (branch `claude/story-trace`, worktree `C:\gd\Dream-World-IX\.claude\worktrees\story-trace-walk`)
  after the full suite: rung-3 retrodiction build, sessions 1-3, the walker fixes (boxed-by-walkers, door pin), the
  facing-gate fix and its s90 closed loop, predictions v2, PLAN/brief/memory updates.
- **Rungs 0-3 in-game PROVEN, rung 4 DONE (the ladder is complete).** Rung 3 = session 4 (`story-rung3d`,
  predictions v2 sha `d6dd541c`): **18/18**. Session 3 (`story-rung3c`) was 17/18 + one VOID (R3-NULL-PRE: no
  stock run gave 355 before 450 -- a Dali child at its door), and session 4 on the fixed walker made it a PASS.
  R3-MIRROR is clean once the F0 side REPLAYS its stock partner's walk. Session 2 (`story-rung3b`, v1 sha
  `220532a8`) is the 16/18 that found the order confound. Both prediction files are sha-frozen
  (`.gitattributes -text`); never edit them -- a change is a new version registered before its session.
  Rung 4 = `fork-report --trace` (merged `3c7fa847`).
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
2. **DONE: session 4** (owner's go, 2026-09-28): `story-rung3d` **18/18**. Every stock run entered 355 before 450,
   and R3-NULL-PRE's VOID is a PASS (214 stock keys before 450, all written by the members; 355's own 12 matched).
   Archived at `C:\gd\Dream-World-IX\.harness-runs\20260928-011959-story-rung3d\`. Rung 3 is closed.
3. **DONE: rung 4** (merged `3c7fa847`): `fork-report <field> --trace <stock runs> [--fork-trace <fork runs>
   --member ...]` shows the traced set difference cut to one field (`docs/FORK_REPORT.md`). On session 3's traces
   the per-field shares partition the whole comparison exactly. A five-agent review's 16 defects are fixed,
   three of them in the reader under every report.
4. **F5, the hub lane under the trace** (branch `claude/story-trace-f5`, this worktree; PLAN.md's F5 section).
   Steps 0-12 are done offline. The build is in `C:\gd\_ns_playtest\f5`. `rung5_hub.py`, `rung5_dryrun.py` (55/55)
   and the FakeGame tests are committed with the frozen predictions v3 (sha `d3ae4121`). **Next, on the owner's go
   with FF9 closed:**
   - master is merged in (`dffd0a22`, deploy_field's claimed microsecond backup stamps), so the batch's
     same-second collision cannot recur; step 14's per-call stamp check still applies;
   - steps 13-15 of the build steps: back up, deploy the 13 ids 31100-31112 additively to FF9CustomMap, and verify
     with `rung5_hub.py --preflight`;
   - step 16: the session, `py tools\play.py studies\story-trace\rung5_hub.py --label story-rung5 --timeout 240`
     (about 67 min; its launch is the one relaunch);
   - step 17: `--analyse`.

   The build steps and the design live in the archive (below). The first real test of the hub leg is P-HUBLEG, run
   before run 1: the spawn stands inside Stiltzkin's collision radius, so the leg calibrates on the hub's twist.
5. **Rung 3's dry-run is 79/80 on master too** (not F5's): session 2's archived reports predate `356ac508`'s seam
   listing. Re-baseline, or compare that line modulo the seam list (owner's call).
6. **Later:**
   - s88/s89/s90 go into the next engine-bundle re-cut. That is a release: outward-facing, confirm first.
   - Keep or revert the 23 fork ids (owner's call). **Do not run their reverts blind -- read
     [REVERTING THE FORKS](#reverting-the-forks-six-reverts-were-half-reverts) first.** Six of them were armed with
     a half-revert. Their backups are now repaired, and the order still matters.
   - An engine tick counter (`ticks`/`rt` in state.json) at the next DLL rebuild, to replace the mtime estimate.
     It matters more now: session 4's render rate flipped between ~60 and ~31 fps four times WITHIN one launch.
   - The facing gate's open items below.
   - Unrelated arc still pending: the owner playtest of photo-mode bench 30956 (`studies/photo-mode/PLAN.md`).

## REVERTING THE FORKS (six reverts were half-reverts)

The 23 forks stay deployed until the owner decides. This is what a revert does now, and how to run it safely.

- **The defect (found 2026-09-28, sweep during the F5 design).** `tools/deploy_field.py` stamped its backups
  (`backups/<file>.preDEPLOY.<STAMP>`) to the second, and the rung-3 batch deployed 22 forks in about 20 s. Six
  pairs landed in one second: 30832/30833, 30835/30836, 30839/30840, 30842/30843, 30846/30847, 30849/30850. In
  each pair the later deploy's backups replaced the earlier one's. By then they held the earlier fork's own
  `FieldScene <id>` line and its `<id> <donor>` ForkDonorPatch row. The earlier fork's revert re-adds every line it
  owns that it finds in its backup (`dictpatch.revert_dictionary_patch`, `forkdonor.revert_row`). So
  `revert_deploy_30832.py` etc. would have deleted the `.eb` and restored the registration, which is the null-.eb
  black screen. The later fork of each pair was never affected. The deploy is fixed (`ff9mapkit.deploybackup`: a
  claimed microsecond stamp, create-exclusive backups), so no new pair can form.
- **The repair (DONE 2026-09-28, no revert run).** `py tools/repair_collided_backups.py --repair 30832 30835 30839
  30842 30846 30849` removed each earlier fork's own line and row from the SHARED DictionaryPatch/ForkDonorPatch
  backups. Each original is kept beside it as `<name>.collided-orig`, and the diff is exactly that line and row.
  The revert scripts themselves are unchanged. The evidence the tool checked for every id:
  - the predecessor snapshot (the previous fork's backup, a second earlier) differs from the shared one only by
    the predecessor's own line and this fork's own line;
  - the ledger shows no prelude revert before the deploy (it could have re-added an older registration);
  - the block-47 `.mes` and JournalPatch snapshots are byte-identical to the predecessor's (30842's block-47
    snapshots are its own, since 30843 is on block 8);
  - the partner reads only its own lines from the shared files, so its revert is unchanged.
  
  A read-only simulation against the live folder gives, for each id: before the repair, the revert leaves
  `FieldScene <id>` and its donor row behind; after it, nothing.
- **Same defect outside rung 3:** 30880 (fight-ledger bench LEDGER1) shared stamp `20260922-232635` with 30883,
  and its backup held `MessageFile 30880` + `FieldScene 30880`. It was repaired the same way with
  `--allow-other-deploys`, because deploy_battle's BattleScene 30871/30872 landed in the gap. It is not a
  story-trace id, so the fight-ledger study owns whether to keep it.
- **To revert (only on the owner's word; never launch the game for it):**
  1. From the main repo, `py tools/repair_collided_backups.py` must print `0 defective` (exit 0). A HALF-REVERT row
     means a backup was restored or re-collided: stop, and `--plan <id>` it.
  2. Run the reverts ONE AT A TIME in REVERSE deploy order, 30852 down to 30830:
     `py tools/scroll_out/revert_deploy_<id>.py`. The dialogue `.mes` and JournalPatch are restored whole from
     snapshots, so last-in-first-out is the order in which every snapshot is the right one. Block 8 depends on it.
     30832 wrote `field/8.mes` fresh and 30843 later wrote the identical bytes over it. 30843's revert restores its
     snapshot (30832's bytes) and 30832's revert then deletes the file. In the other order, or when reverting 30832
     alone, 30832's hash check cannot tell the bytes apart: it deletes the block-8 `.mes` that 30843 still ships
     (redeploy 30843), and a later 30843 revert leaves a copy no revert owns.
  3. The rung-3 scripts import the kit from `.claude\worktrees\story-trace-walk\ff9mapkit`. 30830's (and 30880's /
     30883's) import it from the DELETED `sad-lewin-6cdab0` worktree and fail with ModuleNotFoundError before
     touching anything. Run those with `PYTHONPATH=C:\gd\Dream-World-IX\ff9mapkit`, and do the same for the rung-3
     scripts once `story-trace-walk` is gone.
  4. Check: no `FieldScene 308[3-5]x` line in `<game>\FF9CustomMap\DictionaryPatch.txt` and no `308xx` row in its
     `ForkDonorPatch.txt`. Both files are read at launch, so the registrations drop at the next launch.
  - Redeploying a fork instead is safe either way: its prelude runs its (now repaired) revert first.

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
  waits, no cleared stalls, never boxed -- as clean as the best 58 fps run); and at ~30 fps, forced for one launch
  (`[Graphics] FieldFPS = 30`, `VSync = 0` -- Unity ignores the target under VSync -- the ini restored byte-exact
  after): the clock measured 30.2 / 29.8 fps, check 8/8, tour 7/7, holds reversing 5.3% (the old code at ~31 fps:
  24.0% and 31.6%), no waits, no cleared stalls, never boxed. The fix is proven in both regimes. **Correction
  (session 4, 2026-09-28):** the rate is NOT fixed per launch. It flipped 59.0 -> 31.4 -> 59.7 -> 31.8 fps inside
  one launch. The tick clock caught each flip and re-planned, and the session passed 18/18 across them. CPU load is
  NOT the cause: `studies/test-harness/render_rate_probe.py` held a flat 60.0 fps with all 12 logical CPUs busy
  (`.harness-runs\20260928-092358-render-rate-probe`). The open lead, unverified: both drops came a crossing or two
  after a failed bounce into 353 (Mayor's House), and the rate came back after the return to the title.
  (2) The walk's finish still targets the kit's quad: a walk can end in a 5-point region's dead middle, which the step reads LIVE (no Dali gated door has a
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
  - `story-trace-archive\f5\` -- F5 (`README.txt` maps it):
    - the settled design (`design\design.md`, `checks.json`, `build_steps.txt`, `owner_decisions.txt`; may quote
      `.eb` disassembly, never commit);
    - `cont\fix\freeze_fix.py`, the generator of the committed predictions v3;
    - the gate outputs and mutant harnesses;
    - the design, build and resume workflows (`wf_4574eab4-845`, `wf_134bf773-81f`, the latter killed mid-build,
      and `wf_b80d9ff6-de6`).
  - `story-trace-archive\facing-session\` -- the facing-gate session (2026-09-26/27): `workflows\` (the understand
    `wf_0c8b27cc-198`, the build + five-lens review `wf_0a36f57d-e49`, engine patch s90 `wf_5c7015d9-2df`, the s90
    driver `wf_75e5a330-185`: scripts, journals, readable results) and `scratchpad\` (the census data -- game bytes
    in `stock_eb.pkl`/`eb350.bin`/`ratan_tbl.bin`, never commit -- the s90 gate logs, DRIVER.md, the mutation plugins).
