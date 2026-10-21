# Co-op domain gate: per-test profile

Groundwork for the top recommendations of `studies/workflow-perf/COOP-BUILD-TIMING.md` (on branch
`claude/priceless-wescoff-d1c5a3`, not merged): one full domain gate per build with fast per-stage subsets, which needs
a per-test profile and a `slow_leg` marker, and a fix for the recurring s140-legs flake.

Three results:

1. **The profile.** The domain list ran once, at `-n 6` on an idle machine: 2,854 tests, 42.4 min wall clock and
   223 worker-minutes. 68.6 % of the worker time sits in 264 tests that each run a whole bench leg, story-trace drive
   or rehearsal against the stand-in.
2. **The `slow_leg` marker** labels those 264 tests. `-m "not slow_leg"` keeps 2,590 tests and 4,210 worker-seconds,
   about 12-13 min of wall clock against 42. The two sets split the list exactly. The marker is applied at collection
   from one registry (`ff9mapkit/tests/_slow_leg.py`), not as a decorator, because a decorator would have re-pinned 96
   story-trace tests under G21.
3. **The s140-legs flake** is a sampling race, not slow driver deadlines. The stand-in's green jump is about 12 ms of
   wall clock, and a loaded driver's 4 ms poll misses all of it, or reads its last edge late.
   - Reproduced under load: 43 of 90 runs missed.
   - Fixed in the test's child script with a bounded read handshake. With it, 120 of 120 runs at 3x oversubscription
     saw the jump and measured its landing at exactly one frame.
   - On the real test under 2x load: 6 of 6 green, against 3 of 6 unfixed.
   - Broken on purpose: 30 of 30 runs red.

## 1. The run

- Commit `f6874c9b`, master after the s144 merge. A worktree with the templates extracted (`ff9mapkit extract-templates`),
  so the install-gated slice ran rather than skipping.
- From `ff9mapkit/`: `py -m pytest <18 files> -q -n 6 -p no:cacheprovider --durations=0 --junitxml=profile.xml`.
  Per-test times are the junit `time` of each case (setup + call + teardown), so tests faster than `--durations`' 5 ms
  floor still count.
- The files are the brief's 15 (s143's domain list) plus the 3 that s144 added and that are now on master
  (`test_coop_world_wait.py`, `test_world_coop.py`, `test_world_coop_harness.py`). The next build's list holds all 18.
  The two groups are reported separately below.
- 2026-10-21 12:34-13:17 UTC. The owner cleared the machine. No bench or other `-n 6` run was active at the start
  (CPU 21 %; three orphaned, idle xdist workers from 10-14 and 10-20 were present).
- Result: 2,851 passed, 1 failed, 1 skipped, 1 xfailed in 2,543 s (42.4 min).
  - The one red is not a regression. `test_coop_world_wait.py::test_the_s144_runners_name_every_step` refuses `\r` in
    the s144 runner scripts, and with the system-wide `core.autocrlf=true` and no `.gitattributes` rule for `*.sh`, the
    LF blobs check out as CRLF, in the main checkout too. The s144 merge landed after the 10-21 nightly, so the next
    nightly will hit it as well (see section 5).
  - The 10-21 nightly's three reds did not reproduce: `test_coop_peer.py`'s replay and two `test_harness.py`
    segment-walk tests (`..._walk_loss_in_a_door_...`, `..._bounce_over_inside_the_crossing_wait_...`). That nightly
    ran 92 min against 63 the night before, so it was a loaded night.

| List | Tests | Worker-s | Wall clock at `-n 6` |
|---|---|---|---|
| All 18 files | 2,854 | 13,389 | 42.4 min measured (38.2 min simulated) |
| The brief's 15 files | 2,560 | 9,629 | 26.8 min simulated |
| s144's 3 files | 294 | 3,759 | 11.5 min simulated |

"Simulated" runs the measured per-test times through 6 workers that take the next test in collection order. It
reproduces the measured full run to within 11 % (38.2 against 42.4 min: collection, worker start and xdist overhead
are not in the per-test times), so read every simulated figure as about 10 % low.

## 2. Per file

Worker-seconds, all 18 files, split by the `slow_leg` marker of section 4:

