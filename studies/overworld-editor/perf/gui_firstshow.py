"""gui lane, probe 2: the World tab's first show -- construction, the Scan, _finish, and the first "3D view" click.

    py studies/overworld-editor/perf/gui_firstshow.py [runs]

The real WorldDoc on the native platform (WA_DontShowOnScreen), the app theme applied as the shell applies it,
prefs pinned (gui_common), every runner a FakeRunner (no job can run, so nothing can write the install), and its
drafts root under out/perf/gui/drafts (a draft of FF9CustomMap-world made there once, so the recipe bar reads a
real draft.json / history). Legs and the THREAD each runs on:
  GUI     WorldDoc(...) construction; refresh()'s find_world_trees; _finish (canvas.set_census, the strip, cards,
          the recipe bar's refresh); the first 3D click's own call (lazy imports, RecipeBar, panel, _render_site);
          WorldView3DPanel._finish (the view built, set_scene); the recipe bar's refresh; CarryTool._sync_buttons'
          draft() (read_meta of draft.json) -- each called the way the tab calls it.
  worker  worldscan.scan_tree(folder); worldscan.stock_context(game) warm (the kit cache) and cold (an empty
          cache_root); the card's draft label read (edited_blocks + stale + last_promote).
Evidence: out/perf/gui/gui_firstshow.json.
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

DRAFTS = C.OUT / "drafts"


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    app = C.native_app()
    from ff9mapkit.workspace import shell as S
    from ff9mapkit.workspace import worlddoc as WD
    from ff9mapkit.workspace import worldscan as WS
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import draft as D
    pal = S.pick_palette("dark")
    S._apply_app_theme(app, pal)
    out = {}

    # the draft the recipe bar and the cards read (made once, under OUR out dir)
    t = time.perf_counter()
    d = D.ensure_draft(C.SOURCE, game=C.GAME, root=DRAFTS)
    out["ensure_draft_s"] = round(time.perf_counter() - t, 3)
    out["draft_json_bytes"] = (d / "draft.json").stat().st_size

    def make():
        fakes = {f"{k}_runner": C.FakeRunner() for k in ("forest", "mountain", "recipe", "sink", "coast", "island",
                                                          "transplant", "river", "hill")}
        doc = WD.WorldDoc(pal, game_path_fn=lambda: C.GAME, drafts_root=DRAFTS, **fakes)
        C.hide(doc)
        return doc

    ts, doc = C.wall(make, runs)
    out["construct"] = C.stats(ts)
    doc.resize(1280, 820)
    doc.show()
    C.settle(app)

    ts, trees = C.wall(lambda: WS.find_world_trees(C.GAME), runs)
    out["find_world_trees_gui"] = C.stats(ts)
    target = trees[0]
    assert target.name == "FF9CustomMap-world", target
    ts, census = C.wall(lambda: WS.scan_tree(target), runs + 1)
    out["scan_tree_worker"] = {**C.stats(ts[1:]), "first_s": round(ts[0], 4), "cells": len(census.cells),
                               "has_disc4": census.has_disc4}
    ts, stock = C.wall(lambda: WS.stock_context(C.GAME), runs)
    out["stock_context_warm_worker"] = C.stats(ts)
    cold = []
    for _ in range(runs):
        tmp = Path(tempfile.mkdtemp(prefix="gui_stock_"))
        t = time.perf_counter()
        g = WS.stock_context(C.GAME, cache_root=tmp)
        cold.append(time.perf_counter() - t)
        assert g == stock, "cold derive != cached grid"
    out["stock_context_cold_worker"] = {**C.stats(cold), "note": "run 0 is cold in-process (UnityPy env); later "
                                        "runs re-derive with the env warm"}
    print({k: out[k] for k in ("construct", "find_world_trees_gui", "scan_tree_worker", "stock_context_warm_worker",
                               "stock_context_cold_worker")})

    # the refresh's GUI-thread parts as refresh() runs them, then _finish (chart mode, no 3D page yet)
    doc._game = C.GAME
    doc._trees = trees
    doc.folder_box.clear()
    for tr in trees:
        doc.folder_box.addItem(tr.name, tr)
    sub = {}

    def finish():
        t0 = time.perf_counter()
        doc._finish(census, stock, None)
        return time.perf_counter() - t0

    orig_sc = doc.canvas.set_census

    def set_census(*a, **k):
        t0 = time.perf_counter()
        orig_sc(*a, **k)
        sub["set_census"] = sub.get("set_census", []) + [time.perf_counter() - t0]
    doc.canvas.set_census = set_census
    fin = [finish() for _ in range(runs)]
    out["finish_chart_gui"] = {**C.stats(fin), "set_census": C.stats(sub["set_census"])}
    C.settle(app)
    ts, _ = C.wall(lambda: doc.canvas.select((18, 17)), 5)
    out["canvas_select_gui"] = C.stats(ts)
    print("finish chart", out["finish_chart_gui"]["min_s"], "select", out["canvas_select_gui"]["min_s"])

    # the first "3D view" click: the GUI-thread call, then the worker load, then the panel's _finish
    pfin = []
    orig_pfinish = V.WorldView3DPanel._finish

    def pfinish(self, *a):
        t0 = time.perf_counter()
        orig_pfinish(self, *a)
        pfin.append(time.perf_counter() - t0)
    V.WorldView3DPanel._finish = pfinish                              # before the panel connects its signal
    # the first click's parts, each the way the click runs it (the imports are already paid by this probe's own
    # top-level import of worldview3d: their cost is gui_import.json's lazy_3d, the steady state with bytecode)
    from ff9mapkit.workspace import worldrecipe as WR
    parts = {}
    for name, fn in (("gl_available", V.gl_available),
                     ("RecipeBar()", lambda: WR.RecipeBar(pal, game_fn=lambda: C.GAME, source_fn=lambda: target,
                                                          runner=C.FakeRunner(), drafts_root=DRAFTS)),
                     ("WorldView3DPanel()", lambda: V.WorldView3DPanel(pal))):
        ts, _ = C.wall(fn, runs)
        parts[name] = C.stats(ts)
    out["first_3d_click_parts_gui"] = parts
    print("3D click parts", {k: v["min_s"] for k, v in parts.items()})
    t = time.perf_counter()
    doc.set_view_mode("3d")
    out["first_3d_click_gui_s"] = round(time.perf_counter() - t, 4)
    t = time.perf_counter()
    while doc._view3d.view is None and time.perf_counter() - t < 120:
        app.processEvents()
        time.sleep(0.002)
    out["first_3d_load_wall_s"] = round(time.perf_counter() - t, 3)
    out["panel_finish_gui_s"] = round(pfin[0], 4) if pfin else None
    # the first paint (the GL upload) once the view is up -- the panel's view is a stock WorldView3D, so time the
    # widget's own repaint (paintEvent -> paintGL -> compose); the per-leg GL split is gui_view3d.py's
    C.settle(app, 2)
    view = doc._view3d.view
    t = time.perf_counter()
    view.grabFramebuffer()
    out["first_paint_after_load_gui_s(grab)"] = round(time.perf_counter() - t, 4)
    print("3D click", out["first_3d_click_gui_s"], "load wall", out["first_3d_load_wall_s"], "panel finish",
          out["panel_finish_gui_s"], "first grab", out["first_paint_after_load_gui_s(grab)"])

    # with the 3D page up: the recipe bar's refresh, a card's draft read, _finish again (a Rescan)
    bar = doc._recipe
    ts, _ = C.wall(bar.refresh, 5)
    out["recipe_refresh_gui"] = C.stats(ts)
    ts, _ = C.wall(lambda: D.read_meta(d), 5)
    out["read_meta_gui"] = C.stats(ts)
    ts, _ = C.wall(lambda: D.history(d), 5)
    out["history_gui"] = C.stats(ts)
    ts, _ = C.wall(lambda: (D.edited_blocks(d), D.stale(d), D.last_promote(d)), runs)
    out["draft_label_worker"] = C.stats(ts)
    ts, _ = C.wall(doc._sync_draw_box, 5)
    out["sync_draw_box_gui"] = C.stats(ts)
    ts, _ = C.wall(doc._render_site, 5)
    out["render_site_gui"] = C.stats(ts)
    rescan = []
    for _ in range(runs):
        pfin.clear()
        t = time.perf_counter()
        doc._finish(census, stock, None)
        rescan.append(time.perf_counter() - t)
        t = time.perf_counter()
        while (doc._view3d._busy or not pfin) and time.perf_counter() - t < 120:
            app.processEvents()
            time.sleep(0.002)
        out.setdefault("rescan_3d_reload_wall_s", []).append(round(time.perf_counter() - t, 3))
        out.setdefault("rescan_panel_finish_gui_s", []).append(round(pfin[0], 4) if pfin else None)
    out["finish_3d_gui"] = C.stats(rescan)
    print({k: out[k] for k in ("recipe_refresh_gui", "read_meta_gui", "history_gui", "draft_label_worker",
                               "sync_draw_box_gui", "render_site_gui", "finish_3d_gui", "rescan_3d_reload_wall_s")})
    V.WorldView3DPanel._finish = orig_pfinish
    doc._view3d.view.release_gl()
    C.dump("gui_firstshow.json", out)


if __name__ == "__main__":
    main()
