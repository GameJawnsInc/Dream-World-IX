"""Nightly full-suite test gate for ff9mapkit -- runs the WHOLE pytest suite against master, once,
serially, in a dedicated permanently-provisioned worktree, and writes a machine-readable ledger.

Why this exists (see tools/nightly_gate.md for the full story + setup instructions):
  * The full suite is ~45 min serial and blows up to hours when several sessions run it
    concurrently (shared p0data*.bin I/O contention -- see memory project-ff9-test-suite-perf).
  * Protocol: sessions run only their domain's test files before merging to master; THIS script
    is the one place the full suite runs, nightly, with zero contention and nobody waiting on it.

Moving parts:
  * Gate worktree  (default C:\\gd\\ff9-test-gate)  -- detached checkout re-pointed at master each
    run; provisioned ONCE (templates + fixtures + .ff9mapkit-cache) and kept, so the worktree
    skip-trap (byte-level tests silently not collecting) can't produce a false green here.
  * State dir      (<main repo>\\.test-gate\\, gitignored) -- lock, ledger.jsonl (append-only run
    history), latest.json (most recent result -- what sessions read), runs/<ts>.log (full output).

Modes:
  py tools/nightly_gate.py                  # full gated run (what the scheduled task executes)
  py tools/nightly_gate.py --smoke          # everything EXCEPT the suite run (provision + collect check)
  py tools/nightly_gate.py --register-task  # create/refresh the Windows scheduled task (see --at)
  py tools/nightly_gate.py --unregister-task

The collect-count floor (--collect-floor) is the guard against the worktree skip-trap: if fewer
tests collect than the floor, provisioning is incomplete and the run ABORTS as 'collect-short'
instead of minting a false green.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

TASK_NAME = "FF9 nightly test gate"
DEFAULT_MAIN = Path(r"C:\gd\Dream-World-IX")
DEFAULT_GATE = Path(r"C:\gd\ff9-test-gate")
# The subset of .ff9mapkit-cache worth seeding from the main repo (per project-ff9-test-suite-perf;
# deploy/deploysnap are live deploy state and deliberately NOT copied into the gate).
CACHE_SEED = ["fields", "thumbs", "model_thumbs", "battlemap", "worldstock.json"]


# ---- path resolution ------------------------------------------------------------------------------
def resolve_main_repo() -> Path:
    env = os.environ.get("FF9_MAIN_REPO")
    if env:
        return Path(env)
    # Derive from wherever this script lives: its repo's common git dir's parent is the main repo,
    # regardless of whether the script runs from the main repo, an agent worktree, or the gate.
    here = Path(__file__).resolve().parent
    try:
        out = subprocess.run(
            ["git", "-C", str(here), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=30)
        if out.returncode == 0:
            common = Path(out.stdout.strip())
            if common.name == ".git":
                return common.parent
    except OSError:
        pass
    return DEFAULT_MAIN


def gate_worktree() -> Path:
    return Path(os.environ.get("FF9_GATE_WORKTREE") or DEFAULT_GATE)


# ---- tiny infra -----------------------------------------------------------------------------------
class Log:
    """Append to the run log file AND echo to stdout."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = open(path, "a", encoding="utf-8", errors="replace")
        self.path = path

    def __call__(self, msg: str) -> None:
        line = f"[{datetime.now():%H:%M:%S}] {msg}"
        print(line, flush=True)
        self.fh.write(line + "\n")
        self.fh.flush()


def pid_alive(pid: int) -> bool:
    """Windows-safe liveness probe. NEVER use os.kill(pid, 0) here -- on Windows that TERMINATES."""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    try:
        h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    except OSError:
        return True  # can't tell -> assume alive, don't steal the lock
    if h:
        ctypes.windll.kernel32.CloseHandle(h)
        return True
    return ctypes.get_last_error() == 5  # ERROR_ACCESS_DENIED -> exists but protected


def acquire_lock(lock: Path, log) -> bool:
    lock.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"pid": os.getpid(), "started": datetime.now().isoformat()}).encode())
            os.close(fd)
            return True
        except FileExistsError:
            try:
                holder = json.loads(lock.read_text(encoding="utf-8", errors="replace"))
                pid = int(holder.get("pid", -1))
            except (ValueError, OSError):
                pid = -1
            if pid > 0 and pid_alive(pid):
                log(f"another gate run is in progress (pid {pid}, lock {lock}) -- exiting.")
                return False
            log(f"removing stale lock (pid {pid} not alive).")
            try:
                lock.unlink()
            except OSError:
                return False
    return False


