"""Multi-instance probe P0: a second FF9.exe from the SAME root beside a live harness game (negative control).

Instance A = this harness session on the real install (launched by play.py, cwd = the root, WITH -single-instance).
B  = x64/FF9.exe from the same root WITHOUT -single-instance (+ -logFile to scratch): expected to die at the deny-write
     ./Memoria.log open (Memoria.Prime Log.cs -> Environment.Exit(1)) -- or not.
B2 = the same WITH -single-instance: expected to hit A's path-keyed mutex and quit.
After each: A must still tick, and A's Memoria.log / output_log.txt must not shrink. Any survivor is killed at 20 s.

    py tools/play.py studies/test-harness/multi-instance/p0_second_process.py --label mi-p0

MEASURED 2026-10-15 (6/7, the one red is the finding): A unaffected by both. B (same cwd, no flag) did NOT exit -- its Unity
log stops after loading Memoria.Prime.dll and it sat alive until the 20 s kill (a HANG, not Log.cs's Exit(1)). B2 (flag) hit
A's path-keyed mutex and exited 0 in 0.43 s, before writing any log.
"""
import subprocess
import tempfile
import time
from pathlib import Path

SCR = Path(tempfile.gettempdir()) / "ff9-mi-p0"      # B's -logFile + per-launch results
SCR.mkdir(exist_ok=True)
WAIT_S = 20.0


def _sizes(root: Path) -> dict:
    out = {}
    for p in (root / "Memoria.log", root / "x64" / "FF9_Data" / "output_log.txt"):      # append-only logs
        try:
            st = p.stat()
            out[p.name] = (st.st_size, st.st_mtime)
        except OSError:
            out[p.name] = None
    return out


def _ticks(g, secs: float = 2.0) -> tuple:
    a = g.state.frame
    time.sleep(secs)
    b = g.state.frame
    return a, b


def _launch(g, root: Path, tag: str, single: bool) -> dict:
    exe = root / "x64" / "FF9.exe"
    log = SCR / f"p0-{tag}.unity.log"
    args = [str(exe), "-runbylauncher"] + (["-single-instance"] if single else []) + [
        "-monitor", "0", "-screen-width", "960", "-screen-height", "540", "-screen-fullscreen", "0", "-logFile", str(log)]
    before = _sizes(root)
    t0 = time.time()
    p = subprocess.Popen(args, cwd=str(root))
    code, alive_at = None, None
    while time.time() - t0 < WAIT_S:
        code = p.poll()
        if code is not None:
            break
        time.sleep(0.25)
    dt = round(time.time() - t0, 2)
    if code is None:
        alive_at = dt
        p.kill()
        try:
            code = p.wait(10)
        except subprocess.TimeoutExpired:
            code = "unkillable"
    after = _sizes(root)
    a, b = _ticks(g)
    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else None
    return {"tag": tag, "single": single, "pid": p.pid, "exit": code, "secs": dt, "killed_alive_at": alive_at,
            "before": before, "after": after, "a_frames": (a, b), "unity_log_tail": (text or "")[-1500:],
            "unity_log_exists": text is not None}


def run(g):
    root = Path(g.game_path)
    st = g.state
    g.note(f"P0: instance A is up (frame {st.frame}, ui {st.ui_state})")
    a0, a1 = _ticks(g)
    g.check(a1 > a0, "P0-A: instance A ticks before any second launch", f"frames {a0} -> {a1}")
    for tag, single in (("B-noflag", False), ("B2-flag", True)):
        g.note(f"P0: launching {tag}")
        r = _launch(g, root, tag, single)
        print(f"[p0] {tag}: exit={r['exit']} after {r['secs']} s; killed alive at {r['killed_alive_at']}; "
              f"A frames {r['a_frames']}; sizes before {r['before']} after {r['after']}")
        print(f"[p0] {tag} unity log ({'present' if r['unity_log_exists'] else 'ABSENT'}):\n{r['unity_log_tail']}")
        (SCR / f"p0-{tag}.result.txt").write_text(repr(r), encoding="utf-8")
        g.check(r["a_frames"][1] > r["a_frames"][0], f"P0-{tag}-A: instance A still ticks after {tag}",
                f"frames {r['a_frames']}")
        shrunk = [k for k, v in r["before"].items() if v and r["after"].get(k) and r["after"][k][0] < v[0]]
        g.check(not shrunk, f"P0-{tag}-LOGS: no A log shrank (Memoria.log, output_log.txt)",
                f"shrunk {shrunk}; before {r['before']}; after {r['after']}")
        g.check(r["killed_alive_at"] is None, f"P0-{tag}-EXIT: {tag} exited by itself within {WAIT_S} s",
                f"exit {r['exit']} after {r['secs']} s; killed alive at {r['killed_alive_at']}")
        time.sleep(3)
    st = g.state
    g.note(f"P0 done: A at frame {st.frame}, ui {st.ui_state}")
