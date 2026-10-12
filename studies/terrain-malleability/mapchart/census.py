"""THE MAP ERASE, the census (2026-10-12): every stock island taken off each chart, one at a time.

For each chart (all-world, through `navimap.WORLD_MAP_ART_FRAME`; Mist, through `MIST_MAP_ART_FRAME`), every stock
disc-1 part is rasterized to the chart's per-pixel class (deep / shallow / land, as `maperase.class_rasters`). Every
LAND component of 15-7000 px that lies mostly inside the chart's frame is an island. Each island is removed in the
raster alone, its pixels taking the class of the ring round it (shallow if most of the ring is), and
`maperase.erase_removed` runs on a fresh copy of the chart. One row each: where, how big, the alignment found (shift,
overlap before/after), pixels repainted and as halo, or why it skipped. The before/after crop of each goes to
out/census_<chart>_<n>.png and the rows to out/census.json. Reads the stock charts (the highest folder below
FF9CustomMap-world's own composite: Moguri's HD charts here); writes nothing to the game.
The all-world chart's search starts at its measured drift (`navimap.WORLD_MAP_DRIFT`, fitted from this census run
with `--no-drift`); each chart prints the per-axis plane of the offsets found and what is left off the expected.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/mapchart/census.py [--no-drift] [--chart all|mist]
"""
import json
import sys
import time
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
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    soup = [(p, T.world_tris(b[0], b[1], p, disc=1)) for b, parts in DM._real_parts(1).items()
            for p in parts if p in ME.LAND_PARTS or p in ME.SHALLOW_PARTS]

    def raster(im, frame):
        x0, y0, x1, y1 = NM._world_art_rect(im, frame)
        w, h, ss = im.width, im.height, ME.SUPERSAMPLE
        land, shal = Image.new("L", (w * ss, h * ss)), Image.new("L", (w * ss, h * ss))
        dl, ds = ImageDraw.Draw(land), ImageDraw.Draw(shal)
        for p, tris in soup:
            d = dl if p in ME.LAND_PARTS else ds
            for t in tris:
                if ME._drawable(t):
                    d.polygon([((x0 + v[0][0] / 1536 * (x1 - x0)) * ss, (y0 - v[0][2] / 1280 * (y1 - y0)) * ss)
                               for v in t], fill=255)
        g = np.zeros((h, w), np.uint8)
        g[np.asarray(shal.resize((w, h), Image.BOX)) > 127] = ME.SHALLOW
        g[np.asarray(land.resize((w, h), Image.BOX)) > 127] = ME.LAND
        return g

    rows = {}
    nodrift = "--no-drift" in sys.argv          # the first run: how the drift was measured
    for chart, rel, frame, exclude, base, drift in (
            ("all", NM.MAP_SPRITE_REL, NM.WORLD_MAP_ART_FRAME, (), "FF9CustomMap-world", NM.WORLD_MAP_DRIFT),
            ("mist", NM.MIST_SPRITE_REL, NM.MIST_MAP_ART_FRAME, (NM.MIST_EMBLEM,), None, None)):
        if "--chart" in sys.argv and sys.argv[sys.argv.index("--chart") + 1] != chart:
            continue
        im, src = NM._load_active_world_map(base, sprite_rel=rel)
        drift = None if nodrift or drift is None else NM._drift(im, drift)
        stock = raster(im, frame)
        inside = NM._chart_inside(im, exclude)
        lab, n = ME.label(stock == ME.LAND)
        sizes = np.bincount(lab.ravel())
        islands = [i for i in range(1, n + 1) if 15 <= sizes[i] <= 7000 and inside[lab == i].mean() > 0.5]
        print(f"{chart}: {src}  {len(islands)} islands of {n} land components")
        rows[chart] = []
        for i in islands:
            comp = lab == i
            ring = ME.dilate(comp, 3) & ~comp
            to = ME.SHALLOW if (stock[ring] == ME.SHALLOW).mean() > 0.5 else ME.DEEP
            effective = stock.copy()
            effective[comp] = to
            A = np.asarray(im, float).copy()
            t = time.time()
            reps = ME.erase_removed(A, stock, effective, inside=inside, drift=drift)
            ys, xs = np.nonzero(comp)
            r = reps[0] if reps else {"skipped": "no site"}
            row = {"px": [int(xs.mean()), int(ys.mean())], "size": int(comp.sum()), "new_water": int(to),
                   **{k: v for k, v in r.items() if k != "window"}, "secs": round(time.time() - t, 1)}
            rows[chart].append(row)
            print(f"  {len(rows[chart]) - 1}: {row}")
            if reps:
                a = im.crop(r["window"])
                b = Image.fromarray(np.clip(np.rint(A), 0, 255).astype(np.uint8)).crop(r["window"])
                pair = Image.new("RGB", (a.width * 4 + 4, a.height * 2))
                pair.paste(a.resize((a.width * 2, a.height * 2), Image.NEAREST), (0, 0))
                pair.paste(b.resize((b.width * 2, b.height * 2), Image.NEAREST), (a.width * 2 + 4, 0))
                pair.save(out / f"census_{chart}_{len(rows[chart]) - 1:02d}.png")
        done = [r for r in rows[chart] if r.get("erased_px")]
        print(f"{chart}: {len(done)} erased, {len(rows[chart]) - len(done)} skipped")
        if len(done) > 3:                       # the drift: the found offsets as a plane in (x, y), and what is left
            P = np.array([(*r["px"], *r["shift"], *r.get("expected", (0, 0))) for r in done], float)
            M = np.c_[np.ones(len(P)), P[:, 0], P[:, 1]]
            for k, axis in ((2, "dx"), (3, "dy")):
                c = np.linalg.lstsq(M, P[:, k], rcond=None)[0]
                left = P[:, k] - P[:, k + 2]
                print(f"  {axis} = {c[0]:.2f} + {c[1]:.4f}*x + {c[2]:.4f}*y   (rms {np.sqrt((P[:, k] ** 2).mean()):.2f}; "
                      f"off the expected: rms {np.sqrt((left ** 2).mean()):.2f}, max {np.abs(left).max():.0f})")
    (out / "census.json").write_text(json.dumps(rows, indent=1, default=str))


if __name__ == "__main__":
    main()
