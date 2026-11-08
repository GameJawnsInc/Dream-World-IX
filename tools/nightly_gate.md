# The nightly test gate — full-suite runs on master, off the critical path

The full `ff9mapkit` pytest suite took ~45 min serial when the gate was built. It now takes about
**3 h even at `-n 6`** (2026-11; see "The time budget"), and it degrades further when several
sessions run it concurrently (every install-gated test re-reads the same shared
`StreamingAssets/p0data*.bin` bundles; the OS file cache thrashes — see memory
`project-ff9-test-suite-perf`). The gate replaces "every session tails itself with a full run" with:

- **Sessions run only their domain's test files** before merging to master (seconds–minutes).
- **The full suite runs once per night, on master, alone** — in a dedicated pre-provisioned
  worktree, with a lockfile so two full runs can never overlap.
- **Sessions read the result** from a small JSON ledger instead of re-running anything.
- **Exception:** a diff touching the byte-level fork/graft/content core (the ~15 install-gated
  test files listed in `project-ff9-test-suite-perf`) runs the full suite itself *pre*-merge —
  that is the code where a green subset means the least.

A red morning ledger means one of yesterday's merges broke something: each was a small branch
that already passed its targeted tests, so bisect with the relevant subset.

## Moving parts

| Piece | Where | What |
|---|---|---|
| Runner | `tools/nightly_gate.py` | the whole gate: worktree mgmt, provisioning, lock, run, ledger |
| Results plugin | `tools/gate_plugin/ff9_gate_results.py` | writes each test's outcome as it finishes, so a killed run still names its failures |
| Gate worktree | `C:\gd\ff9-test-gate` | detached checkout, re-pointed at `master` every run; provisioned once and kept |
| State dir | `C:\gd\Dream-World-IX\.test-gate\` (gitignored) | `lock` · `ledger.jsonl` (history) · `latest.json` (read this) · `runs/*.log` · `runs/*.results.jsonl` (newest 30 kept) |
| Scheduled task | Task Scheduler: **"FF9 nightly test gate"** | fires 08:00 UTC: **03:00** EST, 04:00 EDT (the trigger keeps a fixed offset). Wakes the machine, skips overlaps, **4 h limit** |

The gate worktree lives **outside** `.claude\worktrees\` on purpose — it is infrastructure, not an
agent session, and must never be pruned with them. It stays permanently provisioned (templates +
fixtures + `.ff9mapkit-cache` are gitignored, so `checkout --force` never touches them), which is
what defuses the **worktree skip-trap** (a fresh worktree silently fails to collect ~479 byte-level
tests and reports green anyway). Belt-and-braces, the runner also **aborts as `collect-short`** if
fewer tests collect than the floor — which **self-ratchets to 98% of the last full green run's own
collection** (the static `--collect-floor`, default 6500, is only the bootstrap; the old fixed floor
rotted as the suite grew until it admitted a drop 4× the trap it was built for). A collection that
exits non-zero (an import-broken module) aborts as **`collect-error`** — the count alone would clear
the floor while part of the suite silently isn't in it.

## Reading results

`C:\gd\Dream-World-IX\.test-gate\latest.json`:

```json
{
  "timestamp": "2026-08-04T04:41:12",
  "result": "green",            // green | red | error | timeout | collect-short | collect-error | skip-long | lint-up
  "mode": "full",
  "sha": "8cbc39e6",            // the master commit that was tested
  "collected": 6947,
  "ruff_f": 109, "ruff_f_baseline": 109,   // pyflakes findings in the package: a RATCHET (only an increase is a verdict)
  "workers": 6,
  "passed": 6947, "skipped": 15,
  "failed_ids": ["ff9mapkit/tests/test_x.py::test_y"],   // present when not green; error_ids for setup/teardown errors
  "completed": 6962,            // tests that reached an outcome (the results log's count)
  "slowest_files": [["ff9mapkit/tests/test_harness_netsync.py", 9123.4], ...],   // setup+call seconds, top 10
  "worker_busy_s": {"gw0": 10210, "gw1": 9874, ...},     // per-worker seconds: a wide spread is a scheduling tail
  "duration_s": 1130.4,
  "log": "...runs\\<ts>.log",   // the gate's own narration
  "suite_log": "...runs\\<ts>.pytest.log",  // full pytest output, incl. --durations=25 profiling
  "results_log": "...runs\\<ts>.results.jsonl"  // one JSON line per finished test (see below)
}
```

A `timeout` row also carries `timeout_min`, `finished: false`, and the counts and ids of everything that
finished before the kill.

**`latest.json` is a VERDICT file: only a FULL run writes it.** A `--smoke` or narrowed
(`--pytest-args`) run appends to `ledger.jsonl` only — the 2026-08-05 incident (a narrowed
verification run flipped `latest.json` to `skip-long`, restored by hand) is why. So `latest.json`
always answers "what did the whole suite last say", never "what did somebody's subset say".

`ledger.jsonl` is the same shape, one line per run, append-only — grep it for trends. For profiling,
read the ledger row's `slowest_files` and `worker_busy_s` first, then the run's `*.results.jsonl`
(every test's setup+call time). The `--durations=25` block at the end of each `*.pytest.log` shows
only the 25 slowest tests, about 14% of the work on 2026-11-03, and a killed run never prints it.

## A killed run still names its failures

A killed pytest never prints its summary, so the 2026-11-07 and 11-08 timeouts left 5 and 73 `F`
marks in their progress lines and not one name. The suite command now loads
`tools/gate_plugin/ff9_gate_results.py` (`-p ff9_gate_results --gate-results=<runs>\<ts>.results.jsonl`,
with that directory on `PYTHONPATH`). The xdist **controller** writes one JSON line per finished test
and flushes each one. On a timeout the gate reads that file and writes the counts, `failed_ids` and
`error_ids` into the ledger row. A complete run gets the same names, with pytest's summary line still
the authority for the counts, and falls back to the `FAILED`/`ERROR` lines of the short summary if the
results log is missing.

- **The `=` is load-bearing.** Always pass `--gate-results=PATH` as one token, never as two tokens.
  An xdist worker sizes its rootdir before the plugin registers the option, so it reads a separate
  value as a positional path. The worker's rootdir then becomes the common ancestor of the tests and
  the log, which for the nightly is `C:\gd`. The first forced-kill run through `main()` caught this:
  the workers stalled in collection and 0 tests ran in 45 s. `test_nightly_gate.py` pins both the
  token shape and the worker's rootdir.
- **A timeout kills the whole tree** with `taskkill /T /F`. `Popen.kill` killed only the `py` launcher.
  On 2026-11-08 the xdist workers kept writing the suite log for three more minutes and kept tripping
  benchguard.
- Proven 2026-11-08: a narrowed run on a stub suite with `--timeout-min 0.75` was killed and its ledger
  row named the one failure and the one setup error (`finished: false`). Do the same to re-check:
  `--pytest-args "<stub dir>/test_x.py --dist loadfile" --workers 2 --timeout-min 0.75`. A narrowed row
  writes `ledger.jsonl` only.

## The time budget

Task Scheduler kills the task at its **4 h** `ExecutionTimeLimit`. That kill skips `main()`'s
`finally`, so the night leaves **no ledger row at all**. The suite cap therefore lives inside it:
`DEFAULT_TIMEOUT_MIN` (225) + `PRESUITE_BUDGET_MIN` (15) ≤ `TASK_LIMIT_MIN` (240), and a test pins
this. `--register-task` reads the same constant. To raise the cap, raise `TASK_LIMIT_MIN` too, merge,
and re-register. A run started by hand is not under the limit; the gate warns when the two disagree.

**Why 225, from the ledger (all `-n 6`):**

| Night | Collected | Wall |
|---|---|---|
| 10-08 … 10-19 | 11.6k–13.1k | 2,168–2,842 s |
| 10-24 | 14,275 | 7,097 s |
| 11-03 | 15,628 | 10,003 s |
| 11-07 | 16,302 | killed at 98% at the 180 cap, so it needed ~184 min |
| 11-08 | 16,535 | killed at 87% with 73 `F` marks (a red-heavy night runs longer) |

Collection grew 26% from 10-15 to 11-03 while wall time grew 4.4×. The new tests cost far more than the
old ones: the co-op stand-in families (`test_harness_netsync.py`, `test_coop_*.py`) run 150–550 s each.
Since 10-24 wall time has grown about 250–290 s a night. **225 is a stopgap:** from 11-07's ~184 min it
buys about 9 nights at that rate. It is also the most the 4 h task allows.

**What else the numbers say:**

- **Contention is not what drives the overruns.** Measured alone on 2026-11-08, the s139 stand-in leg
  took 497 s against 533 s in the 11-03 gate, about 7%. Night-to-night variance is real, though: 10-28
  ran 5,394 s while its neighbours ran 7,993 and 8,685. The window is now 03:00 to about 06:47. The
  gate holds its lock that whole time, so benches started before then are refused.
- **The two slowest tests are a test-hygiene bug, not slow tests.**
  `test_workspace_encounters.py::test_the_help_badge_keeps_its_glyph_at_150` takes 0.22 s alone and
  took 878 s in the gate. `test_the_library_sidebar_never_scrolls_sideways_under_the_app_sheet` takes
  0.14 s alone and took 740 s. Both call `QApplication.setStyleSheet` app-wide, which repolishes every
  widget that earlier GUI tests left alive in that xdist worker. Fix the test or its cleanup (a Workspace
  task). A slice does not help, because each worker still accumulates its share of leaked widgets.
- **A slice at the same `-n` makes things slower.** Each sequential pytest invocation adds its own
  scheduling tail. A slice pays only at a different worker count. The candidate is the stand-in
  families: alone, a `test_coop_world_wait` bench test used 0.47 cpu-seconds per wall-second, so half
  its time is paced sleep. A higher `-n` for that slice has not been tried, because those tests are
  paced by the wall clock and the co-op sweep already shows load flakes. Size it from one complete
  night's `slowest_files` and `worker_busy_s` before changing anything.

**On red — whose job is the fix?** The gate only detects; the responsibility rule is
**first-reader triages**: the first session of the day that reads a red ledger must triage
*before doing anything else on master* — triage is not optional and not deferrable to "someone
else," because a red that everyone skips silently becomes the ambient state.

1. Re-run the failing test on clean master. Still red with no local changes → suspect
   *deployed-state* preconditions (the shared mod folders another session wiped; see
   `project-ff9-test-suite-perf` §DEPLOYED-STATE) before suspecting any merge.
2. Genuinely red → bisect yesterday's merges with the failing file only (each was a small branch
   that already passed its targeted tests — this is minutes, not hours).
3. Culprit found → **fix it if small or in your domain; otherwise REVERT the culprit merge on
   master and report** (failing test, culprit, revert noted) so the human routes the re-land to a
   domain session. Revert-first because master is shared: every hour it stays red, other sessions
   build on a broken base and the next nightly can't tell old red from new red.

The sessions that *caused* a red are usually closed by morning — sessions are ephemeral, so
author-pays degenerates to "the human points a session at it." First-reader-triages is the rule
that keeps red from being nobody's problem.

## Merge-time enforcement — the post-merge hook

CLAUDE.md telling sessions to read the ledger is advisory; the hook makes it automatic at the one
moment it matters. `.git/hooks/post-merge` in the **main repo** prints the gate state after every
merge **into master** (a loud multi-line banner when not green, a one-liner when green) — the text
lands in the merging session's command output, so no session can merge without seeing it. Hooks
live in the shared `.git`, so every worktree and account inherits it with zero per-session setup.
It is warning-only by design: a fast-forward merge (the common case here) fires no blockable hook,
and post-merge cannot abort — but for agent sessions, pushed text at merge time is effectively
binding, because the protocol instruction arrives in-context the moment it applies.

⚠ **Hooks are NOT tracked by git.** If `.git/hooks/post-merge` goes missing (fresh clone, pruned
`.git`), recreate it with this exact content and `chmod +x`:

```sh
#!/bin/sh
# ff9-test-gate awareness hook -- after any merge INTO master, surface the nightly gate
# ledger loudly so no session can merge without seeing the suite state. Warning-only by
# design (post-merge cannot block; a fast-forward merge fires no blockable hook), but the
# text lands in the merging session's output at exactly the moment the protocol applies.
# NOT tracked by git -- recreate from tools/nightly_gate.md if missing.
[ "$(git symbolic-ref --short -q HEAD)" = "master" ] || exit 0
ledger="$(git rev-parse --path-format=absolute --git-common-dir)/../.test-gate/latest.json"
if [ ! -f "$ledger" ]; then
    echo "[test-gate] no ledger yet ($ledger) -- the nightly gate has not run"
    exit 0
fi
result=$(sed -n 's/.*"result": *"\([^"]*\)".*/\1/p' "$ledger" | head -1)
stamp=$(sed -n 's/.*"timestamp": *"\([^"]*\)".*/\1/p' "$ledger" | head -1)
# A green VERDICT decays: if the scheduled task silently dies (logged out at 04:00 for days,
# task disabled by an update), latest.json stays green forever and every merge reads
# yesterday's suite as today's. GNU date (Git Bash) parses the ISO stamp; if it cannot,
# the age stays unknown and we stay calm rather than cry wolf.
age_h=""
if [ -n "$stamp" ]; then
    then_s=$(date -d "$stamp" +%s 2>/dev/null)
    [ -n "$then_s" ] && age_h=$(( ($(date +%s) - then_s) / 3600 ))
