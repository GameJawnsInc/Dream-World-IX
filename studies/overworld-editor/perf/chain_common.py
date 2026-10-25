"""Lane "chain" (perf of the recipe bar over world/draft.py and world/recipe.py): shared pins, timers, counters.

Every chain_*.py probe imports this first. It pins the WORKTREE package (asserting ff9mapkit resolves under it), pins
the per-user config dir to a temp folder (the conftest pattern), and keeps every write under OUT. Nothing here writes
the install: drafts live under OUT, and `assert_outside_game` guards each root a probe hands the kit.
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import sys
import threading
import time
from pathlib import Path

WT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\terrain-shaping-continue-4647b2")
KIT = WT / "ff9mapkit"
sys.path.insert(0, str(KIT))
import ff9mapkit                                                      # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(KIT.resolve()), ff9mapkit.__file__

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
SOURCE_NAME = "FF9CustomMap-world"
SOURCE = GAME / SOURCE_NAME
OUT = STUDY / "out" / "perf" / "chain"
OUT.mkdir(parents=True, exist_ok=True)

# THE BYTECODE CACHE (chain_pyc): this agent shell carries PYTHONDONTWRITEBYTECODE=1 in its process env only (not the
# User or Machine environment), so every job it starts recompiles the worktree's stale .pyc modules: +2.3 s a job
# that the owner's Workspace does not pay. Every chain_ probe (and each job its cards and bar start: QProcess
# inherits this env) runs with a warm bytecode cache under OUT/pycache instead -- nothing is written in the package.
# CHAIN_ASIS=1 keeps the shell's env (to measure the artifact itself).
if os.environ.get("CHAIN_ASIS") != "1":
    os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
    os.environ["PYTHONPYCACHEPREFIX"] = str(OUT / "pycache")
    sys.dont_write_bytecode = False
    sys.pycache_prefix = str(OUT / "pycache")
GOLD = OUT / "gold"                       # drafts root holding the built 5-step draft (never mutated after build)

# the per-user config dir (prefs.json, update_check.json) -> a temp folder (tests' _isolate_user_config pattern)
from ff9mapkit import provision as _prov                               # noqa: E402
_real_user_dir = _prov._user_dir
_CFG = OUT / "userdir"


def _user_dir(sub):
    if sub == "config":
        return _CFG / sub
    return _real_user_dir(sub)


_prov._user_dir = _user_dir


def assert_outside_game(p):
    p = Path(p).resolve()
    assert not p.is_relative_to(GAME.resolve()), f"refusing a write root inside the install: {p}"
    return p


def fresh_copy(name: str) -> Path:
    """A fresh drafts root under OUT/work/<name> holding a byte copy (copy2: mtimes kept, so the manifest's stat
    fast path holds as it does in the gold) of the gold draft. Returns the drafts root."""
    root = assert_outside_game(OUT / "work" / name)
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(GOLD, root)          # copy2: data + mtime_ns (NTFS keeps 100 ns; the manifest's stat matches)
    return root


def stats(ts):
    return {"min": round(min(ts), 4), "median": round(statistics.median(ts), 4), "runs": [round(t, 4) for t in ts]}


def timeit(fn, n=5, setup=None):
    ts, out = [], None
    for _ in range(n):
        if setup is not None:
            setup()
        t = time.perf_counter()
        out = fn()
        ts.append(time.perf_counter() - t)
    return stats(ts), out


class Calls:
    """Count and time every call of the named module functions, by thread (GUI = the main thread) and nesting
    depth (depth 0: called from outside the module's own functions)."""

    def __init__(self, mod, names):
        self.mod, self.rows, self._orig = mod, [], {}
        self._tl = threading.local()
        for n in names:
            f = getattr(mod, n)
            self._orig[n] = f
            setattr(mod, n, self._wrap(n, f))

    def _wrap(self, name, f):
        def w(*a, **k):
            depth = getattr(self._tl, "d", 0)
            self._tl.d = depth + 1
            t = time.perf_counter()
            try:
                return f(*a, **k)
            finally:
                self._tl.d = depth
                self.rows.append({"fn": name, "gui": threading.current_thread() is threading.main_thread(),
                                  "depth": depth, "s": time.perf_counter() - t, "t_end": time.perf_counter()})
        w.__wrapped__ = f
        return w

    def mark(self):
        return len(self.rows)

    def summary(self, since=0):
        out = {}
        for r in self.rows[since:]:
            key = f"{r['fn']}|{'gui' if r['gui'] else 'worker'}|d{r['depth']}"
            o = out.setdefault(key, {"n": 0, "s": 0.0, "max": 0.0})
            o["n"] += 1
            o["s"] = round(o["s"] + r["s"], 4)
            o["max"] = round(max(o["max"], r["s"]), 4)
        return dict(sorted(out.items()))

    def restore(self):
        for n, f in self._orig.items():
            setattr(self.mod, n, f)


def save(name, obj):
    p = OUT / name
    p.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
    print(f"-> {p}")
    return p


def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")            # the cards need no GL; no window is shown
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class Loop:
    """Run the real Qt event loop until ``until()`` (or ``sec``), with a 2 ms heartbeat timer whose largest gap is
    the GUI thread's longest freeze while the loop ran (a callback that ran on it: a job's finished handler, a
    worker read's result)."""

    def __init__(self, app):
        from PySide6.QtCore import QEventLoop, QTimer
        self.app, self.QEventLoop, self.QTimer = app, QEventLoop, QTimer

    def run(self, until, sec):
        loop = self.QEventLoop()
        beat, poll = self.QTimer(), self.QTimer()
        gaps, last = [], [time.perf_counter()]
        t0 = time.perf_counter()
        ok = [False]

        def tick():
            now = time.perf_counter()
            gaps.append(now - last[0])
            last[0] = now

        def check():
            if until():
                ok[0] = True
                loop.quit()
            elif time.perf_counter() - t0 > sec:
                loop.quit()
        beat.timeout.connect(tick)
        poll.timeout.connect(check)
        beat.start(2)
        poll.start(10)
        loop.exec()
        beat.stop()
        poll.stop()
        gaps.sort()
        return {"ok": ok[0], "wall": round(time.perf_counter() - t0, 3),
                "max_gap": round(gaps[-1], 4) if gaps else None,
                "p99_gap": round(gaps[int(len(gaps) * 0.99)], 4) if gaps else None,
                "gaps_over_50ms": sum(1 for g in gaps if g > 0.05),
                "gaps_over_100ms": [round(g, 3) for g in gaps if g > 0.1]}
