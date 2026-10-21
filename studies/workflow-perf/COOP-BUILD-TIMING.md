# Co-op build workflow timing (s133-s144)

Why the co-op engine-patch build workflows take so long. The s144 build (world-map co-op: wait then rejoin)
ran 13.05 h. This triage covers where the time went, whether any of the caution is extreme, and whether the
domain test time is necessary where it is spent.

Everything below was measured from the workflow transcripts (`journal.jsonl` plus the `agent-*.jsonl` timestamps
and tool calls). **No test, build or game run was made for this report.** Times are UTC (subtract 4 h for EDT).
The s144 run is `wf_c35301b7-0e7` under the gallant-easley session `d4fdd100-…`. Agent ids are given as `aXXXXXXX`.

## Bottom line

1. **About a third of s144's wall clock (4.2 of 13.05 h) was agents sitting idle while the full domain test
   gate ran.** The gate was launched 8 times at 30-42 min a run. The script asks for it at 5 stages (engine D,
   harness core, bench, fix, fix2), each "until green". The other 3 runs were reruns, and 2 of those were caused
   by a flaky test or by an agent editing a harness file while its own run was in flight. Across s138-s144, every
   real red in a full run came from `test_harness_netsync.py` or the patch's own new test files. No red came from
   the other ~10 files of the list. One full gate at the end of the build would have caught the same defects.
2. **The review is not where the time goes, and it is not excessive.** The two review rounds, including 48
   skeptic agents, took about 1 h of the 13 h. Across 8 builds, 92 of 101 round-1 blocking/should findings
   survived two skeptics. Round 2 still had 1-9 surviving blocking/should findings in every build: in s144 it
   caught a regression that the first fix round had introduced. The skeptics are a token cost (40 % of s144's
   output tokens), not a time cost.
3. **The rest is model time on very large contexts, and the gate itself has grown.** On the critical path, model
   thinking and writing between tool calls took 5.3 h (41 %). The long agents worked at a mean context of
   420-640 k tokens, where one call takes 15-20 s against 4.5 s under 100 k. The per-stage gate went from about
   2 min (s137, 3 files) to 37 min (s144, 13 files), and the number of full runs per build went from 1-2 to 8.
   Two blocks dominate the gate's cost: `test_harness.py` and its siblings (about 18 min by themselves), and
   bench-leg tests that drive the stand-in game frame by frame in wall-clock time.

## 1. Where s144's 13 h went (the critical path)

The run is strictly sequential: engine A, B, C and D, then harness core and bench, then review (5 lenses in
parallel, then skeptics), fix, re-review and fix2. The critical path is therefore the sum of the stages.

| Stage (agent) | UTC | Wall | Model | Idle on full gate | Targeted pytest | Bench smokes / mutants | Other tools | Out tok | Mean ctx |
|---|---|---|---|---|---|---|---|---|---|
| engine:A (a9b19061) | 13:49-14:16 | 27 m | 23 | - | - | - | 4 | 20 k | 286 k |
| engine:B (a47af205) | 14:16-14:48 | 32 m | 27 | - | - | 1 | 3 | 32 k | 313 k |
| engine:C (a60f59e8) | 14:48-15:23 | 35 m | 31 | - | - | 0 | 4 | 21 k | 334 k |
| engine:D (a2f9db0d) | 15:23-17:18 | 114 m | 48 | **50** | 11 | 1 | 5 | 25 k | 484 k |
| harness:core (a80237a0) | 17:18-19:46 | 148 m | 52 | **75** | 12 | - | 8 | 40 k | 517 k |
| harness:bench (a7f82801) | 19:46-21:52 | 126 m | 51 | **46** | 1 | 19 | 10 | 134 k | 636 k |
| review, 5 lenses in parallel | 21:52-22:18 | 26 m | ~20 each | - | - | - | ~2 each | 57 k | ~300 k |
| verify, 36 skeptics (tail after the last lens) | 22:18-22:25 | 7 m | | | | | | 353 k (both rounds) | 142 k max |
| fix:s144 (aa6eb971) | 22:25-00:27 | 122 m | 49 | **32** | 24 | 2 | 14 | 40 k | 634 k |
| re-review + 12 skeptics | 00:27-00:59 | 31 m | | | | | | 153 k | ~330 k |
| fix2:s144 (ae7ba6b3) | 00:59-02:52 | 113 m | 35 | **47** | 11 | 10 | 10 | 6 k | 421 k |
| **Total** | | **13.05 h** | **5.3 h** | **4.2 h** | **1.0 h** | **0.5 h** | **0.95 h** | 0.88 M | |

