"""Water-feature census, disc 1: every block's parts, every water-like part measured, and the Terrain's water topographs.

Recon for a water-feature carry (a stock stream, falls, river or lake carried onto a kit island, as world-forest and
world-mountain carry canopy and rock). Reads the install's own worldmap bundles through the kit (no file written
outside out/).
  1. PART INVENTORY: every Disc1/0_1 block's sub-mesh names (from the bundle containers), counted map-wide.
  2. WATER PARTS: every part that is not Terrain / Object / Sea1-6 / Beach1-2 (Falls, River, RiverJoint, Stream,
     Volcano*, ...), per block: tris, plan extent, y range, the topographs its tangent.x IDALLs decode to, its UV span.
  3. TERRAIN WATER TOPOGRAPHS: per block, Terrain tris by topograph 48 and 51 (the two with a walk sink of 0.781,
     ingame/RESULTS.md's instrument lessons) and any other topograph that only occurs next to water parts.
  4. INLAND SEA: blocks whose Sea1-5 sits above y 0.5 or in a block with no Sea4 (candidate lakes), with extents.
RUN:  py studies/terrain-malleability/watercarry/census.py      (writes out/census.json, prints the tables)
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X  # noqa: E402

PLAIN = {"terrain", "object", "beach1", "beach2"} | {f"sea{i}" for i in range(1, 7)}


def inventory(disc=1, lod="0_1"):
    env = X._worldmap_env(disc, None)
    pat = re.compile(rf"worldmap/disc{disc}/{lod}/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
    parts = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            parts[(int(m.group(1)), int(m.group(2)))].add(m.group(3))
    return parts


def measure(bx, by, part):
    bm = X.read_block(bx, by, disc=1, part=part)
    V = np.asarray(bm.verts, dtype=float) + np.array([64.0 * bx, 0.0, -64.0 * by])
    tris = np.asarray(bm.tris, dtype=int)
    tan = bm.chan_arrays[X.CH_TAN]
    topo = Counter()
    for t in tris:
        try:
            topo[X.decode_id(int(round(tan[t[0]][0])))["topograph"]] += 1
        except Exception:                                                       # noqa: BLE001
            topo["?"] += 1
    uv = np.asarray(bm.chan_arrays[X.CH_UV], dtype=float)
    return {"tris": int(len(tris)), "verts": int(len(V)),
            "x": [round(float(V[:, 0].min()), 1), round(float(V[:, 0].max()), 1)],
            "z": [round(float(V[:, 2].min()), 1), round(float(V[:, 2].max()), 1)],
            "y": [round(float(V[:, 1].min()), 2), round(float(V[:, 1].max()), 2)],
            "topo": dict(topo.most_common(6)),
            "uv_u": [round(float(uv[:, 0].min()), 3), round(float(uv[:, 0].max()), 3)],
            "uv_v": [round(float(uv[:, 1].min()), 3), round(float(uv[:, 1].max()), 3)]}


def terrain_topos(bx, by):
    bm = X.read_block(bx, by, disc=1, part="terrain")
    tan = bm.chan_arrays[X.CH_TAN]
    c = Counter()
    for t in bm.tris:
        c[X.decode_id(int(round(tan[t[0]][0])))["topograph"]] += 1
    return c


def main():
    parts = inventory()
    count = Counter(p for ps in parts.values() for p in ps)
    print("PART INVENTORY (disc 1, blocks carrying each part):")
    for p, n in sorted(count.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {p:14s} {n}")
    out = {"inventory": {f"{x},{y}": sorted(ps) for (x, y), ps in sorted(parts.items())}, "water_parts": {},
           "terrain_water_topo": {}, "inland_sea": {}}
    print("\nWATER-LIKE PARTS (not Terrain/Object/Sea/Beach):")
    for (bx, by), ps in sorted(parts.items()):
        for p in sorted(ps - PLAIN):
            try:
                m = measure(bx, by, p)
            except Exception as e:                                              # noqa: BLE001
                m = {"error": f"{type(e).__name__}: {e}"[:160]}
            out["water_parts"][f"{bx},{by},{p}"] = m
            print(f"  ({bx:2d},{by:2d}) {p:12s} " + (m.get("error") or
                  f"{m['tris']:4d} tris  x{m['x']} z{m['z']} y{m['y']}  topo {m['topo']}  uv u{m['uv_u']} v{m['uv_v']}"))
    print("\nTERRAIN WATER TOPOGRAPHS (48, 51) per block:")
    tot = Counter()
    for (bx, by), ps in sorted(parts.items()):
        if "terrain" not in ps:
            continue
        c = terrain_topos(bx, by)
        tot.update(c)
        w = {k: c[k] for k in (48, 51) if c.get(k)}
        if w:
            out["terrain_water_topo"][f"{bx},{by}"] = {"water": w, "other_parts": sorted(ps - PLAIN)}
            print(f"  ({bx:2d},{by:2d}) {w}  parts beside: {sorted(ps - PLAIN) or '-'}")
    print(f"  map-wide Terrain tris: topo48 {tot.get(48, 0)}, topo51 {tot.get(51, 0)}")
    print("\nINLAND SEA candidates (a Sea1-5 above y 0.5, or sea parts in a block with no Sea4):")
    for (bx, by), ps in sorted(parts.items()):
        seas = sorted(p for p in ps if re.fullmatch(r"sea[1-5]", p))
        if not seas or "terrain" not in ps:
            continue
        hi = {}
        for s in seas:
            try:
                m = measure(bx, by, s)
            except Exception:                                                    # noqa: BLE001
                continue
            if m["y"][0] > 0.5 or "sea4" not in ps:
                hi[s] = m
        if hi:
            out["inland_sea"][f"{bx},{by}"] = hi
            print(f"  ({bx:2d},{by:2d}) " + "; ".join(f"{s} {m['tris']} tris y{m['y']} x{m['x']} z{m['z']}"
                                                      for s, m in hi.items()))
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "census.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {HERE / 'out' / 'census.json'}")


if __name__ == "__main__":
    main()
