"""THE ATLAS MAP (study angle 4) — the terrain atlas decoded from STOCK USAGE.

Registration: VSHORE-SEAL-PREDICTION.md "STUDY ANGLES" §4. The white-sliver /
tone-patch / band-poison defect class exists because uv assignment has no
validation target. This decodes the map the engine already obeys: scan every
stock disc-1 Terrain face, cluster the uv rectangles stock actually binds —
WALL bands by their v-pin pairs, GROUND fields by topo class — and annotate
each with atlas content (mean color, alpha-0 poison fraction). READ-ONLY.

Output: atlas_map.json (committed, queryable) + a printed table.
  py atlas_map.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_gate as RG                                    # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402

WALL_NY = 0.35                                              # |ny| <= this = wall class
GROUND_NY = 0.70


def face_ny(a, b, c):
    n = np.cross(np.asarray(b) - np.asarray(a), np.asarray(c) - np.asarray(a))
    L = np.linalg.norm(n)
    return float(n[1] / L) if L > 1e-12 else 0.0


def atlas_probe(tex, u0, u1, v0, v1):
    h, w = tex.shape[:2]
    r0, r1 = int((1.0 - v1) * h), max(int((1.0 - v1) * h) + 1, int((1.0 - v0) * h))
    c0, c1 = int(u0 * w), max(int(u0 * w) + 1, int(u1 * w))
    px = tex[max(r0, 0):r1, max(c0, 0):c1].astype(float)
    if px.size == 0:
        return (0, 0, 0), 1.0
    a0 = float((px[:, :, 3] == 0).mean())
    return tuple(round(float(px[:, :, i].mean()), 1) for i in range(3)), round(a0, 4)


def main():
    walls = defaultdict(lambda: dict(n=0, u_lo=1e9, u_hi=-1e9, topo=Counter(),
                                     blocks=set()))
    grounds = defaultdict(lambda: dict(n=0, us=[], vs=[], blocks=set()))
    blocks = X.list_blocks(disc=1)
    nb = 0
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except Exception:
            continue
        if bm is None:
            continue
        nb += 1
        pos = bm.chan_arrays[X.CH_POS]
        uv = bm.chan_arrays[X.CH_UV]
        tan = bm.chan_arrays[X.CH_TAN]
        for t in bm.tris:
            i0, i1, i2 = int(t[0]), int(t[1]), int(t[2])
            ny = face_ny(pos[i0], pos[i1], pos[i2])
            topo = (int(round(tan[i0][0])) & 0xFC) >> 2
            us = [float(uv[i][0]) for i in (i0, i1, i2)]
            vs = [float(uv[i][1]) for i in (i0, i1, i2)]
            if abs(ny) <= WALL_NY:
                key = (round(min(vs), 3), round(max(vs), 3))
                r = walls[key]
                r["n"] += 1
                r["u_lo"] = min(r["u_lo"], *us)
                r["u_hi"] = max(r["u_hi"], *us)
                r["topo"][topo] += 1
                r["blocks"].add((bx, by))
            elif abs(ny) >= GROUND_NY:
                r = grounds[topo]
                r["n"] += 1
                r["us"] += [min(us), max(us)]
                r["vs"] += [min(vs), max(vs)]
                r["blocks"].add((bx, by))
    print(f"scanned {nb} stock blocks")

    tex = RG.tex_for("Terrain")
    out = dict(wall_bands=[], ground_fields=[], meta=dict(
        source="stock disc-1 Terrain faces", blocks=nb,
        wall_ny=WALL_NY, ground_ny=GROUND_NY,
        note="v is Unity bottom-up 0..1; poison = alpha-0 fraction (renders WHITE)"))

    print(f"\n=== WALL BANDS (v-pin pairs, |ny|<={WALL_NY}) — top by face count ===")
    print(f"{'v range':22s} {'faces':>6s} {'blocks':>6s} {'u range':18s} "
          f"{'topo':12s} {'mean RGB':16s} {'poison':>7s}")
    for key, r in sorted(walls.items(), key=lambda kv: -kv[1]["n"]):
        if r["n"] < 12:
            continue
        rgb, a0 = atlas_probe(tex, r["u_lo"], r["u_hi"], key[0], key[1])
        row = dict(v_lo=key[0], v_hi=key[1], faces=r["n"], blocks=len(r["blocks"]),
                   u_lo=round(r["u_lo"], 4), u_hi=round(r["u_hi"], 4),
                   topo=dict(r["topo"].most_common(3)), rgb=rgb, alpha0=a0)
        out["wall_bands"].append(row)
        print(f"[{key[0]:.3f},{key[1]:.3f}]        {r['n']:6d} {len(r['blocks']):6d} "
              f"[{r['u_lo']:.3f},{r['u_hi']:.3f}]    "
              f"{str(dict(r['topo'].most_common(2))):12s} {str(rgb):16s} {a0:7.1%}")

    print(f"\n=== GROUND FIELDS (per topo, |ny|>={GROUND_NY}) ===")
    print(f"{'topo':>4s} {'faces':>7s} {'blocks':>6s} {'u p1-p99':20s} "
          f"{'v p1-p99':20s} {'mean RGB':16s} {'poison':>7s}")
    for topo, r in sorted(grounds.items(), key=lambda kv: -kv[1]["n"]):
        if r["n"] < 30:
            continue
        u1, u99 = np.percentile(r["us"], 1), np.percentile(r["us"], 99)
        v1, v99 = np.percentile(r["vs"], 1), np.percentile(r["vs"], 99)
        rgb, a0 = atlas_probe(tex, u1, u99, v1, v99)
        row = dict(topo=topo, faces=r["n"], blocks=len(r["blocks"]),
                   u_lo=round(float(u1), 4), u_hi=round(float(u99), 4),
                   v_lo=round(float(v1), 4), v_hi=round(float(v99), 4),
                   rgb=rgb, alpha0=a0)
        out["ground_fields"].append(row)
        print(f"{topo:4d} {r['n']:7d} {len(r['blocks']):6d} "
              f"[{u1:.3f},{u99:.3f}]      [{v1:.3f},{v99:.3f}]      "
              f"{str(rgb):16s} {a0:7.1%}")

    jp = HERE / "atlas_map.json"
    jp.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {jp.name}: {len(out['wall_bands'])} wall bands, "
          f"{len(out['ground_fields'])} ground fields")


if __name__ == "__main__":
    main()