The two review rounds add another 1.1 h (lens and skeptic-tail wall clock). Engine compiles are not a cost:
`build_memoria.py --no-deploy` takes 10-20 s, and all 34 build-related calls of the run total 3.2 min.
`memoria_stack_replay.py` emit, snapshot and diag calls take 12-36 s each, about 2 min in all.

## 2. The full domain gate

### Every full run in s144

| # | Agent | UTC | Tests | Runtime | Result, and why it was run again |
|---|---|---|---|---|---|
| 0 | engine:D | 15:31 to 16:07 | - | killed | A pre-change baseline the agent chose to run. `timeout 1500` (25 min) killed a 36-min suite, and the orphaned xdist workers held the `\| tail` pipe open, so the output was lost. Two workers were found and killed at 16:07. |
| 1 | engine:D | 16:09-16:39 | 2,462 | 30.1 m | 5 red, all real: `test_harness_netsync.py` key-order and stage re-keys. Fixed with `-k` reruns. |
| 2 | engine:D | 16:41-17:15 | 2,462 | 33.9 m | green: the confirmation run |
| 3 | harness:core | 18:18-19:00 | 2,690 | 41.6 m | 2 red, neither real. One was self-inflicted: `fakegame.py` was edited mid-run, so `inspect.getsource` read shifted lines. The other was the s140-legs flake. Both passed alone (19:01, 193 s). |
| 4 | harness:core | 19:04-19:44 | 2,717 | 40.0 m | green: a clean rerun |
| 5 | harness:bench | 21:09-21:50 | 2,788 | 41.1 m | green. Two other sessions ran `-n 6` jobs from 21:41 to 21:51. |
| 6 | fix:s144 | 23:41-00:17 | 2,717 | 36.8 m | green. The new `test_coop_world_wait.py` was run separately (85 tests, 7.4 m). |
| 7 | fix2:s144 | 01:58-02:35 | 2,731 | 36.8 m | 3 red. 2 were real: fix2 had changed the fault table in `test_world_coop_harness.py`. 1 was the s140-legs flake. The 3 passed alone (194 s), then a 287-test confirmation run took 12.5 m. |
| 8 | main session | launched 02:53 | | | The recipe's "verify yourself" step re-runs the same gate that fix2 had just run. |

The owner's ~25 min standalone run matches the s140-era list: the main session ran 2,289 tests in 25-31 min on
10-19. The s144 runs are longer because the list grew. s144 added 3 test files and ~255 tests, and
`test_coop_world_wait.py` alone takes ~7.2 min at `-n 6`. The harness agents also widened the script's 10-file
list to the 15 files of s143's domain list, but the 5 extra files hold only about 95 small tests.

### Every red full run, s137-s144 (15 reds; s137 had none, and s141-s142 were not built by these workflows)

| Build | Red full runs | Failing files |
|---|---|---|
| s138 | 1 | `test_harness_netsync.py` |
| s139 | 2 | `test_harness_netsync.py` (14 tests), plus `test_harness.py::test_o4_drive_presses_123_again_…`, a story-trace O4 test that is not co-op. Nothing fixed it, and it was green on the next full run. |
| s140 | 3 | `test_harness_netsync.py` (13 tests, then 1, then the s140-legs test) |
| s143 | 6 | `test_harness_netsync.py` (16, 4 and 1 tests), the s140-legs test **twice**, and `test_leader_guard.py`, which is s143's own new file |
| s144 | 3 | `test_harness_netsync.py` (5 tests), the s140-legs test **twice**, and `test_world_coop_harness.py`, s144's own new file |

No red ever came from `test_memoria_stack_replay`, `test_coop_peer`, `test_coop`, `test_coop_tab`,
`test_harness_duo`, `test_dress_census`, `test_coop_leader_guard` (outside its own build) or the other s143 list
files. **`test_harness_netsync.py::test_the_s140_legs_run_green_on_the_stand_in_and_calibrate_on_s139` is a
recurring flake.** It went red in 5 full runs across 3 builds and passed every time it was run alone. The agents
blamed it on "a child-process smoke under extra CPU load".

### What the gate is made of

There is no per-file profile, because measuring one would mean running the gate. These are the strongest signals
in the logs and in the nightly gate's `--durations=25` (`.test-gate/runs/20261020-040003.pytest.log`):
- **Stand-in bench legs.** These tests run a whole bench leg, often once per fault lever, against `FakeGame` in a
  child process. FakeGame turns frames at 240 a wall second with real sleeps (`tools/harness/fakegame.py:2151`),
  and the driver polls `state.json`. In the nightly, ten such tests in `test_harness_netsync.py` take 486, 485,
  344, 277, 208, 174, 171, 153, 110 and 110 s, about 2,500 worker-seconds in all. All of them belong to earlier
  patches' benches (s139-s141).