def run(cmd, log, cwd=None, env=None, timeout=None, tee_to=None):
    """Run a child, streaming combined output to the run log (and optionally a separate file)."""
    log(f"$ {' '.join(str(c) for c in cmd)}" + (f"   (cwd={cwd})" if cwd else ""))
    sink = open(tee_to, "a", encoding="utf-8", errors="replace") if tee_to else log.fh
    try:
        p = subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None, env=env,
                           stdout=sink, stderr=subprocess.STDOUT, timeout=timeout)
        return p.returncode
    finally:
        if tee_to:
            sink.close()


def child_env() -> dict:
    """The suite's environment: inherit, but STRIP FF9MAPKIT_DATA -- it redirects both the template
    data dir AND the cache dir, and using it as a provisioning remedy is a documented foot-gun
    (writes land wherever it points). The gate worktree is provisioned for real instead."""
    env = dict(os.environ)
    env.pop("FF9MAPKIT_DATA", None)
    return env


# ---- gate worktree management ---------------------------------------------------------------------
def ensure_gate_worktree(main: Path, gate: Path, log) -> None:
    if not (gate / ".git").exists():
        if gate.exists() and any(gate.iterdir()):
            raise SystemExit(f"{gate} exists but is not a git worktree -- move it aside or set FF9_GATE_WORKTREE.")
        log(f"creating gate worktree at {gate} (detached at master)")
        rc = run(["git", "-C", main, "worktree", "add", "--detach", gate, "master"], log)
        if rc != 0:
            raise SystemExit("git worktree add failed -- see log.")


