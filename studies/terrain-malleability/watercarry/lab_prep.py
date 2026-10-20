"""`world-river` IN GAME, the predictions: every number lab_session.py asserts against, computed OFFLINE from the lab's
own written bytes (out/lab/FF9CustomMap-lab) by the engine's rules, before any launch. READ-ONLY on the install.

The rules (ingame/veh_prep.py's simulator, ported for a multi-cell lab): the ground query is the first registered
walk mesh with a passing hit (IDALL not skipped, geometric ny > 0.1, at or below the ray origin), the first passing
tri in buffer order; a walker or a boat probes the next XZ from its own y + 2.34375 (the boat's hull rides at the
water - 0.703), moves only onto its mask's topographs (foot = TransportControls row 0, the Blue Narciss = {53, 54,
57}), else tries 8 slide angles each side (+rotation first = bearing - k*11.25); a 10-slot cache of the last tris hit
is tested first, unfiltered (WMBlock.cs:145-183). A cell outside the lab binds its stock prefab, or the
SeaBlockPrefab's full-cell Sea4 (topo 57) on open ocean.

REGISTERED (tolerance 0.15 on heights, 1.5u on where a walk or a sail stops):
  R1 REGISTRATION: the player settles at each probe's predicted ground height -- the kit's lawn, the carried island,
     the carried bridge deck -- so the lab's files are what the engine serves.
  R2 A BANK HOLDS: a walk straight at the stream stops where the simulation stops it (the banks are skipped and the
     stream is not foot ground: THE BANK SKIP LAW at work), on built ground, never in the water.
  R3 THE BRIDGE CARRIES: a walk along the deck crosses the channel to the far bank.
  R4 THE BOAT SAILS IN: the Blue Narciss, spawned on the kit's open sea outside the cove, sails across the knit seam
     into the cove toward its beach and stops where the simulation stops it.
  R5 THE CLIFF TOPS HOLD AT THE JOINS: a walk along each join's cliff top, across the column, never drops (min y
     >= 2.5) and stops where the simulation stops it.
  Owner: the bay reads as stock; the river and the stream animate; both joins read as one cliff.
RUN:  py studies/terrain-malleability/watercarry/lab_prep.py   (writes out/lab/prep.json)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X, mesh as M, placement as P, river as R  # noqa: E402

LAB_NAME = "FF9CustomMap-lab"
LAB = HERE / "out" / "lab" / LAB_NAME
BUILD = json.loads((HERE / "out" / "lab" / "build.json").read_text(encoding="utf-8"))
DX, DZ = BUILD["offset_world"]                       # donor frame -> lab world (unwrapped)
WORLD_W = 1536.0


def _mask(l0, l1):
    return {t for t in range(64) if ((l0 >> (t - 32)) & 1 if t > 31 else (l1 >> t) & 1)}


WALK = _mask(1074815, 3640605951)                     # TransportControls row 0 (on foot)
BOAT = _mask(39845888, 0)                             # row 7, the Blue Narciss = {53, 54, 57}
SKIP = (4078, 4088, 2040)
VETO = 0x31EE
RAY_UP = 2.34375
SLICE_BOAT = -180 / 256.0
FOOT_STEP = 0.4375                                    # on-foot XZ per tick (walk)


def topo(idall):
    return (int(idall) & 0xFC) >> 2


def wrap_x(x):
    return x % WORLD_W


def to_lab(x, z):
    """A donor-frame point -> the lab world point the engine uses (x wrapped onto the torus)."""
    return wrap_x(x + DX), z + DZ


# --------------------------------------------------------------------------------------------- the meshes
_CELLS: dict = {}


def cell_meshes(bx, by):
    """[(name, V (T,3,3) block-local, ids)] in registration order: the lab's files where the lab writes, else the
    stock prefab's parts, else the SeaBlockPrefab's Sea4."""
    key = (bx % 24, by)
    if key in _CELLS:
        return _CELLS[key]
    rdir = LAB / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / f"r{by}"
    parts = {}
    files = list(rdir.glob(f"Block[[]{key[0]}[]][[]{by}[]] *.ff9mesh")) if rdir.is_dir() else []
    if files:
        for f in files:
            name = f.name.split("] ", 1)[1][:-len(".ff9mesh")]
            parts[name] = M.blockmesh_from_ff9mesh(f, disc=1, x=key[0], y=by, part=name.lower())
    else:
        own = X.block_parts(disc=1).get(key)
        if own:
            for p in own:
                if P.canonical_part(p):
                    parts[P.canonical_part(p)] = X.read_block(key[0], by, disc=1, part=p)
        else:
            parts["Sea4"] = X.read_block(12, 0, disc=1, part="sea4f")
    out = []
    for name, bm in P.build_meshlist(parts):
        V = np.asarray(bm.verts, dtype=float)
        T = np.asarray(bm.tris, dtype=int).reshape(-1, 3)
        ids = np.asarray([int(round(bm.tangents[t[0]][0])) for t in T], dtype=int)
        out.append((name, V[T] if len(T) else np.zeros((0, 3, 3)), ids))
    _CELLS[key] = out
    return out


def _hit(V, ids, lx, lz, origin_y, filtered=True, sel=None):
    if V.size == 0:
        return None
    a, b, c = V[:, 0], V[:, 1], V[:, 2]
    u, v = b - a, c - a
    cy = u[:, 2] * v[:, 0] - u[:, 0] * v[:, 2]
    L = np.sqrt((u[:, 1] * v[:, 2] - u[:, 2] * v[:, 1]) ** 2 + cy ** 2 + (u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]) ** 2)
    L[L == 0] = 1.0
    d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
    ok = np.abs(d) >= 1e-12
    if filtered:
        ok &= (cy / L > 0.1) & ~np.isin(ids, SKIP)
    if sel is not None:
        ok &= sel
    dd = np.where(ok, d, 1.0)
    w0 = ((b[:, 2] - c[:, 2]) * (lx - c[:, 0]) + (c[:, 0] - b[:, 0]) * (lz - c[:, 2])) / dd
    w1 = ((c[:, 2] - a[:, 2]) * (lx - c[:, 0]) + (a[:, 0] - c[:, 0]) * (lz - c[:, 2])) / dd
    hy = w0 * a[:, 1] + w1 * b[:, 1] + (1 - w0 - w1) * c[:, 1]
    inside = ok & (w0 >= -1e-9) & (w1 >= -1e-9) & (1 - w0 - w1 >= -1e-9)
    if origin_y is not None:
        inside &= hy <= origin_y + 1e-9
    hits = np.nonzero(inside)[0]
    if not hits.size:
        return None
    t = int(hits[0])
    return t, float(hy[t]), int(ids[t])


class Cache:
    """ff9.s_moveCHRCache (WMBlock.cs:145-183): the last 10 (cell, mesh, tri) hits, tested first, unfiltered."""

    def __init__(self):
        self.slots = []

    def test(self, cell, meshes, lx, lz, origin_y):
        for (c, mi, t) in reversed(self.slots):
            if c != cell:
                continue
            name, V, ids = meshes[mi]
            sel = np.zeros(len(ids), bool)
            sel[t] = True
            h = _hit(V, ids, lx, lz, origin_y, filtered=False, sel=sel)
            if h is not None and h[2] != VETO:
                return {"y": h[1], "id": h[2], "topo": topo(h[2]), "part": name}
        return None

    def push(self, cell, mi, t):
        self.slots = (self.slots + [(cell, mi, t)])[-10:]


def query(x, z, origin_y=None, cache=None):
    """The ground query at lab world (x, z) (x wrapped): sky cast when origin_y is None."""
    x = wrap_x(x)
    bx, by = int(math.floor(x / 64.0)), int(math.floor(-z / 64.0))
    ms = cell_meshes(bx, by)
    lx, lz = x - 64.0 * bx, z + 64.0 * by
    if cache is not None:
        h = cache.test((bx, by), ms, lx, lz, origin_y)
        if h:
            return h
    for mi, (name, V, ids) in enumerate(ms):
        h = _hit(V, ids, lx, lz, origin_y)
        if h is None or h[2] == VETO:
            continue
        if cache is not None:
            cache.push((bx, by), mi, h[0])
        return {"y": h[1], "id": h[2], "topo": topo(h[2]), "part": name}
    return None


def drive(x0, z0, bearing, dist, *, mask, step, y0, slice_y=0.0, ticks=None):
    """w_movementControl, straight ahead along ``bearing`` (deg, atan2(dz, dx)): per tick probe the next XZ from
    y + 2.34375, move onto a mask topograph or slide (8 angles each side, +rotation first), stop after 3 dead ticks
    or ``dist`` of progress along the bearing. Returns the trace and the progress where it ended."""
    cache = Cache()
    x, z, y = x0, z0, y0
    ux, uz = math.cos(math.radians(bearing)), math.sin(math.radians(bearing))
    trace, dead, best = [], 0, 0.0
    for t in range(ticks or int(dist / step * 3) + 60):
        moved = False
        for k in range(8):
            for sgn in ((1,) if k == 0 else (-1, 1)):
                ang = math.radians(bearing + sgn * k * 11.25)
                tx, tz = x + math.cos(ang) * step, z + math.sin(ang) * step
                h = query(tx, tz, origin_y=y + RAY_UP, cache=cache)
                if h is None or h["topo"] not in mask:
                    continue
                x, z, y = tx, tz, h["y"] + slice_y
                moved = True
                trace.append({"x": round(x, 3), "z": round(z, 3), "y": round(y, 3), "topo": h["topo"], "part": h["part"],
                              "slide": sgn * k})
                break
            if moved:
                break
        prog = (x - x0) * ux + (z - z0) * uz
        if moved and prog > best + 0.02:
            best, dead = prog, 0
        else:
            dead += 1
        if best >= dist or dead >= 6:
            break
    return {"progress": round(best, 2), "end": trace[-1] if trace else {"x": x0, "z": z0, "y": y0},
            "min_y": round(min([p["y"] for p in trace] + [y0]), 3), "steps": len(trace),
            "topos": sorted({p["topo"] for p in trace}), "reached": best >= dist}


# --------------------------------------------------------------------------------------------- the probes
def pca(pts):
    P_ = np.asarray(pts, dtype=float)
    c = P_.mean(axis=0)
    w, v = np.linalg.eigh(np.cov((P_ - c).T))
    return c, v[:, int(np.argmax(w))]


def point(name, dxz, extra=None):
    x, z = to_lab(*dxz)
    q = query(x, z)
    rec = {"name": name, "donor": [round(dxz[0], 2), round(dxz[1], 2)], "world": [round(x, 3), round(z, 3)],
           "y": None if q is None else round(q["y"], 3), "topo": None if q is None else q["topo"],
           "part": None if q is None else q["part"]}
    rec.update(extra or {})
    return rec


def walk(name, dxz, bearing, dist):
    x, z = to_lab(*dxz)
    q = query(x, z)
    sim = drive(x, z, bearing, dist, mask=WALK, step=FOOT_STEP, y0=q["y"] if q else 0.0)
    return {"name": name, "start": [round(x, 3), round(z, 3)], "start_y": None if q is None else round(q["y"], 3),
            "start_topo": None if q is None else q["topo"], "bearing_deg": round(bearing, 2), "dist": dist, "sim": sim}


def main():
    win = R.read_window(R.CLUSTER_C)
    f = R.build_fragment(win, R.CLUSTER_C)
    # R1: the kit's lawn (well inside the closing), the carried island, the carried bridge deck
    isl = [t for t in f.tris if t["part"] == "terrain" and t["topo"] == 0
           and math.hypot(*(t["P"].mean(axis=0)[[0, 2]] - np.array([1087.5, -1054.8]))) < 12]
    ic = min(isl, key=lambda t: math.hypot(*(t["P"].mean(axis=0)[[0, 2]] - np.array([1087.5, -1054.8]))))
    deck = [t for t in f.tris if t["part"] == "object" and t["idall"] not in SKIP]
    dc, axis = pca([p[[0, 2]] for t in deck for p in t["P"]])
    proj = [float(np.dot(p[[0, 2]] - dc, axis)) for t in deck for p in t["P"]]
    lo, hi = min(proj), max(proj)
    probes = [point("kit_lawn", (1105.0, -955.0)),
              point("island", tuple(ic["P"].mean(axis=0)[[0, 2]])),
              point("bridge_deck", tuple(dc))]
    # R3: along the deck's axis, from 5u before one end to 5u past the other
    a_end = dc + axis * (lo - 5.0)
    br_bearing = math.degrees(math.atan2(axis[1], axis[0]))
    bridge = walk("bridge", tuple(a_end), br_bearing, (hi - lo) + 10.0)
    # R2: straight at the stream from the kit lawn east of its north-south reach
    st = [t["P"].mean(axis=0)[[0, 2]] for t in f.tris if t["part"] == "stream"]
    near = min(st, key=lambda c: math.hypot(c[0] - 1040.0, c[1] + 965.0))
    loc = [c for c in st if math.hypot(*(c - near)) < 10.0]
    cc, cdir = pca(loc)
    perp = np.array([-cdir[1], cdir[0]])
    if perp[0] < 0:
        perp = -perp                                                   # toward the kit lawn east of the channel
    bank_start = cc + perp * 16.0
    bank = walk("bank", tuple(bank_start), math.degrees(math.atan2(-perp[1], -perp[0])), 22.0)
    # R5: along each join's cliff top, across its column (2-2.5u inland of the crest)
    (ce, be), (cw, bw) = f.joins["E"], f.joins["W"]
    join_e = walk("join_E", (ce[0] - 2.0, ce[2] + 10.0), -90.0, 20.0)
    w_from = np.array([1049.0, -1092.0])
    w_to = np.array([1034.0, -1083.0])
    join_w = walk("join_W", tuple(w_from), math.degrees(math.atan2(*(w_to - w_from)[::-1])), 18.0)
    # R4: the boat, from the kit's open sea outside the seam's middle, toward the cove's beach
    S = np.asarray([(p[0], p[2]) for p in f.seaward])
    mid = S[len(S) // 2]
    cove_c = np.asarray([t["P"].mean(axis=0)[[0, 2]] for t in f.tris if t["part"] in R.SEA_PARTS]).mean(axis=0)
    out_dir = (mid - cove_c) / np.linalg.norm(mid - cove_c)
    boat_start = mid + out_dir * 14.0
    beach = [t["P"].mean(axis=0)[[0, 2]] for t in f.tris if t["part"] == "beach1"]
    target = min(beach, key=lambda c: abs(c[0] - boat_start[0]) + 0.2 * abs(c[1] - boat_start[1]) * 0
                 if c[1] > cove_c[1] else 1e9)
    bx_, bz_ = to_lab(*boat_start)
    q0 = query(bx_, bz_)
    b_bearing = math.degrees(math.atan2(target[1] - boat_start[1], target[0] - boat_start[0]))
    boat = {"start": [round(bx_, 3), round(bz_, 3)], "start_topo": None if q0 is None else q0["topo"],
            "target_beach": list(map(lambda v: round(float(v), 2), to_lab(*target))), "bearing_deg": round(b_bearing, 2),
            "sim": drive(bx_, bz_, b_bearing, float(np.linalg.norm(target - boat_start)) + 10.0, mask=BOAT,
                         step=0.9375, y0=(q0["y"] if q0 else 0.0) + SLICE_BOAT, slice_y=SLICE_BOAT)}
    # VIEWS: homes on the kit's lawn, each facing what it shows
    def view(name, home, look):
        h = to_lab(*home)
        lk = to_lab(*look)
        q = query(*h)
        return {"name": name, "home": [round(h[0], 3), round(h[1], 3)], "ground_y": None if q is None else round(q["y"], 3),
                "bearing_deg": round(math.degrees(math.atan2(lk[1] - h[1], lk[0] - h[0])), 2)}
    views = [view("bay", (1110.0, -985.0), (1075.0, -1045.0)),
             view("river", (1062.0, -940.0), (1030.0, -960.0)),
             view("join_E", (1142.0, -1016.0), (1139.0, -1040.0)),
             view("join_W", (1052.0, -1093.0), (1030.0, -1075.0)),
             # the channel is ~2.8u below the lawn, so from the lawn views the low camera sees only its banks: these
             # two put the water in the near field (the deck up the north-south reach; the source end down the
             # east-west reach, which also shows decision 3's zip to lawn)
             view("channel_deck", tuple(dc), (1034.0, -923.0)),
             view("source", (1136.0, -915.0), (1060.0, -915.0))]
    out = {"lab": str(LAB), "offset_world": [DX, DZ], "probes": probes, "walks": [bank, bridge, join_e, join_w],
           "boat": boat, "views": views,
           "deck": {"centre": list(map(float, to_lab(*dc))), "length": round(hi - lo, 2), "tris": len(deck)}}
    (HERE / "out" / "lab" / "prep.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