fi
if [ -n "$age_h" ] && [ "$age_h" -gt 48 ]; then
    cat <<EOF
!! =====================================================================
!! [test-gate] THE LEDGER IS STALE: the last entry ($result) is ${age_h}h
!! old. The nightly gate has NOT run for over 2 days -- its verdict is
!! HISTORY, not the state of master. Check Task Scheduler ('FF9 nightly
!! test gate'; were you logged out at 04:00?), or run
!! tools/nightly_gate.py by hand now.
!! Ledger: $ledger
!! =====================================================================
EOF
    exit 0
fi
case "$result" in
    green)
        echo "[test-gate] last nightly gate: green ($stamp)"
        ;;
    smoke-ok)
        # a legacy latest.json only -- smoke runs no longer write the verdict file
        echo "[test-gate] last ledger entry is smoke-ok ($stamp) -- provisioning only, the SUITE HAS NOT RUN"
        ;;
    *)
        cat <<EOF
!! =====================================================================
!! [test-gate] THE NIGHTLY GATE IS NOT GREEN: result=$result ($stamp)
!! You just merged into master on top of a failing/unknown suite state.
!! PROTOCOL (CLAUDE.md / tools/nightly_gate.md) -- TRIAGE BEFORE ANY
!! FURTHER MASTER WORK: re-run the failing file on clean master (rules
!! out deployed-state false reds), bisect yesterday's merges with that
!! file, fix if small/in-domain, otherwise REVERT the culprit merge and
!! report. Never build on a red master silently.
!! Ledger: $ledger
!! =====================================================================
EOF
        ;;
