"""R1 dry run: cluster C's river ENSEMBLE (ensemble.py) seated verbatim into a kit grass bench, as a canopy is seated.

Nothing is deployed and no game is touched. The ensemble (Stream + RiverJoint parts and the 188 topo-62 banks welded
to them, bytes verbatim: positions, UVs, normals, IDALLs) is translated onto a minted grass bench, levelled so its
LAWN-side rim sits at the bench lawn, and:
  1. HOLE   -- bench tris with a corner inside the ensemble's outer ring, or within CLEAR of it, drop (all must be the
              bench's plain grass, topo 0);
  2. ZIP    -- the hole ring zips to the ensemble's outer ring with the kit's own minimal-chord DP (interior._zip_dp),
              the grass side on the kept grass's exact floats (THE EXACT-WELD LAW);
  3. GATES  -- cracks: no once-edge the bench did not already have; the zip envelope (rise <= 2.34, chord < 9u, ny);
              the ground-query census over the ensemble (registration order Terrain, Stream, RiverJoint; skipped
              IDALLs and steep tris pass through, as the engine) against the DONOR's own census at the same relative
              points: no INTRODUCED misses; skip parity (every bank keeps its IDALL).
The mouth (the ensemble's 20.6u SEA edge) is zipped to lawn here too -- a river ending against grass, the stump THE
STANDALONE-WATER CLOSURE forbids. It is REPORTED as the open interface, not passed: R1's real mouth needs a coast.
RUN:  py studies/terrain-malleability/watercarry/seat_dryrun.py    (writes out/seat.json + out/seat_plan.png)
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X, interior as IN, placement as P  # noqa: E402
from ff9mapkit.world.island import build_landmass  # noqa: E402
import ensemble as E  # noqa: E402

BENCH_C, BENCH_R, SEED = (1380.0, -150.0), 90.0, 42
CLEAR = 2.5
LAWN_Y = 3.2
APRON = "--no-apron" not in sys.argv


def unit():
    """The ensemble tris (dicts: part, P world, uv, idall, topo) and its outer ring classes, from the stock bytes."""
    bp = X.block_parts(disc=1)
    allt = []
    for b in E.NEIGH:
        for part in ("terrain",) + E.WATER + E.SEA + ("object",):
            if part in bp.get(b, ()):
                allt += tris_uv(*b, part)
    water = [t for t in allt if t["part"] in E.WATER and t["blk"] in E.UNIT_BLOCKS]
    keys = {IN.kk3(p) for t in water for p in t["P"]}
    # the banks (topo 62) AND the Terrain's own water tris (48/50/51: the channel markers -- one plugs the source end,
    # IDALL 4044 at (17,14)), welded to the parts, transitively
    left = {id(t): t for t in allt if t["part"] == "terrain" and t["topo"] in (62, 48, 50, 51)
            and t["blk"] in E.UNIT_BLOCKS}
    # ... and the river's CROSSING: the Object tris welded to it (at (16,14), a 40-tri bridge -- a walkable topo-52 deck
    # on skipped 4078 sides); the transitive weld never reaches the separate 76-tri structure to its east
    left.update({id(t): t for t in allt if t["part"] == "object" and t["blk"] in E.UNIT_BLOCKS})
    banks, changed = [], True
    while changed:
        changed = False
        for k, t in list(left.items()):
            if any(IN.kk3(p) in keys for p in t["P"]):
                banks.append(t)
                del left[k]
                keys |= {IN.kk3(p) for p in t["P"]}
                changed = True
    return water, banks, allt


def tris_uv(bx, by, part):
    try:
        bm = X.read_block(bx, by, disc=1, part=part)
    except Exception:                                                           # noqa: BLE001
        return []
    V = np.asarray(bm.verts, dtype=float) + np.array([64.0 * bx, 0.0, -64.0 * by])
    U = np.asarray(bm.chan_arrays[X.CH_UV], dtype=float)
    tan = bm.chan_arrays[X.CH_TAN]
    out = []
    for t in bm.tris:
        idall = int(round(tan[t[0]][0]))
        out.append({"blk": (bx, by), "part": part, "P": V[t], "uv": U[t], "idall": idall,
                    "topo": X.decode_id(idall)["topograph"]})
    return out


def edge_keys(P3):
    return [tuple(sorted((IN.kk3(P3[a]), IN.kk3(P3[b])))) for a, b in ((0, 1), (1, 2), (2, 0))]


def ground(meshes, x, z):
    """The engine's ground query: the FIRST mesh (registration order) with a passing hit, the first passing tri in it.
    Passing: IDALL not skipped, geometric ny > 0.1, the vertical line through (x, z) inside. -> (y, topo) or None."""
    for tris in meshes:
        for t in tris:
            if P.ground_query_skips(t["idall"]):
                continue
            a, b, c = t["P"]
            n = np.cross(b - a, c - a)
            ln = float(np.linalg.norm(n))
            if ln < 1e-12 or n[1] / ln <= 0.1:
                continue
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
            l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
            if l1 >= -1e-9 and l2 >= -1e-9 and 1 - l1 - l2 >= -1e-9:
                return float(l1 * a[1] + l2 * b[1] + (1 - l1 - l2) * c[1]), t["topo"]
    return None


def main():
    water, banks, allt = unit()
    U = water + banks
    # the outer ring + its classes (from ensemble.py's rule, on the unit as built here)
    ec = Counter(e for t in U for e in edge_keys(t["P"]))
    once = {e for e, n in ec.items() if n == 1}
    uid = {id(t) for t in U}
    cls = {}
    for t in allt:
        if id(t) in uid:
            continue
        for e in edge_keys(t["P"]):
            if e in once and e not in cls:
                cls[e] = ("SEA" if t["part"] in E.SEA else
                          "ROCK" if t["part"] in ("terrain", "object") and t["topo"] in E.ROCKY else "LAWN")
    lawn_y = [k[1] for e, c in cls.items() if c == "LAWN" for k in e]
    allP = np.concatenate([t["P"] for t in U])
    cx = (allP[:, 0].min() + allP[:, 0].max()) / 2
    cz = (allP[:, 2].min() + allP[:, 2].max()) / 2
    shift = np.array([BENCH_C[0] - cx, LAWN_Y - float(np.median(lawn_y)), BENCH_C[1] - cz])
    for t in U:
        t["Pw"] = t["P"] + shift
    # outer ring in the SEATED frame, keyed on the carried floats
    c_float, ec2 = {}, Counter()
    for t in U:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ka, kb = IN.kk3(t["Pw"][a]), IN.kk3(t["Pw"][b])
            c_float.setdefault(ka, tuple(t["Pw"][a]))
            c_float.setdefault(kb, tuple(t["Pw"][b]))
            ec2[tuple(sorted((ka, kb)))] += 1
    rings = IN.chain_rings([e for e, n in ec2.items() if n == 1], "ensemble rim")
    rings.sort(key=lambda r: -abs(IN.signed_area(r)))
    outer = rings[0]
    poly = [(c_float[k][0], c_float[k][2]) for k in outer]
    # the bench
    built = build_landmass(center=BENCH_C, base_radius=BENCH_R, seed=SEED, lobes=1, n_patches=0, ground="grass")
    bench = []
    for (bx, by), bm in built["blocks"].items():
        bench += [dict(t, Pw=np.array(t["P"])) for t in _bm_tris(bm, bx, by)]
    apron = {"applied": False}
    if APRON:
        apron = apply_apron(bench, U, cls, outer, c_float, shift)
    b_once = {e for e, n in Counter(e for t in bench for e in edge_keys(t["Pw"])).items() if n == 1}
    drop = [t for t in bench if any(IN.pip(p[0], p[2], poly) or IN.near_poly(p[0], p[2], poly, CLEAR) for p in t["Pw"])]
    did = {id(t) for t in drop}
    kept = [t for t in bench if id(t) not in did]
    drop_topos = Counter(t["topo"] for t in drop)
    k_ec = Counter(e for t in kept for e in edge_keys(t["Pw"]))
    d_edges = {e for t in drop for e in edge_keys(t["Pw"])}
    hole_rings = IN.chain_rings([e for e, n in k_ec.items() if n == 1 and e in d_edges], "hole")
    h_float = {}
    for t in kept:
        for p in t["Pw"]:
            h_float.setdefault(IN.kk3(p), tuple(p))
    hole = max(hole_rings, key=lambda r: abs(IN.signed_area(r)))
    rim = list(outer)
    if IN.signed_area(hole) * IN.signed_area(rim) < 0:
        rim.reverse()
    H, R, zip_tris = IN._zip_dp(hole, rim, lambda k: c_float[k], h_float)
    zt = [{"Pw": np.array([list(p) for p in z]), "idall": int(X.encode_id(topograph=0)), "topo": 0, "part": "zip"}
          for z in zip_tris]
    # gates
    asm = kept + [t for t in U if t["part"] == "terrain"] + zt
    a_once = {e for e, n in Counter(e for t in asm + [t for t in U if t["part"] != "terrain"]
                                    for e in edge_keys(t["Pw"])).items() if n == 1}
    new_once = a_once - b_once
    chord = max(math.dist(z[a][::2], z[b][::2]) for z in zip_tris for a, b in ((0, 1), (1, 2), (2, 0)))
    rise = max(max(p[1] for p in z) - min(p[1] for p in z) for z in zip_tris)
    nys = []
    for z in zip_tris:
        a, b, c = (np.asarray(p, dtype=float) for p in z)
        n = np.cross(b - a, c - a)
        nys.append(abs(float(n[1])) / (float(np.linalg.norm(n)) or 1.0))
    # census: seated vs donor at the same relative points
    seated = [[t for t in U if t["part"] == "object"], [t for t in asm], [t for t in U if t["part"] == "stream"],
              [t for t in U if t["part"] == "riverjoint"]]
    for m in seated:
        for t in m:
            t.setdefault("P", t["Pw"])
    seated = [[dict(t, P=t["Pw"]) for t in m] for m in seated]
    donor = [[t for t in allt if t["part"] in ("object",)], [t for t in allt if t["part"] == "terrain"],
             [t for t in allt if t["part"] == "beach1"], [t for t in allt if t["part"] == "stream"],
             [t for t in allt if t["part"] == "river"], [t for t in allt if t["part"] == "riverjoint"],
             [t for t in allt if t["part"] in E.SEA and t["part"] != "beach1"]]
    xs = np.arange(allP[:, 0].min() + 0.25, allP[:, 0].max(), 1.0)
    zs = np.arange(allP[:, 2].min() + 0.25, allP[:, 2].max(), 1.0)
    miss_s = miss_d = introduced = water_hits = 0
    for x in xs:
        for z in zs:
            if not IN.pip(x + shift[0], z + shift[2], poly):
                continue
            gd = ground(donor, x, z)
            gs = ground(seated, x + shift[0], z + shift[2])
            miss_d += gd is None
            miss_s += gs is None
            introduced += gs is None and gd is not None
            water_hits += gs is not None and gs[1] in (48, 51)
    cls_pts = [((e[0][0] + e[1][0]) / 2 + shift[0], (e[0][2] + e[1][2]) / 2 + shift[2], c) for e, c in cls.items()]

    def near_cls(x, z):
        return min(cls_pts, key=lambda q: (q[0] - x) ** 2 + (q[1] - z) ** 2)[2]
    where = {"zip_rise_or_steep": Counter(), "new_once": Counter(), "introduced_miss": Counter()}
    sea_mid = [(q[0], q[1]) for q in cls_pts if q[2] == "SEA"]

    def to_mouth(x, z):
        return round(min(math.hypot(x - a, z - b) for a, b in sea_mid), 1)
    detail = {"zip_rise_or_steep": [], "new_once": [], "introduced_miss": []}
    for z_, ny in zip(zip_tris, nys):
        if max(q[1] for q in z_) - min(q[1] for q in z_) > 2.34 or ny < 0.5:
            cxz = (sum(q[0] for q in z_) / 3, sum(q[2] for q in z_) / 3)
            where["zip_rise_or_steep"][near_cls(*cxz)] += 1
            detail["zip_rise_or_steep"].append(to_mouth(*cxz))
    for e in new_once:
        where["new_once"][near_cls((e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2)] += 1
        detail["new_once"].append(to_mouth((e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2))
    for x in xs:
        for z in zs:
            if IN.pip(x + shift[0], z + shift[2], poly) and ground(seated, x + shift[0], z + shift[2]) is None                     and ground(donor, x, z) is not None:
                where["introduced_miss"][near_cls(x + shift[0], z + shift[2])] += 1
                detail["introduced_miss"].append(to_mouth(x + shift[0], z + shift[2]))
    skip_pairs = [(t["idall"], t["idall"]) for t in banks]
    sea_len = sum(math.dist(e[0], e[1]) for e, c in cls.items() if c == "SEA")
    if apron["applied"]:
        apron["slope_max"] = apron_slope(kept)
        apron["slope_ok"] = bool(apron["slope_max"] <= IN.MTN_APRON_SLOPE)
    rep = {"apron": apron, "unit": {"water_tris": len(water), "bank_tris": sum(t["part"] == "terrain" for t in banks),
                    "bridge_tris": sum(t["part"] == "object" for t in banks), "rings": len(rings),
                    "outer_ring_pts": len(outer), "shift": [round(float(v), 2) for v in shift]},
           "bench": {"center": BENCH_C, "radius": BENCH_R, "tris": len(bench)},
           "hole": {"dropped": len(drop), "dropped_topos": dict(drop_topos), "hole_rings": len(hole_rings)},
           "zip": {"tris": len(zip_tris), "max_chord": round(chord, 2), "max_rise": round(rise, 2),
                   "ny_min": round(min(nys), 3)},
           "gates": {"new_once_edges": len(new_once),
                     "census": {"donor_miss": miss_d, "seated_miss": miss_s, "introduced": introduced,
                                "water_hits": water_hits},
                     "skip_parity": P.skip_parity_gate(skip_pairs, label="ensemble")["flipped"],
                     "zip_rise_ok": bool(rise <= 2.34), "zip_chord_ok": bool(chord < 9.0)},
           "failures_by_nearest_boundary": {k: dict(v) for k, v in where.items()},
           "failure_distance_to_mouth": {k: sorted(v) for k, v in detail.items()},
           "open_interface": {"mouth_SEA_len": round(sea_len, 1),
                              "status": "zipped to lawn here: a stump -- R1 needs a coast splice"}}
    print(json.dumps(rep, indent=1, default=float))
    (HERE / "out" / ("seat.json" if APRON else "seat_noapron.json")).write_text(json.dumps(rep, indent=1, default=float), encoding="utf-8")
    plan(kept, U, zt, poly, HERE / "out" / ("seat_plan.png" if APRON else "seat_plan_noapron.png"))


def apply_apron(bench, U, cls, outer, c_float, shift):
    """world-mountain's APRON (``interior.carve_mountain``'s ``ground_lift``), ported: a pure-Y lift of the bench's
    plain grass toward the ensemble's rim heights -- IDW over the rim nodes within ``MTN_GBLEND``, faded by
    (1 - d/gblend)^2, dying before the coast band (dnp < 2.5 + 3) -- computed once per POSITION and applied to every
    coincident entry (the weld-safe lift). Rim nodes: the LAWN and ROCK ring only. A mouth node is left out: on a
    bench the mouth has no sea, and pulling the lawn down to sea level there would dig a bowl stock never shows."""
    gblend = IN.MTN_GBLEND
    d2s = {}                                                   # donor key -> seated key, vertex by vertex
    for t in U:
        for i in range(3):
            d2s[IN.kk3(t["P"][i])] = IN.kk3(t["Pw"][i])
    sea_v = {d2s[k] for e, c in cls.items() if c == "SEA" for k in e}
    nodes = [(c_float[k][0], c_float[k][2], c_float[k][1]) for k in outer if k not in sea_v]
    nonplain = np.array([[p[0], p[2]] for t in bench if t["topo"] != 0 for p in t["Pw"]] or [[1e9, 1e9]])
    lift, done = {}, set()
    for t in bench:
        if t["topo"] != 0:
            continue
        for p in t["Pw"]:
            k = IN.kk3(p)
            if k in done:
                continue
            done.add(k)
            wsum = hsum = 0.0
            dmin2 = 1e18
            for nx, nz, hy in nodes:
                dd2 = (p[0] - nx) ** 2 + (p[2] - nz) ** 2
                dmin2 = min(dmin2, dd2)
                if dd2 > gblend * gblend:
                    continue
                w = 1.0 / (dd2 + 0.04)
                wsum += w
                hsum += w * hy
            if wsum <= 0.0 or dmin2 >= gblend * gblend:
                continue
            W = (1.0 - math.sqrt(dmin2) / gblend) ** 2
            dnp = float(np.sqrt(((nonplain - np.array([p[0], p[2]])) ** 2).sum(axis=1).min()))
            pt = max(0.0, min(1.0, (dnp - 2.5) / 3.0))
            lf = pt * W * (hsum / wsum - p[1])
            if abs(lf) > 1e-6:
                lift[k] = lf
    for t in bench:                                            # by POSITION: every coincident entry moves together
        for i in range(3):
            k = IN.kk3(t["Pw"][i])
            if k in lift:
                t["Pw"][i] = t["Pw"][i] + np.array([0.0, lift[k], 0.0])
                t["lifted"] = True
    return {"applied": True, "nodes": len(nodes), "lifted_positions": len(lift),
            "max_lift": round(max((abs(v) for v in lift.values()), default=0.0), 2)}


def apron_slope(kept):
    """The steepest KEPT lifted grass tri, in degrees (world-mountain's MTN_APRON_SLOPE gate)."""
    slope = 0.0
    for t in kept:
        if not t.get("lifted"):
            continue
        a, b, c = t["Pw"]
        n = np.cross(b - a, c - a)
        ln = float(np.linalg.norm(n)) or 1.0
        slope = max(slope, math.degrees(math.acos(max(-1.0, min(1.0, abs(float(n[1])) / ln)))))
    return round(slope, 1)


def _bm_tris(bm, bx, by):
    V = np.asarray(bm.chan_arrays[X.CH_POS], dtype=float) + np.array([64.0 * bx, 0.0, -64.0 * by])
    tan = bm.chan_arrays[X.CH_TAN]
    out = []
    for t in bm.tris:
        idall = int(round(tan[t[0]][0]))
        out.append({"blk": (bx, by), "part": "terrain", "P": V[t], "idall": idall,
                    "topo": X.decode_id(idall)["topograph"]})
    return out


def plan(kept, U, zt, poly, path):
    """A top-down eye: kept grass green, banks brown, water blue, the zip yellow, the ring outline red."""
    from PIL import Image, ImageDraw
    allx = [p[0] for t in kept + U + zt for p in t["Pw"]]
    allz = [p[2] for t in kept + U + zt for p in t["Pw"]]
    x0, z1 = min(allx), max(allz)
    s = 4.0
    W, H = int((max(allx) - x0) * s) + 4, int((z1 - min(allz)) * s) + 4
    im = Image.new("RGB", (W, H), (40, 60, 90))
    d = ImageDraw.Draw(im)

    def xy(p):
        return ((p[0] - x0) * s + 2, (z1 - p[2]) * s + 2)
    for t, col in ([(t, (70, 120, 50)) for t in kept] + [(t, (110, 80, 50)) for t in U if t["part"] == "terrain"]
                   + [(t, (60, 140, 220)) for t in U if t["part"] not in ("terrain", "object")]
                   + [(t, (150, 150, 150)) for t in U if t["part"] == "object"] + [(t, (230, 210, 60)) for t in zt]):
        d.polygon([xy(p) for p in t["Pw"]], fill=col)
    d.line([xy((x, 0, z)) for x, z in poly + poly[:1]], fill=(220, 40, 40), width=1)
    im.save(path)


if __name__ == "__main__":
    main()
