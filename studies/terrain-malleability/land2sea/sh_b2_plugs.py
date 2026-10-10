"""ISLANDS WITH BUILDINGS, question 2 (2026-10-09): what does the building leave when it goes with its island?

sh_b1 found three real islands with a building: Daguerreo, the lagoon island at (553, -1127) and the corner island at
(0, 0). Every stock building plugs a hole (forms/object2_census.py): here, in the sheet of the island's land and the
water round it. For each island: the unit (land and own shore, `transplant._sink_unit`), its BUILDING (the Object and
falls/river/stream/riverjoint tris joined to the unit by shared vertices, traced transitively, with any land they
carry), and the holes of the sheet made of the unit's land and shore plus the kept water and land round it (Objects
and flows left out). A hole the building covers is a PLUG: its ring, its vertices' heights, which of its edges lie on
kept water (they become coast) and at what height, its plan area against the building's, and whether the plan
ear-clipper takes it. Also: the building's vertices below the waterline, and what else it welds to.
Writes out/sh_b2_plugs.json. Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_b2_plugs.py
"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))

SITES = [(425.098, -1020.0), (553.065, -1127.103), (9.909, -22.582)]
FLOW = ("falls", "river", "stream", "riverjoint")
WATER = ("sea1", "sea2", "sea3", "sea5", "sea4", "sea6", "sea4f")


def k3(v):
    return (round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4))


def kk(p):
    return (round(p[0], 4), round(p[1], 4), round(p[2], 4))


def area2(t):
    return 0.5 * abs((t[1][0][0] - t[0][0][0]) * (t[2][0][2] - t[0][0][2])
                     - (t[2][0][0] - t[0][0][0]) * (t[1][0][2] - t[0][0][2]))


def site(at, disc=1):
    from ff9mapkit.world import discmirror as DM, meshedit as ME, transplant as TR
    real = DM._real_parts(disc, "0_1")
    cache = {}

    def tris(b, p):
        if (b, p) not in cache:
            cache[(b, p)] = TR.world_tris(*b, p, disc=disc) if p in real.get(b, ()) else []
        return cache[(b, p)]

    def around(bs):
        return sorted({(b[0] + dx, b[1] + dy) for b in bs for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                       if (b[0] + dx, b[1] + dy) in real})
    _pts, land, island, shore, blocks = TR._sink_unit(at, real, tris, around, disc=disc, max_blocks=9)
    near = around(blocks)
    unit = list(land) + list(shore)
    uid = {id(t) for t in unit}
    ukeys = {k3(v) for t in unit for v in t}
    # the building: Object and flow tris joined to the unit, transitively, with any land they carry
    bparts = [(b, p, t) for b in near for p in ("object",) + FLOW for t in tris(b, p)]
    lparts = [(b, p, t) for b in near for p in TR.SINK_LAND_PARTS for t in tris(b, p) if id(t) not in uid]
    comps = ME.vertex_components([t for _b, _p, t in bparts + lparts])
    who = {id(t): (b, p) for b, p, t in bparts + lparts}
    keys = set(ukeys)
    building = []
    taken = set()
    grew = True
    while grew:
        grew = False
        for i, c in enumerate(comps):
            if i in taken:
                continue
            ck = {k3(v) for t in c for v in t}
            if ck & keys and any(who[id(t)][1] in ("object",) + FLOW for t in c):
                taken.add(i)
                building += c
                keys |= ck
                grew = True
    bid = {id(t) for t in building}
    bkeys = {k3(v) for t in building for v in t}
    parts = Counter(who[id(t)][1] for t in building)
    # what else the building welds to (kept tris, by part)
    kept_keys = {}
    for b in near:
        for p in real[b]:
            for t in tris(b, p):
                if id(t) in uid or id(t) in bid:
                    continue
                for v in t:
                    kept_keys.setdefault(k3(v), set()).add(p)
    bw = Counter()
    for k in bkeys:
        for p in kept_keys.get(k, ()):
            bw[p] += 1
    below = sorted({k for k in bkeys if k[1] < -1e-6})
    # the sheet: the unit plus kept water and land round it (no Objects, no flows); its holes the building covers
    sheet = unit + [t for b in near for p in real[b] if p in WATER + TR.SINK_LAND_PARTS for t in tris(b, p)
                    if id(t) not in uid and id(t) not in bid]
    cyc = ME.boundary_cycles(sheet)
    btile = {}
    for t in building:
        for ij in TR._tiles_touched(t) or {(math.floor(t[0][0][0] / 4.0), math.floor(t[0][0][2] / 4.0))}:
            btile.setdefault(ij, []).append(t)
    plugs = []
    for r in cyc:
        P = [(p[0], p[2]) for p in r]
        ar = 0.5 * sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(P, P[1:] + P[:1]))
        on_b = sum(1 for p in r if kk(p) in bkeys)
        if on_b < len(r) // 2:
            continue
        # which side each ring edge lies on: unit (land/shore) or kept water/land
        ek = Counter()
        side = []
        for t in sheet:
            ks = [k3(v) for v in t]
            for a in range(3):
                ek[(ks[a], ks[(a + 1) % 3])] += 1
        owner = {}
        for t in sheet:
            ks = [k3(v) for v in t]
            tag = "unit" if id(t) in uid else "kept"
            for a in range(3):
                owner.setdefault(tuple(sorted((ks[a], ks[(a + 1) % 3]))), tag)
        for a in range(len(r)):
            e = tuple(sorted((kk(r[a]), kk(r[(a + 1) % len(r)]))))
            side.append(owner.get(e, "?"))
        kept_edges = [(r[a], r[(a + 1) % len(r)]) for a in range(len(r)) if side[a] == "kept"]
        try:
            ear = ME.earclip(P if ar > 0 else P[::-1], quality=True)
            ear_ok = len(ear)
        except ValueError as e:
            ear_ok = f"refused: {e}"
        plugs.append({"verts": len(r), "signed_u2": round(ar, 2), "on_building": on_b,
                      "y": [round(min(p[1] for p in r), 4), round(max(p[1] for p in r), 4)],
                      "edges": dict(Counter(side)),
                      "kept_edge_y": sorted({round(p[1], 4) for e in kept_edges for p in e})[:6],
                      "earclip": ear_ok})
    out = {"at": at, "disc": disc, "unit_tris": len(unit), "shore_tris": len(shore),
           "building_tris": dict(parts), "building_plan_u2": round(sum(area2(t) for t in building), 2),
           "building_y": [round(min(v[0][1] for t in building for v in t), 3),
                          round(max(v[0][1] for t in building for v in t), 3)],
           "building_welds_kept": dict(bw), "building_below_waterline": below[:6], "n_below": len(below),
           "sheet_cycles": len(cyc), "plugs": plugs}
    return out


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    res = {}
    for at in SITES:
        for d in (1, 4):
            try:
                out = site(at, d)
            except ValueError as e:
                out = {"at": at, "disc": d, "refused": str(e)[:200]}
            res[f"{at[0]},{at[1]} d{d}"] = out
            print(json.dumps(out, default=str))
    (HERE / "out" / "sh_b2_plugs.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