| File | Tests | Worker-s | Share | `slow_leg` tests | `slow_leg` worker-s | Left in the subset |
|---|---|---|---|---|---|---|
| `test_harness.py` | 1,083 | 5,502 | 41.1 % | 117 | 2,285 | 3,217 |
| `test_harness_netsync.py` | 1,126 | 3,272 | 24.4 % | 12 | 2,591 | 681 |
| `test_coop_world_wait.py` (s144) | 97 | 3,010 | 22.5 % | 88 | 2,982 | 27 |
| `test_world_coop_harness.py` (s144) | 173 | 747 | 5.6 % | 31 | 735 | 12 |
| `test_coop_leader_guard.py` | 50 | 663 | 4.9 % | 16 | 586 | 77 |
| `test_dress_census.py` | 18 | 71 | 0.5 % | 0 | 0 | 71 |
| `test_harness_world.py` | 16 | 37 | 0.3 % | 0 | 0 | 37 |
| `test_netsync_bridge.py` | 33 | 18 | 0.1 % | 0 | 0 | 18 |
| `test_harness_duo.py` | 12 | 18 | 0.1 % | 0 | 0 | 18 |
| `test_leader_guard.py` | 19 | 14 | 0.1 % | 0 | 0 | 14 |
| `test_dress_polish_census.py` | 19 | 12 | 0.1 % | 0 | 0 | 12 |
| `test_harness_instance.py` | 30 | 8 | 0.1 % | 0 | 0 | 8 |
| `test_coop_tab.py` | 9 | 7 | 0.1 % | 0 | 0 | 7 |
| `test_coop_peer.py` | 65 | 5 | 0.0 % | 0 | 0 | 5 |
| `test_world_coop.py` (s144) | 24 | 3 | 0.0 % | 0 | 0 | 3 |
| `test_coop_gate.py` | 15 | 2 | 0.0 % | 0 | 0 | 2 |
| `test_coop.py` | 59 | 0 | 0.0 % | 0 | 0 | 0 |
| `test_memoria_stack_replay.py` | 6 | 0 | 0.0 % | 0 | 0 | 0 |
| **Total** | **2,854** | **13,389** | | **264** | **9,179** | **4,210** |

Inside `test_harness.py` (5,502 s), by story-trace rung:

| Group | Tests | Worker-s |
|---|---|---|
| Not a story-trace rung test | 789 | 2,692 |
| O4-O8 drives and rehearsals on the fake (marked) | 117 functions, 2,285 s | |
| O1-O3 tests, all kinds | 116 | 434 |
| O4-O8 tests that are not drives or rehearsals on the fake | 59 | 91 |

## 3. Where the time is

- **The tail is long and fat.** The slowest 10 tests hold 19.6 % of the worker time, the slowest 50 hold 40.1 %, and
  the slowest 100 hold 53.1 %. 104 tests of 30 s or more hold 54 %. 1,067 tests of 1 s or more hold 97.4 %, so the
  other 1,787 tests cost almost nothing.
- **The 30 slowest** (worker-seconds; every one is a whole-leg stand-in run or a story-trace drive or rehearsal, except
  `test_o8_tower_goals_are_height_aware`):

