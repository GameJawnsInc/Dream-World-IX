"""The playtest-9 game-cam vantage, reproduced + id-buffer query. READ-ONLY.

  py probe_cove_cam.py render            -> cove_cam render + ids .npy
  py probe_cove_cam.py query x0 x1 y0 y1 -> owner faces of a pixel box
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_gate as RG                                    # noqa: E402

# the playtest-9 shot: Zidane on the north lawn, game cam NW of him, shallow
# pitch (~28 deg), looking SE into the inlet; far wall frontal across water.
VIEW = dict(kind="persp", eye=(371.0, 10.0, -501.0), at=(381.5, 1.0, -514.0),
            fov=50.0, reach=60.0)
IDS = RG.OUTD / "cove_cam_ids.npy"


def render():
    batches = RG.load_batches({})
    img, ids = RG.raster(VIEW, batches, "cove_cam", want_ids=True)
    np.save(IDS, ids)
    print(f"saved ids -> {IDS.name}")


def query(x0, x1, y0, y1):
    batches = RG.load_batches({})
    ids = np.load(IDS)
    sub = ids[y0:y1 + 1, x0:x1 + 1]
    own = Counter(sub[sub >= 0].tolist())
    print(f"box x[{x0},{x1}] y[{y0},{y1}]: {len(own)} owner tris")
    for oid, cnt in own.most_common(20):
        bi, ti = oid >> 20, oid & ((1 << 20) - 1)
        part, verts, uvs, tris = batches[bi]
        t = tris[ti]
        cx = (verts[t[0]] + verts[t[1]] + verts[t[2]]) / 3.0
        n = np.cross(verts[t[1]] - verts[t[0]], verts[t[2]] - verts[t[0]])
        ny = n[1] / (np.linalg.norm(n) + 1e-12)
        u3 = [f"({uvs[i][0]:.4f},{uvs[i][1]:.4f})" for i in t]
        print(f"   {cnt:5d}px {part:8s} b{bi}#t{ti} "
              f"@({cx[0]:7.2f},{cx[1]:6.2f},{cx[2]:8.2f}) ny={ny:+.2f}")
        print(f"          uv {' '.join(u3)}")
        for i in t:
            v = verts[i]
            print(f"          v ({v[0]:8.3f},{v[1]:7.3f},{v[2]:9.3f})")


if __name__ == "__main__":
    if sys.argv[1] == "render":
        render()
    else:
        query(*map(int, sys.argv[2:6]))
