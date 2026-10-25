"""gui lane, probe 4: what a user's hand costs the GUI thread -- a ghost drag, a click, the chart's paint.

    py studies/overworld-editor/perf/gui_interact.py [moves] [base|proto] [tag]

The real cards (ForestTool at c1_lab's spot, MountainTool at c2_lab's), on a real WorldView3DPanel whose view holds
the whole map (load_scene of the game's stack, read only); every runner a FakeRunner (a Check never runs: the per-move
cost is the GUI thread's alone), the soups and outlines read inline (sync=True) ONCE before the timed moves.
Per mouse move during a ghost drag the GUI thread runs the card's drag_to (the shape, the ground under its rim, the
cheap laws, the overlays) and then the view repaints with the ghost (paintGL + glFinish, timed in a subclass).
Also: the coast card's click (place on a block whose windows are cached), the sink card's click, a 3D click's pick +
the World tab's _on_pick GUI part, the 2D chart's paint, the game camera's _seat_party (point_info ON THE GUI THREAD).
Evidence: out/perf/gui/gui_interact.json, gui_interact_<card>.pstats.
"""
from __future__ import annotations

import cProfile
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

DRAFTS = C.OUT / "drafts"
FOREST_SPOT, FOREST_DONOR = (1400.0, -460.0), "13,15"                 # c1_lab
MTN_SPOT, MTN_DONOR = (190.0, -1228.0), "0,0"                         # c2_lab


