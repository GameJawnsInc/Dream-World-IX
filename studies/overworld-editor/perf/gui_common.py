"""Shared setup for the gui_ perf lane (World tab: what freezes the GUI thread, what the 3D view costs).

Pins the worktree package, pins per-user config to a temp dir (the conftest seam: provision._user_dir("config")),
and gives a native QApplication whose widgets use WA_DontShowOnScreen (never a window on the user's desktop).
READ ONLY against the install: every write goes under out/perf/gui/.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]
KIT = WT / "ff9mapkit"
# THIS AGENT SHELL SETS PYTHONDONTWRITEBYTECODE=1 (the user's env does not), so a stale .pyc is recompiled on every
# import (interior.py alone: 117 ms). Measure the user's steady state: bytecode on, cached under OUR out dir (never
# the package's __pycache__). Both are read at import time, so set before the first kit import.
sys.dont_write_bytecode = False
sys.pycache_prefix = str(WT / "studies" / "overworld-editor" / "out" / "perf" / "gui" / "pycache")
sys.path.insert(0, str(KIT))
import ff9mapkit                                                      # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(KIT.resolve()), ff9mapkit.__file__

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
SOURCE = GAME / "FF9CustomMap-world"
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "gui"
OUT.mkdir(parents=True, exist_ok=True)

os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
_CFG = Path(tempfile.mkdtemp(prefix="gui_perf_cfg_"))
from ff9mapkit import provision                                       # noqa: E402
_real_user_dir = provision._user_dir
provision._user_dir = lambda sub: _CFG / "user-config" if sub == "config" else _real_user_dir(sub)
(_CFG / "user-config").mkdir(parents=True, exist_ok=True)
(_CFG / "user-config" / "prefs.json").write_text(json.dumps({
    "theme": "dark", "text_scale": 100, "guided": False, "density": "comfortable", "motion": "off",
    "restore_session": False, "recent": []}), encoding="utf-8")
(_CFG / "user-config" / "update_check.json").write_text(json.dumps({"prompted": True, "enabled": False}),
                                                         encoding="utf-8")


def native_app():
    if os.environ.get("QT_QPA_PLATFORM") in ("offscreen", "minimal"):
        del os.environ["QT_QPA_PLATFORM"]
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app.platformName() not in ("offscreen", "minimal"), app.platformName()
    return app


def hide(w):
    from PySide6.QtCore import Qt
    w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    return w


def settle(app, n=6):
    from PySide6.QtCore import QCoreApplication, QEvent
    for _ in range(n):
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()


def wall(fn, runs=3, *, setup=None):
    """[seconds] for ``runs`` calls of ``fn`` (``setup`` before each, untimed); returns (times, last result)."""
    out, res = [], None
    for _ in range(runs):
        if setup is not None:
            setup()
        t = time.perf_counter()
        res = fn()
        out.append(time.perf_counter() - t)
    return out, res


def stats(ts):
    return {"runs": len(ts), "min_s": round(min(ts), 6), "median_s": round(statistics.median(ts), 6),
            "max_s": round(max(ts), 6), "all_s": [round(t, 6) for t in ts]}


def dump(name, data):
    p = OUT / name
    p.write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")
    print("wrote", p)
    return p


class FakeRunner:
    """A runner that never runs anything (a card or bar job that would write stays inert): records argv only."""

    def __init__(self):
        self.argvs = []

    def start(self, argv, cwd, done):
        self.argvs.append([str(a) for a in argv])

    def kill(self):
        pass

    def busy(self):
        return False

    def wait(self, msecs=0):
        return True
