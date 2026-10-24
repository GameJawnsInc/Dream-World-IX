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


def classes(img, *, sky_rgb=None) -> np.ndarray:
    """A surface class per pixel, by hue: 0 sky / fog (excluded), 1 water (blue), 2 grass (green), 3 sand / earth
    (warm), 4 rock (grey). The render draws the game's own textures, so the classes carry across the frames where a
    land mask cannot: c8's airship frames are nearly all land, and the land IoU scored a 7-degree view as a perfect
    fit (C8.md)."""
    rgb = img / 255.0
    mx, mn = rgb.max(axis=-1), rgb.min(axis=-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    d = np.maximum(mx - mn, 1e-6)
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60.0
    out = np.full(img.shape[:2], 4, dtype=np.int8)                      # grey: rock
    out[(sat > 0.18) & (hue >= 15) & (hue < 55)] = 3                   # warm: sand, earth
    out[(sat > 0.18) & (hue >= 55) & (hue < 160)] = 2                  # green: grass, canopy
    out[(sat > 0.18) & (hue >= 160) & (hue < 260)] = 1                 # blue: water
    sky = (mx > 0.72) & (sat < 0.25)                                   # the game's pale sky and fog
    if sky_rgb is not None:
        sky |= (np.abs(img - np.asarray(sky_rgb, dtype=np.float32)).max(axis=-1) < 2)
    out[sky] = 0
    return out


def agree(a, b, region) -> float:
    """The fraction of the region's pixels (sky in neither frame) whose surface class the two frames share."""
    m = region & (a > 0) & (b > 0)
    return float((a[m] == b[m]).mean()) if m.any() else 0.0


def edges(img) -> np.ndarray:
    """The frame's structure: the luminance gradient's magnitude, blurred, normalised. Colour and light do not reach
    it (WORLD07's dusk tints every surface orange in the game, which no class by hue survives: C8.md)."""
    from scipy.ndimage import gaussian_filter, sobel
    lum = img.astype(np.float64) @ np.array([0.299, 0.587, 0.114])
    lum = (lum - lum.mean()) / (lum.std() or 1.0)
    mag = np.hypot(sobel(lum, axis=0), sobel(lum, axis=1))
    return gaussian_filter(mag, 1.5)


def edge_score(a, b, region) -> float:
    """The Pearson correlation of two edge maps over the region (1 = every edge where the other frame has one)."""
    x, y = a[region], b[region]
    x, y = x - x.mean(), y - y.mean()
    d = math.sqrt(float((x * x).sum()) * float((y * y).sum()))
    return float((x * y).sum() / d) if d else 0.0


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


def main(capture=CAPTURE, compare=COMPARE, prefix="cmp"):
    """Compare each captured still. A row's ``ctl`` (the live travel mode) picks the vehicle's camera (c8: the
    vehicles); ``iou_foot`` scores the same still with the on-foot camera, the control that shows the vehicle's own
    decode is what matched."""
    from ff9mapkit.world import gamecam as G
    from ff9mapkit.world import render as R
    from PIL import Image
    rec = json.loads(Path(capture).read_text(encoding="utf-8"))
    rows = [r for r in rec.get("rows", []) if "error" not in r and r.get("shot")]
    S = G.Settings.from_game(GAME)
    table = G.transport_table(GAME)
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

        mode = int(row.get("ctl") or 0)
        topo = gq.get("topograph")

        def render(**kw):
            v = G.pose((x, y, z), kw.pop("rot", row["cam_rot"]), settings=S, area=area,
                       upper_counter=row["cam_upper"] or 0, ground=ground, mode=kw.pop("mode", mode), table=table,
                       topograph=topo, **{k: kw[k] for k in ("eye_dy", "aim_dy") if k in kw})
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
        foot = None
        if mode:                                               # the control: the same still, the on-foot camera
            _v, ri = render(mirror=mirror, mode=0)
            foot = iou(gl, masks(ri, sky_rgb=R.SKY)[1], region)
        v, ri = render(mirror=mirror, eye_dy=best[1], aim_dy=best[2])
        rl = masks(ri, sky_rgb=R.SKY)[1]
        over = np.zeros((h, w, 3), dtype=np.uint8)
        over[gl & region] = (255, 80, 80)
        over[rl & region] = (80, 160, 255)
        over[gl & rl & region] = (240, 240, 240)
        comp = np.concatenate([gs.astype(np.uint8), ri.astype(np.uint8), over], axis=1)
        name = f"{row['spot']}-{row['turn']}"
        Image.fromarray(comp).save(OUT / f"{prefix}-{name}.png")
        res = {"spot": row["spot"], "turn": row["turn"], "cam_rot": row["cam_rot"], "cam_upper": row["cam_upper"],
               "mode": mode, "type": v["game"]["type"], "type_cam": v["game"]["type_cam"], "topograph": topo,
               "iou_foot": None if foot is None else round(foot, 3),
               "area": area, "player": [x, y, z], "eye": [round(c, 3) for c in v["eye"]],
               "at": [round(c, 3) for c in v["at"]], "fov": round(v["fov"], 2), "lifted": v["game"]["lifted"],
               "iou_right": round(scores[False], 3), "iou_left": round(scores[True], 3), "mirror": mirror,
               "iou_band": round(best[0], 3), "eye_dy": best[1], "aim_dy": best[2],
               "iou_free": round(free[0], 3), "free_drot": free[1], "free_fov_k": free[2]}
        out["rows"].append(res)
        print(res)
    Path(compare).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"-> {compare}")


if __name__ == "__main__":
    main()