esac
exit 0
```

## Setup from scratch

Everything is idempotent; re-running any step is safe.

1. **Prerequisites:** the `py` launcher on PATH; the dev deps installed (`pytest` + `pytest-xdist`
   — the kit's `dev` extra); the FF9 install present (provisioning reads it, read-only).
2. **Make sure master has the gate tooling** (`tools/nightly_gate.py` merged).
3. **Create + provision + verify the gate worktree** (one command — creates the worktree if
   missing, checks out master, runs `extract-templates` if needed, seeds `.ff9mapkit-cache` from
   the main repo, and proves the collection count clears the floor):

   ```bash
   py C:\gd\Dream-World-IX\tools\nightly_gate.py --smoke
   ```

   First run takes a few minutes (template extraction). Expect `smoke OK` and a
   `smoke-ok` row in `ledger.jsonl` (`latest.json` stays untouched — it holds full-suite
   verdicts only, so it won't exist until the first real nightly).
4. **Register the scheduled task** (defaults to daily 04:00):

   ```bash
   py C:\gd\Dream-World-IX\tools\nightly_gate.py --register-task
   ```

   The task runs the **gate worktree's** copy (`C:\gd\ff9-test-gate\tools\nightly_gate.py`), so the
   main repo's checked-out branch never matters. ⚠ That copy is whatever the **last** run checked
   out: a run loads its script *before* it re-points the worktree at master, so a merged gate change
   would first take effect the night after next. After merging a gate change, run `--smoke` once.
   It re-points the gate worktree at master, so tonight's run loads the new script.
5. **Optional first full run now** (instead of waiting for tonight):

   ```bash
   py C:\gd\Dream-World-IX\tools\nightly_gate.py
   ```

## Adjusting things

- **Run time:** re-register with `--register-task --at 03:30` (or edit the trigger in Task
  Scheduler → "FF9 nightly test gate"). The trigger keeps a fixed UTC offset, so it moves an hour
  when the clocks change. The cap and the task limit are covered in "The time budget".
- **Workers:** the task runs the script's defaults (`-n 6` — the measured sweet spot; `-n auto`
  re-contends on disk, don't). That was measured on the old, disk-bound suite. The stand-in families
  that now dominate are about half paced sleep, so re-measure before changing it ("The time budget"). To change permanently, edit `--workers`'s default in the script and
  merge; the gate picks it up the next night. Falls back to serial automatically if xdist is missing.
- **Collect floor:** self-maintaining since Lane C (2026-08-23): the effective floor is 98% of the
  last full green's own `collected` (the ledger is the baseline), with the static `--collect-floor`
  as the bootstrap bound. The old rule here ("raise the default as the suite grows") was never
  executed and the fixed floor rotted to 77% of collection — do not reintroduce a manual number.
  A **deliberate** suite shrink beyond 2% will abort `collect-short`; run once with
  `--no-dynamic-floor` and say why in the merge message.
- **Skip ceiling** (`--skip-ceiling`, default 32 — audit rec 18): the floor is structurally BLIND
  to a module-level `skipif`, which still *collects* the family it silences — 56 coastmorph tests
  skipping en masse would read as a green ledger. A green run whose `skipped` exceeds the ceiling
  gets the verdict `skip-long` (rc 1), which trips the standing RED-LEDGER-TRIAGE rule. Seeded at
  ~2× the last green run's `skipped` (16 on 2026-08-04) so fixture-gated churn has headroom while
  a silenced family (tens of skips) cannot hide. If `skipped` legitimately grows past ~half the
  ceiling, re-seed the same way — do **not** raise it to make a `skip-long` pass without reading
  WHICH tests skipped in the pytest log first. Proven live 2026-08-05: a narrowed run
  (`--pytest-args`, verification only) with `--skip-ceiling 0` flipped the ledger to `skip-long`
  (state restored after).
- **Lint ratchet** (`--no-lint-ratchet` to bypass for one run): `ruff check --select F` (pyflakes
  only — undefined names, unused imports/variables; style rules stay off, see `[tool.ruff]` in
  `ff9mapkit/pyproject.toml`) over the package, recorded as `ruff_f` in every run. A green full run
  whose count EXCEEDS the last full green's gets the verdict `lint-up` (rc 1) and trips the
  RED-LEDGER-TRIAGE rule. The count is a ratchet, not a bar: the ~109 findings it was seeded with are
  frozen, not a to-do list, and every fix lowers the baseline for free. ruff absent → measured as
  nothing and skipped, never red (the `[dev]` extra installs it).
- **Paths:** env overrides `FF9_MAIN_REPO` and `FF9_GATE_WORKTREE` (set them in the task's action
  if you move things). State always lives at `<main repo>\.test-gate\`.
- **Remove:** `py ...\nightly_gate.py --unregister-task`, then optionally
  `git -C C:\gd\Dream-World-IX worktree remove C:\gd\ff9-test-gate` and delete `.test-gate\`.

## Troubleshooting

- **No ledger entry this morning** → the task didn't run. It runs with your interactive login
  token: if you were fully **logged out** (not just locked/asleep) at 04:00 it cannot start.
  `-StartWhenAvailable` re-runs it on the next login/wake. Check Task Scheduler → task history.
- **`collect-short`** → provisioning regressed (a new gitignored asset class, like the
  stolen-ember sidecars were). Run `--smoke`, read its log; usually `extract-templates` in the
  gate worktree fixes it. Do **not** lower the floor to make it pass.
- **`lint-up`** → a merge since the last green added a pyflakes finding (the `.ruff.log` beside the
  run log names it — often an unused import, sometimes an undefined name, which is a `NameError`
  waiting for its code path). Fix it; do **not** pass `--no-lint-ratchet` to make it pass without
  reading which finding rose.
- **A red that goes away when an ignored leftover is deleted** is a test reading the checkout, not
  the code, so fix the test's rule. The 2026-09-23 case was a `__pycache__`-only
  `ff9mapkit/ff9mapkit/tests/` left behind by the test-tree move. `test_provenance_tripwire` now
  counts a leaked package only where `.py` files exist, because a wheel ships modules only (checked
  with a real wheel build). Do **not** add a `git clean` or a tree sweep to the gate. The gate's
  ignored files ARE its provisioning, and every dev checkout keeps the same leftover and would stay red.
- **Stale lock** (`lock` present, no run live) → the runner detects a dead PID and steals it
  automatically; delete `.test-gate\lock` by hand only if it somehow persists.
- **`timeout`** → read the row's `failed_ids`/`error_ids` first. A red-heavy night runs longer, so
  triage those. Then compare `completed` with `collected`. If the run was close, the suite has
  outgrown the cap: read "The time budget" before raising anything. Contention was measured at about
  7% on the heaviest test family, so don't blame contention without numbers.
- **The task must never run concurrently with itself or a manual run** — it doesn't: the task is
  registered `IgnoreNew` and the runner exits gracefully when the lock is held.
- **A live game bench refuses to start while the lock is held** — `tools/play.py` and
  `tools/harness/duo.py` exit 2 (`tools/harness/benchguard.py`), and so on any live pytest
  process. The s159 law is NEVER BENCH UNDER A RUNNING TEST SUITE: on 2026-10-30, under the
  gate's `-n 6`, the s164 regression benches ran at 30 fps and went red on a correct engine.
- **Never run `py -m pytest -n N` under bash `timeout`** (a session's own domain run included).
  `timeout` kills the launcher but orphans the xdist workers, which keep the stdout pipe open,
  so a `| tail` never returns. The orphans also keep loading the machine, and every bench
  refuses until they are killed. Send the output to a log file instead:
  `py -m pytest -q -n 6 <files> > run.log 2>&1`, then read the log. benchguard's refusal names
  every live pytest pid and its command line, which is how you find an orphan.
