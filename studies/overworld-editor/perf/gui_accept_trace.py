"""gui lane, ONE END-TO-END TRACE: a forest card's Check and Accept on the real World tab, then Undo / Redo.

    py studies/overworld-editor/perf/gui_accept_trace.py [base|p1|proto] [cycles] [tag]

The real WorldDoc (native platform, WA_DontShowOnScreen, prefs pinned), its forest card with its REAL QProcessRunner
(world-forest subprocesses, --game given by the card, --mod-folder = a draft under out/perf/gui/drafts_trace_<variant>,
ours alone), every other runner a FakeRunner. Each cycle: Check, Accept, Undo, Redo, Undo (the draft ends as it began).
The legs are timestamped by pass-through wrappers (output untouched), each with the THREAD it ran on: the job (a
subprocess the card waits on), its done on the GUI thread (draft.begin_step / commit_step, the card's _accepted,
WorldDoc._draft_changed: the recipe bar, every card's island_changed, the draw box, _load_view3d), the worker's
whole-map load_scene, the panel's _finish and the first paint (the GL upload), the island soups and the draft label
read again (workers). The headline per leg: from the click (or the job's end) until the 3D view draws again -- the
panel shows "Loading the map..." in its place meanwhile.

  base   the shipped code
  p1     P1 alone (to attribute the two)
  proto  two prototypes, monkeypatched here (nothing in the package changes):
         P1 gui_proto_reload.Proto level 2 with the root-agnostic key: load only the cells whose files changed
         P2 the accepting card skips its own drop/re-read of the soups and the draft label when the tab's on_changed
            will do the same (WorldDoc._draft_changed -> every card's island_changed): one set of worker reads, not two
         After EVERY leg the view's Packed is compared byte-for-byte with an unpatched load_scene of the same site.
Children get bytecode on (cached under our out dir), as the user's do.
Evidence: out/perf/gui/gui_accept_trace_<variant>.json.
"""
from __future__ import annotations

import os
import shutil
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

SPOT, DONOR = (1400.0, -460.0), "13,15"
EV = []
T0 = [None]


def mark(label, t0, t1):
    EV.append({"label": label, "thread": "GUI" if threading.current_thread() is threading.main_thread() else "worker",
               "start_s": round(t0 - T0[0], 4) if T0[0] else None, "dur_s": round(t1 - t0, 4)})


def wrap(owner, name, label=None):
    orig = getattr(owner, name)

    def w(*a, **k):
        t0 = time.perf_counter()
        try:
            return orig(*a, **k)
        finally:
            mark(label or name, t0, time.perf_counter())
    setattr(owner, name, w)
    return orig