| s | File | Test |
|---|---|---|
| 482 | `test_harness_netsync.py` | `test_each_s140_row_reds_on_its_fault_on_the_stand_in[b]` |
| 465 | `test_harness_netsync.py` | `test_the_s139_leg_runs_green_on_the_stand_in_and_red_exactly_where_its_checks_say` |
| 334 | `test_harness_netsync.py` | `test_each_s140_row_reds_on_its_fault_on_the_stand_in[a]` |
| 256 | `test_harness_netsync.py` | `test_each_s140_lever_reds_exactly_its_rows_on_the_stand_in` |
| 247 | `test_harness.py` | `test_o4_rehearsal_gate_reads_the_pair_on_the_fake` |
| 195 | `test_harness_netsync.py` | `test_the_s140_legs_run_green_on_the_stand_in_and_calibrate_on_s139` |
| 178 | `test_harness_netsync.py` | `test_leg_f_runs_green_on_the_stand_in_and_calibrates_on_s140_s139_and_its_lever` |
| 176 | `test_harness_netsync.py` | `test_each_leg_f_row_reds_on_its_fault_on_the_stand_in[c]` |
| 153 | `test_harness_netsync.py` | `test_every_leg_runs_green_together_on_the_s141_stand_in_and_calibrates_on_s140` |
| 144 | `test_coop_world_wait.py` | `test_f3_drives_the_stock_cycle_and_its_close_leaves_the_map_shut_whatever_the_state` |
| 138 | `test_coop_world_wait.py` | `test_the_instrument_rows_go_red_on_their_own_wrong_shapes` |
| 132 | `test_coop_world_wait.py` | `test_the_bench_closes_a_full_map_that_opened_with_select_never_cancel` |
| 111 | `test_harness_netsync.py` | `test_each_leg_f_row_reds_on_its_fault_on_the_stand_in[a]` |
| 107 | `test_harness_netsync.py` | `test_each_leg_f_row_reds_on_its_fault_on_the_stand_in[b]` |
| 98 | `test_coop_world_wait.py` | `test_the_wait_leg_reads_the_tapes_b6_and_calibrates_on_s143` |
| 97 | `test_coop_world_wait.py` | `test_the_rejoin_leg_is_green_on_s144_and_calibrates_on_s143` |
| 96 | `test_world_coop_harness.py` | `test_the_s143_stand_in_reads_exactly_old_predicted_red` |
| 90 | `test_harness.py` | `test_o4_rehearsal_gate_reruns_what_cannot_witness_on_the_fake` |
| 85 | `test_coop_world_wait.py` | `test_d3_keeps_the_bracket_law_under_a_sampler_that_misses_the_arm` |
| 80 | `test_coop_leader_guard.py` | `test_the_bench_calibrates_on_the_s141_stand_in_and_under_the_lever` |
| 79 | `test_world_coop_harness.py` | `test_each_world_fault_turns_exactly_its_rows_red[rejoin_unarmed]` |
| 78 | `test_harness.py` | `test_o4_drive_paced_policy_lands_in_its_band` |
| 75 | `test_harness.py` | `test_o4_drive_paced_tracks_the_closing_prompt_beside_its_successor` |
| 75 | `test_harness.py` | `test_o4_drive_paced_policy_reruns_only_a_read_gap` |
| 74 | `test_harness.py` | `test_o4_drive_v18_on_what_the_game_shows` |
| 73 | `test_world_coop_harness.py` | `test_each_world_fault_turns_exactly_its_rows_red[rejoin_field_recipe]` |
| 72 | `test_harness_netsync.py` | `test_the_g9_duo_leg_steps_its_phases_and_reads_the_tap_last_against_a_stub_duo` |
| 69 | `test_harness.py` | `test_o8_rehearsal_records_the_knight_the_pinch_and_the_movie_on_the_fake` |
| 68 | `test_coop_world_wait.py` | `test_the_solo_leg_calibrates_on_s143_and_under_the_lever` |
| 67 | `test_harness.py` | `test_o8_tower_goals_are_height_aware` |

- **Every test of 1 s or more** (1,067 rows: seconds, `slow_leg`, file, test) is in
  [`GATE-PROFILE-tests.tsv`](GATE-PROFILE-tests.tsv).
- **`test_harness_netsync.py` splits cleanly.** Its 12 whole-leg tests take 61-482 s each and 2,591 s in all. Every
  other test in the file takes 16 s or less, and the other 1,114 tests take 681 s together.
- **The co-op benches cost far more than the code they check.** Their whole-leg tests are 6,894 of the 7,889
  worker-seconds of the five co-op bench files. The rest of the list (the census, bridge, duo, peer and gate files)
  is 210 s.

## 4. The `slow_leg` marker

**What it marks:** a test that drives a whole bench leg, story-trace drive or rehearsal against the stand-in in
wall-clock time. There are two kinds, both registered in `ff9mapkit/tests/_slow_leg.py` and applied by
`ff9mapkit/tests/conftest.py`:

