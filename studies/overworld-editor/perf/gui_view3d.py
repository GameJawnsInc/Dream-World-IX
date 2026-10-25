"""gui lane, probe 3: what the World tab's 3D view costs -- the worker's map load, the GUI thread's GL upload, a frame.

    py studies/overworld-editor/perf/gui_view3d.py [runs]

The site is built as WorldDoc._render_site builds it in its default mode ("As the game loads it"): all 480 cells,
disc 1, the game's Memoria.ini FolderNames stack (read only). Legs, each timed by a pass-through wrapper (output
untouched):
  worker:  render.load_batches(site, stock=True) | seam_copies | pack | tex_for + texture_rgba   (load_scene)
  GUI:     WorldView3D.paintGL's first call after set_scene (the _GLScene.upload inside it, then the draw)
           a steady frame (no upload) -- free orbit overview, game camera, game camera + fog (C18)
           pick_at (a click: the first after a load builds Packed.pick_arrays), ground_y (the game camera's probe)
The first load in the process is COLD in-process (UnityPy env, extract's decode memo empty) -- the first 3D click of a
session; the later ones are the reload an Accept or an undo triggers.
Frame times: paintGL wall incl. glFinish (so the GPU's work lands in the number), driven by grabFramebuffer, the
widget WA_DontShowOnScreen on the native platform (never on the user's screen).
Evidence: out/perf/gui/gui_view3d.json, gui_view3d_load.pstats.
"""
from __future__ import annotations

import cProfile
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402


def site_stack():
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import render as R
    cells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    stack = R.game_stack(C.GAME)
    assert stack is not None
    return R.RenderSite(cells=cells, disc=1, game=C.GAME, stack=stack)


LEGS = {}