def main():
    variant = sys.argv[1] if len(sys.argv) > 1 else "base"
    cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    assert variant in ("base", "proto", "p1")                         # p1: P1 alone (attribution)
    drafts = C.OUT / f"drafts_trace_{variant}"
    os.environ.pop("PYTHONDONTWRITEBYTECODE", None)                   # the children: bytecode on, as the user's
    os.environ["PYTHONPYCACHEPREFIX"] = sys.pycache_prefix
    app = C.native_app()
    from ff9mapkit.workspace import shell as S
    from ff9mapkit.workspace import worlddoc as WD
    from ff9mapkit.workspace import worldforest as WF
    from ff9mapkit.workspace import worldrecipe as WR
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import draft as D
    from ff9mapkit.world import render as R
    pal = S.pick_palette("dark")
    S._apply_app_theme(app, pal)
    if drafts.exists():
        shutil.rmtree(drafts)
    D.ensure_draft(C.SOURCE, game=C.GAME, root=drafts)                 # (the card would make it on its first Check)

    real_load_scene = V.load_scene
    Base = V.WorldView3D

    class TimedView(Base):
        def paintGL(self):                                            # noqa: N802
            t0 = time.perf_counter()
            up = self._pending is not None
            Base.paintGL(self)
            self.context().functions().glFinish()
            if up:
                mark("paintGL (with the GL upload)", t0, time.perf_counter())
    V.WorldView3D = TimedView
    for owner, name, label in (
            (WF.CarryTool, "_run_job", "card._run_job (job start)"),
            (WF.CarryTool, "_job_done", "card._job_done (the job's done, all nested)"),
            (WF.CarryTool, "island_changed", "card.island_changed"),
            (WF.CarryTool, "_read_soup", "card._read_soup (island soup read)"),
            (D, "begin_step", "draft.begin_step"), (D, "commit_step", "draft.commit_step"),
            (D, "undo", "draft.undo"), (D, "redo", "draft.redo"),
            (D, "edited_blocks", "draft.edited_blocks (draft label)"), (D, "stale", "draft.stale (draft label)"),
            (WD.WorldDoc, "_draft_changed", "WorldDoc._draft_changed (all nested)"),
            (WR.RecipeBar, "refresh", "RecipeBar.refresh"),
            (V.WorldView3DPanel, "load", "panel.load (GUI part)"),
            (V.WorldView3DPanel, "_finish", "panel._finish")):
        wrap(owner, name, label)
    proto = None
    if variant in ("proto", "p1"):
        from gui_proto_reload import Proto
        proto = Proto(R, V, roots_in_key=False)
        proto.install(2)                                              # P1
    if variant == "proto":
        orig_accepted = WF.CarryTool._accepted

        def accepted(self, v):                                        # P2
            if self._on_changed is None:
                return orig_accepted(self, v)
            real = {k: getattr(self, k) for k in ("_drop_soups", "_refresh_draft_label", "_load_soup")}
            for k in real:
                setattr(self, k, lambda *a, **kw: None)
            outer = self._on_changed

            def on_changed(d):
                for k, fn in real.items():                            # the tab's island_changed does all three
                    setattr(self, k, fn)
                self._on_changed = outer
                outer(d)
            self._on_changed = on_changed
            try:
                return orig_accepted(self, v)
            finally:
                for k in real:                                        # (instance attrs only: the class's methods
                    self.__dict__.pop(k, None)                        # resolve again)
                self._on_changed = outer
        WF.CarryTool._accepted = accepted
    wrap(WF.CarryTool, "_accepted", "card._accepted")
    timed_load = wrap(V, "load_scene", "load_scene (whole map)")

    fakes = {f"{k}_runner": C.FakeRunner() for k in ("mountain", "recipe", "sink", "coast", "island", "transplant",
                                                      "river", "hill")}
    doc = WD.WorldDoc(pal, game_path_fn=lambda: C.GAME, drafts_root=drafts, **fakes)
    C.hide(doc)
    doc.resize(1280, 850)
    doc.show()
    C.settle(app)

    def pump(until, sec):
        t = time.perf_counter()
        while time.perf_counter() - t < sec:
            app.processEvents()
            if until():
                return time.perf_counter() - t
            time.sleep(0.003)
        raise SystemExit(f"timed out after {sec}s")

    def view_back():
        return not doc._view3d._busy and any(e["label"].startswith("paintGL") for e in EV)

    def identity():
        """The view's scene == an unpatched load_scene of the site it drew (proto: the memo changed nothing)."""
        if proto is None:
            return None
        proto.uninstall()
        try:
            ref, _ = real_load_scene(doc._view3d.site)
        finally:
            proto.install(2)
        from gui_proto_reload import same_packed
        return same_packed(doc._view3d.view.packed, ref)

    out = {"variant": variant, "legs": []}
    T0[0] = time.perf_counter()
    doc.refresh()
    out["scan_wall_s"] = round(pump(lambda: doc._census is not None and not doc._busy, 60), 3)
    doc.set_view_mode("3d")
    out["first_3d_wall_s"] = round(pump(lambda: doc._view3d.view is not None and not doc._view3d._busy, 180), 3)
    C.settle(app)
    forest = doc.open_forest()
    forest.donor_box.setCurrentIndex(forest.donor_box.findData(DONOR))
    out["card_open_reads_wall_s"] = round(pump(lambda: forest._ix is not None and forest.donor() in forest._outlines,
                                               120), 3)

    def leg(name, act, until_done=None):
        EV.clear()
        C.settle(app)
        T0[0] = time.perf_counter()
        act()
        gui_call = time.perf_counter() - T0[0]
        t_done = pump(until_done, 300) if until_done else 0.0
        t_view = pump(view_back, 300)
        t_reads = pump(lambda: forest.isHidden() or forest._ix is not None, 120)
        rec = {"leg": name, "click_gui_call_s": round(gui_call, 4), "until_job_done_s": round(t_done, 3),
               "job_done_to_view_back_s": round(t_view, 3), "click_to_view_back_s": round(t_done + t_view, 3),
               "then_until_soup_back_s": round(t_reads, 3), "identical": identity(), "events": list(EV)}
        if proto is not None:
            rec["proto_misses_total"] = proto.misses
        gui = [e for e in EV if e["thread"] == "GUI"]
        rec["gui_over_100ms"] = [e for e in gui if e["dur_s"] >= 0.1 and "all nested" not in e["label"]]
        out["legs"].append(rec)
        print(f"{name:8s} gui-call {gui_call:.3f}s  job {t_done:.2f}s  ->view {t_view:.2f}s  total "
              f"{t_done + t_view:.2f}s  identical={rec['identical']}  gui>=100ms: "
              + ", ".join(f"{e['label']} {e['dur_s']}" for e in rec["gui_over_100ms"]))
        return rec

    for _c in range(cycles):
        forest.open_tool() if forest.isHidden() else None
        pump(lambda: forest._ix is not None and forest.donor() in forest._outlines, 120)
        EV.clear()
        T0[0] = time.perf_counter()
        forest.place(*SPOT, 3.0)
        t_check = pump(lambda: forest._current_verdict() is not None, 300)
        out.setdefault("check_wall_s", []).append(round(t_check, 3))
        assert forest.accept_btn.isEnabled(), forest.verdict_lbl.text()
        leg("accept", forest.accept_btn.click, lambda: forest._job is None and forest.center is None)
        forest.close_tool()
        C.settle(app)
        leg("undo", doc._recipe.undo)
        leg("redo", doc._recipe.redo)
        leg("undo", doc._recipe.undo)
    out["summary"] = {k: C.stats([r["click_to_view_back_s"] for r in out["legs"] if r["leg"] == k])
                      for k in ("accept", "undo", "redo")}
    print(out["summary"])
    doc._view3d.view.release_gl()
    tag = sys.argv[3] if len(sys.argv) > 3 else ""                    # a repeat run's own evidence file
    C.dump(f"gui_accept_trace_{variant}{('_' + tag) if tag else ''}.json", out)


if __name__ == "__main__":
    main()