- **The patch's own bench tests.** `test_coop_world_wait.py` runs 85 tests in 434-446 s at `-n 6`, about
  43 worker-minutes. `test_world_coop_harness.py` runs 165 tests in about 150 s, and 3 of its per-fault tests
  took 194 s.
- **`test_harness.py` and its siblings: probably the biggest single block.** In s133 a run of only
  `test_harness.py`, `test_harness_duo.py`, `test_harness_instance.py` and `test_harness_world.py` took
  18.3 min at `-n 6` for 1,138 tests (agent ada8919e, 23:11 on 10-15). In s137 the 3-file netsync gate (about
  950 tests) ran in 1.5-2.5 min (9 runs measured), while the same files plus the harness files took 17.9 min.
  `test_harness.py` has 990 tests, and 291 of them are O4/O8 story-trace rehearsals, which are not co-op. Five of
  the nightly's 25 slowest tests are O4/O8 rehearsals (274, 98, 93, 88 and 86 s). The co-op patches do edit the
  modules it tests (`fakegame.py`, `session.py`, `channel.py`), so it belongs in the final gate.
- The rest is a fast long tail.

## 3. Trend: s133 to s144

| Build | Wall | Agents | Full runs (≥1,000 tests) | Tests a run | Minutes a run | Gate runtime | Idle on tests | Everything else |
|---|---|---|---|---|---|---|---|---|
| s133 | 2.9 h | 24 | 2 | 1.1-1.2 k | 16-18 | 0.6 h | 0.7 h | 2.2 h |
| s134 | 3.4 h | 64 | 0 (3-file gate, ~2 min) | - | - | - | 0.2 h | 3.2 h |
| s135 | 3.9 h | 38 | 1 | 1.2 k | 20 | 0.3 h | 0.6 h | 3.3 h |
| s136 | 4.1 h | 52 | 0 (3-file gate) | - | - | - | 0.5 h | 3.6 h |
| s137 | 4.5 h | 42 | 1 | 1.2 k | 18 | 0.3 h | 0.7 h | 3.8 h |
| s138 (audit + build) | 5.4 h | 147 | 4 | 2.06 k | 17-20 | 1.2 h | 1.5 h | 3.9 h |
| s139 | 5.7 h | 46 | 5 | 2.06-2.19 k | 18-22 | 1.6 h | 1.9 h | 3.8 h |
| s140 | 6.1 h | 9 | 3 | 2.27-2.28 k | 23-25 | 1.0 h | 1.2 h | 4.9 h |
| s143 | 7.9 h | 42 | 8 | 2.37-2.53 k | 28-38 | 4.0 h | 4.0 h | 3.9 h |
| s144 | 13.0 h | 66 | 8, plus 1 killed | 2.46-2.79 k | 30-42 | 4.9 h | 5.2 h | 7.8 h |

"Idle on tests" counts the agents' polling waits plus foreground pytest. It is summed over agents, but reviewers
rarely run tests, so it approximates the critical path. "Everything else" is mostly model time.

The non-test time stayed at 3-4 h from s133 to s143. **The growth up to s143 is all test time.** Two things grew:
- **The list:** 3 files through s137, then `test_harness.py` joined (s139 script), then `test_coop`, `test_coop_tab`,
  `test_harness_duo` and `test_dress_census` (s143), then the two leader-guard files and 3 new files (s144).
- **The number of full runs:** the s143 and s144 scripts put the full list into the capture gate of D, fix and
  fix2, and harness core and bench are told "Run the domain tests until green".

s144 then doubled the non-test time as well (7.8 h). It is a bigger feature: 4 sequential engine agents where
s143 had 1, 12 clone files, and two harness agents of about 2 h and 180-230 calls each, at the largest contexts
of any build.

## 4. Review and skeptics

| Build | Round 1 findings (nits) | Round 1 blocking/should, survived | Round 2 findings (nits) | Round 2 blocking/should, survived | Skeptic agents |
|---|---|---|---|---|---|
| s134 | 30 (15) | 15 → 14 | 24 (13) | 11 → 9 | 52 |
| s135 | 22 (12) | 10 → 10 | 12 (9) | 3 → 3 | 26 |
| s136 | 24 (12) | 12 → 9 | 21 (13) | 8 → 5 | 40 |
| s137 | 21 (11) | 10 → 9 | 16 (11) | 5 → 5 | 30 |
| s138 | 22 (9) | 13 → 12 | 13 (11) | 2 → 1 | 30 |
| s139 | 23 (12) | 11 → 10 | 14 (8) | 6 → 5 | 34 |
| s143 | 28 (16) | 12 → 12 | 9 (6) | 3 → 3 | 30 |
| s144 | 37 (19) | 18 → 16 | 18 (12) | 6 → 5 | 48 |

