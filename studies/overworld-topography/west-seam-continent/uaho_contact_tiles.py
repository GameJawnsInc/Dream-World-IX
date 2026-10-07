"""Does each live rock-grass contact wear stock's transition tile? -- the owner's screenshot-3 defect (read-only).

Owner, on the live Uaho look (R5 U5): "the cliff hits the grass with no transition tile" at (1456, -491); the
raised coastal-rock stretch at (1434, -482) "looks fine". Stock law (stock_fringe_census.py): 92% of disc-1
rock-grass contact tris wear the fringed r10 c6-9 tile.

For every live rock (topo 49) tri sharing an edge with a grass (topo 0) tri, in the massif blocks:
  - its atlas tile, course height, world centroid, nearest massif;
  - fringe = r10 c6-9;
  - HOME: the same tri found in the donor's stock block by its uv triple (the carry is verbatim), and the topo
    classes of its HOME edge neighbours (none = sea / no terrain; 58 = coast cliff).
Calibration: the same contact predicate over every stock disc-1 block must give stock's 92% (positive control).

    py -X utf8 studies/overworld-topography/west-seam-continent/uaho_contact_tiles.py [--stock]
"""
import json
import math
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                 # noqa: E402

TU, TV, PU, PV = 0.0625, 0.03125, 0.015625, 0.01953125
ROCK, GRASS = 49, 0
LIVE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap-world\FF9_Data"
            r"\WorldMap\Disc1\0_1")
BLOCKS = [(bx, by) for bx in (21, 22, 23) for by in (5, 6, 7, 8)]
MASSIFS = {"uaho": ((1442.0, -478.0), [(0, 0)]), "comp20": ((1486.0, -386.0), [(12, 16), (12, 17)])}
SHOT3 = (1456.0, -491.0)
OUT = HERE / "uaho_contact_tiles.json"


def tile(uvs):
    uc = sum(u for u, v in uvs) / 3
    vc = sum(v for u, v in uvs) / 3
    return int((vc - PV) / TV), int((uc - PU) / TU)


def is_fringe(t):
    return t[0] == 10 and 6 <= t[1] <= 9


