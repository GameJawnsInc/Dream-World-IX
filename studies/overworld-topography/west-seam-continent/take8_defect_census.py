"""Take 8's three owner-named defects, localized to TRIANGLES and to who authored them (read-only).

Owner verdict on the harness frames (rimwalk_take8, 2026-10-06): (1) THE SLIVER -- a thin dark spike
running west along the lawn from the wall foot ("should be ground"); (2) a grass-to-mountain
TRANSITION TILE at the base, slight, in frames 09/10/12; (3) a "triangular" GRASS WEDGE on the far
side. Every tri in and around the SW window is classified:

  carried  -- donor geometry (uv triple matches a donor tri, or all 3 verts land on the fitted
              donor->site transform: profile_base_measure.classify)
  minted   -- everything take 8 (or an earlier take) authored: zip / foot / apron / contact tris
  tile     -- atlas (row, col) of the uv centroid (fringe_realign's constants); r6 c4-7 = the tufty
              grass-to-rock transition course
  topo     -- 49 rock, 0 grass

    py studies/overworld-topography/west-seam-continent/take8_defect_census.py
"""
import json
import math
import struct
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from envelope_profile import SITE_BLOCKS, WM                         # noqa: E402
from profile_base_measure import (classify, donor_data, fit_transform,   # noqa: E402
                                  uvkey)
from fringe_realign import TU, TV, PU, PV                            # noqa: E402

ROI = (1400.0, -500.0, 1452.0, -452.0)          # the SW window + a margin round it
LAWN = 3.2
OUT = HERE / "take8_defect_census.json"


def load():
    rows = []
    for bx, by in SITE_BLOCKS:
        p = WM / "Disc1" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if not p.is_file():
            continue
        d = p.read_bytes()
        _, vc, _, fl = struct.unpack_from("<iiii", d, 4)
        off = 20
        verts = [struct.unpack_from("<fff", d, off + i * 12) for i in range(vc)]
        off += vc * 12 + (vc * 12 if fl & 1 else 0)
        uvs = [struct.unpack_from("<ff", d, off + i * 8) for i in range(vc)]
        off += vc * 8
        topos = [(int(round(struct.unpack_from("<f", d, off + i * 16)[0])) >> 2) & 0x3F
                 for i in range(vc)]
        for t in range(vc // 3):
            i = t * 3
            ws = [(bx * 64 + verts[i + k][0], verts[i + k][1], verts[i + k][2] - by * 64)
                  for k in range(3)]
            rows.append({"block": [bx, by], "tri": t, "w": ws, "uv": uvs[i:i + 3], "topo": topos[i]})
    return rows


def geom(ws):
    a, b, c = ws
    e = [math.dist(a, b), math.dist(b, c), math.dist(c, a)]
    u = [b[k] - a[k] for k in range(3)]
    v = [c[k] - a[k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    area = 0.5 * math.sqrt(sum(x * x for x in n))
    ny = abs(n[1]) / (2 * area) if area > 1e-9 else 0.0
    plan = 0.5 * abs(u[0] * v[2] - u[2] * v[0])                   # area seen from above
    return {"edges": e, "area": area, "plan": plan, "ny": ny,
            "aspect": (max(e) ** 2 / area) if area > 1e-9 else float("inf"),
            "c": [sum(p[k] for p in ws) / 3 for k in range(3)],
            "ymin": min(p[1] for p in ws), "ymax": max(p[1] for p in ws)}


def tile(uv):
    uc = sum(u[0] for u in uv) / 3
    vc = sum(u[1] for u in uv) / 3
    return int((vc - PV) / TV), int((uc - PU) / TU)


def main():
    dn_tris, dn_keys = donor_data()
    rows = load()
    st = [(r["w"][0], r["w"][1], r["w"][2], r["topo"]) for r in rows]
    sk = [uvkey(r["uv"]) for r in rows]
    xf = fit_transform(st, sk, dn_tris, dn_keys)
    carried = classify(st, sk, dn_keys, dn_tris, xf)
    roi = []
    for r, c in zip(rows, carried):
        g = geom(r["w"])
        x, _, z = g["c"]
        if not (ROI[0] <= x <= ROI[2] and ROI[1] <= z <= ROI[3]):
            continue
        r.update(g, carried=c, tile=tile(r["uv"]))
        roi.append(r)
    print(f"ROI tris {len(roi)}: carried {sum(r['carried'] for r in roi)}, "
          f"minted {sum(not r['carried'] for r in roi)}")

    def show(r):
        return (f"  blk{tuple(r['block'])} t{r['tri']:4d} {'CARRIED' if r['carried'] else 'minted '} "
                f"topo {r['topo']:2d} tile r{r['tile'][0]}c{r['tile'][1]:<2d} "
                f"c=({r['c'][0]:7.2f},{r['c'][2]:7.2f}) y {r['ymin']:5.2f}..{r['ymax']:5.2f} "
                f"ny {r['ny']:.2f} aspect {r['aspect']:6.1f} longest {max(r['edges']):5.1f}")

    # (1) the sliver: thin, low tris -- near the lawn, long edge, small area
    sliver = sorted((r for r in roi if r["aspect"] > 12 and r["ymin"] < LAWN + 1.5
                     and max(r["edges"]) > 4.0), key=lambda r: -r["aspect"])
    print(f"\n(1) SLIVER candidates (aspect > 12, low, long): {len(sliver)}")
    for r in sliver[:15]:
        print(show(r))

    # (2) transition-tile tris on the window base: r6 c4-7, within 4u of the lawn
    trans = [r for r in roi if r["tile"][0] == 6 and 4 <= r["tile"][1] <= 7 and r["ymin"] < LAWN + 4.0]
    print(f"\n(2) TRANSITION tiles (r6 c4-7) within 4u of the lawn: {len(trans)} "
          f"(carried {sum(r['carried'] for r in trans)}, minted {sum(not r['carried'] for r in trans)})")
    for r in sorted(trans, key=lambda r: r["c"][0])[:30]:
        print(show(r))
    print("    tiles of the low course overall:",
          Counter(f"r{r['tile'][0]}c{r['tile'][1]}" for r in roi
                  if r["topo"] == 49 and r["ymin"] < LAWN + 2.0).most_common(10))

    # (3) the grass wedge: grass that is NOT lawn -- grass-topo or grass-tile tris lifted above it
    wedge = sorted((r for r in roi if r["topo"] == 0 and r["ymax"] > LAWN + 1.5),
                   key=lambda r: -r["ymax"])
    print(f"\n(3) WEDGE candidates (grass topo, top > lawn + 1.5): {len(wedge)} "
          f"(carried {sum(r['carried'] for r in wedge)}, minted {sum(not r['carried'] for r in wedge)})")
    for r in wedge[:25]:
        print(show(r))

    keep = lambda r: {k: r[k] for k in ("block", "tri", "carried", "topo", "tile", "c", "ymin", "ymax",   # noqa: E731
                                        "ny", "aspect", "area")}
    OUT.write_text(json.dumps({"sliver": [keep(r) for r in sliver], "transition": [keep(r) for r in trans],
                               "wedge": [keep(r) for r in wedge]}, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT.name}")


if __name__ == "__main__":
    main()