- **Real defects, not wording.** s144's round 1 included:
  - A real engine bug: a field-recipe `_followWarpedTo` survives onto the world map and silently blocks the
    world rejoin.
  - Bench checks that could not fail: RJ-DIAL never tested decision 9's world dial, and its s143 prediction was
    wrong.
  - The ~ "Release world freeze" not giving the world map back.

  Round 2 caught `rfreeze-1`, a regression that fix 1 had introduced (the released-guest key mask passed Confirm),
  and `rharness-1`, an instrument row that would have gone red on the owner's own `Memoria.ini`. That one would
  have cost a calibration round in game. Only the README status-row finding was documentation.
- **The skeptics re-read code. They do not re-derive the design or re-run tests.** No skeptic ran pytest. Each
  made 10-40 Grep/Read/sed calls in 1-8 min, started from a 6 k-character prompt, and peaked at a 142 k mean
  context. Across 145 skeptic pairs in 8 builds, both upheld 119, both refuted 17 and 9 split (6 %).
- **Wall clock:** the skeptics run in parallel. The tail after the last lens was 7 and 8 min. The workflow's
  concurrency cap (10 agents, hit at 22:09) delayed some round-1 skeptics by up to 3.4 min.
- **Redundancy:** in s144's round 1, three issues were reported by two or three lenses each (RJ-DIAL ×3, the
  stale `_followWarpedTo` ×2, the release ×2). That is 4 redundant findings, or 8 of the 36 skeptic agents.
- **Reviewers ran tests in two places:** `rereview:harness` and `rereview:wire` each started a `-n 6` run
  (00:35 and 00:42), 12 workers on a 6-core machine. They could have read the fix agent's log.

## 5. Concurrency

The machine is a Ryzen 5 5600X: 6 cores, 12 threads. One `-n 6` run uses every core.
- **Inside the workflow:** 5 of s144's 8 full runs had no other heavy work running at the same time. During run 1,
  engine:D ran a `-n 2` three-file job of 6.9 min and four `-k` runs, 9.7 min of overlap in all. The s143 engine
  run (23:49-00:27) overlapped 10.4 min of its own foreground runs.
- **Other sessions:** across the s144 window, only `terrain-shaping-progress` and `sweet-kare` ran tests (and one
  `play.py` at 17:11). Their `-n 6` jobs overlapped s144's run 5 for about 10 min, and run 5 was among the
  slowest (41 min). Contention is a minor factor in the totals. It does matter for the timing-sensitive stand-in
  tests, which is where the flake fires.

## 6. Verdicts

**(b) Is any of the caution extreme?** Mostly no.
- **The review is proportionate.** The 5 lenses, 2 skeptics and 2 rounds cost about 1 h of 13 h, and every round
  of every build had surviving blocking/should findings. The s144 ones checked here were real defects.
- **"Every check can fail" earns its keep.** The fault-per-leg tests are expensive, but at fix2 they caught 2 real
  errors in s144's own fault table.
- **The one excess is running the FULL domain gate at every stage.** It ran 8 times in the workflow plus once in
  the main session. Across 15 red full runs in s137-s144, nothing outside `test_harness_netsync.py` and the
  patch's own files was a real catch: the others were the s140-legs flake, one story-trace flake and one
  self-inflicted red.

**(c) Is the domain test time necessary where it is spent?**
- **Once per build: yes.** Every co-op patch edits shared harness modules (`fakegame.py`, `session.py`,
  `channel.py`, `battlewire.py`). The older benches' stand-in legs are the only regression check on them.
- **Eight or nine times: no.** At the intermediate stages the useful part is `test_harness_netsync.py`'s fast
  structural tests plus the patch's own new tests. Re-running every earlier patch's 2-8 min legs and the O4/O8
  rehearsals at each stage repeats work that the final gate does anyway.

## 7. Recommendations, ranked by time saved

