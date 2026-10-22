"""THE GUTTER CENSUS: does stock ever paint a tri from the Moguri atlas's pure-white gutter texels?

The round-21 plug sampled a 1-texel white gutter line (v 0.200-0.202) and `_atlas_gate_mountain` could not see it (it
flags only transparent AND dark texels). Before the gate refuses white, this measures stock: every disc-1 Terrain tri
(and Object tri) sampled exactly as the gate samples a new tri (66 barycentric points, bilinear, at the gate's own
v-flip), counting the samples whose RGB all reach WHITE. Per topograph: tris with any white sample, and the worst
count. Control: the round-21 lab variant A's plug tris (block (21,1) tris 571/572) must show white samples, or the
instrument cannot see the defect.
RUN:  py studies/terrain-malleability/snowmassif/gutter_census.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit import config  # noqa: E402
from ff9mapkit.world import extract as X, mesh as M  # noqa: E402
from PIL import Image  # noqa: E402

WHITE = 250
GP = Path(config.find_game_path(None))
MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / "textures" / "res(1_24)_terrain.png"
ATL = np.asarray(Image.open(MOG).convert("RGBA")).astype(float)
AH, AW = ATL.shape[:2]
W = np.array([(i / 10.0, j / 10.0, 1 - i / 10.0 - j / 10.0) for i in range(11) for j in range(11 - i)])


def samples(uv3):
    """The gate's 66 bilinear samples of one tri's UVs -> (n, 4) RGBA."""
    u = W @ uv3[:, 0]
    v = W @ uv3[:, 1]
    fx = (u % 1.0) * AW - 0.5
    fy = (1.0 - v % 1.0) * AH - 0.5
    x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - x0, fy - y0
    out = np.zeros((len(u), 4))
    for dx, dy, wg in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)), (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        px = np.clip(x0 + dx, 0, AW - 1)
        py = np.clip(y0 + dy, 0, AH - 1)
        out += ATL[py, px] * wg[:, None]
    return out


def white_count(uv3) -> int:
    s = samples(uv3)
    return int(((s[:, :3] >= WHITE).all(1)).sum())


def main():
    per_topo = defaultdict(lambda: [0, 0, 0])          # tris, tris with white, worst count
    examples = defaultdict(list)
    for bx in range(24):
        for by in range(20):
            for part in ("terrain", "object"):
                try:
                    bm = X.read_block(bx, by, disc=1, part=part) if part != "terrain" else X.read_block(bx, by, disc=1)
                except Exception:                                          # noqa: BLE001
                    continue
                U = np.asarray(bm.uvs, float)
                Tn = bm.tangents
                fi = bm.flat_index
                for t in range(len(fi) // 3):
                    ids = fi[3 * t:3 * t + 3]
                    topo = X.decode_id(int(round(Tn[ids[0]][0])))["topograph"]
                    key = f"{part}:{topo}"
                    n = white_count(U[ids])
                    rec = per_topo[key]
                    rec[0] += 1
                    if n:
                        rec[1] += 1
                        rec[2] = max(rec[2], n)
                        if len(examples[key]) < 3:
                            examples[key].append({"block": [bx, by], "tri": t, "white": n,
                                                  "uv": np.round(U[ids], 4).tolist()})
    # the control: the round-21 lab plug
    ctl = None
    lab = HERE / "out" / "lab" / "A" / "FF9CustomMap-lab" / M.override_relpath(1, 21, 1)
    if lab.is_file():
        d = M.read_ff9mesh(lab)
        U = np.asarray(d["uvs"], float)
        idx = np.asarray(d["indices"]).reshape(-1, 3)
        ctl = {t: white_count(U[idx[t]]) for t in (571, 572) if t < len(idx)}
    out = {"white": WHITE, "per_topo": {k: {"tris": v[0], "with_white": v[1], "worst": v[2]}
                                         for k, v in sorted(per_topo.items())},
           "examples": examples, "control_lab_plug": ctl}
    for k, v in out["per_topo"].items():
        if v["with_white"]:
            print(f"{k:12s} {v['tris']:6d} tris, {v['with_white']:5d} with white samples, worst {v['worst']}/66")
    print("stock tris total", sum(v["tris"] for v in out["per_topo"].values()),
          "with any white", sum(v["with_white"] for v in out["per_topo"].values()))
    print("control (lab A plug tris 571/572):", ctl)
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "gutter_census.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
