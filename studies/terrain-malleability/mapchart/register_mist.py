"""THE MIST CHART'S FRAME (2026-10-12): where the disc-1 Mist map draws the world.

`world_map_full_mistcontinent.png` (shown below scenario 5990) is not a crop of the all-world chart: it is a separately
painted close-up of the Mist continent, so `navimap.MIST_MAP_ART_FRAME` is registered here the way the all-world frame
was (2026-07-12): every stock disc-1 land triangle (terrain, beach1, object) rasterized at 1 px/u, rescaled by
(sx, sy), and correlated (FFT) against the chart's land pixels; each scale's best offset is scored by Dice over the
painted art (frame and corner emblem excluded). A uniform-aspect sweep first, then x and y apart round its best.
Result (Moguri's 1273x1080 chart): sx 1.300, sy 1.308, world (0, 0) at (-778, -586), Dice 0.934 (0.909 with the first
run's cruder land mask, sy 1.3075 on its finer grid: the kit's frame), the optimum interior to both sweeps. Reads the active Mist chart (the stacked mod folders, else the stock texture); writes nothing.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/mapchart/register_mist.py
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))


def main():
    import numpy as np
    from PIL import Image, ImageDraw
    import ff9mapkit
    assert Path(ff9mapkit.__file__).resolve().is_relative_to(KIT.resolve()), ff9mapkit.__file__
    from ff9mapkit.world import discmirror as DM, maperase as ME, navimap as NM, transplant as T

    im, src = NM._load_active_world_map(None, sprite_rel=NM.MIST_SPRITE_REL)
    print("chart:", src, im.size)
    A = np.asarray(im, float)
    H, W = A.shape[:2]
    inside = NM._chart_inside(im, (NM.MIST_EMBLEM,))
    # the chart's LAND: well off the local parchment (a halo is ~25-40 off; land 40+)
    F0 = np.median(A[inside].reshape(-1, 3), axis=0)
    dist = np.sqrt(((A - F0) ** 2).sum(-1))
    feat = ME.blur(dist, 1) > 25
    for _ in range(2):
        F, _got = ME.fill_field(A, ~ME.dilate(feat, 3) & inside, (40, 120, 300))
        dist = np.sqrt(((A - F) ** 2).sum(-1))
        feat = ME.blur(dist, 1) > 15
    art = (ME.blur(dist, 1) > 40) & inside

    world = Image.new("L", (1536, 1280), 0)
    d = ImageDraw.Draw(world)
    for b, parts in DM._real_parts(1).items():
        for p in parts & {"terrain", "beach1", "object"}:
            for t in T.world_tris(b[0], b[1], p, disc=1):
                d.polygon([(v[0][0], -v[0][2]) for v in t], fill=255)

    hc, wc = H + int(1280 * 1.75) + 1, W + int(1536 * 1.75) + 1   # no circular wrap for any swept scale
    fa = np.fft.rfft2(art.astype(float), (hc, wc))

    def score(sx, sy):
        wa = (np.asarray(world.resize((int(round(1536 * sx)), int(round(1280 * sy))), Image.BILINEAR)) > 127)
        corr = np.fft.irfft2(fa * np.conj(np.fft.rfft2(wa.astype(float), (hc, wc))), (hc, wc))
        ay, ax = np.unravel_index(np.argmax(corr), corr.shape)
        ay, ax = (ay - hc if ay > hc // 2 else ay), (ax - wc if ax > wc // 2 else ax)
        placed = ME._crop(wa, -ay, H - ay, -ax, W - ax) & inside
        return 2 * (placed & art).sum() / (placed.sum() + art.sum()), int(ax), int(ay)

    k = NM.WORLD_MAP_ART_FRAME[3] * 1080 / 1280 / (NM.WORLD_MAP_ART_FRAME[2] * 1273 / 1536)   # the all-world aspect
    best = max((score(s, s * k) + (s, s * k)) for s in np.arange(1.10, 1.70, 0.01))
    print(f"uniform aspect: s {best[3]:.3f}  Dice {best[0]:.4f}")
    s0 = best[3]
    best = max((score(sx, sy) + (sx, sy)) for sx in np.arange(s0 - 0.01, s0 + 0.0201, 0.0025)
               for sy in np.arange(s0 * k - 0.04, s0 * k + 0.0101, 0.0025))
    dice, ax, ay, sx, sy = best
    print(f"x/y apart: sx {sx:.4f}  sy {sy:.4f}  world (0,0) at ({ax}, {ay})  Dice {dice:.4f}")
    print(f"frame = ({ax} / {W}, {ay} / {H}, {sx:.4f} * 1536 / {W}, {sy:.4f} * 1280 / {H})")
    print("kit's MIST_MAP_ART_FRAME:", tuple(round(v, 5) for v in NM.MIST_MAP_ART_FRAME))


if __name__ == "__main__":
    main()
