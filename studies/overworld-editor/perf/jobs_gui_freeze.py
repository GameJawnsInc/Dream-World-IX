"""Lane jobs: the GUI-thread freeze of a card's Check and Accept, measured on the REAL card (offscreen: the cards
need no GL; the real QProcessRunner runs the real subprocess jobs) with a 10 ms QTimer heartbeat on the GUI thread.
A gap between two heartbeats is a time the window could not repaint or take input. Reported: the longest gap and
the summed time in gaps over 100 ms, during each phase (Check: place -> verdict; Accept: click -> the card's
post-accept state).

The card makes its own draft under out/perf/jobs/freeze/<verb>/ (its drafts_root seam; deleted after), so the first
Accept also meets every draft file's first open. For the sink a SECOND Accept on another island in the same draft
gives the steady state.

    py studies/overworld-editor/perf/jobs_gui_freeze.py sink|forest|coast     -> out/perf/jobs/gui_freeze_<verb>.json
"""
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

if os.environ.get("JOBS_PYC", "warm") == "warm":         # the user's Workspace: bytecode cached (into a prefix tree
    os.environ.pop("PYTHONDONTWRITEBYTECODE", None)        # under out/perf/jobs, so nothing lands in the package);
    os.environ["PYTHONPYCACHEPREFIX"] = str(Path(__file__).resolve().parents[1] / "out" / "perf" / "jobs" / "pycache")
    sys.dont_write_bytecode = False                       # the card's QProcess jobs inherit this environment
    sys.pycache_prefix = os.environ["PYTHONPYCACHEPREFIX"]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from ff9mapkit import provision  # noqa: E402

_CFG = Path(tempfile.mkdtemp(prefix="jobs_cfg_"))
_real = provision._user_dir
provision._user_dir = lambda sub: _CFG if sub == "config" else _real(sub)

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])
from ff9mapkit.editor.theme import pick_palette  # noqa: E402
from ff9mapkit.workspace.worldforest import QProcessRunner  # noqa: E402
from ff9mapkit.workspace.worldview3d import WorldView3DPanel  # noqa: E402

PAL = pick_palette("dark")
SPANS = []                                               # (kind, start, end): begin/commit on the GUI thread, workers


def _instrument():
    """Spans for the gap attribution: draft.begin_step / commit_step (called on the GUI thread by the card) and every
    CarryTool._bg worker read (its own thread)."""
    from ff9mapkit.world import draft as D
    from ff9mapkit.workspace import worldforest as WF
    for name in ("begin_step", "commit_step"):
        f = getattr(D, name)

        def w(*a, _f=f, _n=name, **k):
            t = time.perf_counter()
            try:
                return _f(*a, **k)
            finally:
                SPANS.append((_n, t, time.perf_counter()))
        setattr(D, name, w)
    real_bg = WF.CarryTool._bg

    def bg(self, what, fn):
        def run(_fn=fn, _what=what):
            t = time.perf_counter()
            try:
                return _fn()
            finally:
                SPANS.append(("worker:" + _what, t, time.perf_counter()))
        return real_bg(self, what, run)
    WF.CarryTool._bg = bg


_instrument()
beats = []
SAMPLES = {}                                             # GUI-thread stack samples taken while no heartbeat lands
import collections  # noqa: E402
import threading  # noqa: E402
import traceback  # noqa: E402

_MAIN = threading.main_thread().ident
_sampling = {"on": False}


def _sampler():
    while True:
        time.sleep(0.02)
        if not _sampling["on"] or not beats or time.perf_counter() - beats[-1] < 0.1:
            continue
        fr = sys._current_frames().get(_MAIN)
        if fr is None:
            continue
        st = traceback.extract_stack(fr)
        mine = [f"{Path(f.filename).name}:{f.name}" for f in st
                if "ff9mapkit" in f.filename or "PySide6" in f.filename or "site-packages" not in f.filename]
        key = " < ".join(reversed(mine[-4:]))
        SAMPLES[key] = SAMPLES.get(key, 0) + 1


threading.Thread(target=_sampler, daemon=True).start()
hb = QTimer()
hb.setInterval(10)
hb.timeout.connect(lambda: beats.append(time.perf_counter()))


