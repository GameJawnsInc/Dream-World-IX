"""verify (gui skeptic): after a reload with the game camera ON, which scene does the game camera's eye probe?
WorldView3DPanel.set_game_camera builds GameCamera(ground=lambda gx, gz: ground_y(packed, gx, gz)) with
``packed = self.view.packed`` captured once; _finish on a reload calls set_scene + _seat_party but never rebinds it.
Two tiny synthetic scenes (one up-facing triangle each, at y=1 then y=9) on a real panel (native platform,
WA_DontShowOnScreen), no game data read except Settings/transport tables from the install (read only).

    py studies/overworld-editor/perf/verify_gui_stale_ground.py
Evidence: out/perf/gui/verify/verify_gui_stale_ground.json
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

C.OUT = C.OUT / "verify"


def scene(V, np, y):
    tri = np.array([[0, y, 0, 0, 0], [3000, y, 0, 1, 0], [0, y, -3000, 0, 1]], dtype=np.float32)
    # winding so the normal faces up (n[:, 1] > 0)
    v = tri[:, :3].astype(np.float64)
    if np.cross(v[1] - v[0], v[2] - v[0])[1] <= 0:
        tri = tri[[0, 2, 1]]
    return V.Packed(arrays={"Terrain": tri}, draws=[("Terrain", 0, 3)], tris=1)


def main():
    import numpy as np
    app = C.native_app()
    from ff9mapkit.workspace import shell as S
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import render as R
    pal = S.pick_palette("dark")
    panel = V.WorldView3DPanel(pal)
    C.hide(panel)
    panel.resize(800, 600)
    panel.show()
    panel.site = R.RenderSite(cells=((21, 7),), disc=1, game=C.GAME, stack=R.game_stack(C.GAME))
    a, b = scene(V, np, 1.0), scene(V, np, 9.0)
    panel._finish(a, {"Terrain": None}, None)
    C.settle(app)
    panel.view.focus(1400.0, -460.0)
    panel.set_game_camera(True)
    cam = panel.view.camera
    out = {"game_mode": panel.view.game_mode(), "probe_before_reload": cam.ground(1400.0, -460.0)}
    panel._finish(b, {"Terrain": None}, None)                         # a reload lands (an Accept, Undo, Rescan)
    C.settle(app)
    cam2 = panel.view.camera
    out.update({"same_camera_object": cam2 is cam, "view_packed_is_new": panel.view.packed is b,
                "camera_probe_after_reload": cam2.ground(1400.0, -460.0),
                "ground_y_of_drawn_scene": V.ground_y(panel.view.packed, 1400.0, -460.0),
                "party_y_seated_from_drawn_scene": cam2.player[1]})
    out["stale"] = out["camera_probe_after_reload"] != out["ground_y_of_drawn_scene"]
    print(out)
    panel.view.release_gl()
    C.dump("verify_gui_stale_ground.json", out)


if __name__ == "__main__":
    main()
