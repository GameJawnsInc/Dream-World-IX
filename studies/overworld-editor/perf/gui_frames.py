"""gui lane, probe: a 3D frame's cost on the GUI thread -- free orbit, the game camera, the game camera with fog (C18),
shipped vs P4 (gui_proto_preview.GroundGrid as worldview3d.ground_y: the pose's four ground probes).

    py studies/overworld-editor/perf/gui_frames.py [rounds]

paintGL + glFinish timed in a subclass (the widget WA_DontShowOnScreen on the native platform), driven by
grabFramebuffer; each frame follows camera.orbit(3, 0), as a sideways drag does (the game camera then poses again).
Evidence: out/perf/gui/gui_frames.json.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402


def main():
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    app = C.native_app()
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import fog as FG
    from ff9mapkit.world import gamecam as G
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import render as R
    import gui_proto_preview as PP
    cells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    site = R.RenderSite(cells=cells, disc=1, game=C.GAME, stack=R.game_stack(C.GAME))
    packed, textures = V.load_scene(site)
    timing = {}
    Base = V.WorldView3D

    class TimedView(Base):
        def paintGL(self):                                            # noqa: N802
            t = time.perf_counter()
            Base.paintGL(self)
            self.context().functions().glFinish()
            timing["paint"] = time.perf_counter() - t

    view = TimedView()
    C.hide(view)
    view.resize(1280, 720)
    view.show()
    C.settle(app)
    view.set_scene(packed, textures)
    view.grabFramebuffer()
    spot = (1400.0, 0.0, -460.0)
    settings, table = G.Settings.from_game(C.GAME), G.transport_table(C.GAME)
    fog = FG.from_game(C.GAME, mist=True)
    orig_gy = V.ground_y
    gg = PP.GroundGrid(packed)
    out = {"res": list(view.device_res())}

    def run(label, cam, fog_on, n=8):
        view.set_camera(cam)
        view.fog = fog if fog_on else None
        ts = []
        for _ in range(rounds):
            for _k in range(n):
                cam.orbit(3.0, 0.0)
                timing.clear()
                view.grabFramebuffer()
                ts.append(timing["paint"])
        out[label] = C.stats(ts)
        print(f"{label:34s} min {min(ts) * 1e3:7.2f} ms  median {sorted(ts)[len(ts) // 2] * 1e3:7.2f} ms")

    for variant in ("shipped", "P4"):
        V.ground_y = orig_gy if variant == "shipped" else (lambda p, x, z: gg.ground_y(x, z))
        run(f"{variant}: orbit overview", V.OrbitCamera(), False)
        run(f"{variant}: orbit close", V.OrbitCamera(target=spot, dist=160.0), False)
        gc = lambda: V.GameCamera(spot, 0.0, settings=settings, table=table,              # noqa: E731
                                  ground=lambda gx, gz: V.ground_y(packed, gx, gz))
        run(f"{variant}: game camera, no fog", gc(), False)
        run(f"{variant}: game camera, fog", gc(), True)
    V.ground_y = orig_gy
    view.release_gl()
    C.dump("gui_frames.json", out)


if __name__ == "__main__":
    main()
