"""PREP for in-game experiment 11 (the disc-4 crescent ridge, D4-09), NO DEPLOY.

The disc-4 lane found ~53 narrow topo-49 ridges laid on unchanged walkable ground (disc4/out/rock_ribbons.json);
the cheapest probe is to stand beside one and try to walk across. For the ridge, this computes on DISC 4's live
effective ground (a live Disc4 override, where present, else stock; arealib):
  * a crossing line through the centroid perpendicular to the ridge's long axis, sampled every 0.5u
    (topograph, height, event) -- the walk's expected wall position is where topo 49 starts
  * side points A/B 7u either side, on-foot walkable, and a FACE-HOME point (open walkable ground with no event
    tile within 32u -- world_face probes walk ~30u in any direction)
  * a parallel line on side A (the "walkable alongside" control)

Rerun:  py studies/terrain-malleability/ingame/disc4_prep.py   -> ingame/out/disc4_prep.json
"""
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "gap_area_layer"))
import arealib as A                                  # noqa: E402
import numpy as np                                   # noqa: E402
from ff9mapkit.world.placement import WALK_OK        # noqa: E402

DISC = 4
RIBBONS = json.loads((HERE.parent / "disc4" / "out" / "rock_ribbons.json").read_text(encoding="utf-8"))
_LIVE = None
_M = {}


def meshes(bx, by):
    global _LIVE
    if (bx, by) in _M:
        return _M[(bx, by)]
    if _LIVE is None:
        _LIVE = A.live_cells()
    cf = _LIVE.get((DISC, bx, by), {})
    if cf:
        _pk, why, walk = A.live_walk_list(DISC, bx, by, cf)
    else:
        walk, why = [(n, k, "stock") for n, k in A.stock_walk_list(DISC, bx, by)], "stock"
    _M[(bx, by)] = (A.load_walk_arrays(walk), why)
    return _M[(bx, by)]


def ground(x, z):
    bx, by = int(math.floor(x / 64.0)), int(math.floor(-z / 64.0))
    ms, why = meshes(bx, by)
    lx, lz = x - bx * 64.0, z + by * 64.0
    for name, V, ids in ms:
        if V.size == 0:
            continue
        a, b, c = V[:, 0], V[:, 1], V[:, 2]
        u, v = b - a, c - a
        cy = u[:, 2] * v[:, 0] - u[:, 0] * v[:, 2]
        L = np.linalg.norm(np.cross(u, v), axis=1)
        L[L == 0] = 1.0
        d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
        ok = (cy / L > 0.1) & ~np.isin(ids, A.IDALL_SKIP) & (np.abs(d) >= 1e-12)
        dd = np.where(ok, d, 1.0)
        w0 = ((b[:, 2] - c[:, 2]) * (lx - c[:, 0]) + (c[:, 0] - b[:, 0]) * (lz - c[:, 2])) / dd
        w1 = ((c[:, 2] - a[:, 2]) * (lx - c[:, 0]) + (a[:, 0] - c[:, 0]) * (lz - c[:, 2])) / dd
        w2 = 1 - w0 - w1
        hit = np.nonzero(ok & (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9))[0]
        if hit.size == 0:
            continue
        t = hit[0]
        idv = int(ids[t])
        if idv == A.VETO:
            continue
        return {"y": round(float(w0[t] * a[t, 1] + w1[t] * b[t, 1] + w2[t] * c[t, 1]), 3), "topo": (idv & 0xFC) >> 2,
                "event": (idv & 0xC000) >> 14, "area": (idv & 0x3F00) >> 8, "part": name, "src": why}
    return {"y": None, "topo": None, "event": None, "part": "MISS", "src": why}


def walkable(gr):
    return gr["topo"] in WALK_OK and gr["event"] == 0


def plan(rib):
    cx, cz = rib["centroid_world"]
    ax = math.radians(rib["pc1_dir_deg"])
    perp = ax + math.pi / 2
    px, pz = math.cos(perp), math.sin(perp)
    line = []
    for k in range(-24, 25):
        s = k * 0.5
        g = ground(cx + s * px, cz + s * pz)
        line.append({"s": s, **g})
    blocked = [r["s"] for r in line if r["topo"] is not None and r["topo"] not in WALK_OK]
    sideA = (cx - 7 * px, cz - 7 * pz)
    sideB = (cx + 7 * px, cz + 7 * pz)
    # face home: walk back from side A along -perp until a 32u disc is all walkable/no-event (coarse 4u ring check)
    home = None
    for D in range(20, 90, 4):
        hx, hz = cx - D * px, cz - D * pz
        ok = walkable(ground(hx, hz))
        for r in (8, 16, 24, 32):
            if not ok:
                break
            for k in range(16):
                a = 2 * math.pi * k / 16
                if not walkable(ground(hx + r * math.cos(a), hz + r * math.sin(a))):
                    ok = False
                    break
        if ok:
            home = [round(hx, 2), round(hz, 2)]
            break
    alongside = [ground(sideA[0] + t * math.cos(ax), sideA[1] + t * math.sin(ax)) for t in range(-8, 9, 2)]
    return {"ribbon": rib, "perp_bearing_deg": round(math.degrees(perp) % 360, 2),
            "axis_bearing_deg": round(rib["pc1_dir_deg"] % 360, 2),
            "sideA": [round(sideA[0], 2), round(sideA[1], 2)], "sideB": [round(sideB[0], 2), round(sideB[1], 2)],
            "sideA_ground": ground(*sideA), "sideB_ground": ground(*sideB),
            "blocked_s": [min(blocked), max(blocked)] if blocked else None,
            "events_on_line": sum(1 for r in line if r["event"]), "line": line, "face_home": home,
            "alongside_walkable": all(walkable(g) for g in alongside)}


def main():
    res = {"ridges": [plan(RIBBONS[0]), plan(RIBBONS[1])]}
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "disc4_prep.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for p in res["ridges"]:
        print(p["ribbon"]["landmark"], "perp", p["perp_bearing_deg"], "blocked span", p["blocked_s"],
              "events on line", p["events_on_line"], "A", p["sideA"], p["sideA_ground"], "B", p["sideB"],
              p["sideB_ground"], "home", p["face_home"], "alongside ok", p["alongside_walkable"])
        print("   topo along the crossing:", [r["topo"] for r in p["line"]])


if __name__ == "__main__":
    main()