def main():
    moves = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    variant = sys.argv[2] if len(sys.argv) > 2 else "base"          # proto: P3 + P4 of gui_proto_preview patched in
    assert variant in ("base", "proto")
    app = C.native_app()
    from ff9mapkit.workspace import shell as S
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import render as R
    pal = S.pick_palette("dark")
    S._apply_app_theme(app, pal)
    timing = {}

    Base = V.WorldView3D

    class TimedView(Base):
        def paintGL(self):                                            # noqa: N802
            t = time.perf_counter()
            Base.paintGL(self)
            self.context().functions().glFinish()
            timing["paint"] = time.perf_counter() - t
    V.WorldView3D = TimedView                                         # the panel builds its view from this name

    cells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    site = R.RenderSite(cells=cells, disc=1, game=C.GAME, stack=R.game_stack(C.GAME))
    t = time.perf_counter()
    packed, textures = V.load_scene(site)
    out = {"load_scene_s": round(time.perf_counter() - t, 3), "moves": moves, "variant": variant}
    if variant == "proto":
        import gui_proto_preview as PP
        from ff9mapkit.world import forestedit as FE
        FE.footprint_preview = PP.footprint_preview_p3                # P3 (ForestTool._preview_at calls FE.<name>)
        gg = PP.GroundGrid(packed)
        orig_gy = V.ground_y
        V.ground_y = (lambda p, x, z: gg.ground_y(x, z) if p is not None and p.arrays is packed.arrays   # P4 (the
                      else orig_gy(p, x, z))                          # pick test below swaps in a fresh Packed of
        #                                                               the same arrays)
    panel = V.WorldView3DPanel(pal)
    C.hide(panel)
    panel.resize(1280, 760)
    panel.show()
    panel.site = site
    panel._finish(packed, textures, None)
    C.settle(app)
    view = panel.view
    view.grabFramebuffer()                                            # the upload frame, out of the way

    def frame():
        timing.clear()
        view.grabFramebuffer()
        return timing.get("paint", float("nan"))

    def drag(tool, spot, label):
        tool.open_tool()
        C.settle(app)
        tool.place(*spot, 3.0)
        C.settle(app)
        assert tool._ix is not None and tool.donor() in tool._outlines, (label, tool.verdict_lbl.text())
        view.set_camera(V.OrbitCamera(target=(spot[0], 0.0, spot[1]), dist=160.0))
        hand, paint = [], []
        pr = cProfile.Profile()
        for k in range(moves):
            x, z = spot[0] + 2.0 * (k + 1), spot[1] + 1.0 * (k + 1)
            t0 = time.perf_counter()
            pr.enable()
            tool.drag_to(x, z)
            pr.disable()
            hand.append(time.perf_counter() - t0)
            paint.append(frame())
        pr.dump_stats(str(C.OUT / f"gui_interact_{label}_{variant}.pstats"))
        # a drop (the drag's end): the same redraw + the check armed at once (the FakeRunner swallows it)
        t0 = time.perf_counter()
        tool.drop_at(spot[0], spot[1])
        drop = time.perf_counter() - t0
        rec = {"drag_to_gui": C.stats(hand), "paint_with_ghost_gui": C.stats(paint), "drop_at_gui_s": round(drop, 4),
               "overlay_tris": int(sum(len(o[0]) for o in view.overlays)) // 3, "preview": str(tool._preview)[:200],
               "verdict_text": tool.verdict_lbl.text()[:160]}
        # the parts of one move, each called as _redraw calls it
        parts = {}
        ts, _ = C.wall(tool.draft, 5)
        parts["draft()_read_meta"] = C.stats(ts)
        ts, _ = C.wall(tool.handles, 5)
        parts["handles()"] = C.stats(ts)
        ts, _ = C.wall(tool._sync_buttons, 5)
        parts["_sync_buttons"] = C.stats(ts)
        rec["parts"] = parts
        tool.close_tool()
        C.settle(app)
        print(label, {k: (v["min_s"], v["median_s"]) for k, v in rec.items() if isinstance(v, dict) and "min_s" in v},
              {k: v["min_s"] for k, v in parts.items()})
        return rec

    from ff9mapkit.workspace.worldforest import ForestTool
    from ff9mapkit.workspace.worldmountain import MountainTool
    kw = dict(game_fn=lambda: C.GAME, source_fn=lambda: C.SOURCE, drafts_root=DRAFTS, sync=True)
    forest = ForestTool(pal, panel, runner=C.FakeRunner(), **kw)
    forest.donor_box.setCurrentIndex(forest.donor_box.findData(FOREST_DONOR))
    out["forest"] = drag(forest, FOREST_SPOT, "forest")
    mtn = MountainTool(pal, panel, runner=C.FakeRunner(), **kw)
    mtn.donor_box.setCurrentIndex(mtn.donor_box.findData(MTN_DONOR))
    out["mountain"] = drag(mtn, MTN_SPOT, "mountain")

    # the coast card's click on a block whose windows are cached (2,7): place() runs CE.edited over the stack
    from ff9mapkit.workspace.worldcoast import CoastTool
    coast = CoastTool(pal, panel, runner=C.FakeRunner(), **kw)
    coast.open_tool()
    from ff9mapkit.workspace.worldscan import block_center
    cx, cz = block_center(2, 7)
    coast.place(cx, cz)                                               # first: reads the windows (cached JSON)
    C.settle(app)
    ts = []
    for k in range(5):
        t0 = time.perf_counter()
        coast.place(cx + k, cz)
        ts.append(time.perf_counter() - t0)
    ts_ed, _ = C.wall(lambda: coast._edited((2, 7)), 5)
    out["coast_click_gui"] = {**C.stats(ts), "edited()": C.stats(ts_ed), "verdict_text": coast.verdict_lbl.text()[:160]}
    coast.close_tool()
    print("coast click", out["coast_click_gui"]["min_s"], "edited", out["coast_click_gui"]["edited()"]["min_s"])

    # a 3D click: the view's pick (on the GUI thread) -- the first after a load builds the pick arrays
    view.set_camera(V.OrbitCamera(target=(FOREST_SPOT[0], 0.0, FOREST_SPOT[1]), dist=160.0))
    fresh = V.Packed(arrays=packed.arrays, draws=packed.draws, tris=packed.tris)
    view.packed = fresh
    t0 = time.perf_counter()
    view.pick_at(640, 380)
    first = time.perf_counter() - t0
    ts, _ = C.wall(lambda: view.pick_at(600, 380), 5)
    out["pick_at_gui"] = {**C.stats(ts), "first_after_load_s": round(first, 4)}

    # the game camera's _seat_party: point_info(site, x, z) on the GUI thread (a click with the game camera on, a
    # vehicle change, the height spin, every reload)
    from ff9mapkit.world import pointinfo as PI
    pts = [(FOREST_SPOT[0] + 9.0 * k, FOREST_SPOT[1] - 5.0 * k) for k in range(5)]
    ts = []
    for x, z in pts:
        t0 = time.perf_counter()
        PI.point_info(site, x, z, landmark=False)
        ts.append(time.perf_counter() - t0)
    far = []
    for x, z in [(300.0 + 61.0 * k, -300.0 - 47.0 * k) for k in range(3)]:  # other blocks: first read of each
        t0 = time.perf_counter()
        PI.point_info(site, x, z, landmark=False)
        far.append(time.perf_counter() - t0)
    panel.game_btn.setChecked(True)                                   # the real path: set_game_camera -> _seat_party
    C.settle(app)
    gframes = []
    for k in range(8):                                                # a sideways drag with the game camera: orbit
        view.camera.orbit(3.0, 0.0)                                   # turns it, the next paint poses it again
        gframes.append(frame())
    out["game_camera_orbit_frame_gui"] = C.stats(gframes)
    seat = []
    for x, z in pts:
        view.camera.player = (x, 0.0, z)
        t0 = time.perf_counter()
        panel._seat_party()
        seat.append(time.perf_counter() - t0)
    out["point_info_gui"] = {"same_block": C.stats(ts), "new_blocks": C.stats(far), "_seat_party": C.stats(seat)}
    panel.game_btn.setChecked(False)
    print("game cam frame", out["game_camera_orbit_frame_gui"]["min_s"], out["game_camera_orbit_frame_gui"]["median_s"])
    print("pick", out["pick_at_gui"]["min_s"], "point_info", out["point_info_gui"]["same_block"]["min_s"],
          out["point_info_gui"]["new_blocks"]["min_s"], "seat", out["point_info_gui"]["_seat_party"]["min_s"])

    # the 2D chart: a full paint of the atlas canvas (WorldDoc's chart, a real census)
    from ff9mapkit.workspace import worlddoc as WD
    from ff9mapkit.workspace import worldscan as WS
    canvas = WD.AtlasCanvas(pal)
    C.hide(canvas)
    canvas.resize(1100, 700)
    canvas.show()
    canvas.set_census(WS.scan_tree(C.SOURCE), WS.stock_context(C.GAME))
    C.settle(app)
    ts, _ = C.wall(lambda: canvas.viewport().grab(), 5)
    ts_sel, _ = C.wall(lambda: canvas.select((18, 17)), 5)
    out["chart_gui"] = {"paint(grab)": C.stats(ts), "select(redraw)": C.stats(ts_sel)}
    print("chart", {k: v["min_s"] for k, v in out["chart_gui"].items()})
    view.release_gl()
    tag = sys.argv[3] if len(sys.argv) > 3 else ""                    # a repeat run's own evidence file
    C.dump(f"gui_interact_{variant}{('_' + tag) if tag else ''}.json", out)


if __name__ == "__main__":
    main()
