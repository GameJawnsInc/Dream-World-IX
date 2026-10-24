"""Rung C18: the 3D view's own GPU path, with and without the game's fog, beside the game's frames.

    py studies/overworld-editor/c18_gpu_compare.py

C7's decoded camera for one still per spot, drawn by ``worldview3d.render_still`` (the shader the World tab's view
runs) on the real blocks, with no fog and with ``world.fog``'s Mist; composites game | no fog | fog to the gitignored
``out/`` (game frames never enter the repo), and each one's far-land colour error to the game's.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lab as C1                                                    # noqa: E402  (pins the worktree package)
import c7_compare as CC                                                # noqa: E402

GAME = C1.GAME
PICK = {("landing", 0), ("hill", 1), ("river", 1)}


def main():
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication(sys.argv[:1])                                 # noqa: F841 -- the GL platform
    from PIL import Image
    from ff9mapkit.world import fog as FG
    from ff9mapkit.world import gamecam as G
    from ff9mapkit.world import render as R
    from ff9mapkit.workspace import worldview3d as V
    cap = json.loads(CC.CAPTURE.read_text(encoding="utf-8"))
    cmp_rows = {(r["spot"], r["turn"]): r for r in json.loads(CC.COMPARE.read_text(encoding="utf-8"))["rows"]}
    S, table, stack = G.Settings.from_game(GAME), G.transport_table(GAME), R.game_stack(GAME)
    names = [p.name for p in stack]
    gsite = R.RenderSite(cells=(), disc=1, game=GAME, stack=stack)
    fog = FG.from_game(GAME)
    res = []
    for row in cap["rows"]:
        if (row["spot"], row["turn"]) not in PICK:
            continue
        gi = CC._load(row["shot"])
        H, W = gi.shape[:2]
        w, h = W // 2, H // 2
        gs = CC._small(gi, w, h)
        x, y, z = row["x"], row["y"], row["z"]
        bx, by = int(x // 64), int(-z // 64)
        cells = tuple((cx, cy) for cx in range(bx - 4, bx + 5) for cy in range(max(0, by - 4), min(20, by + 5)))
        site = R.RenderSite(cells=cells, disc=1, game=GAME, stack=stack, res=(w, h))
        batches = R.load_batches(site, stock=True)
        gq = C1._ground(gsite, x, z, names)
        best = cmp_rows.get((row["spot"], row["turn"]), {})
        v = G.pose((x, y, z), row["cam_rot"], settings=S, area=int(gq.get("area", 14) or 0),
                   upper_counter=row["cam_upper"] or 0,
                   ground=lambda px, pz: C1._ground(gsite, px % 1536.0, pz, names).get("y"),
                   mode=int(row.get("ctl") or 0), table=table, topograph=gq.get("topograph"),
                   eye_dy=best.get("eye_dy", 0.0) or 0.0, aim_dy=best.get("aim_dy", 0.0) or 0.0)
        v["reach"] = 600.0
        plain = V.render_still(batches, v, res=(w, h), site=site).astype(np.float32)
        fogged = V.render_still(batches, v, res=(w, h), site=site, fog=fog).astype(np.float32)
        _img, dep = R.raster(v, batches, "c18", site=site, out_dir=None, verbose=False, want_depth=True)
        far = np.isfinite(dep) & (dep > 25.0)
        far[: int(h * 0.12), int(w * 0.55):] = False                     # the co-op banner
        e0 = float(np.abs(plain[far] - gs[far]).mean())
        e1 = float(np.abs(fogged[far] - gs[far]).mean())
        name = f"{row['spot']}-{row['turn']}"
        Image.fromarray(np.concatenate([gs, plain, fogged], axis=1).clip(0, 255).astype(np.uint8)).save(
            HERE / "out" / f"c18-gpu-{name}.png")
        res.append({"still": name, "err_no_fog": e0, "err_fog": e1, "far_px": int(far.sum())})
        print(f"{name}: the view's far land against the game's, no fog {e0:.1f} -> with the fog {e1:.1f} "
              f"({int(far.sum())} px)")
    (HERE / "out" / "c18_gpu_compare.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
