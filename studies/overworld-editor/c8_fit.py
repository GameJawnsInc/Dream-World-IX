"""c8's fit: which camera parameter does the airship's decode get wrong? A coordinate search, per still, over the
eye's distance scale, eye height, aim height, field of view and yaw, starting from world.gamecam's pose; it prints the
fit's offsets from the decode. Offline (the stills are in the gitignored run archive)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lab as C1                                                    # noqa: E402
import c7_compare as CMP                                               # noqa: E402

GAME = C1.GAME
METRIC = "edges"                                                       # or "classes" (the colour classes)


def main(spots, capture="c8_capture.json", fit="c8_fit.json"):
    from ff9mapkit.world import gamecam as G
    from ff9mapkit.world import render as R
    rec = json.loads((HERE / "out" / capture).read_text(encoding="utf-8"))
    rows = [r for r in rec["rows"] if r.get("shot") and f"{r['spot']}-{r['turn']}" in spots]
    S, table = G.Settings.from_game(GAME), G.transport_table(GAME)
    stack = R.game_stack(GAME)
    names = [p.name for p in stack]
    gsite = R.RenderSite(cells=(), disc=1, game=GAME, stack=stack)
    out = {}
    for row in rows:
        img = CMP._load(row["shot"])
        H, W = img.shape[:2]
        w, h = W // CMP.SCALE, H // CMP.SCALE
        gs = CMP._small(img, w, h)
        x, y, z = row["x"], row["y"], row["z"]
        bx, by = int(x // 64), int(-z // 64)
        cells = tuple((cx, cy) for cx in range(bx - 3, bx + 4) for cy in range(max(0, by - 3), min(20, by + 4)))
        site = R.RenderSite(cells=cells, disc=1, game=GAME, stack=stack, res=(w, h))
        batches = R.load_batches(site, stock=True)
        gq = C1._ground(gsite, x, z, names)

        def ground(px, pz):
            return C1._ground(gsite, px % 1536.0, pz, names).get("y")
        base = G.pose((x, y, z), row["cam_rot"], settings=S, area=int(gq.get("area", 14) or 0), mode=row["ctl"],
                      table=table, topograph=gq.get("topograph"), ground=ground)
        region = CMP._region(h, w)
        gc = CMP.classes(gs) if METRIC == "classes" else CMP.edges(gs)

        def score(p):
            e = np.asarray(base["eye"], dtype=float)
            a = np.asarray(base["at"], dtype=float)
            d = e - a
            yaw = math.radians(p["drot"])
            dx, dz = d[0] * math.cos(yaw) + d[2] * math.sin(yaw), -d[0] * math.sin(yaw) + d[2] * math.cos(yaw)
            e2 = a + np.array([dx * p["k"], d[1] + p["eye"], dz * p["k"]])
            a2 = a + np.array([0.0, p["aim"], 0.0])
            v = {"kind": "persp", "eye": tuple(e2), "at": tuple(a2), "fov": p["fov"], "reach": 400.0}
            ri = R.raster(v, batches, "fit", site=site, out_dir=None, verbose=False).astype(np.float32)
            if METRIC == "classes":
                return CMP.agree(gc, CMP.classes(ri, sky_rgb=R.SKY), region)
            return CMP.edge_score(gc, CMP.edges(ri), region)
        p = {"k": 1.0, "eye": 0.0, "aim": 0.0, "fov": base["fov"], "drot": 0.0}
        best = score(p)
        steps = {"k": 0.1, "eye": 2.0, "aim": 2.0, "fov": 3.0, "drot": 3.0}
        for _round in range(4):
            for key in ("fov", "drot", "eye", "aim", "k"):
                for sgn in (+1, -1):
                    while True:
                        q = dict(p)
                        q[key] += sgn * steps[key]
                        s = score(q)
                        if s > best + 1e-4:
                            p, best = q, s
                        else:
                            break
            steps = {k: v / 2.0 for k, v in steps.items()}
        name = f"{row['spot']}-{row['turn']}"
        out[name] = {"decoded": {"fov": round(base["fov"], 2), "eye": [round(c, 2) for c in base["eye"]],
                                 "at": [round(c, 2) for c in base["at"]], "game": base["game"]},
                     "decoded_iou": round(score({"k": 1.0, "eye": 0.0, "aim": 0.0, "fov": base["fov"], "drot": 0.0}), 3),
                     "fit": {k: round(v, 3) for k, v in p.items()}, "fit_iou": round(best, 3)}
        print(name, json.dumps({k: out[name][k] for k in ("decoded_iou", "fit", "fit_iou")}))
    (HERE / "out" / fit).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--c7"]:                                          # the on-foot stills: the metric's own check
        main(args[1:] or ["landing-0", "hill-1", "river-1"], capture="c7_capture.json", fit="c7_fit.json")
    else:
        main(args or ["air-spawn-0", "air-climbed-0", "air-high-0", "air-ceiling-0", "boat-0", "choco-lawn-0",
                      "choco-forest-0"])
