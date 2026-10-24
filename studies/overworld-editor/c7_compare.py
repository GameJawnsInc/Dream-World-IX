"""c7's compare: world.gamecam's pose for each captured still, drawn by render.raster, beside the game's own frame.

Run through ``c7_lab.py compare``. Writes composites (game | render | the land masks overlaid) and the scores to
``out/c7_lab/`` and ``out/c7_compare.json`` (both gitignored: game frames never enter the repo).

THE MASKS. render.py draws no fog, and the game's fog eats the land past ~45u (the FOG-FRAMING LAW), so the frames are
compared where both see the ground plainly: the lower part of the frame, the party's own sprite boxed out. A pixel is
WATER when blue leads it (the sea's own textures in both), LAND when it is neither water nor sky; the score is the
land masks' intersection over union. The search: the two chiralities (render.py's right vector is cross(fwd, up),
right-handed; Unity's LookAt frame is left-handed), the eye and aim heights inside the decode's settle bands, and,
apart, a free yaw / pitch / fov nudge, to name what the decode leaves.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lab as C1                                                    # noqa: E402

GAME = C1.GAME
OUT = HERE / "out" / "c7_lab"
CAPTURE = HERE / "out" / "c7_capture.json"
COMPARE = HERE / "out" / "c7_compare.json"
SCALE = 4                                                              # render at 1/SCALE of the still (speed)


def _load(path):
    from PIL import Image
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)


def _small(img, w, h):
    from PIL import Image
    return np.asarray(Image.fromarray(img.astype(np.uint8)).resize((w, h), Image.BILINEAR), dtype=np.float32)


def masks(img, *, sky_rgb=None):
    """``(water, land)`` boolean masks of an RGB frame."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    bright = img.mean(axis=-1)
    sat = img.max(axis=-1) - img.min(axis=-1)
    sky = (bright > 185) & (sat < 60)                                  # the game's pale sky and fog
    if sky_rgb is not None:
        sky |= (np.abs(img - np.asarray(sky_rgb, dtype=np.float32)).max(axis=-1) < 2)
    water = (b > r + 25) & (b > g + 4) & ~sky
    land = ~water & ~sky
    return water, land


def _region(h, w):
    """The compared region: the lower 60% of the frame, the party's sprite (centre) boxed out."""
    m = np.zeros((h, w), dtype=bool)
    m[int(h * 0.40):, :] = True
    cy, cx = int(h * 0.56), w // 2
    m[cy - int(h * 0.14):cy + int(h * 0.10), cx - int(w * 0.045):cx + int(w * 0.045)] = False
    return m


def iou(a, b, region):
    a, b = a & region, b & region
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 1.0


def main():
    from ff9mapkit.world import gamecam as G
    from ff9mapkit.world import render as R
    from PIL import Image
    rec = json.loads(CAPTURE.read_text(encoding="utf-8"))
    rows = [r for r in rec.get("rows", []) if "error" not in r and r.get("shot")]
    S = G.Settings.from_game(GAME)
    stack = R.game_stack(GAME)
    names = [p.name for p in stack]
    gsite = R.RenderSite(cells=(), disc=1, game=GAME, stack=stack)
    OUT.mkdir(parents=True, exist_ok=True)
    out = {"settings": S.__dict__, "rows": []}
    cache = {}
    for row in rows:
        game_img = _load(row["shot"])
        H, W = game_img.shape[:2]
        w, h = W // SCALE, H // SCALE
        gs = _small(game_img, w, h)
        x, y, z = row["x"], row["y"], row["z"]
        bx, by = int(x // 64), int(-z // 64)
        cells = tuple((cx, cy) for cx in range(bx - 3, bx + 4) for cy in range(max(0, by - 3), min(20, by + 4)))
        key = (bx, by)
        if key not in cache:
            site = R.RenderSite(cells=cells, disc=1, game=GAME, stack=stack, res=(w, h))
            cache[key] = (site, R.load_batches(site, stock=True))
        site, batches = cache[key]
        gq = C1._ground(gsite, x, z, names)
        area = int(gq.get("area", 14) or 0)

        def ground(px, pz):
            g = C1._ground(gsite, px % 1536.0, pz, names)
            return g.get("y") if g.get("y") is not None else None

        def render(**kw):
            v = G.pose((x, y, z), kw.pop("rot", row["cam_rot"]), settings=S, area=area,
                       upper_counter=row["cam_upper"] or 0, ground=ground, **{k: kw[k] for k in ("eye_dy", "aim_dy")
                                                                            if k in kw})
            v["fov"] *= kw.get("fov_k", 1.0)
            v["reach"] = 400.0
            img = R.raster(v, batches, "c7", site=site, out_dir=None, verbose=False).astype(np.float32)
            return v, (img[:, ::-1] if kw.get("mirror") else img)
        region = _region(h, w)
        _gw, gl = masks(gs)
        scores = {}
        for mirror in (False, True):
            v, ri = render(mirror=mirror)
            scores[mirror] = iou(gl, masks(ri, sky_rgb=R.SKY)[1], region)
        mirror = scores[True] > scores[False]
        best = (scores[mirror], 0.0, 0.0)
        for eye_dy in (-1.0, -0.5, 0.0, 0.5, 1.0):
            for aim_dy in (-0.5, 0.0, 0.5):
                _v, ri = render(mirror=mirror, eye_dy=eye_dy, aim_dy=aim_dy)
                s = iou(gl, masks(ri, sky_rgb=R.SKY)[1], region)
                if s > best[0]:
                    best = (s, eye_dy, aim_dy)
        free = (best[0], 0.0, 1.0)
        for drot in (-4.0, -2.0, 2.0, 4.0):
            for fk in (0.95, 1.0, 1.05):
                _v, ri = render(mirror=mirror, eye_dy=best[1], aim_dy=best[2], rot=row["cam_rot"] + drot, fov_k=fk)
                s = iou(gl, masks(ri, sky_rgb=R.SKY)[1], region)
                if s > free[0]:
                    free = (s, drot, fk)
        v, ri = render(mirror=mirror, eye_dy=best[1], aim_dy=best[2])
        rl = masks(ri, sky_rgb=R.SKY)[1]
        over = np.zeros((h, w, 3), dtype=np.uint8)
        over[gl & region] = (255, 80, 80)
        over[rl & region] = (80, 160, 255)
        over[gl & rl & region] = (240, 240, 240)
        comp = np.concatenate([gs.astype(np.uint8), ri.astype(np.uint8), over], axis=1)
        name = f"{row['spot']}-{row['turn']}"
        Image.fromarray(comp).save(OUT / f"cmp-{name}.png")
        res = {"spot": row["spot"], "turn": row["turn"], "cam_rot": row["cam_rot"], "cam_upper": row["cam_upper"],
               "area": area, "player": [x, y, z], "eye": [round(c, 3) for c in v["eye"]],
               "at": [round(c, 3) for c in v["at"]], "fov": round(v["fov"], 2), "lifted": v["game"]["lifted"],
               "iou_right": round(scores[False], 3), "iou_left": round(scores[True], 3), "mirror": mirror,
               "iou_band": round(best[0], 3), "eye_dy": best[1], "aim_dy": best[2],
               "iou_free": round(free[0], 3), "free_drot": free[1], "free_fov_k": free[2]}
        out["rows"].append(res)
        print(res)
    COMPARE.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"-> {COMPARE}")


if __name__ == "__main__":
    main()