- **`LEGS`**: the co-op benches' whole-leg stand-in runs, by file and function, with every parametrization:
  - `test_harness_netsync.py`: 9 functions, 12 tests. These are the s138 to s141 legs I, G (with the G9 duo leg),
    S/W/X/N/T and F, each smoked in a child process.
  - `test_coop_leader_guard.py`: 5 functions, 16 tests (s143's bench).
  - `test_world_coop_harness.py`: 3 functions, 31 tests (s144's stand-in bench).
  - `test_coop_world_wait.py`: 15 functions, 88 tests (s144's solo, T2 and duo legs and their faults).

  The brief named the s139-s141 legs. The s138, s143 and s144 legs are the same kind of test, and every one of them
  belongs to an earlier patch for the next build (s145). A build's own new legs can join the registry when they land,
  because a stage subset runs the patch's own files whole anyway (see the usage below).
- **`STORY_DRIVES`**: `test_harness.py`'s story-trace drives and rehearsals on the fake, O4 to O8. The rule is a name
  matching `test_o[4-8]_(drive|rehears)` plus the `game` fixture (the stand-in running), so a new drive is marked when
  it is written. It marks 117 functions, 2,285 worker-seconds. The pure tests of the same rungs (`tmp_path` or
  `monkeypatch` only) stay in every subset.
  - The brief said "O4/O8 rehearsal tests". It is read here as O4 through O8. Every rung from O4 to O8 has its own
    rehearsal and driver section, and the report's "291 O4/O8 tests" matches the 294 `test_o*` tests of all rungs.
    O4 and O8 alone would be 48 functions and 1,393 s.

**Why the marker is applied at collection, not as a decorator.** `studies/story-trace/segment_regress.py`'s G21 pins
the sha256 of `ast.dump` of each pinned test function in `test_harness.py`, and that dump includes the decorator list.
96 of the 117 story drives are pinned (307 `test_harness.py` functions are pinned in all). A `@pytest.mark.slow_leg`
line would have changed 96 pins, and each would need a re-baseline row with its reason. The registry changes no test's
source. The marker is set by a `tryfirst` `pytest_collection_modifyitems` hook, so it is on every item before pytest's
own `-m` deselection reads it.

**Proof that the split is exact** (collection over the 18 files):

| Run | Collected |
|---|---|
| Whole list | 2,854 |
| `-m slow_leg` | 264 |
| `-m "not slow_leg"` | 2,590 |

The two node-id sets are disjoint, and their union is byte-for-byte the whole list. Per file, the marked functions are
exactly the registry's. No assertion changed.

**The guard test, `ff9mapkit/tests/test_slow_leg_marker.py`** (3 tests, about 12 s):
- Every registered name must be a top-level test its file defines, so a rename reads as missing instead of silently
  falling out of the marker.
- The story rule must take only drives and rehearsals on the fake, and at least one per rung from O4 to O8.
- A subprocess collect of `test_coop_leader_guard.py` must split exactly into `-m slow_leg` and `-m "not slow_leg"`.
- **Broken on purpose, both ways:**
  - A hook that marks nothing turns it red ("no tests collected").
  - A `trylast` hook, which runs after the deselection, turns it red too.

  The hook's order is load-bearing (the default order happens to work too; `tryfirst` states it).

**What a stage subset costs** (simulated, about 10 % low, see section 1):

| Subset | Worker-s | Wall clock at `-n 6` | Slowest test |
|---|---|---|---|
| All 18 files | 13,389 | 38.2 min (42.4 measured) | 482 s |
| `-m "not slow_leg"`, 18 files | 4,210 | 11.9 min | 67 s |
| `-m "not slow_leg"`, the brief's 15 files | 4,167 | 11.6 min | 67 s |
| `-m slow_leg` only | 9,179 | 26.5 min | 482 s |

**Usage, for when the owner adopts recommendation 1:**
- Intermediate stages run the domain list with `-m "not slow_leg"`, plus the patch's own new test files whole (no `-m`).
- The last stage runs the whole list once.
- A G7-style regression receipt (`segment_regress.py --pytest-junit`) needs the whole list, because it checks that every
  baseline test still ran.

**What is still slow in the subset:**
- `test_o8_tower_goals_are_height_aware` (67 s) and `test_o8_tower_knight_watch_reads_the_seat_by_place` (65 s): O8 but
  not drives.
- `test_no_smooth_hold_planned_across_stock_350_sweeps_into_another_exit` (53 s).
- Two poisoned-scenario tests (46 s each), `test_segment_naming_on_page_rows_on_the_fake` (40 s) and
  `test_dress_census.py::test_the_rig_rows_regenerate_from_the_install` (33 s).

None of these is a whole leg, so they stay unmarked. The subset's wall clock is bounded by its 4,210 worker-seconds,
not by any one test.

## 5. The s140-legs flake

**The signature.** In the workflow transcripts,
`test_harness_netsync.py::test_the_s140_legs_run_green_on_the_stand_in_and_calibrate_on_s139` went red six times between
10-19 and 10-21: three times in the s143 build, twice in the s144 build, and once in another session's run on 10-19.
Every red had the same assertion:

```
assert "(2557, 8)" in d["S140-X3"]
  "... TRIG_J: body 192 (want 192); 0 jump-slot publishes (anim, frame_n) [] (want frame_n 8: the SOURCE clip's);
   the landing 0.00 s (want <= 0.50: stock's 0 ticks + 0.5 s)"
```

X3 itself stays green, because a run with no alias publish "is judged on the landing alone" (`judge_x3`). Only the
smoke's detail assertion goes red.

**The mechanism.** The cause is a sampling window, not a slow deadline:
- The stand-in's J conductor (`FakeGame._self_cond_j`) plays a green jump in 3 stand-in frames: PREJUMP 2, then the
  landing 1, from `J_JUMP0`/`J_JUMP1` = 2/6 on the source clip's 8 frames.
- The loop turns 240 frames a second, and the scenario sets `stateevery 1`. Each jump publish lives about 4 ms, and the
  whole jump about 12 ms.
- The driver reads them with `cb.watch`, which polls `state.json` every 4 ms from the same child process.
- `judge_x3` reads two things off the samples it sees:
  - the jump-slot publishes, which give the detail's `(2557, 8)`;
  - the landing, from the first sample that shows J_LAND to the first that shows J_END. This is timed on the stand-in's
    virtual clock `rt`, which is frame-exact.
- On a loaded host the poller is not scheduled for 12 ms, sees J_LAND and J_END in one sample (hence "the landing
  0.00 s"), and records no jump publish.
- The same race has a second edge, found while measuring the fix. The poller reads J_LAND on time but reads J_END
  late. The one-frame landing then measures as many frames: up to 0.48 s, then 0.67 s, which is over the 0.5 s bound,
  so the X3 row itself goes red.
- Alone, the test is always green. In a full `-n 6` run, usually with other sessions' jobs beside it, it sometimes is not.

**Measured with a probe.** A probe (outside the repo) ran the test's own child script (`_SS_SMOKE`, `_SS_FO`) with the
X leg only: 6 concurrent probes alongside B busy-loop processes on the 12 hardware threads. A run "missed" when X3's
detail lacked `(2557, 8)`.

| Child script | Load | Runs | Missed | X3 red | Landing measured |
|---|---|---|---|---|---|
| Unfixed (master) | none | 2 | 0 | 0 | |
| Unfixed (master) | 12 burners (1x saturation) | 90 | **43** | 0 | |
| J conductor paced at the 30 Hz field tick | 12 burners | 90 | 0 | 0 | |
| J conductor paced at the 30 Hz field tick | 24 burners (2x) | 90 | **25** | 0 | |
| Handshake, J frames only (first version) | 24 burners (2x) | 90 | 0 | 0 | |
| Handshake, J frames only (first version) | 36 burners (3x) | 60 | 0 | **1** (landing 0.67 s) | |
| Handshake, J frames only (first version), traced | 36 burners (3x) | 120 | 0 | 0 | 0.02-0.48 s |
| **Handshake through the J_END publish (the fix)**, traced | 36 burners (3x) | 120 | **0** | **0** | **0.02 s in all 120** |
| Fix, with the jump's publishes hidden (break-it) | 12 burners | 30 | **30** | 0 | |

The calibration came first: the unfixed script must reproduce the miss under load, or a green under load proves
nothing. It does, with the production signature exactly, and with X3 green in every miss.

**Measured on the real test.** Six concurrent copies of the test itself (`pytest <node id>`), each its own process,
under B burners:

| Load | Unfixed (master) | Fixed |
|---|---|---|
| 0 burners | 4 / 6 green (2 red on the detail) | 6 / 6 (first version) |
| 6 burners | 2 / 6 green (2 on the detail, 2 on the X3 row) | 6 / 6 (first version) |
| 12 burners | 3 / 6 green (2 on the detail, 1 on the X3 row) | 5 / 6 (first version: 1 X3-row landing), **6 / 6 (the fix)** |

An earlier unfixed run at 12 burners, made while other work was also on the machine, was 1 of 6 green. Those reds were
`S140-W1` and `S139-G3m`, rows this fix does not touch.
- **W1** times the idle timer, 160 stand-in frames, against a fixed 5 s hold (the child's `IDLE_PAST_S`). It needs
  the stand-in above about 32 fps. The child's own comment budgets for a 40 fps worst case.
- **G3m** judges the twin's moogle on its mid-move publishes, another sampled window.

Neither row ever reddened a recorded gate run (all six recorded reds were X3), and neither appeared at the same
burner count when nothing else was running. They are the test's next limits, at a load above the gate's. They are
written down here, not widened.

**The fix** is in `_SS_SMOKE`, the child script that the s140 trio and the leg-F trio share:
- From J's trigger to the frame after J's DONE, each stand-in frame waits, bounded by 2 s, until the driver has read
  the last publish. The driver's reads are seen through `Channel.state`, which is patched in the throwaway child only.
- Every J publish is therefore sampled, under any load: the jump slot, J_LAND, and J_END on its own frame. What the
  frames publish, and the virtual clock that X3's landing reads, do not change, and the landing measures exactly one
  frame.
- Pacing the jump at the engine's 30 Hz tick, about 8x the window, was the first fix tried. It held at 1x saturation
  and failed at 2x. Two concurrent `-n 6` sessions can reach 2x.
- The first handshake version held only the J conductor's own frames, and at 3x load it still read J_END late (the
  0.67 s landing). The fix holds one frame more.
- **The break-it** keeps the fix and hides every publish the stand-in makes during the jump. All 30 runs then lose
  `(2557, 8)`, so the assertion still reads real samples and still fails when the jump is not seen. The landing bound
  keeps its own red case: the `law-timeline` lever plays the jump on the alias's 50 frames, a 42-frame landing, and
  `test_each_s140_lever_reds_exactly_its_rows_on_the_stand_in` requires X3 red there. It is green with the fix.

**Not used, and why:**
- **`xdist_group`, or running the test serially.** `xdist_group` takes effect only under `--dist loadgroup`, and the gate
  runs the default `--dist load`. A test kept on one worker is still loaded by the other five workers and by other
  sessions, which is where the miss comes from.
- **Auto-rerun.** Never: it would hide a real timing regression, and the report rules it out.

**The touched file.** `test_harness_netsync.py` and `test_slow_leg_marker.py` ran whole at `-n 6` with the fix:
1,128 passed and 1 skipped. The six tests on `_SS_SMOKE` cost the same as before, within run-to-run noise:
- `test_each_s140_row_reds_on_its_fault_on_the_stand_in[b]` took 453 s against 482 in the profile.
- `test_the_s140_legs_run_green_on_the_stand_in_and_calibrate_on_s139` took 204 s against 195.
- The untouched s139 leg took 475 s against 465.

**For the owner, not changed here.** X3 is green on a run that saw no jump publish, because `judge_x3` judges "a run
with no alias publish ... on the landing alone". The live bench polls `state.json` the same way. On a loaded host, the
in-game X3 could therefore pass without ever seeing the jump slot, and that is the same shape of check that cannot fail.
The smoke's `(2557, 8)` assertion is what keeps the stand-in honest. The live leg has no such guard.

## 6. Other findings (not fixed here)

- **The CRLF runner red, which will hit the next nightly.** `test_coop_world_wait.py::test_the_s144_runners_name_every_step`
  asserts no `\r` in the s144 `.sh` runners ("LF line endings (bash)"). `core.autocrlf=true` is set in the system
  gitconfig, and `.gitattributes` has no `*.sh` rule, so a checkout writes CRLF. The s144 runners came out CRLF in this
  worktree and in the main checkout, and so did the s143 ones (`cal143`/`full143`). The s143 test reads them as text
  and does not check, but bash is still handed CRLF. The fix is a `.gitattributes` line (`*.sh text eol=lf`) and a
  re-checkout of those files.
- **Orphaned xdist workers.** Three `python -c "import sys;exec(eval(sys.stdin.readline()))"` processes with dead
  parents were found, started 10-14 and 10-20. They were idle and were left alone.
- **The 10-21 nightly's three reds** did not reproduce on an idle machine (section 1). The nightly that produced them
  ran 46 % longer than the night before.

## Method

- Durations come from the profile's junit XML. Collection order and the marked sets come from `--collect-only -q` with
  and without `-m`.
- The wall-clock simulation is greedy: the next test in collection order goes to the first free of 6 workers.
- The flake signature comes from the workflow transcripts (`tool_result` text holding the test's failure).
- The load probe and runner (`xprobe.py`, `loadrun.py`) are scratch scripts outside the repo. They import the test
  module's own `_SS_SMOKE` and `_SS_FO`, so the probe runs the test's real child lifecycle with the X leg selected.
