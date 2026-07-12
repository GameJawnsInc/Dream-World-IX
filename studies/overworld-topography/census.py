"""OVERWORLD INTERIOR TOPOGRAPHY CENSUS -- the regenerable study behind the
interior-topography knowledge base (memory: project-ff9-overworld-interior-topography).

Reads the user's OWN FF9 install (no game bytes ship with this study) and emits, into
--out (default ./out, gitignored):

  topo_census.json    part inventory, per-topograph geometry table, adjacency, true
                      colors, per-topo dominant UV tiles
  topo_map_true.png   the whole world on the 4u tile lattice, colored by each
                      topograph's REAL mean atlas color (reads like the painted map)
  relief_map.png      mean walkable height per 4u cell
  topo_legend.png     swatch + area/height/slope/foot per topograph
  probes.txt          terrace histogram, forest anatomy, river-part anatomy

Run from the repo root:  py studies/overworld-topography/census.py [--out DIR]
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import atlas as A                     # noqa: E402
from ff9mapkit.world import extract as X                   # noqa: E402

# the engine on-foot topograph set (w_movementCheckTopographID masks {0x0010667F, 0xD8FF3CFF})
FOOT = set(range(0, 8)) | {10, 11, 12, 13} | set(range(16, 24)) | {27, 28, 30, 31} \
     | set(range(32, 39)) | {41, 42, 45, 46, 52}
G = 4.0                                                    # the engine tile lattice
GW, GH = int(1536 / G), int(1280 / G)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent / "out"))
    ap.add_argument("--disc", type=int, default=1)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log = open(out / "probes.txt", "w", encoding="utf-8")

    def say(*a):
        print(*a, flush=True)
        print(*a, file=log)

    # ---- part inventory ------------------------------------------------------
    env = X._worldmap_env(args.disc)
    pat = re.compile(rf"worldmap/disc{args.disc}/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9]+)(?:\.asset)?$")
    parts = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            parts[(int(m.group(1)), int(m.group(2)))].add(m.group(3))
    part_freq = Counter(p for s in parts.values() for p in s)
    special = {p: sorted(xy for xy, s in parts.items() if p in s)
               for p in part_freq if p not in ("terrain", "object")
               and not p.startswith(("sea", "beach"))}
    say("PART FREQUENCY:", dict(sorted(part_freq.items())))
    for p, cells in special.items():
        say(f"  {p}: {cells}")

    # ---- per-block terrain sweep ---------------------------------------------
    blocks = X.list_blocks(disc=args.disc)
    say(f"{len(blocks)} terrain blocks")
    topo_grid = np.full((GH, GW), -1, dtype=np.int16)
    hgt_grid = np.full((GH, GW), np.nan, dtype=np.float32)
    prio = np.zeros((GH, GW), dtype=np.float32)
    stats = defaultdict(lambda: {"tris": 0, "area": 0.0, "hts": [], "slopes": [],
                                 "blocks": set(), "events": 0})
    tile_count = defaultdict(Counter)
    walk_hts, forest_edges, forest_relief = [], [], []

    for (bx, by) in blocks:
        bm = X.read_block(bx, by, disc=args.disc)
        v = np.asarray(bm.verts, dtype=np.float64)
        uv = bm.uvs
        tan = bm.tangents
        ox, oz = 64.0 * bx, -64.0 * by
        for tri in bm.tris:
            a, b, c = v[tri[0]], v[tri[1]], v[tri[2]]
            d = X.decode_id(int(tan[tri[0]][0]))
            topo = d["topograph"]
            n = np.cross(b - a, c - a)
            upness = n[1] / (np.linalg.norm(n) + 1e-12)
            plan = 0.5 * abs((b[0]-a[0])*(c[2]-a[2]) - (c[0]-a[0])*(b[2]-a[2]))
            cy = (a[1] + b[1] + c[1]) / 3
            s = stats[topo]
            s["tris"] += 1
            s["area"] += float(plan)
            s["hts"].append(float(cy))
            s["slopes"].append(float(np.degrees(np.arccos(np.clip(upness, -1, 1)))))
            s["blocks"].add((bx, by))
            s["events"] += 1 if d["event"] else 0
            tile_count[topo][tuple(sorted((round(uv[i][0], 3), round(uv[i][1], 3)) for i in tri))] += 1
            if topo in FOOT:
                walk_hts.append(float(cy))
            if topo in (36, 37):
                for p, q in ((a, b), (b, c), (c, a)):
                    forest_edges.append(float(np.linalg.norm(p - q)))
                forest_relief.append(float(max(a[1], b[1], c[1]) - min(a[1], b[1], c[1])))
            gx, gz = int((( a[0]+b[0]+c[0])/3 + ox) // G), int((-((a[2]+b[2]+c[2])/3 + oz)) // G)
            if 0 <= gx < GW and 0 <= gz < GH and plan > prio[gz, gx]:
                prio[gz, gx] = plan
                topo_grid[gz, gx] = topo
                hgt_grid[gz, gx] = cy

    # ---- per-topo table + true colors ------------------------------------------
    img = A.load_atlas("terrain")
    rows, true_col, top_tiles = [], {}, {}
    for topo in sorted(stats):
        s = stats[topo]
        h = np.array(s["hts"]); sl = np.array(s["slopes"])
        rows.append(dict(topo=topo, tris=s["tris"], area=round(s["area"]), blocks=len(s["blocks"]),
                         foot=("Y" if topo in FOOT else "-"), events=s["events"],
                         h_lo=round(float(np.percentile(h, 2)), 1), h_med=round(float(np.median(h)), 1),
                         h_hi=round(float(np.percentile(h, 98)), 1),
                         sl_med=round(float(np.median(sl))), sl_hi=round(float(np.percentile(sl, 95)))))
        tops = tile_count[topo].most_common(6)
        top_tiles[topo] = [{"uv": [list(p) for p in key], "n": n} for key, n in tops]
        acc, wsum = np.zeros(3), 0
        for key, n in tops:
            if A.tile_is_blank(img, key):
                continue
            region = A.crop_tile(img, key, pad=0).convert("RGB")
            if region.width * region.height >= 1:
                acc += np.array(ImageStat.Stat(region).mean[:3]) * n
                wsum += n
        true_col[topo] = tuple(int(x) for x in acc / wsum) if wsum else (255, 0, 255)
    say(f"{'topo':>4} {'tris':>6} {'area':>7} {'blk':>4} foot {'evt':>4} h2/med/98  sl med/95")
    for r in rows:
        say(f"{r['topo']:>4} {r['tris']:>6} {r['area']:>7} {r['blocks']:>4}   {r['foot']}  {r['events']:>4} "
            f"{r['h_lo']}/{r['h_med']}/{r['h_hi']}  {r['sl_med']}/{r['sl_hi']}")

    # ---- adjacency on the lattice ------------------------------------------------
    adj = Counter()
    for gz in range(GH):
        for gx in range(GW):
            t0 = topo_grid[gz, gx]
            if t0 < 0:
                continue
            for dz, dx in ((0, 1), (1, 0)):
                if gz + dz < GH and gx + dx < GW:
                    t1 = topo_grid[gz + dz, gx + dx]
                    if t1 >= 0 and t1 != t0:
                        adj[tuple(sorted((int(t0), int(t1))))] += 1

    # ---- probes --------------------------------------------------------------------
    h = np.array(walk_hts)
    hist, edges = np.histogram(h, bins=np.arange(-4, 40, 1.0))
    say("\nWALKABLE-LAND HEIGHT HISTOGRAM (1u bins):")
    for i, n in enumerate(hist):
        if n > hist.max() * 0.01:
            say(f"  {edges[i]:>5.0f}..{edges[i+1]:<3.0f} {'#' * int(60 * n / hist.max())} {n}")
    fe, fr = np.array(forest_edges), np.array(forest_relief)
    if len(fe):
        say(f"\nFOREST (36/37): edge med {np.median(fe):.2f} p90 {np.percentile(fe, 90):.2f}; "
            f"tri relief med {np.median(fr):.2f} p90 {np.percentile(fr, 90):.2f}")

    # ---- renders --------------------------------------------------------------------
    sea = (24, 48, 100)
    imgm = np.zeros((GH, GW, 3), dtype=np.uint8)
    imgm[...] = sea
    for topo in np.unique(topo_grid):
        if topo >= 0:
            imgm[topo_grid == topo] = true_col.get(int(topo), (255, 0, 255))
    Image.fromarray(imgm).resize((GW * 2, GH * 2), Image.NEAREST).save(out / "topo_map_true.png")

    hh = np.nan_to_num(hgt_grid, nan=-8.0)
    hn = np.clip((hh + 8) / 48.0, 0, 1)
    rel = np.zeros((GH, GW, 3), dtype=np.uint8)
    rel[..., 0] = rel[..., 1] = (hn * 255).astype(np.uint8)
    rel[..., 2] = ((1 - hn) * 120 + hn * 255).astype(np.uint8)
    rel[np.isnan(hgt_grid)] = (10, 10, 30)
    Image.fromarray(rel).resize((GW * 2, GH * 2), Image.NEAREST).save(out / "relief_map.png")

    rows_by_area = sorted(rows, key=lambda r: -r["area"])
    leg = Image.new("RGB", (520, 18 * len(rows_by_area) + 8), (25, 25, 25))
    dr = ImageDraw.Draw(leg)
    for i, r in enumerate(rows_by_area):
        y = 4 + 18 * i
        dr.rectangle([6, y, 40, y + 14], fill=true_col.get(r["topo"], (255, 0, 255)))
        dr.text((48, y + 2), f"topo {r['topo']:>2}  area {r['area']:>6}  h {r['h_lo']}..{r['h_hi']}"
                             f"  slope {r['sl_med']}  foot {r['foot']}", fill=(230, 230, 230))
    leg.save(out / "topo_legend.png")

    json.dump({"part_freq": dict(part_freq),
               "special_parts": {p: [list(c) for c in v] for p, v in special.items()},
               "topo_table": rows,
               "adjacency": {f"{a}|{b}": n for (a, b), n in adj.most_common()},
               "true_colors": {str(k): list(v) for k, v in true_col.items()},
               "top_tiles": {str(k): v for k, v in top_tiles.items()}},
              open(out / "topo_census.json", "w"), indent=1)
    say(f"\nartifacts -> {out}")
    log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