def read_live(bx, by):
    p = LIVE / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
    if not p.is_file():
        return None
    d = p.read_bytes()
    _, vc, _, fl = struct.unpack_from("<iiii", d, 4)
    off = 20
    verts = [struct.unpack_from("<fff", d, off + i * 12) for i in range(vc)]
    off += vc * 12 + (vc * 12 if fl & 1 else 0)
    uvs = [struct.unpack_from("<ff", d, off + i * 8) for i in range(vc)]
    off += vc * 8
    topos = [(int(round(struct.unpack_from("<f", d, off + i * 16)[0])) >> 2) & 0x3F for i in range(vc)]
    tris = [(3 * t, 3 * t + 1, 3 * t + 2) for t in range(vc // 3)]
    return verts, uvs, topos, tris


def read_stock(bx, by):
    bm = X.read_block(bx, by, disc=1)
    topos = [((int(round(t[0])) >> 2) & 0x3F) for t in bm.tangents]
    return bm.verts, bm.uvs, topos, bm.tris


def contacts(mesh, bx, by):
    """Rock tris sharing an edge (by position) with a grass tri: [(tri, neighbour topo set)]."""
    verts, uvs, topos, tris = mesh
    edges = defaultdict(list)
    for ti, tri in enumerate(tris):
        for i, j in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            k = tuple(sorted((tuple(round(x, 3) for x in verts[i]), tuple(round(x, 3) for x in verts[j]))))
            edges[k].append(ti)
    nb = defaultdict(set)
    for tl in edges.values():
        for t in tl:
            nb[t].update(topos[tris[o][0]] for o in tl if o != t)
            if len(tl) == 1:
                nb[t].add(None)                    # an open edge: sea / no terrain on the other side
    return [(t, nb[t]) for t in range(len(tris)) if topos[tris[t][0]] == ROCK and GRASS in nb[t]], nb


def uvkey(uvs):
    return tuple(sorted((round(u, 5), round(v, 5)) for u, v in uvs))


def stock_calibration():
    n = fr = 0
    for bx in range(24):
        for by in range(20):
            try:
                mesh = read_stock(bx, by)
            except Exception:
                continue
            cs, _ = contacts(mesh, bx, by)
            for t, _nb in cs:
                n += 1
                fr += is_fringe(tile([mesh[1][i] for i in mesh[3][t]]))
    print(f"CALIBRATION (stock disc 1): {n} rock-grass contact tris, fringe r10 c6-9 {fr} "
          f"({100 * fr / max(1, n):.0f}%) -- stock_fringe_census.py read 1130 / 92%")


def main():
    if "--stock" in sys.argv:
        stock_calibration()
    homes = {}
    for name, (_c, dblocks) in MASSIFS.items():
        idx = {}
        for hb in dblocks:
            mesh = read_stock(*hb)
            _cs, nb = contacts(mesh, *hb)
            for t, tri in enumerate(mesh[3]):
                if mesh[2][tri[0]] == ROCK:
                    idx[uvkey([mesh[1][i] for i in tri])] = (hb, t, sorted(nb[t], key=str),
                                                             is_fringe(tile([mesh[1][i] for i in tri])))
        homes[name] = idx
    rows = []
    for bx, by in BLOCKS:
        mesh = read_live(bx, by)
        if mesh is None:
            continue
        verts, uvs, topos, tris = mesh
        cs, _nb = contacts(mesh, bx, by)
        for t, nbs in cs:
            ws = [(bx * 64 + verts[i][0], verts[i][1], verts[i][2] - by * 64) for i in tris[t]]
            c = [sum(p[k] for p in ws) / 3 for k in range(3)]
            name = min(MASSIFS, key=lambda m: math.dist((c[0], c[2]), MASSIFS[m][0]))
            cx, cz = MASSIFS[name][0]
            tl = tile([uvs[i] for i in tris[t]])
            home = homes[name].get(uvkey([uvs[i] for i in tris[t]]))
            rows.append({"block": [bx, by], "tri": t, "massif": name, "c": [round(c[0], 2), round(c[1], 2), round(c[2], 2)],
                         "bearing": round((math.degrees(math.atan2(c[2] - cz, c[0] - cx)) + 360) % 360, 1),
                         "course": round(max(p[1] for p in ws) - min(p[1] for p in ws), 2),
                         "ymin": round(min(p[1] for p in ws), 2),
                         "tile": list(tl), "fringe": is_fringe(tl),
                         "home": None if home is None else {"block": list(home[0]), "tri": home[1],
                                                           "nb": [x for x in home[2]], "fringe": home[3]},
                         "shot3": round(math.dist((c[0], c[2]), SHOT3), 1)})
    json.dump(rows, open(OUT, "w", encoding="utf-8"), indent=1)
    for name in MASSIFS:
        rs = [r for r in rows if r["massif"] == name]
        fr = sum(r["fringe"] for r in rs)
        print(f"\n{name}: {len(rs)} live rock-grass contact tris, fringe {fr} ({100 * fr / max(1, len(rs)):.0f}%); "
              f"home-matched {sum(r['home'] is not None for r in rs)}")
        print("  tiles:", Counter(f"r{r['tile'][0]}c{r['tile'][1]}" for r in rs).most_common(8))
        nf = [r for r in rs if not r["fringe"]]
        print(f"  NON-fringe contacts by HOME neighbour class: "
              f"{Counter(str(r['home']['nb']) if r['home'] else 'unmatched' for r in nf).most_common(6)}")
        print(f"  fringe contacts by HOME neighbour class: "
              f"{Counter(str(r['home']['nb']) if r['home'] else 'unmatched' for r in rs if r['fringe']).most_common(6)}")
    print("\nUaho contacts in bearing order (0 = east, 90 = north); * = non-fringe; d3 = distance to screenshot 3")
    for r in sorted((r for r in rows if r["massif"] == "uaho"), key=lambda r: r["bearing"]):
        print(f"  {'*' if not r['fringe'] else ' '} brg {r['bearing']:5.1f}  c ({r['c'][0]:.1f},{r['c'][2]:.1f}) "
              f"ymin {r['ymin']:.2f} course {r['course']:.2f}  tile r{r['tile'][0]}c{r['tile'][1]}  "
              f"home nb {r['home']['nb'] if r['home'] else '?'}  d3 {r['shot3']}")


if __name__ == "__main__" and "--edges" not in sys.argv:
    main()


# ---------------------------------------------------------------- per EDGE: where is the painted lawn line?
def contact_edges(mesh):
    """Rock-grass contact EDGES: [(rock tri, (vi, vj), grass tri)] -- the visible base line."""
    verts, uvs, topos, tris = mesh
    edges = defaultdict(list)
    for ti, tri in enumerate(tris):
        for i, j in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            k = tuple(sorted((tuple(round(x, 3) for x in verts[i]), tuple(round(x, 3) for x in verts[j]))))
            edges[k].append((ti, i, j))
    out = []
    for tl in edges.values():
        rk = [e for e in tl if topos[tris[e[0]][0]] == ROCK]
        gr = [e for e in tl if topos[tris[e[0]][0]] == GRASS]
        for r in rk:
            for g in gr:
                out.append((r[0], (r[1], r[2]), g[0]))
    return out


def lawn_line(mesh, rt, vij):
    """Each edge end's v measured from the rock tri's tile top, in tiles: 1.0 = the tile's lawn line (fringe row)."""
    verts, uvs, topos, tris = mesh
    row, _c = tile([uvs[i] for i in tris[rt]])
    return [round((uvs[i][1] - PV) / TV - row, 3) for i in vij]


def edge_home_nb(home_mesh, home_idx, live_uvs_tri, live_uvs_edge):
    """The donor's HOME neighbour across the same edge (matched by the rock tri's uv triple + the edge's uvs)."""
    hit = home_idx.get(uvkey(live_uvs_tri))
    if hit is None:
        return "unmatched"
    verts, uvs, topos, tris = home_mesh
    ht = hit[1]
    want = sorted((round(u, 5), round(v, 5)) for u, v in live_uvs_edge)
    tri = tris[ht]
    for i, j in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
        if sorted((round(uvs[i][0], 5), round(uvs[i][1], 5)) for i in (i, j)) == want:
            ka = tuple(sorted((tuple(round(x, 3) for x in verts[i]), tuple(round(x, 3) for x in verts[j]))))
            others = []
            for o, otri in enumerate(tris):
                if o == ht:
                    continue
                ks = {tuple(sorted((tuple(round(x, 3) for x in verts[a]), tuple(round(x, 3) for x in verts[b]))))
                      for a, b in ((otri[0], otri[1]), (otri[1], otri[2]), (otri[2], otri[0]))}
                if ka in ks:
                    others.append(topos[otri[0]])
            return others or [None]
    return "edge-unmatched"


def edge_census():
    # positive control: stock fringe contact edges -- where does stock put the lawn line?
    st = []
    for bx in range(24):
        for by in range(20):
            try:
                mesh = read_stock(bx, by)
            except Exception:
                continue
            for rt, vij, gt in contact_edges(mesh):
                if is_fringe(tile([mesh[1][i] for i in mesh[3][rt]])):
                    st.append(min(lawn_line(mesh, rt, vij)))
    lo = sum(x < 0.9 for x in st)
    print(f"STOCK fringe contact edges: {len(st)}; lower end's lawn-line v (1.0 = the painted fringe row) "
          f"p01 {sorted(st)[len(st) // 100]:.2f} p05 {sorted(st)[len(st) // 20]:.2f} p50 {sorted(st)[len(st) // 2]:.2f}; "
          f"edges with an end < 0.90: {lo} ({100 * lo / len(st):.1f}%)")
    homes = {}
    for name, (_c, dblocks) in MASSIFS.items():
        hb = dblocks[0]
        hm = read_stock(*hb)
        idx = {uvkey([hm[1][i] for i in tri]): (hb, t) for t, tri in enumerate(hm[3]) if hm[2][tri[0]] == ROCK}
        homes[name] = (hm, idx, dblocks)
    for name, (cxz, dblocks) in MASSIFS.items():
        rows = []
        for bx, by in BLOCKS:
            mesh = read_live(bx, by)
            if mesh is None:
                continue
            verts, uvs, topos, tris = mesh
            for rt, vij, gt in contact_edges(mesh):
                ws = [(bx * 64 + verts[i][0], verts[i][1], verts[i][2] - by * 64) for i in vij]
                mid = ((ws[0][0] + ws[1][0]) / 2, (ws[0][2] + ws[1][2]) / 2)
                if min(MASSIFS, key=lambda m: math.dist(mid, MASSIFS[m][0])) != name:
                    continue
                ll = lawn_line(mesh, rt, vij)
                hnb = "n/a"
                for hb in dblocks:
                    hm = read_stock(*hb)
                    hidx = {uvkey([hm[1][i] for i in tri]): (hb, t) for t, tri in enumerate(hm[3]) if hm[2][tri[0]] == ROCK}
                    hnb = edge_home_nb(hm, hidx, [uvs[i] for i in tris[rt]], [uvs[i] for i in vij])
                    if hnb not in ("unmatched", "edge-unmatched"):
                        break
                rows.append((ws, ll, hnb, rt, (bx, by)))
        bad = [r for r in rows if min(r[1]) < 0.9]
        L = sum(math.dist((r[0][0][0], r[0][0][2]), (r[0][1][0], r[0][1][2])) for r in rows)
        Lb = sum(math.dist((r[0][0][0], r[0][0][2]), (r[0][1][0], r[0][1][2])) for r in bad)
        print(f"\n{name}: {len(rows)} live contact edges ({L:.1f}u); an end off the lawn line (< 0.90): {len(bad)} "
              f"({Lb:.1f}u, {100 * Lb / max(L, 1e-9):.0f}% of length)")
        print(f"  HOME neighbour across the edge, lawn-line edges: {Counter(str(r[2]) for r in rows if min(r[1]) >= 0.9).most_common()}")
        print(f"  HOME neighbour across the edge, OFF-line edges:  {Counter(str(r[2]) for r in bad).most_common()}")
        for ws, ll, hnb, rt, b in sorted(bad, key=lambda r: r[0][0][0]):
            print(f"    {b} t{rt} ({ws[0][0]:.1f},{ws[0][2]:.1f},y{ws[0][1]:.2f})-({ws[1][0]:.1f},{ws[1][2]:.1f},y{ws[1][1]:.2f}) "
                  f"lawn-line v {ll} home nb {hnb}  d3 {math.dist(((ws[0][0] + ws[1][0]) / 2, (ws[0][2] + ws[1][2]) / 2), SHOT3):.1f}")


if __name__ == "__main__" and "--edges" in sys.argv:
    edge_census()
