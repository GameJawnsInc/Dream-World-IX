"""THE TUCK DONOR — the bench's OWN wall cross-section, exactly. READ-ONLY.

Playtest 10 killed the carried stock overhang over cut sea (THE OVERHANG-
CONTEXT LAW). The replacement vocabulary is the island's own coast — the
construction the owner has approved everywhere else. This dumps it verbatim:
per wall COLUMN (the faces between two consecutive crest verts), the crest
edge, the foot edge, the plan offset of foot vs crest, lean ny, uv corners,
topo. Read from the BASELINE bytes (pre-corner), so the corner's own
deviation cannot contaminate the reference.

  py probe_bench_wall_xsec.py [near|far|all]
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402
from vcorner_crest import BASELINE_T                        # noqa: E402

JOINT_A = (372.482, -506.271)                               # the V-carry entry
JOINT_B = (376.274, -528.455)                               # the V-carry exit
FAR = [(375.1, -486.6), (448.5, -512.0), (448.0, -544.3)]


def baseline_tris():
    """Every baseline Terrain tri in world frame: (pts, uvs, topo, ny)."""
    out = []
    for (bx, by), p in BASELINE_T.items():
        d = W.M.read_ff9mesh(p)
        ox, oz = 64.0 * bx, -64.0 * by
        tan, uv, vs, idx = d["tangents"], d["uvs"], d["verts"], d["indices"]
        for t0 in range(0, len(idx), 3):
            t = idx[t0:t0 + 3]
            pts = [(vs[i][0] + ox, vs[i][1], vs[i][2] + oz) for i in t]
            topo = (int(round(tan[t[0]][0])) & 0xFC) >> 2
            a, b, c = (np.array(q) for q in pts)
            n = np.cross(b - a, c - a)
            L = float(np.linalg.norm(n))
            if L < 1e-12:
                continue
            out.append((pts, [tuple(uv[i][:2]) for i in t], topo,
                        float(n[1] / L), n / L, (bx, by), t0 // 3))
    return out


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "near"
    tris = baseline_tris()
    walls = [r for r in tris if r[2] == 58]
    print(f"baseline: {len(tris)} tris, {len(walls)} topo-58 wall faces\n")

    spots = ([("joint-A", *JOINT_A), ("joint-B", *JOINT_B)] if which != "far" else [])
    if which in ("far", "all"):
        spots += [(f"far{i}", x, z) for i, (x, z) in enumerate(FAR)]

    for (name, sx, sz) in spots:
        near = [r for r in walls
                if math.hypot(sum(p[0] for p in r[0]) / 3 - sx,
                              sum(p[2] for p in r[0]) / 3 - sz) < 4.5]
        print(f"=== {name} @({sx},{sz}): {len(near)} wall faces ===")
        if not near:
            continue
        # group into columns by shared crest edge (both crest verts at LAWN_Y)
        cols = defaultdict(list)
        for r in near:
            ys = [p[1] for p in r[0]]
            hi = [i for i in range(3) if ys[i] > max(ys) - 0.05]
            k = tuple(sorted((round(r[0][i][0], 2), round(r[0][i][2], 2))
                             for i in hi))
            cols[k].append(r)
        print(f"   {len(cols)} crest groups")
        for k, rs in sorted(cols.items())[:4]:
            ys = [p[1] for r in rs for p in r[0]]
            crest_y, foot_y = max(ys), min(ys)
            cps = [p for r in rs for p in r[0] if p[1] > crest_y - 0.05]
            fps = [p for r in rs for p in r[0] if p[1] < foot_y + 0.05]
            print(f"   -- crest {k}  y {crest_y:.2f} -> {foot_y:.2f}  "
                  f"{len(rs)} faces, ny {[round(r[3], 3) for r in rs]}")
            for p in sorted(set((round(q[0], 3), round(q[1], 3), round(q[2], 3))
                                for q in cps)):
                print(f"      crest v {p}")
            for p in sorted(set((round(q[0], 3), round(q[1], 3), round(q[2], 3))
                                for q in fps)):
                print(f"      foot  v {p}")
            # foot offset along the crest-edge normal, seaward positive
            if len(k) == 2 and cps and fps:
                (ax, az), (bx2, bz2) = k
                ed = np.array([bx2 - ax, bz2 - az])
                ed /= (np.linalg.norm(ed) or 1.0)
                perp = np.array([-ed[1], ed[0]])
                cm = np.mean([[p[0], p[2]] for p in cps], axis=0)
                fm = np.mean([[p[0], p[2]] for p in fps], axis=0)
                off = float((fm - cm) @ perp)
                print(f"      FOOT OFFSET along edge-normal: {off:+.3f}u "
                      f"(sign vs sea decided by ny {np.median([r[3] for r in rs]):+.2f})")
            for r in rs:
                print(f"      uv {[(round(u, 4), round(v, 4)) for (u, v) in r[1]]}")
        # aggregate
        nys = [r[3] for r in near]
        us = [u for r in near for (u, v) in r[1]]
        vs2 = [v for r in near for (u, v) in r[1]]
        print(f"   ny p10/p50/p90 {np.percentile(nys,10):+.3f}/"
              f"{np.percentile(nys,50):+.3f}/{np.percentile(nys,90):+.3f}   "
              f"u [{min(us):.4f},{max(us):.4f}]  v [{min(vs2):.4f},{max(vs2):.4f}]\n")


if __name__ == "__main__":
    main()
