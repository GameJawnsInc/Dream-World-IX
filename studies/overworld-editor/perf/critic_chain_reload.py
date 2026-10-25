"""critic probe: what a user waits when draft changes come FASTER than the 3D view's whole-map reload, and on the
recipe bar's Edit / Cancel edit with the 3D page attached (no lane measured either).

    py studies/overworld-editor/perf/critic_chain_reload.py [rounds]

WorldView3DPanel.load queues a request that arrives while a load runs (``_next``), and when the running load lands
``_finish`` DISCARDS it and starts the queued one. So two changes inside one reload cost the rest of the first load
plus a whole second one. The gui lane's trace waited for the view after every leg; the chain lane's Edit/Delete
timings ran with no 3D page. This probe uses the real WorldDoc (native platform, WA_DontShowOnScreen, prefs pinned
by gui_common), the forest card's REAL QProcessRunner into OUR draft (out/perf/critic/drafts_chainreload), every
other runner a FakeRunner. Shipped code only: nothing is patched except pass-through timers.

Per round:
  control_undo / control_redo   one click, wait until the view draws again
  rapid_undo_redo               Undo, then Redo 1.0 s later (inside the reload): time from the Undo click and from
                                the Redo click until the view draws again; load_scene calls counted
  edit_click                    RecipeBar.select(0) + edit(): until the view draws again, and until the card's soup
                                is back (the card is usable only when both are)
  cancel_edit                   the card's close during the edit (= Cancel edit): until the view draws again
Evidence: out/perf/critic/critic_chain_reload.json
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

OUT = C.WT / "studies" / "overworld-editor" / "out" / "perf" / "critic"
OUT.mkdir(parents=True, exist_ok=True)
SPOT, DONOR = (1400.0, -460.0), "13,15"
LOADS = []
PAINTS = [0]
LT0 = [0.0]


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    drafts = OUT / "drafts_chainreload"
    os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
    os.environ["PYTHONPYCACHEPREFIX"] = sys.pycache_prefix
    app = C.native_app()
    from ff9mapkit.workspace import shell as S
    from ff9mapkit.workspace import worlddoc as WD
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import draft as D
    assert Path(WD.__file__).resolve().is_relative_to(C.KIT.resolve()), WD.__file__
    pal = S.pick_palette("dark")
    S._apply_app_theme(app, pal)
    if drafts.exists():
        shutil.rmtree(drafts)
    D.ensure_draft(C.SOURCE, game=C.GAME, root=drafts)
    assert str(drafts.resolve()) in str(D.draft_path(C.SOURCE, root=drafts).resolve())

    real_ls = V.load_scene

    def load_scene(site):
        t0 = time.perf_counter()
        try:
            return real_ls(site)
        finally:
            LOADS.append({"start_s": round(t0 - LT0[0], 3), "dur_s": round(time.perf_counter() - t0, 3)})
    V.load_scene = load_scene
    Base = V.WorldView3D

    class TimedView(Base):
        def paintGL(self):                                            # noqa: N802
            Base.paintGL(self)
            PAINTS[0] += 1
    V.WorldView3D = TimedView

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

    def view_back_since(p0):
        return lambda: not doc._view3d._busy and PAINTS[0] > p0 and doc._view3d._stack.currentWidget() is \
            doc._view3d.view

    out = {"rounds": [], "note": "shipped code; real forest QProcessRunner into our draft; others FakeRunner"}
    doc.refresh()
    out["scan_s"] = round(pump(lambda: doc._census is not None and not doc._busy, 60), 3)
    doc.set_view_mode("3d")
    out["first_3d_s"] = round(pump(lambda: doc._view3d.view is not None and not doc._view3d._busy, 240), 3)
    C.settle(app)
    forest = doc.open_forest()
    forest.donor_box.setCurrentIndex(forest.donor_box.findData(DONOR))
    pump(lambda: forest._ix is not None and forest.donor() in forest._outlines, 120)
    forest.place(*SPOT, 3.0)
    out["check_s"] = round(pump(lambda: forest._current_verdict() is not None, 300), 3)
    assert forest.accept_btn.isEnabled(), forest.verdict_lbl.text()
    p0 = PAINTS[0]
    t0 = time.perf_counter()
    forest.accept_btn.click()
    pump(lambda: forest._job is None and forest.center is None, 300)
    pump(view_back_since(p0), 300)
    out["accept_click_to_view_s"] = round(time.perf_counter() - t0, 3)
    forest.close_tool()
    C.settle(app)
    pump(lambda: all(not t._bg_busy() if hasattr(t, "_bg_busy") else True for t in doc._carry_tools()), 5)
    bar = doc._recipe
    assert len(bar.steps()) == 1, bar.steps()

    def one(name, act, extra=None):
        C.settle(app)
        time.sleep(1.5)                                               # let earlier workers end (soups, labels)
        app.processEvents()
        n0, p = len(LOADS), PAINTS[0]
        t = time.perf_counter()
        act()
        gui = time.perf_counter() - t
        rec = {"leg": name, "click_gui_call_s": round(gui, 3)}
        LT0[0] = t
        if extra is not None:
            extra(rec, t)
        pump(view_back_since(p), 300)
        end = time.perf_counter()
        rec["click_to_view_back_s"] = round(end - t, 3)               # from the click, extra()'s time included
        if "_t2" in rec:
            rec["redo_click_to_view_back_s"] = round(end - rec.pop("_t2"), 3)
        rec["load_scene_calls"] = LOADS[n0:]
        print(name, rec)
        return rec

    for r in range(rounds):
        rnd = {"round": r}
        rnd["control_undo"] = one("control_undo", bar.undo)
        rnd["control_redo"] = one("control_redo", bar.redo)

        def rapid(rec, t):
            pump(lambda: time.perf_counter() - t >= 1.0, 5)
            t2 = time.perf_counter()
            bar.redo()
            rec["redo_at_s"] = round(t2 - t, 3)
            rec["_t2"] = t2
        rec = one("rapid_undo_redo", bar.undo, rapid)
        rnd["rapid_undo_redo"] = rec
        assert D.history(bar.draft())["cursor"] == 1

        def edit():
            bar.select(0)
            bar.edit()

        def soup(rec, t):
            pump(lambda: not forest.isHidden() and forest._ix is not None and forest.editing(), 300)
            rec["click_to_card_soup_s"] = round(time.perf_counter() - t, 3)
        e = one("edit_click", edit, soup)
        e["card_usable_s"] = max(e["click_to_view_back_s"], e["click_to_card_soup_s"])
        rnd["edit_click"] = e
        rnd["cancel_edit"] = one("cancel_edit", forest.close_tool)
        assert bar._edit is None and D.history(bar.draft())["cursor"] == 1
        out["rounds"].append(rnd)

    def col(k, f="click_to_view_back_s"):
        v = [rd[k][f] for rd in out["rounds"]]
        return {"min": min(v), "median": sorted(v)[len(v) // 2], "all": v}
    out["summary"] = {"control_undo": col("control_undo"), "control_redo": col("control_redo"),
                      "rapid_from_undo_click": col("rapid_undo_redo"),
                      "rapid_from_redo_click": col("rapid_undo_redo", "redo_click_to_view_back_s"),
                      "edit_view_back": col("edit_click"), "edit_card_soup": col("edit_click", "click_to_card_soup_s"),
                      "edit_card_usable": col("edit_click", "card_usable_s"), "cancel_edit": col("cancel_edit")}
    print(out["summary"])
    doc._view3d.view.release_gl()
    p = OUT / "critic_chain_reload.json"
    import json
    p.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("wrote", p)


if __name__ == "__main__":
    main()
