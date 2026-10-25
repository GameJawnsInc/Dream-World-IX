#!/usr/bin/env python3
"""Walkmesh-connectivity pass over the census's PLAYER-MOVING interactions: does the interaction connect two
walkmesh components that are NOT connected on foot (so a guest who cannot use it is stranded / must warp),
or is it a shortcut inside one component? READ-ONLY: reads each field's stock .bgi from the install
(extract.stock_walkmesh -> the existing field index; refuses to run if that index would have to be BUILT,
because building writes a cache file into StreamingAssets).

Usage: py walkmesh_pass.py full_v3.json wm_v1.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

import interaction_census as C           # pins + asserts the worktree kit
from ff9mapkit import extract
from ff9mapkit.eventscan import _region_points, _zone_quad

IDX = Path(r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/StreamingAssets/.ff9mapkit-field-index.json")
assert IDX.exists(), "field index missing -- building it would WRITE into the install; aborting"

MOVERS = {"ladder-navigable", "ladder-auto", "jump", "carry-loop", "walk", "teleport"}


def zone_of(fld, ei):
    for f in fld.eb.entry(ei).funcs:
        for ins in fld.instrs(ei, f.tag):
            if ins.op == 0x29:
                pts = _region_points(ins)
                if len(pts) >= 3:
                    return _zone_quad(pts)
    return None


def npc_pos(fld, ei):
    f0 = fld.eb.entry(ei).func_by_tag(0)
    if not f0:
        return None
    for ins in fld.instrs(ei, 0):
        if ins.op in (0x1D, 0xA1) and len(ins.args) >= 2 and not any(ins.arg_is_expr[:2]):
            a = ins.args
            if ins.op == 0x1D:
                return (C.s16(a[0]), C.s16(a[1]))
            if len(a) >= 3 and not ins.arg_is_expr[2]:
                return (C.s16(a[0]), C.s16(a[2]))
    return None


def player_walkable(t):
    """The engine's player-crossing rule (WalkMesh.cs:1145-1170 / FieldMapActorController.cs:1270): a
    neighbour is enterable only if ACTIVE (triFlags & 1) and not CPC-restricted ((triFlags >> 8) & 0x80
    under the default attributeMask 255). Static: runtime EnablePathTriangle toggles are invisible."""
    return (t.tri_flags & 1) and not ((t.tri_flags >> 8) & 0x80)


def player_components(wm):
    from collections import deque
    seen, comps = set(), []
    for s0 in range(len(wm.tris)):
        if s0 in seen:
            continue
        comp, q = [], deque([s0])
        while q:
            t = q.popleft()
            if t in seen:
                continue
            seen.add(t)
            comp.append(t)
            if not player_walkable(wm.tris[t]):
                continue                  # a blocked tri is its own island (you can stand on it only by script)
            for n in wm.tris[t].nbr:
                if 0 <= n < len(wm.tris) and n not in seen and player_walkable(wm.tris[n]):
                    q.append(n)
        comps.append(comp)
    return comps


def comps_at(wm, comp_of, x, z, r=0):
    out = set()
    pts = [(x, z)] if r == 0 else [(x + dx, z + dz) for dx in (-r, 0, r) for dz in (-r, 0, r)]
    for (px, pz) in pts:
        for t in wm.tris_at(px, pz):
            if player_walkable(wm.tris[t]):
                out.add(comp_of[t])
    return out


def main(inp, outp):
    d = json.load(open(inp, encoding="utf-8"))
    rows = [r for r in d["rows"] if r["loco"] in MOVERS and r["root"] in ("QUAD", "TREAD-POLL", "NPC")]
    bundle = C.EventBundle()
    cache = {}
    res = []
    for r in rows:
        fid = r["fid"]
        if fid not in cache:
            try:
                wm = extract.stock_walkmesh(fid)
                comps = player_components(wm)
                comp_of = {}
                for ci, cl in enumerate(comps):
                    for t in cl:
                        comp_of[t] = ci
                eb = C.EbScript.from_bytes(bundle.eb_for_id(fid))
                cache[fid] = (wm, comp_of, len(comps), C.Field(fid, eb))
            except Exception as ex:
                cache[fid] = ex
        ent = cache[fid]
        if isinstance(ent, Exception):
            res.append({**_k(r), "wm": f"no-bgi:{type(ent).__name__}"}); continue
        wm, comp_of, ncomp, fld = ent
        if r["root"] == "NPC":
            p = npc_pos(fld, r["entry"])
            center = p
            zone = None
        else:
            zone = zone_of(fld, r["entry"])
            center = (sum(p[0] for p in zone) / len(zone), sum(p[1] for p in zone) / len(zone)) if zone else None
        lands = [(l[1], l[3]) for l in r["landings"] if l[1] is not None and l[3] is not None]
        if center is None or not lands:
            res.append({**_k(r), "wm": "no-geom", "ncomp": ncomp}); continue
        cx, cz = center
        wv = wm.world_verts()

        def comp_y(x, z, y):
            """component of the WALKABLE tri at (x,z) whose height is nearest y (y None -> all walkable)."""
            best = None
            for t in wm.tris_at(x, z):
                tri = wm.tris[t]
                if not player_walkable(tri):
                    continue
                h = sum(wv[v][1] for v in tri.vtx) / 3.0
                err = 0 if y is None else abs(h - y)
                if best is None or err < best[0]:
                    best = (err, comp_of[t], tri.floor_ndx)
            if best is None or (y is not None and best[0] > 250):
                return None
            return best[1:]

        touched, floors = set(), set()
        zc = set()
        for (zx, zz) in ([(cx, cz)] + [tuple(p) for p in (zone or [])]):
            for t in wm.tris_at(zx, zz):
                if player_walkable(wm.tris[t]):
                    zc.add(comp_of[t]); floors.add(wm.tris[t].floor_ndx)
        lands3 = [(l[1], l[2], l[3]) for l in r["landings"] if l[1] is not None and l[3] is not None]
        land_comps = []
        for (x, y, z) in lands3:
            cy = comp_y(x, z, y)
            if cy:
                land_comps.append(cy[0]); floors.add(cy[1])
        touched = set(land_comps) | zc
        far = max(lands, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cz) ** 2)
        dist = ((far[0] - cx) ** 2 + (far[1] - cz) ** 2) ** 0.5
        if not land_comps:
            verdict = "off-mesh"
        elif len(set(land_comps) | zc) >= 2 and not (set(land_comps) <= zc and len(zc) >= 2 and len(set(land_comps)) == 1):
            verdict = "LINKS-COMPONENTS"
        else:
            verdict = "intra-component"
        res.append({**_k(r), "wm": verdict, "ncomp": ncomp, "center": [round(cx), round(cz)], "far": list(far),
                    "dist": round(dist), "zone_comps": sorted(zc), "landing_comps": land_comps,
                    "floors": sorted(floors)})
    json.dump(res, open(outp, "w", encoding="utf-8"), indent=1)
    by = Counter((x["loco"], x["class"], x["wm"]) for x in res)
    for k, v in sorted(by.items(), key=lambda kv: (kv[0][0], -kv[1])):
        print(f"{k[0]:18s} {k[1]:18s} {k[2]:16s} {v}")
    print("TOTAL by verdict:", Counter(x["wm"] for x in res))


def _k(r):
    return {k: r[k] for k in ("fid", "name", "root", "entry", "class", "loco", "reasons", "gate")}


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