| # | Change | Est. saving (s144 scale) | Risk it adds |
|---|---|---|---|
| 1 | **One full domain gate per build.** Each stage (D, core, bench, fix) runs a subset in the background: `test_harness_netsync.py` without earlier patches' stand-in legs, `test_memoria_stack_replay.py`, the patch's own new test files including its own legs, and the test file of any harness module the stage edited (for `fakegame.py`/`session.py`/`channel.py` that means `test_harness.py` without its O4/O8 rehearsals). The last fix agent runs the full list once. Drop "until green" on the full list: re-run only the red file, then the full list once at the end. A `slow_leg` pytest marker on the earlier patches' leg tests and the O4/O8 rehearsals makes the subset one flag (a `-k` expression works in the meantime). | **2-3 h** (about 250 min idle drops to about 85-110) | A regression outside the subset shows up at the last stage, not at the stage that caused it. Observed rate: 0 of 15 red full runs. The final gate still blocks capture. |
| 2 | **Fix the s140-legs flake** (`test_the_s140_legs_run_green_on_the_stand_in_and_calibrate_on_s139`): run it serially or in an `xdist_group`, or give its driver deadlines headroom under load. It went red 5 times in 3 builds; each time it forced a 30-40 min rerun or a confirmation run. | 0.5-1 h a build | Low. Do not paper over it with auto-rerun, which would hide a real timing regression. |
| 3 | **Background-gate hygiene in the script's HARD RULES:** no edits to repo or harness files while your own gate runs; no `timeout` shorter than the suite (it killed run 0); no second pytest `-n` job beside your own gate; reviewers read the fix agent's log instead of starting `-n 6` runs; write the output to a file and poll it, without `\| tail`. | 0.5-0.7 h when it bites (run 3's self-inflicted red cost a 40-min rerun) | None |
| 4 | **The main session reads the workflow's final gate log instead of re-running it**, when `git status` and the clone's diag are unchanged since that run. The recipe's step 2 currently re-runs it. The main session ran it twice after s140 (10-19 03:23 and 06:13, 25-31 min), once after s143 (10-20 07:04-07:41), and again at 02:53, 18 min after s144's fix2 had finished one. | 25-37 min a build, on the owner's clock | None, if the tree is checked as unchanged |
| 5 | **Leaner contexts for the long agents:** pass the ENGINE and HARNESS summaries as file paths instead of inline JSON (each review and re-review prompt carries 169 k characters of it, and fix carries 155 k); read narrow `grep -n`/`sed` ranges of `NetSyncClient.cs` (7.7 k lines), `test_harness_netsync.py` (25 k), `fakegame.py` (13 k) and `battlewire.py` (10 k); split harness:core and harness:bench. Mean latency per call is 4.5 s under 100 k context and 15-20 s at 300 k or more. | 0.5-1.5 h (uncertain: a correlation, not a proven cause) | Medium: agents can miss context they used to have |
| 6 | **Dedupe findings across lenses before the skeptics** (in s144, 4 redundant findings drew 8 of 36 skeptics) | Tokens only, about 0 wall clock | Low |
| 7 | **One skeptic per finding, or Sonnet skeptics** (the pairs agree 94 % of the time) | Tokens only. Verify is 40 % of s144's output tokens but at most 9 min of wall clock a round. | About 6 % of serious findings could flip, and weaker refutations would send more false findings to fix. Not worth it for time. |

**Not recommended**, because the logs show nothing to gain:
- **Compile-only intermediate stages:** A-C already run only the compile gate, and a compile takes 10-20 s.
- **Skipping re-review when round 1 is clean:** round 1 was never clean (10-18 serious findings in every build),
  and round 2 had surviving blocking/should findings in every build (1-9).
- **Sonnet for the engine, harness or fix stages:** none of them is mechanical. Each needs design work, a
  7.7 k-line `NetSyncClient.cs` and a byte-exact patch-stack capture.

Recommendations 1-4 together would have put s144 at about 9-10 h instead of 13 h, with the same final gate
before capture.

**First step, cheap and safe:** when the machine is idle, run the domain list once with `--durations=0`, or have
the nightly gate print `--durations=200`. That gives the per-test profile the `slow_leg` marker needs; this
report could not measure it without running the suite.

## Method

Python parsers over the transcripts gave per-agent first and last timestamps; each tool call's duration (from
tool_use to tool_result), command, `run_in_background` flag and output tail; and each API message's latency
against its usage. Pytest summary lines were joined back to the run that produced them, and outputs that an agent
merely re-read from another agent's run were dropped. Whole-file pytest durations were collected across builds,
the nightly gate's `--durations=25` was read, and the heavy commands of all sessions in the s144 window were
scanned. The scripts are in the shared notes folder at
`side-session-notes/local_2b870c8f-…/workflow-perf-scripts/`, outside the repo.

**Caveats:**
- "Model" time is wall clock minus tool time, so it includes streaming output.
- The workflow reports 16.25 M subagent tokens. The usage fields give 0.88 M output tokens and about 0.96 B
  context tokens, almost all of them cache reads.
- The gate's per-file split is inferred, not profiled.