def _wrap(mod, name, key):
    orig = getattr(mod, name)

    def w(*a, **k):
        t = time.perf_counter()
        try:
            return orig(*a, **k)
        finally:
            LEGS[key] = LEGS.get(key, 0.0) + time.perf_counter() - t
    setattr(mod, name, w)
    return orig


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    app = C.native_app()
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import render as R
    site = site_stack()
    _wrap(R, "load_batches", "load_batches")
    _wrap(V, "seam_copies", "seam_copies")
    _wrap(V, "pack", "pack")
    _wrap(R, "tex_for", "tex_for")
    _wrap(V, "texture_rgba", "texture_rgba")
    out = {"site": {"cells": len(site.cells), "stack": [str(p) for p in site.stack]}, "loads": []}
    packed = textures = None
    for i in range(runs + 1):
        LEGS.clear()
        t = time.perf_counter()
        packed, textures = V.load_scene(site)
        total = time.perf_counter() - t
        rec = {"run": i, "cold_in_process": i == 0, "total_s": round(total, 4),
               **{k: round(v, 4) for k, v in LEGS.items()}}
        out["loads"].append(rec)
        print(rec)
    warm = [r["total_s"] for r in out["loads"][1:]]
    out["load_warm"] = C.stats(warm)
    out["packed"] = {"tris": packed.tris, "parts": len(packed.arrays), "draws": len(packed.draws),
                     "bytes": sum(a.nbytes for a in packed.arrays.values()),
                     "tex_bytes": sum(t.nbytes for t in textures.values() if t is not None)}
    print(out["packed"])
    # the shares of a warm load (cProfile inflates call-heavy code: shares, not totals)
    pr = cProfile.Profile()
    pr.enable()
    V.load_scene(site)
    pr.disable()
    pr.dump_stats(str(C.OUT / "gui_view3d_load.pstats"))

    # -------------------------------------------------------------- GL, on the GUI thread
    orig_upload = V._GLScene.upload
    timing = {}

    class TimedView(V.WorldView3D):
        """paintGL timed (+ glFinish). A SUBCLASS, defined before the instance: PySide caches a virtual's Python
        override per class, so patching WorldView3D.paintGL after the fact is never called (memory: Qt class-patch
        poison)."""

        def paintGL(self):                                            # noqa: N802
            t = time.perf_counter()
            V.WorldView3D.paintGL(self)
            self.context().functions().glFinish()
            timing["paint"] = time.perf_counter() - t

    view = TimedView()
    C.hide(view)
    view.resize(1280, 720)
    view.show()
    C.settle(app)

    def upload(self, *a, **k):
        t = time.perf_counter()
        r = orig_upload(self, *a, **k)
        timing["upload"] = time.perf_counter() - t
        return r

    V._GLScene.upload = upload
    gl = {"res": list(view.device_res()), "first_frames": [], "frames": {}}
    for i in range(runs):                                             # a fresh scene each time: the upload frame
        timing.clear()
        view.set_scene(packed, textures)
        view.grabFramebuffer()
        gl["first_frames"].append({"paint_s": round(timing.get("paint", -1), 4),
                                   "upload_s": round(timing.get("upload", -1), 4)})
    print("first frames", gl["first_frames"])

    def frames(label, n=8):
        ts = []
        for _ in range(n):
            timing.clear()
            view.camera.orbit(3.0, 0.0)
            view.grabFramebuffer()
            ts.append(timing["paint"])
        gl["frames"][label] = C.stats(ts)
        print(label, gl["frames"][label]["min_s"], gl["frames"][label]["median_s"])

    view.set_camera(V.OrbitCamera())                                  # the free view's default: the whole map
    frames("orbit_overview")
    view.set_camera(V.OrbitCamera(target=(1400.0, 0.0, -460.0), dist=160.0))
    frames("orbit_close")
    from ff9mapkit.world import fog as FG
    from ff9mapkit.world import gamecam as G
    settings = G.Settings.from_game(C.GAME)
    cam = V.GameCamera.from_orbit(view.camera, (1400.0, 0.0, -460.0), settings=settings,
                                  ground=lambda gx, gz: V.ground_y(packed, gx, gz), table=G.transport_table(C.GAME))
    view.set_camera(cam)
    view.fog = None
    frames("game_camera_no_fog")
    view.fog = FG.from_game(C.GAME, mist=True)
    frames("game_camera_fog")
    view.fog = None
    # grabFramebuffer's own overhead (the readback) is outside paint_s; the full grab wall for reference
    t = time.perf_counter()
    view.grabFramebuffer()
    gl["grab_wall_s"] = round(time.perf_counter() - t, 4)

    # -------------------------------------------------------------- a click and the game camera's probes
    view.set_camera(V.OrbitCamera(target=(1400.0, 0.0, -460.0), dist=160.0))
    pk = {}
    fresh = V.Packed(arrays=packed.arrays, draws=packed.draws, tris=packed.tris)   # pick_arrays not yet built
    view.packed = fresh
    t = time.perf_counter()
    hit = view.pick_at(640, 360)
    pk["first_pick_after_load_s"] = round(time.perf_counter() - t, 4)
    ts = []
    for k in range(5):
        t = time.perf_counter()
        view.pick_at(600 + 10 * k, 360)
        ts.append(time.perf_counter() - t)
    pk["pick"] = C.stats(ts)
    pk["hit"] = str(hit)
    fresh2 = V.Packed(arrays=packed.arrays, draws=packed.draws, tris=packed.tris)
    t = time.perf_counter()
    V.ground_y(fresh2, 1400.0, -460.0)
    pk["first_ground_y_after_load_s"] = round(time.perf_counter() - t, 4)
    ts = []
    for k in range(5):
        t = time.perf_counter()
        V.ground_y(fresh2, 1400.0 + k, -460.0)
        ts.append(time.perf_counter() - t)
    pk["ground_y"] = C.stats(ts)
    # GameCamera.view() (gamecam.pose with the ground probe) per camera change
    ts = []
    for k in range(5):
        cam.rotation += 7.0
        cam._memo = None
        t = time.perf_counter()
        cam.view()
        ts.append(time.perf_counter() - t)
    pk["gamecam_pose"] = C.stats(ts)
    print(pk)
    out["gl"], out["pick"] = gl, pk
    V._GLScene.upload = orig_upload
    view.release_gl()
    C.dump("gui_view3d.json", out)


if __name__ == "__main__":
    main()