def pump(until, sec):
    t = time.time()
    while time.time() - t < sec:
        app.processEvents()
        if until():
            return True
        time.sleep(0.005)
    return False


def phase(name, start, until, sec):
    """Run ``start()`` then pump until ``until()``; return the heartbeat gaps of the phase."""
    beats.clear()
    SPANS.clear()
    SAMPLES.clear()
    _sampling["on"] = True
    hb.start()
    t0 = time.perf_counter()
    beats.append(t0)
    start()
    ok = pump(until, sec)
    t1 = time.perf_counter()
    beats.append(t1)
    hb.stop()
    _sampling["on"] = False
    gaps = [b - a for a, b in zip(beats, beats[1:])]
    worst = max(gaps) if gaps else 0.0
    attrib = {}
    for a, b in zip(beats, beats[1:]):
        if b - a <= 0.1:
            continue
        for kind, s0, s1 in SPANS:
            ov = min(b, s1) - max(a, s0)
            if ov > 0:
                attrib[kind] = round(attrib.get(kind, 0.0) + ov, 3)
    return {"phase": name, "ok": ok, "wall_s": round(t1 - t0, 3), "longest_gui_gap_s": round(worst, 3),
            "gaps_over_100ms_s": round(sum(g for g in gaps if g > 0.1), 3),
            "n_gaps_over_100ms": sum(1 for g in gaps if g > 0.1),
            "gap_overlap_s": attrib,
            "gui_stack_samples_20ms": dict(sorted(SAMPLES.items(), key=lambda kv: -kv[1])[:8])}


def make(cls, drafts):
    tool = cls(PAL, WorldView3DPanel(PAL), game_fn=lambda: J.GAME, source_fn=lambda: J.SOURCE,
               runner=QProcessRunner(), drafts_root=drafts, ask=lambda t, x: True)
    tool.open_tool()
    return tool


def main():
    verb = sys.argv[1]
    drafts = J.OUT / "freeze" / verb
    if drafts.exists():
        shutil.rmtree(drafts)
    out = {"verb": verb, "phases": []}
    if verb == "sink":
        from ff9mapkit.workspace.worldsink import ISLANDS, SinkTool
        tool = make(SinkTool, drafts)
        assert pump(lambda: tool._ix is not None and ISLANDS in tool._outlines, 900), "no island list"
        rows = sorted(tool._outlines[ISLANDS], key=lambda w: w.get("land_u2", 0))
        first = (495.116, -293.767)
        order = [first] + [tuple(w["at"]) for w in rows if tuple(w["at"]) != first]
    elif verb == "forest":
        from ff9mapkit.workspace.worldforest import ForestTool
        tool = make(ForestTool, drafts)
        tool.donor_box.setCurrentIndex(tool.donor_box.findData("13,15"))
        assert pump(lambda: tool._ix is not None and (13, 15) in tool._outlines, 300), "no island"
        order = [(1400.0, -460.0)]
    else:
        raise SystemExit("verb: sink | forest")
    accepted = 0
    for at in order:
        if accepted >= (2 if verb == "sink" else 1):
            break
        tool._verdict = None
        pc = phase(f"check@{at}", lambda: tool.place(at[0] + (1.0 if verb == "sink" else 0.0),
                                                     at[1] + (1.0 if verb == "sink" else 0.0), 3.0),
                   lambda: tool._current_verdict() is not None or (tool._preview is not None
                                                                   and not tool._preview.get("ok")), 300)
        v = tool._current_verdict()
        pc["verdict_ok"] = None if v is None else v.get("ok")
        print(json.dumps(pc), flush=True)
        if not (v and v.get("ok") and tool.accept_btn.isEnabled()):
            continue
        out["phases"].append(pc)
        pa = phase(f"accept@{at}", tool.accept_btn.click,
                   lambda: tool._job is None and tool.center is None, 900)
        pa["after"] = tool.verdict_lbl.text()[:160]
        print(json.dumps(pa), flush=True)
        out["phases"].append(pa)
        accepted += 1
        pump(lambda: False, 3.0)                         # let the post-accept reads land before the next island
    (J.OUT / f"gui_freeze_{verb}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    tool.close_tool()
    shutil.rmtree(drafts, ignore_errors=True)


if __name__ == "__main__":
    main()
