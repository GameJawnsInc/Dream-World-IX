# The nightly test gate — full-suite runs on master, off the critical path

The full `ff9mapkit` pytest suite takes ~45 min serial and degrades to **hours** when several
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
| Gate worktree | `C:\gd\ff9-test-gate` | detached checkout, re-pointed at `master` every run; provisioned once and kept |
| State dir | `C:\gd\Dream-World-IX\.test-gate\` (gitignored) | `lock` · `ledger.jsonl` (history) · `latest.json` (read this) · `runs/*.log` |
| Scheduled task | Task Scheduler: **"FF9 nightly test gate"** | daily 04:00, wakes the machine, skips overlaps, 4 h limit |

The gate worktree lives **outside** `.claude\worktrees\` on purpose — it is infrastructure, not an
agent session, and must never be pruned with them. It stays permanently provisioned (templates +
fixtures + `.ff9mapkit-cache` are gitignored, so `checkout --force` never touches them), which is
what defuses the **worktree skip-trap** (a fresh worktree silently fails to collect ~479 byte-level
tests and reports green anyway). Belt-and-braces, the runner also **aborts as `collect-short`** if
fewer than `--collect-floor` (default 6500) tests collect, rather than minting a false green.

## Reading results

`C:\gd\Dream-World-IX\.test-gate\latest.json`:

```json
{
  "timestamp": "2026-08-04T04:41:12",
  "result": "green",            // green | red | error | timeout | collect-short | smoke-ok
  "mode": "full",
  "sha": "8cbc39e6",            // the master commit that was tested
  "collected": 6947,
  "workers": 6,
  "passed": 6947, "skipped": 15,
  "duration_s": 1130.4,
  "log": "...runs\\<ts>.log",   // the gate's own narration
  "suite_log": "...runs\\<ts>.pytest.log"  // full pytest output, incl. --durations=25 profiling
}
```

`ledger.jsonl` is the same shape, one line per run, append-only — grep it for trends. The
`--durations=25` block at the end of each `*.pytest.log` is the standing profiling data: if the
suite creeps toward the timeout, look there first.

**On red:** re-run the failing test on clean master first — if it is still red with no local
changes, suspect *deployed-state* preconditions (the shared mod folders another session wiped;
see `project-ff9-test-suite-perf` §DEPLOYED-STATE) before suspecting any merge. Then bisect
yesterday's merges with the failing file only.

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
   `smoke-ok` ledger entry.
4. **Register the scheduled task** (defaults to daily 04:00):

   ```bash
   py C:\gd\Dream-World-IX\tools\nightly_gate.py --register-task
   ```

   The task runs the **gate worktree's** copy (`C:\gd\ff9-test-gate\tools\nightly_gate.py`), which
   is always at master — so the gate self-updates when you merge changes to the script; the main
   repo's checked-out branch never matters.
5. **Optional first full run now** (instead of waiting for tonight):

   ```bash
   py C:\gd\Dream-World-IX\tools\nightly_gate.py
   ```

## Adjusting things

- **Run time:** re-register with `--register-task --at 03:30` (or edit the trigger in Task
  Scheduler → "FF9 nightly test gate").
- **Workers:** the task runs the script's defaults (`-n 6` — the measured sweet spot; `-n auto`
  re-contends on disk, don't). To change permanently, edit `--workers`'s default in the script and
  merge; the gate picks it up the next night. Falls back to serial automatically if xdist is missing.
- **Collect floor:** the suite grows; if `collected` in the ledger rises well above 6500, raise the
  default in the script so the guard stays meaningful (floor ≈ 90% of current collection).
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
- **Stale lock** (`lock` present, no run live) → the runner detects a dead PID and steals it
  automatically; delete `.test-gate\lock` by hand only if it somehow persists.
- **`timeout`** → almost always contention (something else was hammering the machine at 04:00),
  not a slow test — see the memory's contention section before chasing anything.
- **The task must never run concurrently with itself or a manual run** — it doesn't: the task is
  registered `IgnoreNew` and the runner exits gracefully when the lock is held.
