"""The owner's open observation on the live river (PLAN.md "The CLI verb"): the two shallow triangles at the river
mouth's beach corners "look a little weird". They lie inside the verbatim cove, so they should be home's own look.

This reads the LIVE deploy (FF9CustomMap-world, placement 512,128 = block offset (8,-2)) and HOME (cluster C in the
stock tree) round the mouth and compares them tri for tri, every part: positions (home translated by the
placement), UVs, normals, tangents, IDALLs. Then it names the tris at the mouth's beach corners, so the in-game
stills can be aimed at them.
RUN:  py studies/terrain-malleability/watercarry/mouth_compare.py   (-> out/mouth_compare.json)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X, mesh as M, river as R  # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LIVE = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
OFF_BLOCKS = (8, -2)                                    # the live placement, 512,128
WORLD_W = 64.0 * M.GRID_COLS if hasattr(M, "GRID_COLS") else 1536.0
RADIUS = 24.0                                           # round the mouth


def live_tris(cells):
    out = []
    for bx, by in cells:
        d = LIVE / f"r{by}"
        for part, name in R.PART_NAME.items():
            p = d / f"Block[{bx}][{by}] {name}.ff9mesh"
            if p.is_file():
                bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part=part)
                if bm.tris:
                    out += R.block_tris(bm, bx, by, part)
    return out


def to_live(P):
    Q = np.array(P, dtype=float)
    Q[:, 0] = (Q[:, 0] + 64.0 * OFF_BLOCKS[0]) % WORLD_W
    Q[:, 2] = Q[:, 2] - 64.0 * OFF_BLOCKS[1]
    return Q


def _wrapx(P):
    Q = np.array(P, dtype=float).copy()
    Q[:, 0] %= WORLD_W
    return Q


def key(part, P):
    Q = np.array(P, dtype=float).copy()
    Q[:, 0] %= WORLD_W
    return part, tuple(sorted(tuple(round(float(v), 3) for v in q) for q in Q))


def main():
    home = R.read_window(R.CLUSTER_C)
    rj = np.array([t["P"].mean(axis=0) for t in home if t["part"] == "riverjoint"])
    mouth = rj.mean(axis=0)
    near_h = [t for t in home if np.hypot(*(t["P"].mean(axis=0)[[0, 2]] - mouth[[0, 2]])) < RADIUS]
    cells = sorted({(int(M.wrap_block_col(t["blk"][0] + OFF_BLOCKS[0])), t["blk"][1] + OFF_BLOCKS[1]) for t in near_h})
    live = live_tris(cells)
    mouth_l = to_live([mouth])[0]
    near_l = [t for t in live if np.hypot(*((t["P"].mean(axis=0)[[0, 2]] - mouth_l[[0, 2]] + WORLD_W / 2) % WORLD_W
                                           - WORLD_W / 2)) < RADIUS]
    H = {key(t["part"], to_live(t["P"])): t for t in near_h}
    L = {key(t["part"], t["P"]): t for t in near_l}
    only_h = [k for k in H if k not in L]
    only_l = [k for k in L if k not in H]
    diffs = Counter()
    where = {}
    for k in set(H) & set(L):
        h, li = H[k], L[k]
        # vertex order may differ: match each live vertex to its home vertex by position
        oh = [int(np.argmin(np.abs(to_live(h["P"]) - p).sum(axis=1))) for p in _wrapx(li["P"])]
        for ch in ("uv", "nrm", "tan"):
            a, b = h[ch], li[ch]
            if a is None or b is None:
                if (a is None) != (b is None):
                    diffs[f"{k[0]}:{ch} presence"] += 1
                continue
            A, B = np.asarray(a)[oh], np.asarray(b)
            tags = []
            if ch == "tan":
                if not np.allclose(A[:, 0], B[:, 0], atol=1e-6):
                    ha, la = X.decode_id(int(round(A[0, 0]))), X.decode_id(int(round(B[0, 0])))
                    tags.append(f"{k[0]}:idall " + ",".join(f"{f} {ha[f]}->{la[f]}" for f in ha if ha[f] != la[f]))
                if not np.allclose(A[:, 1:], B[:, 1:], atol=1e-6):
                    tags.append(f"{k[0]}:tan yzw")
            elif not np.allclose(A, B, atol=1e-6):
                tags.append(f"{k[0]}:{ch}")
            for tag in tags:
                diffs[tag] += 1
                where.setdefault(tag, []).append([round(float(v), 2) for v in li["P"].mean(axis=0)])
    # the beach corners: shallow sea tris sharing an edge with both a beach1 tri and a river-part tri
    def edges(t):
        P = [tuple(round(float(v), 3) for v in p) for p in _wrapx(t["P"])]
        return {tuple(sorted((P[i], P[(i + 1) % 3]))) for i in range(3)}
    by_edge = {}
    for t in near_l:
        for e in edges(t):
            by_edge.setdefault(e, []).append(t)
    corners = []
    for t in near_l:
        if t["part"] not in R.SEA_PARTS:
            continue
        nb = {o["part"] for e in edges(t) for o in by_edge[e] if o is not t}
        if "beach1" in nb and nb & set(R.RIVER_PARTS):
            corners.append({"part": t["part"], "centre": [round(float(v), 3) for v in t["P"].mean(axis=0)],
                            "P": [[round(float(v), 3) for v in p] for p in t["P"]],
                            "uv": [[round(float(v), 4) for v in p] for p in t["uv"]], "idall": t["idall"],
                            "neighbours": sorted(nb)})
    rep = {"mouth_home": [round(float(v), 3) for v in mouth], "mouth_live": [round(float(v), 3) for v in mouth_l],
           "radius": RADIUS, "cells_live": cells,
           "tris": {"home": len(near_h), "live": len(near_l), "matched": len(set(H) & set(L)),
                    "only_home": len(only_h), "only_live": len(only_l)},
           "parts_home": dict(Counter(t["part"] for t in near_h)), "parts_live": dict(Counter(t["part"] for t in near_l)),
           "only_home": [(k[0], [list(v) for v in k[1]]) for k in only_h[:12]],
           "only_live": [(k[0], [list(v) for v in k[1]]) for k in only_l[:12]],
           "channel_diffs": dict(diffs), "diff_where": {k: v[:6] for k, v in where.items()},
           "beach_corner_sea_tris": corners}
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "mouth_compare.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("mouth_home", "mouth_live", "cells_live", "tris", "parts_home", "parts_live",
                                          "channel_diffs", "diff_where", "only_home", "only_live")}, indent=1))
    print(f"beach-corner sea tris: {len(corners)}")
    for c in corners:
        print("  ", c["part"], c["centre"], c["neighbours"], "uv", c["uv"])


if __name__ == "__main__":
    main()