def checkout_master(gate: Path, log) -> str:
    # --force: a crashed run may leave tracked-file dirt; ignored files (templates/fixtures/cache)
    # are never touched by checkout, so provisioning survives.
    rc = run(["git", "-C", gate, "checkout", "--force", "--detach", "master"], log)
    if rc != 0:
        raise SystemExit("checkout of master failed -- see log.")
    sha = subprocess.run(["git", "-C", str(gate), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    log(f"gate worktree at master ({sha})")
    return sha


# ---- provisioning ---------------------------------------------------------------------------------
def templates_present(kit: Path) -> bool:
    p = subprocess.run([py_exe(), "-c", "from ff9mapkit import provision; print(provision.templates_present())"],
                       cwd=str(kit), env=child_env(), capture_output=True, text=True)
    return p.stdout.strip().endswith("True")


def provision(main: Path, gate: Path, log) -> None:
    kit = gate / "ff9mapkit"
    if not templates_present(kit):
        log("templates absent -- running extract-templates (reads YOUR install, read-only; one-time)")
        rc = run([py_exe(), "-m", "ff9mapkit", "extract-templates"], log, cwd=kit, env=child_env(),
                 timeout=1800)
        if rc != 0 or not templates_present(kit):
            raise SystemExit("extract-templates failed -- the gate cannot run without provisioning.")
    else:
        log("templates present")

    # Seed .ff9mapkit-cache from the main repo (a third asset set extract-templates does NOT build).
    gate_cache = kit / ".ff9mapkit-cache"
    main_cache = main / "ff9mapkit" / ".ff9mapkit-cache"
    if not gate_cache.is_dir() and main_cache.is_dir():
        log(f"seeding .ff9mapkit-cache from {main_cache}")
        gate_cache.mkdir(parents=True)
        for name in CACHE_SEED:
            src = main_cache / name
            if src.is_dir():
                shutil.copytree(src, gate_cache / name)
            elif src.is_file():
                shutil.copy2(src, gate_cache / name)


# ---- pytest ---------------------------------------------------------------------------------------
def py_exe() -> str:
    return shutil.which("py") or sys.executable


def xdist_available(kit: Path) -> bool:
    return subprocess.run([py_exe(), "-c", "import xdist"], cwd=str(kit), env=child_env(),
                          capture_output=True).returncode == 0


def collect_count(kit: Path, log, run_log: Path) -> int:
    rc = run([py_exe(), "-m", "pytest", "--collect-only", "-q"], log, cwd=kit, env=child_env(),
             timeout=1200, tee_to=run_log)
    tail = run_log.read_text(encoding="utf-8", errors="replace")[-4000:]
    m = re.findall(r"(\d+) tests? collected", tail)
    n = int(m[-1]) if m else 0
    log(f"collected {n} tests (pytest rc={rc})")
    return n


def parse_summary(run_log: Path) -> dict:
    tail = run_log.read_text(encoding="utf-8", errors="replace")[-4000:]
    counts = {}
    for n, word in re.findall(r"(\d+) (passed|failed|skipped|errors?|xfailed|xpassed|deselected)", tail):
        counts[word.rstrip("s") if word.startswith("error") else word] = int(n)
    return counts


# ---- ledger ---------------------------------------------------------------------------------------
def write_ledger(state: Path, entry: dict, log) -> None:
    entry = {"timestamp": datetime.now().isoformat(timespec="seconds"), **entry}
    with open(state / "ledger.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    (state / "latest.json").write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
    log(f"ledger: {entry.get('result')} -> {state / 'latest.json'}")


# ---- scheduled task -------------------------------------------------------------------------------
def register_task(main: Path, gate: Path, at: str, log) -> None:
    ensure_gate_worktree(main, gate, log)
    checkout_master(gate, log)
    script = gate / "tools" / "nightly_gate.py"
    if not script.is_file():
        raise SystemExit(f"{script} not found -- merge the gate tooling to master first, then re-run.")
    ps = (
        f"$a = New-ScheduledTaskAction -Execute '{py_exe()}' -Argument '\"{script}\"';"
        f"$t = New-ScheduledTaskTrigger -Daily -At {at};"
        f"$s = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable "
        f"-ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew;"
        f"Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $a -Trigger $t -Settings $s -Force | Out-Null;"
        f"Write-Output 'registered'"
    )
    p = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    if p.returncode != 0 or "registered" not in p.stdout:
        raise SystemExit(f"task registration failed:\n{p.stdout}\n{p.stderr}")
    log(f"scheduled task '{TASK_NAME}' registered: daily at {at}, runs {script}")


def unregister_task(log) -> None:
    p = subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Unregister-ScheduledTask -TaskName '{TASK_NAME}' -Confirm:$false"],
                       capture_output=True, text=True)
    log("task removed" if p.returncode == 0 else f"removal failed (already gone?):\n{p.stderr}")


# ---- main -----------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--smoke", action="store_true", help="provision + collect check only, no suite run")
    ap.add_argument("--workers", type=int, default=6, help="xdist workers (default 6; 0 = serial)")
    ap.add_argument("--collect-floor", type=int, default=6500,
                    help="abort if fewer tests collect (the worktree skip-trap guard)")
    ap.add_argument("--timeout-min", type=int, default=180, help="suite hard timeout (default 180)")
    ap.add_argument("--register-task", action="store_true", help="create/refresh the scheduled task")
    ap.add_argument("--unregister-task", action="store_true", help="remove the scheduled task")
    ap.add_argument("--at", default="04:00", help="daily trigger time for --register-task (default 04:00)")
    args = ap.parse_args()

    main_repo = resolve_main_repo()
    gate = gate_worktree()
    state = main_repo / ".test-gate"
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    log = Log(state / "runs" / f"{ts}.log")
    log(f"main repo: {main_repo}   gate: {gate}   mode: "
        + ("register" if args.register_task else "unregister" if args.unregister_task
           else "smoke" if args.smoke else "full"))

    if args.unregister_task:
        unregister_task(log)
        return 0
    if args.register_task:
        register_task(main_repo, gate, args.at, log)
        return 0

    if not acquire_lock(state / "lock", log):
        return 0  # graceful: a run is already going; the scheduler also has IgnoreNew
    t0 = time.time()
    entry = {"result": "error", "mode": "smoke" if args.smoke else "full", "log": str(log.path)}
    try:
        ensure_gate_worktree(main_repo, gate, log)
        entry["sha"] = checkout_master(gate, log)
        provision(main_repo, gate, log)

        kit = gate / "ff9mapkit"
        n = collect_count(kit, log, log.path.with_suffix(".collect.log"))
        entry["collected"] = n
        if n < args.collect_floor:
            entry["result"] = "collect-short"
            log(f"ABORT: only {n} tests collected (< floor {args.collect_floor}) -- provisioning is "
                f"incomplete; a run now would be the skip-trap's false green. See nightly_gate.md.")
            return 1
        if args.smoke:
            entry["result"] = "smoke-ok"
            log("smoke OK: worktree + provisioning + collection all healthy.")
            return 0

        cmd = [py_exe(), "-m", "pytest", "-q", "--durations=25"]
        workers = args.workers if args.workers and xdist_available(kit) else 0
        if workers:
            cmd += ["-n", str(workers)]
        entry["workers"] = workers or 1
        suite_log = log.path.with_suffix(".pytest.log")
        entry["suite_log"] = str(suite_log)
        try:
            rc = run(cmd, log, cwd=kit, env=child_env(), timeout=args.timeout_min * 60, tee_to=suite_log)
        except subprocess.TimeoutExpired:
            entry["result"] = "timeout"
            log(f"suite exceeded {args.timeout_min} min -- killed.")
            return 1
        entry.update(parse_summary(suite_log))
        entry["result"] = "green" if rc == 0 else "red" if rc == 1 else "error"
        entry["exit_code"] = rc
        log(f"suite done: {entry['result']} ({ {k: v for k, v in entry.items() if k in ('passed', 'failed', 'skipped', 'error')} })")
        return rc
    finally:
        entry["duration_s"] = round(time.time() - t0, 1)
        write_ledger(state, entry, log)
        try:
            (state / "lock").unlink()
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
